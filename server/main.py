import os
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from NewOrder import import_orders_excel
from fastapi import Query
from fastapi.responses import FileResponse
import shutil
import tempfile
import zipfile
from pathlib import Path
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
from CreateStickesr import process_excel
from Models import OrderCreate
from Models import PickingStart
from Models import CustomerCreate, PickingEnd,WorkdayAssignmentRequest
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_ORDERS_TABLE = os.getenv("AIRTABLE_ORDERS_TABLE")
AIRTABLE_CUSTOMERS_TABLE = os.getenv("AIRTABLE_CUSTOMERS_TABLE")
AIRTABLE_AGENTS_TABLE = os.getenv("AIRTABLE_AGENTS_TABLE")
AIRTABLE_WORKERS_TABLE= os.getenv("AIRTABLE_WORKERS_TABLE")
from DB import get_customers
from DB import create_customer
from DB import get_table_records
from DB import get_employees
from DB import get_orders_filter_by_status,update_order_workflow,upload_file_to_airtable,create_order
from WorkdayAssignment import workday_assignment

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://adar-portal-dxrr.vercel.app",
    ],
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "server is running"}



@app.get("/api/customers")
def get_Customers():
    return get_customers()
 


@app.post("/api/customers")
def CreateCustomer(customer:CustomerCreate)  :
   return create_customer(customer=customer)  
    
@app.get("/api/agents")
def get_agents():
    return get_table_records(AIRTABLE_AGENTS_TABLE, "סוכן")





@app.post("/api/orders")
def CreateOrder(order:OrderCreate):
    return create_order(order=order)

@app.get("/api/employees")
def GetEmployes():
    return get_employees()


@app.get("/api/orders/filter_by_status")
def Get_orders_filter_by_status(status: str = Query(..., description="סטטוס ההזמנות")):
    return get_orders_filter_by_status(status=status)
            


from datetime import datetime, timezone

from zoneinfo import ZoneInfo

@app.patch("/api/orders/start-picking")
def start_picking(data: PickingStart):
    record = update_order_workflow(
        data.order_id,
        employee_id=data.employee_id,
        status="בליקוט",
        start_time=True,
    )

    return {
        "success": True,
        "record": record,
    }




@app.patch("/api/orders/end-picking")
def end_picking(data: PickingEnd):
    record = update_order_workflow(
        data.order_id,
        status="מלוקט",
        end_time=True,
        amount=data.amount,
        notes=data.notes,
        invoice=data.invoice,
         break_minutes=data.break_minutes
    )

    return {
        "success": True,
        "record": record,
    }
@app.patch("/api/orders/check")
def check_order(data: PickingEnd):
    record = update_order_workflow(
        data.order_id,
        status="בבדיקה",
        notes=data.notes,
        amount=data.amount,
        invoice=data.invoice,
       
        
    )

    return {
        "success": True,
        "record": record,
        
    }
class LoadingOrder(BaseModel):
    order_id: str
    notes: str | None = None


class LoadingRequest(BaseModel):
    orders: list[LoadingOrder]

@app.patch("/api/orders/loading")
def loading_orders(data: LoadingRequest):

    results = []

    for order in data.orders:

        record = update_order_workflow(
            order.order_id,
            status="הועמס",
            LoadingNotes=order.notes
        )

        results.append(record)

    return {
        "success": True,
        "updated": len(results),
        "results": results
    }
from fastapi import FastAPI, File, Form, UploadFile
@app.patch("/api/orders/upload-file")
async def upload_order_file(
    order_id: str = Form(...),
    file: UploadFile = File(...)
):
    file_bytes = await file.read()

    result = upload_file_to_airtable(
        record_id=order_id,
        file_name=file.filename,
        content_type=file.content_type,
        file_bytes=file_bytes,
    )

    return {
        "success": True,
        "result": result,
    }
from fastapi import File, UploadFile

@app.post("/api/orders/import-excel")
async def importOrdersFromExcel(
    file: UploadFile = File(...)
):
    return await import_orders_excel(file)
@app.post("/api/workday-assignment")
def assign_order_to_workday(
    request: WorkdayAssignmentRequest
):
    try:
        result = workday_assignment(
            max_date=request.max_date,
            order_id=request.order_id,
        )

        return result

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
#יצירת סטיקרים
@app.post("/api/products/create-pdfs")
async def create_product_pdfs(
    excel_file: UploadFile = File(...),
    certificate_files: list[UploadFile] = File(...),
    certificate_paths: list[str] = Form(...),
):
    """
    מקבל:
    - קובץ Excel
    - תיקיית תעודות כקובצי PDF
    - הנתיב היחסי של כל תעודה בתוך התיקייה

    יוצר תיקיות מוצר ומחזיר ZIP להורדה.
    """

    excel_name = excel_file.filename or ""

    if not excel_name.lower().endswith(
        (".xlsx", ".xls")
    ):
        raise HTTPException(
            status_code=400,
            detail="יש להעלות קובץ Excel מסוג XLSX או XLS.",
        )

    if not certificate_files:
        raise HTTPException(
            status_code=400,
            detail="לא התקבלו קובצי תעודות.",
        )

    if len(certificate_files) != len(certificate_paths):
        raise HTTPException(
            status_code=400,
            detail="מספר הקבצים אינו תואם למספר הנתיבים.",
        )

    work_root = Path(
        tempfile.mkdtemp(
            prefix="portal_adar_products_"
        )
    )

    excel_dir = work_root / "excel"
    certificates_dir = work_root / "certificates"
    output_dir = work_root / "output"

    excel_dir.mkdir(parents=True, exist_ok=True)
    certificates_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ============================
        # שמירת קובץ האקסל
        # ============================

        safe_excel_name = Path(excel_name).name
        excel_path = excel_dir / safe_excel_name

        with excel_path.open("wb") as destination:
            while chunk := await excel_file.read(
                1024 * 1024
            ):
                destination.write(chunk)

        # ============================
        # שמירת תיקיית התעודות
        # ============================

        for uploaded_file, relative_path in zip(
            certificate_files,
            certificate_paths,
        ):
            if not uploaded_file.filename:
                continue

            if not uploaded_file.filename.lower().endswith(
                ".pdf"
            ):
                continue

            # מונע כתיבה מחוץ לתיקיית העבודה
            relative_file_path = Path(
                relative_path.replace("\\", "/")
            )

            safe_parts = [
                part
                for part in relative_file_path.parts
                if part not in ("", ".", "..")
            ]

            # בדרך כלל החלק הראשון הוא שם התיקייה
            if len(safe_parts) > 1:
                safe_parts = safe_parts[1:]

            if not safe_parts:
                safe_parts = [
                    Path(uploaded_file.filename).name
                ]

            destination_path = (
                certificates_dir.joinpath(*safe_parts)
            )

            destination_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with destination_path.open("wb") as destination:
                while chunk := await uploaded_file.read(
                    1024 * 1024
                ):
                    destination.write(chunk)

        # ============================
        # הרצת הפונקציה הקיימת
        # ============================

        result = process_excel(
            excel_path=str(excel_path),
            output_root=str(output_dir),
            certificate_folder=str(certificates_dir),
        )

        # שומרים גם סיכום של התהליך
        summary_path = output_dir / "סיכום_תהליך.txt"

        summary_lines = [
            "סיכום יצירת תיקי מוצר",
            "=" * 40,
            "",
            (
                f"מוצרים שנוצרו: "
                f"{result.get('created_products', 0)}"
            ),
            (
                f"שורות לא תקינות: "
                f"{result.get('invalid_rows', 0)}"
            ),
            (
                f"שגיאות נתונים: "
                f"{result.get('error_count', 0)}"
            ),
            (
                f"שגיאות תעודות: "
                f"{result.get('certificate_error_count', 0)}"
            ),
            (
                f"שגיאות תיקיות ישנות: "
                f"{result.get('old_folder_error_count', 0)}"
            ),
        ]

        summary_path.write_text(
            "\n".join(summary_lines),
            encoding="utf-8-sig",
        )

        # ============================
        # יצירת ZIP
        # ============================

        zip_path = work_root / "product_pdfs.zip"

        with zipfile.ZipFile(
            zip_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zip_file:
            for file_path in output_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                archive_name = file_path.relative_to(
                    output_dir
                )

                zip_file.write(
                    filename=file_path,
                    arcname=archive_name,
                )

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename="product_pdfs.zip",
            background=None,
        )

    except HTTPException:
        raise

    except Exception as error:
        shutil.rmtree(
            work_root,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=500,
            detail=f"שגיאה ביצירת הקבצים: {error}",
        ) from error