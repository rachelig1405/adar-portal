import os
import requests

from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from DB import (
    get_all_airtable_records,
    AIRTABLE_BASE_ID,
    AIRTABLE_TOKEN,
)


router = APIRouter()


AIRTABLE_DAILY_AREAS_TABLE = os.getenv(
    "AIRTABLE_DAILY_AREAS_TABLE"
)


class AreaScanRequest(BaseModel):
    record_id: str
    barcode: str


def airtable_headers():
    return {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }


def normalize_area(value):
    """
    1 / 1.0 / "1" -> "1"
    """

    if value is None:
        return ""

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))

    return str(value).strip()


# =========================================================
# שליפת האזור הבא שלא נסרק היום
# =========================================================

@router.get("/api/daily-area/next")
def get_next_daily_area():

    formula = (
        "OR("
            "{זמן}=BLANK(),"
            "NOT("
                "IS_SAME("
                    "{זמן},"
                    "TODAY(),"
                    "'day'"
                ")"
            ")"
        ")"
    )

    records = get_all_airtable_records(
        AIRTABLE_DAILY_AREAS_TABLE,

        filter_formula=formula,

        fields=[
            "אזור",
            "תיאור",
            "זמן",
        ],

        sort=[
            ("אזור", "asc"),
        ],
    )


    # הכל נסרק היום
    if not records:

        return {
            "done": True,
            "area": None,
        }


    record = records[0]

    fields = record.get(
        "fields",
        {}
    )


    return {
        "done": False,

        "area": {
            "id":
                record["id"],

            "area_number":
                normalize_area(
                    fields.get("אזור")
                ),

            "description":
                str(
                    fields.get(
                        "תיאור",
                        ""
                    )
                ),

            "last_scan":
                fields.get(
                    "זמן"
                ),
        }
    }


# =========================================================
# סריקת אזור
# =========================================================

@router.patch("/api/daily-area/scan")
def scan_daily_area(
    payload: AreaScanRequest
):

    # -----------------------------------------------------
    # מביאים את הרשומה לפי Record ID
    # -----------------------------------------------------

    table = quote(
        AIRTABLE_DAILY_AREAS_TABLE,
        safe=""
    )

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/"
        f"{table}/"
        f"{payload.record_id}"
    )


    response = requests.get(
        url,
        headers=airtable_headers(),
        timeout=20,
    )


    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )


    record = response.json()

    fields = record.get(
        "fields",
        {}
    )


    expected_barcode = normalize_area(
        fields.get("אזור")
    )

    scanned_barcode = str(
        payload.barcode
    ).strip()


    # -----------------------------------------------------
    # הברקוד לא שייך לאזור שמוצג
    # -----------------------------------------------------

    if scanned_barcode != expected_barcode:

        raise HTTPException(
            status_code=400,
            detail=(
                f"הברקוד שנסרק הוא "
                f"{scanned_barcode}, "
                f"אבל האזור הנדרש הוא "
                f"{expected_barcode}"
            )
        )


    # -----------------------------------------------------
    # עדכון זמן סריקה
    # -----------------------------------------------------

    now_utc = (
        datetime.now(timezone.utc)
        .isoformat()
    )


    update_response = requests.patch(
        url,

        headers=airtable_headers(),

        json={
            "fields": {
                "זמן": now_utc
            }
        },

        timeout=20,
    )


    if not update_response.ok:

        raise HTTPException(
            status_code=update_response.status_code,
            detail=update_response.text,
        )


    return {
        "success": True,
        "area_number": expected_barcode,
        "scan_time": now_utc,
    }