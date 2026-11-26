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
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File,Form
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
    transport_other_name: str | None = None
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
        suppliers = records(
            'AIRTABLE_SUPPLIERS_TABLE',
            formula="{ספק מכולות}=1"
)
        transports = records(
        'AIRTABLE_SUPPLIERS_TABLE',
        formula="{הובלת מכולות}=1"
)
        workers = records(
    "AIRTABLE_WORKERS_TABLE",
    fields=["שם", "תפקיד", "פעיל"]
)

        warehouse_workers = [
            {
                "id": r["id"],
                "label": str(
                    r.get("fields", {}).get("שם") or ""
                ).strip()
            }
            for r in workers
            if r.get("fields", {}).get("פעיל") is True
            and str(
                r.get("fields", {}).get("תפקיד") or ""
            ).strip().lower() == "warehouse"
            and str(r.get("fields", {}).get("שם") or "").strip()
        ]

        end_containers = [
            {
                "id": r["id"],
                "label": str(
                    r.get("fields", {}).get("מספר מכולה") or ""
                ).strip()
            }
            for r in containers
            if str(
                r.get("fields", {}).get("סטטוס") or ""
            ).strip() == "בפריקה"
        ]
        return {
            'containers': [
                {'id':r['id'], 'label':str(r.get('fields', {}).get('מספר מכולה') or '').strip()}
                for r in containers if str(r.get('fields', {}).get('סטטוס') or '').strip() == 'לפני פריקה'
                and str(r.get('fields', {}).get('מספר מכולה') or '').strip()
            ],
            'suppliers': [{'id':r['id'], 'label':label_of(r.get('fields', {}), ['שם ספק', 'ספק', 'Name'])}
                          for r in suppliers],
            'transports': [{'id':r['id'], 'label':label_of(r.get('fields', {}), ['שם ספק', 'ספק', 'Name'])}
                           for r in transports],
            'photo_containers': [
                {'id':r['id'], 'label':str(r.get('fields', {}).get('מספר מכולה') or '').strip()}
                for r in containers if str(r.get('fields', {}).get('סטטוס') or '').strip() in ('בפריקה', 'לפני פריקה')
            ],
            "end_containers": end_containers,
            "workers": warehouse_workers,
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
        for val in (body.container_record_id, body.supplier_record_id):
            if not record_id(val): raise HTTPException(422, 'מזהה רשומה אינו תקין')
        if body.transport_record_id != "other":
            if not record_id(body.transport_record_id):
                raise HTTPException(422, 'מזהה חברת הובלה אינו תקין')
        truck_number = (body.truck_number or "").strip()
        warehouse = (body.warehouse or "").strip()
        if not warehouse: raise HTTPException(422, 'חובה להזין מחסן')
        driver = (body.driver_name or "").strip()
        if not driver: raise HTTPException(422, 'חובה להזין שם נהג')
        container = api('GET', 'AIRTABLE_CONTAINERS_TABLE', record=body.container_record_id)
        if str(container.get('fields', {}).get('סטטוס') or '').strip() != 'לפני פריקה':
            raise HTTPException(409, 'המכולה אינה בסטטוס לפני פריקה')
        # בדיקה שקיים צילום מכולה
        attachments = container.get("fields", {}).get("Attachments") or []
        now = datetime.now(
            ZoneInfo("Asia/Jerusalem")
        ).isoformat()

        if not attachments:
            raise HTTPException(
                status_code=422,
                detail="חובה לצלם או להעלות תמונת מכולה לפני תחילת הפריקה"
            )
        # Verify linked record IDs refer to the intended tables before updating.
        api('GET', 'AIRTABLE_SUPPLIERS_TABLE', record=body.supplier_record_id)
        if body.transport_record_id == "other":
            new_name = (body.transport_other_name or "").strip()

            if not new_name:
                raise HTTPException(
                    422,
                    "חובה להזין שם חברת הובלה חדשה"
                )

            if len(new_name) > 150:
                raise HTTPException(
                    422,
                    "שם חברת ההובלה ארוך מדי"
                )

            # בדיקה האם החברה כבר קיימת
            all_suppliers = records('AIRTABLE_SUPPLIERS_TABLE')

            existing = next(
                (
                    r for r in all_suppliers
                    if str(
                        r.get("fields", {}).get("שם ספק") or ""
                    ).strip().casefold() == new_name.casefold()
                ),
                None
            )

            if existing:
                transport_id = existing["id"]

                # סימון הרשומה הקיימת כחברת הובלת מכולות
                if not existing.get("fields", {}).get("הובלת מכולות"):
                    api(
                        "PATCH",
                        "AIRTABLE_SUPPLIERS_TABLE",
                        record=transport_id,
                        payload={
                            "fields": {"הובלת מכולות": True}
                        }
                    )
            else:
                created = api(
                    "POST",
                    "AIRTABLE_SUPPLIERS_TABLE",
                    payload={
                        "fields": {
                            "שם ספק": new_name,
                            "הובלת מכולות": True
                        }
                    }
                )

                transport_id = created["id"]

        else:
            transport_id = body.transport_record_id

            transport = api(
                "GET",
                "AIRTABLE_SUPPLIERS_TABLE",
                record=transport_id
            )

            if not transport.get("fields", {}).get("הובלת מכולות"):
                raise HTTPException(
                    422,
                    "החברה שנבחרה אינה מוגדרת להובלת מכולות"
                )
                now = datetime.now(ZoneInfo('Asia/Jerusalem')).isoformat()
        updated = api('PATCH', 'AIRTABLE_CONTAINERS_TABLE', record=body.container_record_id,
            payload={'fields': {
                'ספק': [body.supplier_record_id],
                'חברת הובלה': [transport_id],
                'שם נהג': driver,
                'מחסן': warehouse,
                'שעת התחלה': now,
                'פורק': [wid],
                'סטטוס': 'בפריקה',
                'מספר משאית':truck_number
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
    
    @router.post("/finish")
    async def finish_unloading(
        container_record_id: str = Form(...),
        forklift_operator: str = Form("[]"),
        assistant_forklift_operator: str = Form("[]"),
        pallet_location_worker: str = Form("[]"),
        pallets_on_floor: bool = Form(False),
        file: UploadFile = File(...)
    ):
        # בדיקת מזהה המכולה
        if not record_id(container_record_id):
            raise HTTPException(
                status_code=422,
                detail="מזהה המכולה אינו תקין"
            )

        # פענוח רשימות העובדים
        def parse_workers(raw, field_name):
            try:
                ids = json.loads(raw)
            except (ValueError, TypeError):
                raise HTTPException(
                    422,
                    f"נתונים לא תקינים בשדה {field_name}"
                )

            if not isinstance(ids, list):
                raise HTTPException(
                    422,
                    f"השדה {field_name} חייב להיות רשימה"
                )

            if not ids:
                raise HTTPException(
                    422,
                    f"חובה לבחור לפחות עובד אחד: {field_name}"
                )

            if (
                len(ids) > 30
                or len(ids) != len(set(ids))
                or not all(record_id(x) for x in ids)
            ):
                raise HTTPException(
                    422,
                    f"מזהי עובדים לא תקינים: {field_name}"
                )

            return ids

        forklift_ids = parse_workers(
            forklift_operator, "מלגזן"
        )
        assistant_ids = parse_workers(
            assistant_forklift_operator, "עוזר מלגזן"
        )
        location_ids = parse_workers(
            pallet_location_worker, "מזין משטחים במיקום"
        )

        # בדיקת מצב המכולה
        container = api(
            "GET",
            "AIRTABLE_CONTAINERS_TABLE",
            record=container_record_id
        )

        status = str(
            container.get("fields", {}).get("סטטוס") or ""
        ).strip()

        if status != "בפריקה":
            raise HTTPException(
                status_code=409,
                detail="ניתן לסיים רק מכולה בסטטוס בפריקה"
            )

        # בדיקת הרשומות בטבלת העובדים
        workers = records(
            "AIRTABLE_WORKERS_TABLE",
            fields=["שם", "תפקיד", "פעיל"]
        )

        allowed_ids = {
            r["id"]
            for r in workers
            if r.get("fields", {}).get("פעיל") is True
            and str(
                r.get("fields", {}).get("תפקיד") or ""
            ).strip().lower() == "warehouse"
        }

        selected_ids = set(
            forklift_ids + assistant_ids + location_ids
        )

        if not selected_ids.issubset(allowed_ids):
            raise HTTPException(
                status_code=422,
                detail="אחד העובדים אינו פעיל או אינו מחסנאי"
            )

        # צילום מכולה ריקה הוא חובה
        photo = await file.read(MAX_IMAGE_SIZE + 1)

        if not photo or len(photo) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="חובה לצרף תמונה בגודל עד 10MB"
            )

        if photo.startswith(b"\xff\xd8\xff"):
            mime, ext = "image/jpeg", "jpg"
        elif photo.startswith(b"\x89PNG\r\n\x1a\n"):
            mime, ext = "image/png", "png"
        elif (
            photo[:4] == b"RIFF"
            and photo[8:12] == b"WEBP"
        ):
            mime, ext = "image/webp", "webp"
        else:
            raise HTTPException(
                status_code=415,
                detail="מותר להעלות JPG, PNG או WEBP בלבד"
            )

        c = conf()

        field = quote("Attachments", safe="")
        upload_url = (
            f"{FILE_API}/{c['AIRTABLE_BASE_ID']}/"
            f"{container_record_id}/{field}/uploadAttachment"
        )

        filename = (
            f"empty_container_{container_record_id}_"
            f"{int(datetime.now().timestamp())}.{ext}"
        )

        # קודם שומרים צילום, ורק אחר כך מסיימים פריקה
        try:
            upload_response = requests.post(
                upload_url,
                headers={
                    "Authorization":
                        f"Bearer {c['AIRTABLE_TOKEN']}",
                    "Content-Type": "application/json"
                },
                json={
                    "contentType": mime,
                    "filename": filename,
                    "file": base64.b64encode(photo).decode("ascii")
                },
                timeout=90
            )
        except requests.RequestException as exc:
            raise HTTPException(
                502, "שגיאת תקשורת בשמירת הצילום"
            ) from exc

        if not upload_response.ok:
            raise HTTPException(
                status_code=502,
                detail=(
                    "שמירת צילום המכולה נכשלה "
                    f"({upload_response.status_code})"
                )
            )

        final_status = (
            "פריקה הסתיימה מידוף טרם הושלם"
            if pallets_on_floor
            else "פריקה הסתיימה"
        )

        now = datetime.now(
            ZoneInfo("Asia/Jerusalem")
        ).isoformat()

        updated = api(
            "PATCH",
            "AIRTABLE_CONTAINERS_TABLE",
            record=container_record_id,
            payload={
                "fields": {
                    "מלגזן": forklift_ids,
                    "עוזר מלגזן": assistant_ids,
                    "מזין משטחים במיקום": location_ids,
                    "שעת סיום": now,
                    "סטטוס": final_status
                }
            }
        )

        return {
            "success": True,
            "container_record_id": updated["id"],
            "status": final_status,
            "ended_at": now
        }


    return router