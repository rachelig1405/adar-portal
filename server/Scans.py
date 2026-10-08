import os
from pydantic import BaseModel 
from datetime import datetime, timezone,date
import requests

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel

from DB import (
    airtable_headers,
    get_all_airtable_records,
)
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_LOADINGS_TABLE = os.getenv(
    "AIRTABLE_LOADINGS_TABLE"
)

AIRTABLE_LOADING_SCANS_TABLE = os.getenv(
    "AIRTABLE_LOADING_SCANS_TABLE"
)
AIRTABLE_ORDERS_TABLE = os.getenv(
    "AIRTABLE_ORDERS_TABLE"
)
class ScanRequest(BaseModel):
    order_number: str
    worker_id: str
    notes: str | None = None
    confirm_overage: bool = False
#פונקציה למציאת או יצירת העמסה
def get_or_create_today_loading():
    now = datetime.now(
        ZoneInfo("Asia/Jerusalem")
    )

    today = now.date().isoformat()

    records = get_all_airtable_records(
        AIRTABLE_LOADINGS_TABLE,
        filter_formula=(
            'AND('
                'IS_SAME('
                    '{זמן},'
                    f'DATETIME_PARSE("{today}"),'
                    '"day"'
                '),'
                '{סטטוס}="פתוחה"'
            ')'
        ),
    )

    # קיימת העמסה פתוחה היום
    if records:
        return records[0]

    # אין - יוצרים העמסה חדשה
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{AIRTABLE_LOADINGS_TABLE}"
    )

    fields = {
        "זמן": now.isoformat(),
        "סטטוס": "פתוחה",
    }

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

    return response.json()
#פונקציה למציאת ההזמנה שנסרקה
def find_order_by_number(
    order_number: str
):
    order_number = str(order_number).strip()

    safe_order_number = (
        order_number
        .replace("\\", "\\\\")
        .replace('"', '\\"')
    )

    records = get_all_airtable_records(
        AIRTABLE_ORDERS_TABLE,
        filter_formula=(
            f'({{מספר הזמנה}} & "")='
            f'"{safe_order_number}"'
        ),
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail=(
                f"הזמנה {order_number} "
                "לא נמצאה במערכת"
            ),
        )

    return records[0]
#פונקיית הסריקה
def create_loading_scan(
    scan: ScanRequest
):
    now = datetime.now(
        ZoneInfo("Asia/Jerusalem")
    )

    # --------------------------------
    # 1. מציאת / יצירת העמסה של היום
    # --------------------------------

    loading_record = (
        get_or_create_today_loading()
    )

    loading_id = loading_record["id"]

    # --------------------------------
    # 2. מציאת ההזמנה
    # --------------------------------

    order_record = find_order_by_number(
        scan.order_number
    )

    order_id = order_record["id"]

    order_fields = order_record.get(
        "fields",
        {}
    )

    # --------------------------------
    # 3. הצפי שהבודק הזין
    # --------------------------------

    expected = (
        order_fields.get(
            "כמות משטחים",
            0
        )
        or 0
    )

    # --------------------------------
    # 4. כמה כבר הועמסו
    # זה שדה Count ב-Airtable
    # --------------------------------

    loaded = (
        order_fields.get(
            "משטחים שהועמסו",
            0
        )
        or 0
    )

    # --------------------------------
    # 5. בדיקת חריגה מהצפי
    # --------------------------------

    is_overage = (
        expected > 0
        and loaded >= expected
    )

    # אם כבר הגענו לצפי,
    # לא יוצרים עדיין סריקה.
    # מחזירים ל-Frontend בקשת אישור.
    if (
        is_overage
        and not scan.confirm_overage
    ):
        return {
            "success": False,
            "code": "OVER_EXPECTED",
            "message": (
                "הגעת לכמות המשטחים "
                "שהוגדרה להזמנה."
            ),
            "order_number": scan.order_number,
            "expected": expected,
            "loaded": loaded,
            "remaining": 0,
            "requires_confirmation": True,
        }

    # --------------------------------
    # 6. יצירת רשומת סריקה
    # --------------------------------

    scan_fields = {
        "תאריך ושעה": now.isoformat(),

        # Link to הזמנות
        "הזמנה": [order_id],

        # Link to עובדים
        "עובד": [scan.worker_id],

        # Link to העמסות
        "העמסות": [loading_id],

        "יש חריגה": is_overage,
    }

    if is_overage:
        scan_fields["סוג חריגה"] = (
            "מעל הצפי"
        )

    if scan.notes:
        scan_fields["הערות"] = (
            scan.notes
        )

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{AIRTABLE_LOADING_SCANS_TABLE}"
    )

    response = requests.post(
        url,
        headers=airtable_headers(),
        json={
            "fields": scan_fields
        },
        timeout=30,
    )

    if response.status_code not in (
        200,
        201,
    ):
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    created_scan = response.json()

    # --------------------------------
    # 7. נתונים להחזרה למסך
    # --------------------------------

    loaded_after = loaded + 1

    remaining = max(
        expected - loaded_after,
        0
    )

    return {
        "success": True,

        "loading_id": loading_id,

        "scan_id": created_scan["id"],

        "order_id": order_id,

        "order_number": scan.order_number,

        "expected": expected,

        "loaded": loaded_after,

        "remaining": remaining,

        "exception": is_overage,
    }