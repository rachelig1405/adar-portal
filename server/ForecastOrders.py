from datetime import datetime
import os

from fastapi import APIRouter, HTTPException

from DB import get_all_airtable_records


router = APIRouter()

AIRTABLE_ORDERS_TABLE = os.getenv(
    "AIRTABLE_ORDERS_TABLE"
)


def clean_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(
            str(item) for item in value
        )

    return str(value).strip()


def clean_number(value, default=0):
    if value is None:
        return default

    if isinstance(value, list):
        value = value[0] if value else default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@router.get("/api/orders/forecast")
def get_forecast_orders(
    date: str | None = None
):

    # =====================================================
    # אם נבחר תאריך:
    # לא מתייחסים בכלל לשדה "בצפי"
    # =====================================================

    if date:

        try:
            datetime.strptime(
                date,
                "%Y-%m-%d"
            )

        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="תאריך לא תקין"
            )

        filter_formula = (
            "IS_SAME("
                "{תאריך אספקה},"
                f'DATETIME_PARSE("{date}"),'
                '"day"'
            ")"
        )


    # =====================================================
    # אם לא נבחר תאריך:
    # מציגים רק הזמנות שבצפי
    # =====================================================

    else:

        filter_formula = (
            "{בצפי}=1"
        )


    # =====================================================
    # שליפת הזמנות מ-Airtable
    # =====================================================

    records = get_all_airtable_records(
        AIRTABLE_ORDERS_TABLE,

        filter_formula=filter_formula,

        fields=[
            "מספר הזמנה",
            "שם לקוח",
            "סטטוס",
            "שורות ליקוט",
            "כמות משטחים",
            "תאריך אספקה",
            "בצפי",

            # לצורך מיון
            "עדיפות",
            "עדיפות קו הפצה",
            "לקוח",
        ],

        sort=[
            ("עדיפות", "desc"),
            ("תאריך אספקה", "asc"),
            ("עדיפות קו הפצה", "asc"),
            ("לקוח", "asc"),
        ],
    )


    # =====================================================
    # הכנת הפלט
    # =====================================================

    orders = []

    total_unpicked_lines = 0
    total_pallets = 0


    for record in records:

        fields = record.get(
            "fields",
            {}
        )


        order_number = clean_text(
            fields.get("מספר הזמנה")
        )


        customer_name = clean_text(
            fields.get("שם לקוח")
        )


        status = clean_text(
            fields.get("סטטוס")
        )


        picking_lines = int(
            clean_number(
                fields.get("שורות ליקוט"),
                0
            )
        )


        pallets = clean_number(
            fields.get("כמות משטחים"),
            0
        )


        delivery_date = clean_text(
            fields.get("תאריך אספקה")
        )


        # =================================================
        # שורות שעדיין לא סיימו ליקוט
        # =================================================

        if status in (
            "לפני יצור",
            "בליקוט",
        ):
            total_unpicked_lines += (
                picking_lines
            )


        total_pallets += pallets


        orders.append({

            "id":
                record["id"],

            "order_number":
                order_number,

            "customer_name":
                customer_name,

            "status":
                status,

            "picking_lines":
                picking_lines,

            "pallets":
                pallets,

            "delivery_date":
                delivery_date,
        })


    # =====================================================
    # תשובה ל-React
    # =====================================================

    return {

        # forecast = תצוגת בצפי
        # date = תצוגת תאריך מסוים
        "mode":
            "date" if date else "forecast",

        "selected_date":
            date,

        "summary": {

            "orders":
                len(orders),

            "unpicked_lines":
                total_unpicked_lines,

            "pallets":
                total_pallets,
        },

        "orders":
            orders,
    }