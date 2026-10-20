import os
import requests
from DB import get_all_airtable_records

from fastapi import HTTPException
from DB import airtable_headers
from OrdersStickers import create_order_label_zpl


AIRTABLE_BASE_ID = os.getenv(
    "AIRTABLE_BASE_ID"
)
AIRTABLE_ORDERS_TABLE = os.getenv(
    "AIRTABLE_ORDERS_TABLE"
)

AIRTABLE_PRINT_QUEUE_TABLE = os.getenv(
    "AIRTABLE_PRINT_QUEUE_TABLE"
)
def find_next_order():
    records = get_all_airtable_records(
                AIRTABLE_ORDERS_TABLE,
                filter_formula= 
                f'{{סטטוס}}="לפני יצור"',
                  
                sort= [ ("עדיפות", "desc"),("תאריך אספקה", "asc"),("עדיפות קו הפצה", "asc"),("שורות ליקוט", "desc"),("לקוח","asc"), 
                    ],)
    zpl=create_order_label_zpl(records[0])
    create_print_job(
    order_id=records[0].get("id"),
    zpl=zpl
)

def create_print_job(
    order_id: str,
    zpl: str
):
    if not order_id:
        raise ValueError(
            "חסר Record ID של ההזמנה"
        )


    if not zpl or not zpl.strip():
        raise ValueError(
            "ZPL ריק"
        )

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{AIRTABLE_PRINT_QUEUE_TABLE}"
    )

    fields = {
        "הזמנה":
            [order_id],

        "ZPL":
            zpl,

        "סטטוס":
            "ממתין",
    }

    response = requests.post(
        url,
        headers=airtable_headers(),
        json={
            "fields": fields
        },
        timeout=30,
    )

    if response.status_code not in (
        200,
        201
    ):
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()
    #שליפת העבודה הבאה
def get_next_print_job():
    records = get_all_airtable_records(
        AIRTABLE_PRINT_QUEUE_TABLE,
        filter_formula='{סטטוס}="ממתין"',
    )

    if not records:
        return None

    record = records[0]

    fields = record.get(
        "fields",
        {}
    )

    return {
        "id": record["id"],

        "zpl": fields.get(
            "ZPL",
            ""
        ),

        "order": fields.get(
            "הזמנה",
            []
        ),
    }
def delete_print_job(
    record_id: str
):
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{AIRTABLE_PRINT_QUEUE_TABLE}/"
        f"{record_id}"
    )

    response = requests.delete(
        url,
        headers=airtable_headers(),
        timeout=30,
    )

    if not response.ok:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()
def mark_print_job_error(
    record_id: str,
    error: str
):
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{AIRTABLE_PRINT_QUEUE_TABLE}/"
        f"{record_id}"
    )

    response = requests.patch(
        url,
        headers=airtable_headers(),
        json={
            "fields": {
                "סטטוס": "שגיאה",
                "שגיאה": str(error),
            }
        },
        timeout=30,
    )

    if not response.ok:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()