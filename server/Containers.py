"""Unified Pydantic model for container unloading workflows.

Copy ContainerCreate into the existing server/Models.py file.
Do not replace the entire Models.py: it may contain other models.
"""
from datetime import datetime
from typing import Any
import os
import base64
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote
from typing import Callable, Any
from pydantic import BaseModel, Field
import requests
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field,ConfigDict

AIRTABLE = 'https://api.airtable.com/v0'
FILE_API = 'https://content.airtable.com/v0'
ALLOWED_WAREHOUSES = {'100', '200', '300', '600'}
MAX_IMAGE_SIZE = 10 * 1024 * 1024

class ContainerCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    container_number: str | None = Field(default=None, alias="מספר מכולה")
    start_time: datetime | None = Field(default=None, alias="שעת התחלה")
    end_time: datetime | None = Field(default=None, alias="שעת סיום")
    status: str | None = Field(default=None, alias="סטטוס")
    attachments: list[dict[str, Any]] | None = Field(default=None, alias="Attachments")
    supplier: list[str] | None = Field(default=None, alias="ספק")
    transport_company: list[str] | None = Field(default=None, alias="חברת הובלה")
    driver_name: str | None = Field(default=None, alias="שם נהג")
    truck_number: str | None = Field(default=None, alias="מספר משאית")
    warehouse: str | None = Field(default=None, alias="מחסן")
    starting_employee: list[str] | None = Field(default=None, alias="עובד מתחיל")
    unloader: list[str] | None = Field(default=None, alias="פורק")
    forklift_operator: list[str] | None = Field(default=None, alias="מלגזן")
    assistant_forklift_operator: list[str] | None = Field(default=None, alias="עוזר מלגזן")
    pallet_location_worker: list[str] | None = Field(default=None, alias="מזין משטחים במיקום")
    container_record_id: str | None = None
    supplier_record_id: str | None = None
    transport_record_id: str | None = None
    employee_id: str | None = None
def conf():
    names = ['AIRTABLE_TOKEN', 'AIRTABLE_BASE_ID', 'AIRTABLE_CONTAINERS_TABLE',
             'AIRTABLE_SUPPLIERS_TABLE','AIRTABLE_WORKERS_TABLE']
    values = {n: os.getenv(n) for n in names}
    if not all(values.values()):
        raise HTTPException(503, 'חסרות הגדרות Airtable בשרת')
    return values

def api(method, table, *, record=None, params=None, payload=None, timeout=30):
    c = conf()
    url = f"{AIRTABLE}/{c['AIRTABLE_BASE_ID']}/{quote(c[table], safe='')}"
    if record:
        url += '/' + quote(record, safe='')
    try:
        r = requests.request(method, url, headers={
            'Authorization': f"Bearer {c['AIRTABLE_TOKEN']}",
            'Content-Type': 'application/json',
        }, params=params, json=payload, timeout=timeout)
    except requests.RequestException as e:
        raise HTTPException(502, 'שגיאת תקשורת עם Airtable') from e
    if not r.ok:
        # Avoid passing potentially sensitive Airtable diagnostics to portal clients.
        raise HTTPException(502, f'שגיאת Airtable ({r.status_code})')
    return r.json()

def records(table_key, fields=None, formula=None):
    result, offset = [], None
    while True:
        params = {'pageSize': 100}
        if fields: params['fields[]'] = fields
        if formula: params['filterByFormula'] = formula
        if offset: params['offset'] = offset
        page = api('GET', table_key, params=params)
        result.extend(page.get('records', []))
        offset = page.get('offset')
        if not offset: return result

def record_id(v):
    return isinstance(v, str) and v.startswith('rec') and len(v) >= 10

def label_of(fields, preferred):
    for key in preferred:
        value = fields.get(key)
        if isinstance(value, list): value = ', '.join(str(x) for x in value)
        if value is not None and str(value).strip(): return str(value).strip()
    # Airtable primary field not exposed without knowing its actual name.
    return ''

def build_container_unloading_router():
    """The auth dependency MUST verify a real server-side session/token and return
    an identity with an Airtable worker record ID, e.g. {'worker_record_id':'rec...'}.
    """
    router = APIRouter(prefix='/api/container-unloading', tags=['Container Unloading'])

    def worker_id(user):
        if isinstance(user, dict): wid = user.get('worker_record_id')
        else: wid = getattr(user, 'worker_record_id', None)
        if not record_id(wid):
            raise HTTPException(403, 'לא נמצא קישור מאומת לרשומת עובד ב-Airtable')
        return wid

    @router.get('/options')
    def options():
        
        containers = records('AIRTABLE_CONTAINERS_TABLE',
                             fields=['מספר מכולה', 'סטטוס'])
        suppliers = records('AIRTABLE_SUPPLIERS_TABLE')
        transports = suppliers
        return {
            'containers': [
                {'id':r['id'], 'label':str(r.get('fields', {}).get('מספר מכולה') or '').strip()}
                for r in containers if str(r.get('fields', {}).get('סטטוס') or '').strip() == 'לפני פריקה'
                and str(r.get('fields', {}).get('מספר מכולה') or '').strip()
            ],
            'suppliers': [{'id':r['id'], 'label':label_of(r.get('fields', {}), ['שם ספק', 'ספק', 'Name'])}
                          for r in suppliers],
            'transports': [{'id':r['id'], 'label':label_of(r.get('fields', {}), ['שם חברת הובלה', 'חברת הובלה', 'Name'])}
                           for r in transports],
            'photo_containers': [
                {'id':r['id'], 'label':str(r.get('fields', {}).get('מספר מכולה') or '').strip()}
                for r in containers if str(r.get('fields', {}).get('סטטוס') or '').strip() in ('בפריקה', 'לפני פריקה')
            ],
        }

    @router.post('/start')
    def start(body: ContainerCreate,):
        wid = (body.employee_id or "").strip()

        if not record_id(wid):
            raise HTTPException(
                status_code=422,
                detail="מזהה העובד אינו תקין"
            )

        employee = api(
            "GET",
            "AIRTABLE_WORKERS_TABLE",
            record=wid
        )

        if not employee.get("fields", {}).get("פעיל", False):
            raise HTTPException(
                status_code=403,
                detail="העובד אינו פעיל"
            )
        for val in (body.container_record_id, body.supplier_record_id, body.transport_record_id):
            if not record_id(val): raise HTTPException(422, 'מזהה רשומה אינו תקין')
        warehouse = (body.warehouse or "").strip()
        if not warehouse: raise HTTPException(422, 'חובה להזין מחסן')
        driver = (body.driver_name or "").strip()
        if not driver: raise HTTPException(422, 'חובה להזין שם נהג')
        container = api('GET', 'AIRTABLE_CONTAINERS_TABLE', record=body.container_record_id)
        if str(container.get('fields', {}).get('סטטוס') or '').strip() != 'לפני פריקה':
            raise HTTPException(409, 'המכולה אינה בסטטוס לפני פריקה')
        # Verify linked record IDs refer to the intended tables before updating.
        api('GET', 'AIRTABLE_SUPPLIERS_TABLE', record=body.supplier_record_id)
        api('GET', 'AIRTABLE_TRANSPORT_TABLE', record=body.transport_record_id)
        now = datetime.now(ZoneInfo('Asia/Jerusalem')).isoformat()
        updated = api('PATCH', 'AIRTABLE_CONTAINERS_TABLE', record=body.container_record_id,
            payload={'fields': {
                'ספק': [body.supplier_record_id],
                'חברת הובלה': [body.transport_record_id],
                'שם נהג': driver,
                'מחסן': warehouse,
                'שעת התחלה': now,
                'עובד מתחיל': [wid],
                'סטטוס': 'בפריקה',
            }})
        return {'success': True, 'container_record_id': updated['id'], 'warehouse': warehouse, 'started_at': now}

    @router.post('/{container_record_id}/photo')
    async def upload_photo(container_record_id: str, file: UploadFile = File(...)):
        
        if not record_id(container_record_id): raise HTTPException(422, 'מזהה מכולה אינו תקין')
        container = api('GET', 'AIRTABLE_CONTAINERS_TABLE', record=container_record_id)
        if str(container.get('fields', {}).get('סטטוס') or '').strip() not in ('בפריקה', 'לפני פריקה'):
            raise HTTPException(409, 'לא ניתן לצלם מכולה בסטטוס הזה')
        data = await file.read(MAX_IMAGE_SIZE + 1)
        if not data or len(data) > MAX_IMAGE_SIZE:
            raise HTTPException(413, 'יש להעלות תמונה עד 10MB')
        mime = None
        if data.startswith(b'\xff\xd8\xff'): mime = 'image/jpeg'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'): mime = 'image/png'
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP': mime = 'image/webp'
        if not mime: raise HTTPException(415, 'אפשר להעלות JPG, PNG או WEBP בלבד')
        c = conf()
        # Airtable uploadAttachment adds a file to the existing attachment field.
        field = quote('Attachments', safe='')
        url = f"{FILE_API}/{c['AIRTABLE_BASE_ID']}/{container_record_id}/{field}/uploadAttachment"
        try:
            r = requests.post(url, headers={'Authorization': f"Bearer {c['AIRTABLE_TOKEN']}",
                 'Content-Type': 'application/json'}, json={
                    'contentType': mime,
                    'filename': f'container_{container_record_id}_{int(datetime.now().timestamp())}.{mime.split("/")[1]}',
                    'file': base64.b64encode(data).decode('ascii'),
                }, timeout=90)
        except requests.RequestException as e:
            raise HTTPException(502, 'שגיאת העלאת צילום') from e
        if not r.ok: raise HTTPException(502, f'שגיאה בשמירת התמונה ({r.status_code})')
        return {'success': True}

    return router