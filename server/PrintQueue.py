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