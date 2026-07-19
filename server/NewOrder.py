#קליטת הזמנה  מאקסל
from Models import OrderCreate
from io import BytesIO
from datetime import date, datetime
import os
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

from fastapi import File, UploadFile
from python_calamine import CalamineWorkbook
from fastapi import FastAPI
from DB import create_order,find_customer_record_id,find_agent_record_id


AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_ORDERS_TABLE = os.getenv("AIRTABLE_ORDERS_TABLE")
AIRTABLE_CUSTOMERS_TABLE = os.getenv("AIRTABLE_CUSTOMERS_TABLE")
AIRTABLE_AGENTS_TABLE = os.getenv("AIRTABLE_AGENTS_TABLE")
AIRTABLE_WORKERS_TABLE= os.getenv("AIRTABLE_WORKERS_TABLE")

def normalize_header(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def normalize_text(value) -> str:
    if value is None:
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text


def normalize_boolean(value) -> bool:
    if isinstance(value, bool):
        return value

    text = normalize_text(value).lower()

    return text in {
        "1",
        "true",
        "yes",
        "כן",
        "וי",
        "v",
    }


def normalize_integer(value) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_date(value) -> str | None:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    text = normalize_text(value)

    for date_format in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d.%m.%Y",
    ):
        try:
            return datetime.strptime(
                text,
                date_format,
            ).date().isoformat()
        except ValueError:
            continue

    raise ValueError(
        f"תאריך לא תקין: {text}"
    )



async def import_orders_excel(
    file: UploadFile
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="לא התקבל שם קובץ",
        )

    if not file.filename.lower().endswith(
        (".xlsx", ".xlsm")
    ):
        raise HTTPException(
            status_code=400,
            detail="יש להעלות קובץ Excel מסוג XLSX",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="הקובץ ריק",
        )

    try:
        workbook = CalamineWorkbook.from_filelike(
            BytesIO(file_bytes)
        )

        sheet_names = workbook.sheet_names

        if not sheet_names:
            raise ValueError(
                "לא נמצאו גיליונות בקובץ"
            )

        sheet = workbook.get_sheet_by_name(
            sheet_names[0]
        )

        rows = sheet.to_python()

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"שגיאה בקריאת האקסל: {error}",
        )

    if len(rows) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "הקובץ צריך להכיל כותרות "
                "ולפחות שורת הזמנה אחת"
            ),
        )

    headers = [
        normalize_header(value)
        for value in rows[0]
    ]

    required_headers = {
        "הזמנה",
        "לקוח",
    }

    missing_headers = (
        required_headers - set(headers)
    )

    if missing_headers:
        raise HTTPException(
            status_code=400,
            detail=(
                "חסרות עמודות חובה: "
                + ", ".join(missing_headers)
            ),
        )

    header_indexes = {
        header: index
        for index, header in enumerate(headers)
        if header
    }

    def get_value(row, header):
        index = header_indexes.get(header)

        if index is None:
            return None

        if index >= len(row):
            return None

        return row[index]

    successes = []
    errors = []

    customer_cache: dict[str, str | None] = {}
    agent_cache: dict[str, str | None] = {}
    data_rows = rows[1:] 

    for i, row in enumerate(data_rows):
   
        excel_row_number = i+2

        order_number = normalize_text(
            get_value(row, "הזמנה")
        )
        next_order_number = None

    # האם קיימת שורה הבאה?
        if i + 1 < len(data_rows):
            next_row = data_rows[i + 1]

            next_order_number = normalize_text(
            get_value(next_row, "הזמנה")
            )
        if next_order_number !=order_number:
            customer_number = normalize_text(
            row[2] if len(row) > 2 else None
            )

            # דילוג על שורה ריקה
            if not order_number and not customer_number:
                continue

            try:
                if not order_number:
                    raise ValueError(
                        "מספר הזמנה חסר"
                )

                if not customer_number:
                    raise ValueError(
                        "מספר לקוח חסר"
                )

                if customer_number not in customer_cache:
                    customer_cache[customer_number] = (
                        find_customer_record_id(
                            customer_number
                    )
                )

                customer_id = customer_cache[
                    customer_number
            ]

                if not customer_id:
                    raise ValueError(
                        f"לא נמצא לקוח מספר "
                        f"{customer_number}"
                )

                agent_name = normalize_text(
                    get_value(row, "סוכן")
            )

                agent_id = None

                if agent_name:
                    if agent_name not in agent_cache:
                        agent_cache[agent_name] = (
                            find_agent_record_id(
                                agent_name
                        )
                    )

                    agent_id = agent_cache[
                        agent_name
                    ]

                    if not agent_id:
                        raise ValueError(
                            f"לא נמצא סוכן: "
                            f"{agent_name}"
                    )

                delivery_date = normalize_date(
                    get_value(
                        row,
                        "ת.אספקה",
                )
            )

                picking_rows = normalize_integer(
                    get_value(
                        row,
                        "ש.",
                    )
            )

                goes_with_us = None
                    
            

                line = None

                delivery_notes = normalize_text(
                    get_value(
                        row,
                        "הערה",
                )
            )

                warehouse_notes = normalize_text(
                    get_value(
                        row,
                        "הערה",
                )
            )
                order = OrderCreate(
                        order_number=order_number,
                        customer_id=customer_id,
                        agent_id=agent_id,
                        delivery_date=delivery_date,
                        picking_rows=picking_rows,
                        goes_with_us=goes_with_us,
                        line=line,
                        delivery_notes=delivery_notes,
                        warehouse_notes=warehouse_notes,
                )


                record = create_order(
                    order
            )   

                successes.append({
                    "excel_row": excel_row_number,
                    "order_number": order_number,
                    "record_id": record["id"],
            })

            except HTTPException as error:
                errors.append({
                    "excel_row": excel_row_number,
                    "order_number": order_number,
                    "error": error.detail,
            })

            except Exception as error:
                errors.append({
                    "excel_row": excel_row_number,
                    "order_number": order_number,
                    "error": str(error),
                })

    return {
     "success": len(errors) == 0,
     "created_count": len(successes),
     "failed_count": len(errors),
     "created": successes,
     "errors": errors,
    
            }