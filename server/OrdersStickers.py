from DB import get_all_airtable_records
import os
from urllib.parse import quote
from fastapi import HTTPException
import requests

AIRTABLE_ORDERS_TABLE = os.getenv("AIRTABLE_ORDERS_TABLE")
def clean_zpl_value(value) -> str:
    return str(value or "").replace("^", "").replace("~", "").strip()

def clean_airtable_value(value):
    if isinstance(value, list):
        if not value:
            return ""

        return str(value[0])

    if value is None:
        return ""

    return str(value)
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
    order_number = clean_airtable_value(order_number)
    customer_number = clean_airtable_value(customer_number)
    customer_name = clean_airtable_value(customer_name)
    address = clean_airtable_value(address)
    city = clean_airtable_value(city)


    return f"""
^XA
^CI28
^PW800
^LL560

^PQ4

^FO740,50
^A0R,45,45
^FD{order_number}^FS

^FO650,50
^BY3,2,120
^BCR,120,N,N,N
^FD{order_number}^FS

^FO480,50
^A0R,40,40
^FDמספר לקוח: {customer_number}^FS

^FO410,50
^A0R,34,34
^FDשם לקוח: {customer_name}^FS

^FO340,50
^A0R,34,34
^FDכתובת: {address}^FS

^FO270,50
^A0R,34,34
^FDעיר: {city}^FS

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