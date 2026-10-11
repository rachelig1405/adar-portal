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
class FinishLoadingRequest(BaseModel):
    worker_id: str
    notes: str | None = None
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
        )
    )

    if not records:
        return None

    return records[0]
def finish_loading(
    request: FinishLoadingRequest
):
    now = datetime.now(
        ZoneInfo("Asia/Jerusalem")
    )

    # --------------------------------
    # 1. מציאת ההעמסה הפתוחה
    # --------------------------------

    loading = get_today_open_loading()

    if not loading:
        raise HTTPException(
            status_code=404,
            detail="לא נמצאה העמסה פתוחה להיום"
        )

    loading_id = loading["id"]

    # --------------------------------
    # 2. קבלת סיכום ההעמסה
    # --------------------------------

    loading_summary = get_loading_summary()

    orders = loading_summary.get(
        "orders",
        []
    )

    # --------------------------------
    # 3. מציאת פערים
    # --------------------------------

    gaps = []

    for order in orders:
        expected = (
            order.get("expected", 0)
            or 0
        )

        loaded = (
            order.get("loaded", 0)
            or 0
        )

        gap = loaded - expected

        if gap != 0:
            gaps.append({
                "order_id": (
                    order.get("order_id")
                ),
                "order_number": (
                    order.get("order_number")
                ),
                "customer": (
                    order.get("customer", "")
                ),
                "expected": expected,
                "loaded": loaded,
                "gap": gap,
            })

    # --------------------------------
    # 4. קביעת סטטוס
    # --------------------------------

    if len(gaps) == 0:
        status = "נסגרה תקין"
    else:
        status = "נסגרה עם חריגות"

    # --------------------------------
    # 5. עדכון רשומת ההעמסה
    # --------------------------------

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{AIRTABLE_LOADINGS_TABLE}/"
        f"{loading_id}"
    )

    fields = {
        "סטטוס": status,
        "זמן סיום": now.isoformat(),
        "נסגר על ידי": [
            request.worker_id
        ],
        "פערים": len(gaps),
    }

    if request.notes:
        fields["הערות"] = request.notes

    response = requests.patch(
        url,
        headers=airtable_headers(),
        json={
            "fields": fields
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

    # --------------------------------
    # 6. תשובה למסך
    # --------------------------------

    return {
        "success": True,
        "loading_id": loading_id,
        "status": status,
        "summary": loading_summary[
            "summary"
        ],
        "gaps": gaps,
        "message": (
            "העמסה נסגרה בהצלחה"
            if not gaps
            else
            "העמסה נסגרה עם חריגות"
        ),
    }