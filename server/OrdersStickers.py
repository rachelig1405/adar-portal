from DB import get_all_airtable_records
import os
from urllib.parse import quote
from fastapi import HTTPException
import requests

AIRTABLE_ORDERS_TABLE = os.getenv("AIRTABLE_ORDERS_TABLE")
def clean_zpl_value(value) -> str:
    return str(value or "").replace("^", "").replace("~", "").strip()

import ast
def clean_text(text):
    if text is None:
        return ""

    if isinstance(text, list):
        text = text[0] if text else ""

    return str(text)


def right_align_x(text, right_x=850, char_width=18):
    """
    מחזיר ערך X כך שהטקסט יסתיים באותו קו ימין.

    text       - הטקסט להדפסה
    right_x    - קו הימין הרצוי
    char_width - רוחב משוער של כל תו בפונט
    """



    return right_x - (len(text) * char_width)


def clean_airtable_value(value):
    if value is None:
        return ""

    # רשימה אמיתית שמגיעה מ-Airtable Lookup
    if isinstance(value, (list, tuple)):
        if not value:
            return ""

        return clean_airtable_value(value[0])

    text = str(value).strip()

    # מחרוזת שנראית כמו רשימה: "['6161']"
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed_value = ast.literal_eval(text)

            if isinstance(parsed_value, (list, tuple)):
                if not parsed_value:
                    return ""

                return clean_airtable_value(parsed_value[0])
        except (ValueError, SyntaxError):
            pass

    # הסרת סוגריים וגרשיים במקרה שלא הצלחנו לפענח
    text = text.strip("[]")
    text = text.strip()
    text = text.strip("'\"")

    return text.strip()

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
    customer_phone= clean_zpl_value(
                fields.get("טלפון")
            )
    order_number = clean_airtable_value(order_number)
    customer_number = clean_airtable_value(customer_number)
    customer_name = clean_airtable_value(customer_name)
    address = clean_airtable_value(address)
    city = clean_airtable_value(city)
    customer_phone=clean_airtable_value(customer_phone)


    return f"""
^XA
^CI28
^PW800
^LL560

^PQ4

^FO570,130
^A0R,40,40

^FD{order_number}^FS

^FO650,50

^BY3,2,120
^BCR,120,N,N,N
^FD{order_number}^FS

^FO480,{right_align_x('מספר לקוח: ' + customer_number)}

^A0R,34,34
^FDמספר לקוח: {customer_number}^FS

^FO410,{right_align_x('שם לקוח: ' + customer_name)}

^A0R,34,34
^FDשם לקוח: {customer_name}^FS

^FO340,{right_align_x('כתובת: ' + address)}

^A0R,34,34
^FDכתובת: {address}^FS

^FO270,{right_align_x('עיר: ' + city)}

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

