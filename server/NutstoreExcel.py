
import os
import re
import hmac
from io import BytesIO
from datetime import datetime
from urllib.parse import urljoin, unquote
from xml.etree import ElementTree as ET

import requests
from fastapi import APIRouter, Header, HTTPException
from python_calamine import CalamineWorkbook

router = APIRouter()

BASE = "https://dav.jianguoyun.com"
FOLDER = (
    "/dav/EYAL/OZ%20VEHADAR/"
    "BA%20OZ%20VHADAR%20NISIM/"
    "BOOKS%20IN%20PRODUCTION/"
)
SHEET = "Processing orders-生产中"

WANTED = {
    "FACTORY ITEM NO": "factory_item_no",
    "CONFIRM FILE": "confirm_file",
    "COVER": "cover",
    "PORZAZ": "porzaz",
}


@router.get("/api/automation/nutstore-orders")
def read_nutstore_orders(
    x_automation_key: str = Header(default="")
):
    secret = os.getenv("MAKE_AUTOMATION_KEY", "")

    if not secret or not hmac.compare_digest(
        x_automation_key, secret
    ):
        raise HTTPException(401, "Unauthorized")

    username = os.getenv("NUTSTORE_EMAIL")
    password = os.getenv("NUTSTORE_APP_PASSWORD")

    if not username or not password:
        raise HTTPException(
            500, "Nutstore credentials not configured"
        )

    auth = (username, password)
    folder_url = BASE + FOLDER

    # איתור קובצי Excel בתיקייה
    response = requests.request(
        "PROPFIND",
        folder_url,
        auth=auth,
        headers={"Depth": "1"},
        timeout=(15, 60),
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)
    candidates = []

    pattern = re.compile(
        r"^EYAL-PRODUCTION FILE "
        r"(\d{4}\.\d{2}\.\d{2})\.xlsx$",
        re.IGNORECASE,
    )

    for node in root.findall(
        ".//{DAV:}response"
    ):
        href = node.findtext("{DAV:}href")
        if not href:
            continue

        filename = unquote(href).rstrip("/").split("/")[-1]
        match = pattern.fullmatch(filename)

        if match:
            try:
                file_date = datetime.strptime(
                    match.group(1), "%Y.%m.%d"
                )
                candidates.append((file_date, href))
            except ValueError:
                continue

    if not candidates:
        raise HTTPException(
            404, "No matching Excel file found"
        )

    # בחירת הקובץ עם התאריך המאוחר ביותר בשם
    _, href = max(candidates, key=lambda x: x[0])
    file_url = urljoin(BASE, href)
    filename = unquote(href).split("/")[-1]

    # הורדת האקסל לשרת Python בלבד
    response = requests.get(
        file_url,
        auth=auth,
        timeout=(15, 180),
    )
    response.raise_for_status()

    # בדיקת הגודל לפני פתיחת הקובץ
    if len(response.content) > 80 * 1024 * 1024:
        raise HTTPException(413, "File too large")

    workbook = CalamineWorkbook.from_filelike(
        BytesIO(response.content)
    )

    if SHEET not in workbook.sheet_names:
        raise HTTPException(
            404, f"Worksheet not found: {SHEET}"
        )

    values = workbook.get_sheet_by_name(
        SHEET
    ).to_python(skip_empty_area=False)

    # איתור שורת הכותרות
    header_index = None
    indexes = {}

    for i, row in enumerate(values[:50]):
        normalized = [
            str(v or "").strip().upper()
            for v in row
        ]

        if all(name in normalized for name in WANTED):
            header_index = i
            indexes = {
                name: normalized.index(name)
                for name in WANTED
            }
            break

    if header_index is None:
        raise HTTPException(
            422, "Required column headers not found"
        )

    results = []
    total = 0

 
    for excel_index, row in enumerate(
        values[header_index + 1:],
        start=header_index + 2,
    ):
        item = {"excel_row": excel_index}

        # קריאת ארבע העמודות
        for source, target in WANTED.items():
            idx = indexes[source]
            value = row[idx] if idx < len(row) else None
            item[target] = (
                str(value).strip()
                if value is not None else ""
            )

        # דילוג על שורה שאין בה מספר פריט
        if not item["factory_item_no"]:
            continue

        # בדיקה אילו שדות ריקים בשורה
        missing = [
            column
            for column in (
                "CONFIRM FILE",
                "COVER",
                "PORZAZ"
            )
            if not item[WANTED[column]]
        ]

        # דילוג על שורות ללא חוסרים
        if not missing:
            continue

        # הוספת רשימת החוסרים לתוצאה
        item["missing"] = missing

        total += 1

        
        results.append(item)


    return {
        "filename": filename,
        "sheet": SHEET,
        "total_matching_rows": total,
        "returned_rows": len(results),
        "preview_only": False,
        "rows": results,
    }
