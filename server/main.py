import os
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_ORDERS_TABLE = os.getenv("AIRTABLE_ORDERS_TABLE")
AIRTABLE_CUSTOMERS_TABLE = os.getenv("AIRTABLE_CUSTOMERS_TABLE")
AIRTABLE_AGENTS_TABLE = os.getenv("AIRTABLE_AGENTS_TABLE")
AIRTABLE_WORKERS_TABLE= os.getenv("AIRTABLE_WORKERS_TABLE")

class CustomerCreate(BaseModel):
    customer_number: str | None = ""
    customer_name: str
    contact_name: str | None = ""
    phone: str | None = ""
    address: str | None = ""
    city: str | None = ""
    segment: bool = False
    mikasa: bool = False
app = FastAPI()
class PickingStart(BaseModel):
    order_id:str
    employee_id: str

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)

allowed_origins = [
    "http://localhost:5173",
    FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def airtable_headers():
    return {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }

@app.get("/")
def home():
    return {"status": "server is running"}

def get_table_records(table_name: str, name_field: str):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
    response = requests.get(url, headers=airtable_headers())

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return [
        {
            "id": record["id"],
            "name": record["fields"].get(name_field, "")
        }
        for record in response.json().get("records", [])
        if record.get("fields", {}).get(name_field)
    ]

@app.get("/api/customers")

def get_customers():
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_CUSTOMERS_TABLE}"
    response = requests.get(url, headers=airtable_headers())

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    customers = []

    for record in response.json().get("records", []):
        fields = record.get("fields", {})

        customer_number = fields.get("מספר לקוח", "")
        customer_name = fields.get("שם לקוח", "")

        customers.append({
            "id": record["id"],
            "number": customer_number,
            "name": customer_name,
            "display": f"{customer_number} - {customer_name}"
        })

    return customers
@app.post("/api/customers")
def create_customer(customer:CustomerCreate):
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{AIRTABLE_CUSTOMERS_TABLE}"
    )

    fields = {
        "שם לקוח": customer.customer_name,
        "סיגמנט": customer.segment,
        "מיקאסה": customer.mikasa,
    }

    if customer.customer_number:
        fields["מספר לקוח"] = customer.customer_number

    if customer.contact_name:
        fields["שם איש קשר"] = customer.contact_name

    if customer.phone:
        fields["טלפון"] = customer.phone

    if customer.address:
        fields["כתובת"] = customer.address

    if customer.city:
        fields["עיר"] = customer.city

    response = requests.post(
        url,
        headers=airtable_headers(),
        json={"fields": fields},
        timeout=30,
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    record = response.json()
    saved_fields = record.get("fields", {})

    customer_number = saved_fields.get("מספר לקוח", "")
    customer_name = saved_fields.get("שם לקוח", "")

    return {
        "id": record["id"],
        "number": customer_number,
        "name": customer_name,
        "display": f"{customer_number} - {customer_name}".strip(" -"),
    }
    
    
@app.get("/api/agents")
def get_agents():
    return get_table_records(AIRTABLE_AGENTS_TABLE, "סוכן")


class OrderCreate(BaseModel):
    order_number: str
    customer_id: str
    agent_id: str | None = ""
    delivery_date: str | None = ""
    picking_rows: int | None = None
    goes_with_us: bool | None = False
    line: str | None = ""
    delivery_notes: str | None = ""
    warehouse_notes: str | None = ""


@app.post("/api/orders")
def create_order(order: OrderCreate):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_ORDERS_TABLE}"

    fields = {
      "מספר הזמנה": order.order_number,
        "לקוח": [order.customer_id],
        "סטטוס": "לפני יצור"
    }

    if order.agent_id:
      fields["סוכן"] = [order.agent_id]

    if order.line:
     fields["קו אלי"] = {"name": order.line}

    if order.agent_id:
        fields["סוכן"] = [{"id": order.agent_id}]

    if order.delivery_date:
        fields["תאריך אספקה"] = order.delivery_date

    if order.picking_rows is not None:
        fields["שורות ליקוט"] = order.picking_rows

    if order.goes_with_us is not None:
        fields["יוצא איתנו"] = order.goes_with_us

    if order.line:
        fields["קו אלי"] = order.line

    if order.delivery_notes:
        fields["הערות אספקה"] = order.delivery_notes

    if order.warehouse_notes:
        fields["הערות למחסן"] = order.warehouse_notes

    payload = {"fields": fields}

    response = requests.post(url, headers=airtable_headers(), json=payload)

    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"success": True, "record": response.json()}
   

@app.get("/api/employees")
def get_employees():
    records = get_all_airtable_records(
        AIRTABLE_WORKERS_TABLE
    )

    employees = []

    for record in records:
        fields = record.get("fields", {})

        employee_name = (
            fields.get("שם")
            or fields.get("עובד")
            or fields.get("שם")
            or ""
        )

        if not employee_name:
            continue

        employees.append({
            "id": record["id"],
            "name": str(employee_name),
        })

    return employees
def get_all_airtable_records(
    table_name: str,
    *,
    filter_formula: str | None = None,
    fields: list[str] | None = None,
):
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{table_name}"
    )

    records = []
    offset = None

    while True:
        params = {
            "pageSize": 100,
        }

        if filter_formula:
            params["filterByFormula"] = filter_formula

        if fields:
            params["fields[]"] = fields

        if offset:
            params["offset"] = offset

        response = requests.get(
            url,
            headers=airtable_headers(),
            params=params,
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text,
            )

        response_data = response.json()
        records.extend(response_data.get("records", []))

        offset = response_data.get("offset")

        if not offset:
            break

    return records
from fastapi import Query
@app.get("/api/orders/filter_by_status")
def get_orders_filter_by_status(    status: str = Query(..., description="סטטוס ההזמנות")
):
    records = get_all_airtable_records(
        AIRTABLE_ORDERS_TABLE,
          filter_formula=f'{{סטטוס}}="{status}"'
    )

    orders = []

    for record in records:
        fields = record.get("fields", {})

        order_number = str(
            fields.get("מספר הזמנה", "")
        )

        customer_name = fields.get("שם לקוח", "")
        amount= fields.get("כמות משטחים", "")
        notes=fields.get("הערות למחסן", "")

        # אם שם הלקוח הוא Lookup, לפעמים מתקבל מערך
        if isinstance(customer_name, list):
            customer_name = ", ".join(
                str(value) for value in customer_name
            )

        display = order_number

        if customer_name:
            display += f" - {customer_name}"

        if amount:
            display += f" - {amount} משטחים"
        if notes:
             display += f" - {notes} "

        orders.append({
            "id": record["id"],
            "order_number": order_number,
            "customer_name": customer_name,
            "display": display,
            "quantity": fields.get("כמות", 0),
            "notes": notes,
            "amount": amount
        })

    return orders

from datetime import datetime, timezone

from zoneinfo import ZoneInfo

@app.patch("/api/orders/start-picking")
def start_picking(data: PickingStart):
    record = update_order_workflow(
        data.order_id,
        employee_id=data.employee_id,
        status="בליקוט",
        start_time=True,
    )

    return {
        "success": True,
        "record": record,
    }
 
def update_order_workflow(
    order_id: str,
    *,
    employee_id: str | None = None,
    status: str | None = None,
    start_time: bool = False,
    end_time: bool = False,
    extra_fields: dict | None = None,
    amount:float | None = None,
    notes: str | None = None,
    LoadingNotes: str | None = None,
    


):
    if not order_id.startswith("rec"):
        raise HTTPException(
            status_code=400,
            detail="מזהה ההזמנה אינו תקין",
        )

    fields = {}

    if employee_id:
        if not employee_id.startswith("rec"):
            raise HTTPException(
                status_code=400,
                detail="מזהה העובד אינו תקין",
            )

        fields["עובדים"] = [employee_id]

    if status:
        fields["סטטוס"] = status

    current_time = datetime.now(
        ZoneInfo("Asia/Jerusalem")
    ).isoformat()

    if start_time:
        fields["שעת התחלה"] = current_time
    
    if end_time:
        fields["שעת סיום"] = current_time

    if amount:
        fields["כמות משטחים"] = amount
    if extra_fields:
        fields.update(extra_fields)
    if notes:
        fields["הערות ליקוט"] = notes
    if LoadingNotes:
        fields["הערות העמסה"] = LoadingNotes

    if not fields:
        raise HTTPException(
            status_code=400,
            detail="לא התקבלו שדות לעדכון",
        )

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{AIRTABLE_ORDERS_TABLE}/{order_id}"
    )

    response = requests.patch(
        url,
        headers=airtable_headers(),
        json={
            "fields": fields,
            "typecast": True,
        },
        timeout=30,
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()
class PickingEnd(BaseModel):
    order_id: str
    amount:float |None=None
    notes: str |None=None


@app.patch("/api/orders/end-picking")
def end_picking(data: PickingEnd):
    record = update_order_workflow(
        data.order_id,
        status="מלוקט",
        end_time=True,
        amount=data.amount,
        notes=data.notes
    )

    return {
        "success": True,
        "record": record,
    }
@app.patch("/api/orders/check")
def check_order(data: PickingEnd):
    record = update_order_workflow(
        data.order_id,
        status="בבדיקה",
        notes=data.notes,
        amount=data.amount,
        
    )

    return {
        "success": True,
        "record": record,
        
    }
class LoadingOrder(BaseModel):
    order_id: str
    notes: str | None = None


class LoadingRequest(BaseModel):
    orders: list[LoadingOrder]

@app.patch("/api/orders/loading")
def loading_orders(data: LoadingRequest):

    results = []

    for order in data.orders:

        record = update_order_workflow(
            order.order_id,
            status="הועמס",
            LoadingNotes=order.notes
        )

        results.append(record)

    return {
        "success": True,
        "updated": len(results),
        "results": results
    }
import base64
import mimetypes
from pathlib import Path
from urllib.parse import quote

import requests
import base64
import requests
from urllib.parse import quote
from fastapi import FastAPI, File, Form, UploadFile

def upload_file_to_airtable(
    record_id: str,
    file_name: str,
    content_type: str,
    file_bytes: bytes,
):
    # קידוד הקובץ ל-Base64
    encoded_file = base64.b64encode(file_bytes).decode("utf-8")

    # שם השדה מסוג Attachment באיירטייבל
    field_name = "תמונה/ צירוף קובץ"

    # קידוד שם השדה ל-URL
    encoded_field = quote(field_name, safe="")

    url = (
        f"https://content.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{record_id}/"
        f"{encoded_field}/uploadAttachment"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "contentType": content_type,
        "filename": file_name,
        "file": encoded_file,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60,
    )

    if not response.ok:
        raise Exception(
            f"שגיאה בהעלאת הקובץ:\n"
            f"{response.status_code}\n"
            f"{response.text}"
        )

    return response.json()
@app.patch("/api/orders/upload-file")
async def upload_order_file(
    order_id: str = Form(...),
    file: UploadFile = File(...)
):
    file_bytes = await file.read()

    result = upload_file_to_airtable(
        record_id=order_id,
        file_name=file.filename,
        content_type=file.content_type,
        file_bytes=file_bytes,
    )

    return {
        "success": True,
        "result": result,
    }
#קליטת הזמנה מאקסל
