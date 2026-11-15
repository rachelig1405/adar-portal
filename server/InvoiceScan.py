import io
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
import json
import os
import requests
from DB import (
    get_all_airtable_records,
    AIRTABLE_BASE_ID,
    AIRTABLE_TOKEN,
)

AIRTABLE_INVOICE_DRAFTS_TABLE = os.getenv(
    "AIRTABLE_INVOICE_DRAFTS_TABLE"
)

router = APIRouter()


class InventoryScanRow(BaseModel):
    product_barcode: str
    quantity: float
    location: str


class InventoryScanExportRequest(BaseModel):
    rows: list[InventoryScanRow]
class InventoryDraftRequest(BaseModel):
    user_id: str
    rows: list[InventoryScanRow]
#שליפת טיוטה
@router.get("/api/inventory-scan/draft")
def get_inventory_draft(user_id: str):

    records = get_all_airtable_records(
        AIRTABLE_INVOICE_DRAFTS_TABLE,
        filter_formula=(
            f'AND('
             f'FIND("{user_id}", ARRAYJOIN({{Employee Record ID}})),'
            f'{{סטטוס}}="טיוטה"'
            f')'
        )
    )

    if not records:
        return {
            "rows": []
        }

    fields = records[0].get(
        "fields",
        {}
    )

    raw_data = fields.get(
        "נתונים",
        "[]"
    )

    try:
        rows = json.loads(raw_data)
    except Exception:
        rows = []

    return {
        "id": records[0]["id"],
        "rows": rows
    }
#שמירת טיוטה
@router.put("/api/inventory-scan/draft")
def save_inventory_draft(
    payload: InventoryDraftRequest
):

    records = get_all_airtable_records(
        AIRTABLE_INVOICE_DRAFTS_TABLE,
        filter_formula=(
            f'AND('
            f'FIND("{payload.user_id}", ARRAYJOIN({{Employee Record ID}})),'
            f'{{סטטוס}}="טיוטה"'
            f')'
        )
    )

    rows_json = json.dumps(
        [
            {
                "product_barcode":
                    row.product_barcode,

                "quantity":
                    row.quantity,

                "location":
                    row.location,
            }
            for row in payload.rows
        ],
        ensure_ascii=False
    )

    fields = {
        "עובד": [payload.user_id],
        "נתונים": rows_json,
        "סטטוס": "טיוטה"
    }

    if records:

        record_id = records[0]["id"]

        response = requests.patch(
            f"https://api.airtable.com/v0/"
            f"{AIRTABLE_BASE_ID}/"
            f"{AIRTABLE_INVOICE_DRAFTS_TABLE}/"
            f"{record_id}",

            headers={
                "Authorization":
                    f"Bearer {AIRTABLE_TOKEN}",

                "Content-Type":
                    "application/json",
            },

            json={
                "fields": fields
            },

            timeout=20,
        )

    else:

        response = requests.post(
            f"https://api.airtable.com/v0/"
            f"{AIRTABLE_BASE_ID}/"
            f"{AIRTABLE_INVOICE_DRAFTS_TABLE}",

            headers={
                "Authorization":
                    f"Bearer {AIRTABLE_TOKEN}",

                "Content-Type":
                    "application/json",
            },

            json={
                "fields": fields
            },

            timeout=20,
        )

    if not response.ok:
        raise HTTPException(
            status_code=500,
            detail=response.text
        )

    return {
        "success": True
    }
#מחקית הטיטה בסיום
@router.delete("/api/inventory-scan/draft")
def delete_inventory_draft(
    user_id: str
):


    records = get_all_airtable_records(
        AIRTABLE_INVOICE_DRAFTS_TABLE,
        filter_formula=(
            f'AND('
            f'FIND("{user_id}", ARRAYJOIN({{Employee Record ID}})),'
            f'{{סטטוס}}="טיוטה"'
            f')'
        )
    )

    for record in records:

        requests.delete(
            f"https://api.airtable.com/v0/"
            f"{AIRTABLE_BASE_ID}/"
            f"{AIRTABLE_INVOICE_DRAFTS_TABLE}/"
            f"{record['id']}",

            headers={
                "Authorization":
                    f"Bearer {AIRTABLE_TOKEN}"
            },

            timeout=20,
        )

    return {
        "success": True
    }

@router.post("/api/inventory-scan/export")
def export_inventory_scan(
    payload: InventoryScanExportRequest
):
    if not payload.rows:
        raise HTTPException(
            status_code=400,
            detail="אין נתונים לייצוא"
        )

    wb = Workbook()

    ws = wb.active
    ws.title = "חשבונית בסריקה"

    # גיליון מימין לשמאל
    ws.sheet_view.rightToLeft = True

    headers = [
        "ברקוד",
        "כמות",
        "מיקום",
    ]

    ws.append(headers)

    # כותרות
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(
            horizontal="center"
        )

    for row in payload.rows:
        ws.append([
            str(row.product_barcode),
            row.quantity,
            str(row.location),
        ])

        current_row = ws.max_row

        # קריטי:
        # ברקוד כמחרוזת כדי שלא יאבד ספרות באקסל
        ws.cell(
            row=current_row,
            column=1
        ).number_format = "@"

        # גם מיקום נשמר כטקסט
        ws.cell(
            row=current_row,
            column=3
        ).number_format = "@"

    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 25

    ws.freeze_panes = "A2"

    ws.auto_filter.ref = (
        f"A1:C{ws.max_row}"
    )

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    filename = (
        "חשבונית_בסריקה"
        + datetime.now().strftime(
            "%Y-%m-%d_%H-%M"
        )
        + ".xlsx"
    )

    encoded_filename = quote(filename)

    return StreamingResponse(
        output,
        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                f"attachment; "
                f"filename*=UTF-8''"
                f"{encoded_filename}"
        },
    )