import os
import requests
from fastapi import FastAPI, HTTPException

from datetime import datetime, timezone,date

from zoneinfo import ZoneInfo
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_ORDERS_TABLE = os.getenv("AIRTABLE_ORDERS_TABLE")
AIRTABLE_CUSTOMERS_TABLE = os.getenv("AIRTABLE_CUSTOMERS_TABLE")
AIRTABLE_AGENTS_TABLE = os.getenv("AIRTABLE_AGENTS_TABLE")
AIRTABLE_WORKERS_TABLE= os.getenv("AIRTABLE_WORKERS_TABLE")
AIRTABLE_WORKDAY_TABLE=os.getenv("AIRTABLE_WORKDAY_TABLE")
from Models import CustomerCreate,OrderCreate
def airtable_headers():
    return {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }
#קבלת כל רשומות טבלה מסוימת
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
#החזרת טבלה לקוחות
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
#יצירת לקוח חדש
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
#יצירת הזמנה חדשה 
def create_order(order: OrderCreate):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_ORDERS_TABLE}"

    fields = {
      "מספר הזמנה": order.order_number,
        "לקוח": [order.customer_id],
        "סטטוס": "לפני יצור"
    }

    if order.agent_id:
      fields["סוכן"] = [order.agent_id]

    #if order.line:
    #  fields["קו אלי"] = {"name": order.line}

   # if order.agent_id:
   #     fields["סוכן"] = [{"id": order.agent_id}]

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

    return {"success": True, "record": response.json(),"record_id": response.json()["id"]}
#החזרת כל הטבלה לפי פומרמולה
def get_all_airtable_records(
    table_name: str,
    *,
    filter_formula: str | None = None,
    fields: list[str] | None = None,
    view: str | None = None,
):
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{table_name}"
    )
    params = {}

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
        if view:
            params["view"] = view

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
#החזרת טבלת עובדים
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
#החזת טבלת הזמנות לפי סטטוס מסוים
def get_orders_filter_by_status(    status: str ):

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
#מציאת לקוח לפי מספר לקוח
def find_customer_record_id(
    customer_number: str
) -> str | None:

    records = get_all_airtable_records(
        AIRTABLE_CUSTOMERS_TABLE,
        filter_formula=(
            f'{{מספר לקוח}}="{customer_number}"'
        ),
    )

    if not records:
        return None

    return records[0].get("id")

  
#מציאת סוכן לפי מספר סוכן
def find_agent_record_id(
    agent_name: str,
) -> str | None:
    if not agent_name:
        return None

    records = get_all_airtable_records(
        AIRTABLE_AGENTS_TABLE,
        filter_formula=(
            f'{{סוכן}}="{agent_name}"'
        ),
    )

    if not records:
        return None

    return records[0].get("id")
#מציאת רשומת יום עבוד לפי יום עבודה
def find_workday_record_id(workday:date):
    if not workday:
        return None
    records=get_all_airtable_records(
        AIRTABLE_WORKDAY_TABLE,
        filter_formula=(
            f'{{יום עבודה}}="{workday}"'
        ))
    if not records:
            return None

    return records[0].get("id")
 
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
    workday_id: str| None = None
    


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
    if workday_id:
        if not workday_id.startswith("rec"):
            raise HTTPException(
                status_code=400,
                detail="מזהה יום עבודה אינו תקין",
            )
        fields["יום עבודה"]=[workday_id]

        

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
#העלת קובץ לטבלה הזמנות לרשומה קובץ/ תמונה
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
def get_order_by_record_id(record_id: str):
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{AIRTABLE_ORDERS_TABLE}/{record_id}"
    )

    response = requests.get(
        url,
        headers=airtable_headers(),
        timeout=30,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()