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
AIRTABLE_USERS_TABLE = os.getenv(
    "AIRTABLE_USERS_TABLE"
   
)
AIRTABLE_CHAT_TABLE=os.getenv("AIRTABLE_CHAT_TABLE")
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

    records = get_all_airtable_records(
        table_name=AIRTABLE_CUSTOMERS_TABLE,
        fields=[
            "מספר לקוח",
            "שם לקוח",
        ],
    )

    customers = []

    for record in records:
        fields = record.get("fields", {})

        customer_number = fields.get("מספר לקוח", "")
        customer_name = fields.get("שם לקוח", "")

        # אם השדה הוא Lookup ומתקבלת רשימה
        if isinstance(customer_number, list):
            customer_number = ", ".join(
                str(value) for value in customer_number
            )

        if isinstance(customer_name, list):
            customer_name = ", ".join(
                str(value) for value in customer_name
            )

        customers.append({
            "id": record["id"],
            "number": str(customer_number),
            "name": str(customer_name),
            "display": (
                f"{customer_number} - {customer_name}"
            ),
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
    sort: list[tuple[str, str]] | None = None,

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
        if sort:
            for i, (field, direction) in enumerate(sort):
                params[f"sort[{i}][field]"] = field
                params[f"sort[{i}][direction]"] = direction

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
def get_orders_filter_by_status(    status: str ,action: int|None=None,user_id: str|None=None):
    if action==1:
         records = get_all_airtable_records(
        AIRTABLE_ORDERS_TABLE,
          filter_formula='{{בצפי}}=1',
          sort= [
        ("יום עבודה", "asc"),
        ("תאריך אספקה", "asc"),
        ],
    )
    else :
        records = get_all_airtable_records(
        AIRTABLE_ORDERS_TABLE,
        filter_formula=f'{{סטטוס}}="{status}"',   sort= [
                ("יום עבודה בפועל", "asc"),
                ("תאריך אספקה", "asc"),("שורות ליקוט", "desc")
                ],)
        if action==2:
                   if user_id:
                        records = [
                        record
                        for record in records
                        if user_id in (
                            record.get("fields", {}).get("עובדים") or []
                        )
                    ]
                 

     

    orders = []

    for record in records:
        fields = record.get("fields", {})

        order_number = str(
            fields.get("מספר הזמנה", "")
        )

        customer_name = fields.get("שם לקוח", "")
        amount= fields.get("כמות משטחים", 0)
        notes=fields.get("הערות למחסן", "")
        picking_lines = fields.get("שורות ליקוט", 0)
        segment = fields.get("סיגמנט", False)
        order_date=fields.get("תאריך אספקה", "")
        eli_line=fields.get("קו אלי", "")
        going_out_with_us=fields.get("יוצא איתנו", False)
        order_status=fields.get("סטטוס", "")

        if(order_status)=="בבדיקה":
            order_status="נבדק"

        else:
            order_status="לא נבדק"





        # אם שם הלקוח הוא Lookup, לפעמים מתקבל מערך
        if isinstance(customer_name, list):
            customer_name = ", ".join(
                str(value) for value in customer_name
            )
        if isinstance(segment, list):
            segment = ", ".join(
                str(value) for value in segment
            )

        display = order_number

        if customer_name:
            display += f" - {customer_name}"

        
        if picking_lines:
             display += f"\nשורות ליקוט: {picking_lines}"
        if isinstance(segment, list):
            segment = segment[0] if segment else False
        is_segment = (
        segment is True
        or str(segment).strip().lower() == "true"
        )
        if is_segment:
             display += f"\nלקוח סיגמנט "
        
        if notes:
             display += f"\n הערות: {notes} "
        if amount:
            display += f"\n{amount} משטחים"
        if order_date:
            display += f"\nתאריך אספקה: {order_date}"
        if eli_line:
            display += f"\nקו אלי {eli_line}"
        if going_out_with_us:
            display += f"\nיוצא איתנו"
        
            


        orders.append({
            "id": record["id"],
            "order_number": order_number,
            "customer_name": customer_name,
            "display": display,
            "quantity": fields.get("כמות", 0),
            "notes": notes,
            "amount": amount,

            "picking_lines": picking_lines,
            "segment": segment,
            "order_status": order_status
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
    workday_id: str| None = None,
    invoice:str| None = None,
    break_minutes:int| None = None


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
    if invoice:
        fields["חשבונית"] = invoice
    if break_minutes:
        fields["הפסקה"] = break_minutes
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
#יצירת רשומה בטבלה ימי עבודה
def create_workday_record(workday_date: date):
    table_name = quote(
        AIRTABLE_WORKDAY_TABLE,
        safe="",
    )

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{table_name}"
    )

    payload = {
        "fields": {
            "יום עבודה": workday_date.isoformat(),
        }
    }

    response = requests.post(
        url,
        headers=airtable_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()
#חיפוש שם משתמש בטבלת משתמשים
def get_airtable_user(username: str):
    if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
        raise RuntimeError(
            "חסרים משתני AIRTABLE_TOKEN או AIRTABLE_BASE_ID"
        )

    table_name = quote(
        AIRTABLE_WORKERS_TABLE,
        safe="",
    )

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{table_name}"
    )

    safe_username = (
        username
        .replace("\\", "\\\\")
        .replace("'", "\\'")
    )

    formula = f"{{שם משתמש}}='{safe_username}'"
    print(formula)

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        },
        params={
            "filterByFormula": formula,
            "maxRecords": 1,
        },
        timeout=20,
    )

    if not response.ok:
        print("Airtable error:", response.text)
        raise RuntimeError(
            "שגיאה בקריאת המשתמשים מ-Airtable"
        )

    records = response.json().get("records", [])

    if not records:
        return None
    print("1")

    return records[0]
#פונקציה ליצירת הודעה
from urllib.parse import quote



def create_chat_message(user_id: str, message: str):
    message = str(message).strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="לא ניתן לשלוח הודעה ריקה",
        )

    table_name = quote(
        AIRTABLE_CHAT_TABLE,
        safe="",
    )

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{table_name}"
    )

    payload = {
        "fields": {
            "הודעה": message,
            "שולח": [user_id],
        }
    }

    response = requests.post(
        url,
        headers=airtable_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()
#פונקתיה קבלת הודעה
def get_chat_messages(limit: int = 100):
    records = get_all_airtable_records(
        table_name=AIRTABLE_CHAT_TABLE,
        fields=[
            "הודעה",
            "שולח",
            "שם שולח",
            "תאריך יצירה",
        ],
        view="Grid view",
    )

    messages = []

    for record in records:
        fields = record.get("fields", {})

        sender_name = fields.get("שם שולח", "")

        if isinstance(sender_name, list):
            sender_name = (
                str(sender_name[0])
                if sender_name
                else ""
            )

        sender_ids = fields.get("שולח", [])

        if not isinstance(sender_ids, list):
            sender_ids = []

        messages.append({
            "id": record["id"],
            "message": str(
                fields.get("הודעה", "")
            ),
            "sender_id": (
                sender_ids[0]
                if sender_ids
                else None
            ),
            "sender_name": (
                str(sender_name)
                if sender_name
                else "עובד"
            ),
            "created_at": fields.get(
                "תאריך יצירה",
                record.get("createdTime", ""),
            ),
        })

    messages.sort(
        key=lambda item: item.get("created_at", "")
    )

    return messages[-limit:]
#בדיקה האם קיימת כבר הזמנה בליקוט לעובד
def employee_has_active_picking(
    employee_id: str,
    exclude_order_id: str | None = None,
) -> dict | None:
    records = get_all_airtable_records(
        table_name=AIRTABLE_ORDERS_TABLE,
        filter_formula='{סטטוס}="בליקוט"',
    )

    for record in records:
        if exclude_order_id and record.get("id") == exclude_order_id:
            continue

        fields = record.get("fields", {})
        workers = fields.get("עובדים") or []

        if not isinstance(workers, list):
            workers = [workers]

        if employee_id in workers:
            return {
                "id": record.get("id"),
                "order_number": str(
                    fields.get("מספר הזמנה", "")
                ),
                "customer_name": fields.get(
                    "שם לקוח",
                    "",
                ),
            }

    return None
from fastapi import HTTPException


def start_picking_order(
    order_id: str,
    employee_id: str,
):
    active_order = employee_has_active_picking(
        employee_id=employee_id,
        exclude_order_id=order_id,
    )

    if active_order:
        order_number = (
            active_order.get("order_number")
            or "ללא מספר"
        )

        raise HTTPException(
            status_code=409,
            detail=(
                "יש לך כבר הזמנה באמצע ליקוט: "
                f"{order_number}"
            ),
        )

    # מכאן ממשיכים לקוד הקיים שלך
    # שמעדכן את ההזמנה לסטטוס בליקוט
    # ומקשר אליה את העובד

 