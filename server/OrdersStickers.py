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

    return f"""
^XA
^PW800
^LL560
^CI28

^FO40,30
^A0N,45,45
^FDOrder: {order_number}^FS

^FO40,100
^BY3,2,100
^BCN,100,Y,N,N
^FD{order_number}^FS

^FO40,260
^A0N,34,34
^FDCustomer: {customer_name}^FS

^FO40,320
^A0N,30,30
^FDAddress: {address}^FS

^FO40,380
^A0N,30,30
^FDCity: {city}^FS

^XZ
"""
def create_today_orders_zpl() -> str:
    records = get_all_airtable_records(table_name=AIRTABLE_ORDERS_TABLE,filter_formula=  "IS_SAME("
        "{יום עבדוה בפועל},"
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