from DB import get_all_airtable_records
import os
from urllib.parse import quote
from fastapi import HTTPException
import requests

AIRTABLE_ORDERS_TABLE = os.getenv("AIRTABLE_ORDERS_TABLE")
def clean_zpl_value(value) -> str:
    return str(value or "").replace("^", "").replace("~", "").strip()


def create_order_label_zpl(order: dict) -> str:
    fields = order.get("fields", {})

    order_number = clean_zpl_value(
        fields.get("מספר הזמנה")
    )

    customer_name = clean_zpl_value(
        fields.get("שם לקוח")
    )

    address = clean_zpl_value(
        fields.get("כתובת")
    )

    city = clean_zpl_value(
        fields.get("עיר")
    )
    customer_number= clean_zpl_value(
            fields.get("מספר לקוח")
        )


    return f"""
^XA
^CI28
^PW800
^LL560

^PQ4

^FO250,20
^A0N,34,34
^FD{order_number}^FS

^FO70,100
^BY4,3,120
^BCN,120,N,N,N
^FD{order_number}^FS

^FO40,270
^A0N,40,40
^FD{customer_number}^FS

^FO40,340
^A0N,34,34
^FD{customer_name}^FS

^FO40,400
^A0N,34,34
^FD{address}^FS

^FO40,460
^A0N,34,34
^FD{city}^FS

^XZ
"""
def create_today_orders_zpl() -> str:
    records = get_all_airtable_records(table_name=AIRTABLE_ORDERS_TABLE,filter_formula=  "IS_SAME("
        "{יום עבודה בפועל},"
        "TODAY(),"
        "'day'"
        ")")

    if not records:
        raise HTTPException(
            status_code=404,
            detail="לא נמצאו הזמנות ליום העבודה הנוכחי",
        )

    labels = [
        create_order_label_zpl(record)
        for record in records
    ]

    return "\n".join(labels)