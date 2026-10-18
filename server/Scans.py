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
    update_order_workflow
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
    confirm_not_in_forecast: bool = False
    confirm_not_in_line: bool = False
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

   loading =
    get_today_open_loading()

    if not loading:
        return {
            "success": False,
            "code": "NO_OPEN_LOADING",
            "message": "לא קיימת העמסה פתוחה",
        }

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
    in_forecast = (
    order_fields.get("בצפי", 0)
    or 0
)  
    line= order_fields.get("קו הפצה", "")
    




    is_not_in_forecast = (
        int(in_forecast) != 1
    )
    
    if (
    is_not_in_forecast
    and not scan.confirm_not_in_forecast
    
):
        return {
            "success": False,
            "code": "NOT_IN_FORECAST",
            "message": (
                "משטח זה לא מופיע "
                "בצפי האספקה להיום."
            ),
            "order_number": scan.order_number,
            "customer": (
                order_fields.get(
                    "שם לקוח",
                    ""
                )
                or ""
            ),
            "requires_confirmation": True,
        }
    if (
        line!="סוסנא"
        and not scan.confirm_not_in_line
    
):
        return {
                "success": False,
                "code": "NOT_IN_LINE",
                "message": (
                    "משטח זה לא מופיע "
                    "בקו הפצה סוסנא"
                ),
                "order_number": scan.order_number,
                "customer": (
                    order_fields.get(
                        "שם לקוח",
                        ""
                    )
                    or ""
                ),
                "requires_confirmation": True,
        }
    #בדיקה אם ההזמנה עברה בדיקה
    status=order_fields.get("סטטוס", "")
    if(status!="בבדיקה"):
        return{
            "success": False,
                "code": "NOT_CHECKED",
                "message": (
                    "אין להעמיס הזמנה שלא נבדקה "
                
                ),
                "order_number": scan.order_number,
                "customer": (
                    order_fields.get(
                        "שם לקוח",
                        ""
                    )
                    or ""
                ),
                "requires_confirmation": True,
        }
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
    has_exception = (
        is_overage
        or is_not_in_forecast
        or line!="סוסנא"
)
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

        "יש חריגה": has_exception,
    }
    if is_not_in_forecast:
        scan_fields["סוג החריגה"] = "לא בצפי"

    elif is_overage:
        scan_fields["סוג החריגה"] = "מעל הצפי"

    if line !="סוסנא":
        scan_fields["סוג החריגה"] = (
            "לא בקו הפצה סוסנא"
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
    if remaining==0:
        update_order_workflow(order_id=order_id,status="הועמס")


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
def get_loading_summary():
    now = datetime.now(
        ZoneInfo("Asia/Jerusalem")
    )

    today = now.date().isoformat()

    # ==========================================
    # 1. כל ההזמנות שנמצאות בצפי + קו סוסנא
    # ==========================================

    orders = get_all_airtable_records(
        AIRTABLE_ORDERS_TABLE,
        filter_formula=(
            'AND('
            '{בצפי}=1,'
            '{קו הפצה}="סוסנא"'
            ')'
        )
    )

    # ==========================================
    # 2. כל הסריקות שבוצעו היום
    # ==========================================

    scans_today = get_all_airtable_records(
        AIRTABLE_LOADING_SCANS_TABLE,
        filter_formula=(
            'IS_SAME('
            '{תאריך ושעה},'
            f'DATETIME_PARSE("{today}"),'
            '"day"'
            ')'
        )
    )

    # כל רשומת סריקה = משטח אחד שהועמס
    total_loaded = len(scans_today)

    # ==========================================
    # 3. חישוב הצפי והנותר
    # ==========================================

    total_expected = 0
    total_remaining = 0

    order_list = []

    for record in orders:
        fields = record.get(
            "fields",
            {}
        )

        expected = (
            fields.get(
                "כמות משטחים",
                0
            )
            or 0
        )

        loaded = (
            fields.get(
                "משטחים שהועמסו",
                0
            )
            or 0
        )

        expected = int(expected)
        loaded = int(loaded)

        remaining = max(
            expected - loaded,
            0
        )

        total_expected += expected

        # חשוב:
        # הנותר מחושב לכל הזמנה שבצפי
        # ולא לפי כלל הסריקות
        total_remaining += remaining

        order_list.append({
            "order_id": record["id"],

            "order_number": (
                fields.get(
                    "מספר הזמנה",
                    ""
                )
            ),

            "customer": (
                fields.get(
                    "שם לקוח",
                    ""
                )
                or ""
            ),

            "expected": expected,

            "loaded": loaded,

            "remaining": remaining,

            "complete": (
                loaded >= expected
                and expected > 0
            ),

            "over": (
                loaded > expected
            ),
        })

    # ==========================================
    # 4. תשובה
    # ==========================================

    return {
        "success": True,

        "summary": {
            "expected": total_expected,

            # כל הסריקות היום
            "loaded": total_loaded,

            # רק מה שעדיין חסר להזמנות שבצפי
            "remaining": total_remaining,
        },

        "orders": order_list,
    }
    //פונקציה שמחפשת העמסה
    def get_today_open_loading():
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

    if not records:
        return None

    return records[0]