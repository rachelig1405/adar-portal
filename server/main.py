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
from fastapi import BackgroundTasks
from pathlib import Path
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
from CreateStickesr import process_excel
from Models import OrderCreate
from Models import PickingStart
from typing import Optional
from Models import CustomerCreate, PickingEnd,WorkdayAssignmentRequest,LoginRequest,ChatMessageCreate
#הגדרת נתיב לדיסק
import uuid
import traceback
PERSISTENT_STORAGE = Path("/var/data")
PERSISTENT_STORAGE.mkdir(parents=True, exist_ok=True)
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_ORDERS_TABLE = os.getenv("AIRTABLE_ORDERS_TABLE")
AIRTABLE_CUSTOMERS_TABLE = os.getenv("AIRTABLE_CUSTOMERS_TABLE")
AIRTABLE_AGENTS_TABLE = os.getenv("AIRTABLE_AGENTS_TABLE")
AIRTABLE_WORKERS_TABLE= os.getenv("AIRTABLE_WORKERS_TABLE")
AIRTABLE_USERS_TABLE = os.getenv(
    "AIRTABLE_USERS_TABLE"
)
from DB import get_customers
from DB import create_customer
from DB import get_table_records
from DB import get_employees
from DB import get_orders_filter_by_status,update_order_workflow,upload_file_to_airtable,create_order,get_airtable_user,create_chat_message,get_chat_messages,get_all_airtable_records
from WorkdayAssignment import workday_assignment
from fastapi.responses import PlainTextResponse
from OrdersStickers import create_today_orders_zpl
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)
from requests import Response

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
def Get_orders_filter_by_status(status: str = Query(..., description="סטטוס ההזמנות"), action: Optional[int] = Query(None, description="פעולה"),
    user_id: Optional[str] = Query(None, description="מזהה המשתמש"),):
    return get_orders_filter_by_status(status=status,action=action,user_id=user_id)
   


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
            LoadingNotes=order.notes,
            amount=order.amount
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
    print(
        "===== WORKDAY ASSIGNMENT START =====",
        flush=True
    )
    print(
        "max_date:",
        request.max_date,
        "order_id:",
        request.order_id,
        flush=True
    )

    try:
        result = workday_assignment(
            max_date=request.max_date,
            order_id=request.order_id,
        )

        print(
            "WORKDAY RESULT:",
            result,
            flush=True
        )

        return result

    except HTTPException:
        raise

    except Exception as error:

        print(
            "===== WORKDAY ASSIGNMENT ERROR =====",
            flush=True
        )

        traceback.print_exc()

        print(
            "ERROR:",
            repr(error),
            flush=True
        )

        print(
            "====================================",
            flush=True
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
#יצירת סטיקרים
import json
import uuid
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# תיקייה לשמירת סטטוס ה-jobs על הדיסק במקום בזיכרון.
# חייבת להיות באותו נתיב זמני שהתהליכים כותבים אליו, כדי לא לבזבז עוד מקום.
'''
JOBS_DIR = Path(tempfile.gettempdir()) / "portal_adar_jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)
'''
JOBS_DIR = PERSISTENT_STORAGE / "jobs_status"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

def _job_file(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def create_pdf_job() -> str:
    job_id = str(uuid.uuid4())
    job_data = {
        "status": JobStatus.PENDING,
        "progress": 0,
        "total": 0,
        "zip_path": None,
        "error": None,
        "work_root": None,
    }
    _job_file(job_id).write_text(
        json.dumps(job_data, ensure_ascii=False),
        encoding="utf-8",
    )
    return job_id


def read_job(job_id: str) -> dict | None:
    path = _job_file(job_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def update_job(job_id: str, **updates):
    job_data = read_job(job_id) or {}
    job_data.update(updates)
    _job_file(job_id).write_text(
        json.dumps(job_data, ensure_ascii=False),
        encoding="utf-8",
    )
async def run_create_pdfs_job(job_id: str, excel_path: Path, output_dir: Path, work_root: Path):
    try:
        update_job(job_id, status=JobStatus.RUNNING, work_root=str(work_root))

        def progress_callback(progress_index: int, total: int):
            update_job(job_id, progress=progress_index, total=total)

        result = await process_excel(
            excel_path=str(excel_path),
            output_root=str(output_dir),
            progress_callback=progress_callback,
        )

        zip_path = result.get("zip_path")

        summary_lines = [
            "סיכום יצירת תיקי מוצר",
            "=" * 40,
            "",
            f"מוצרים שנוצרו: {result.get('created_products', 0)}",
            f"שורות לא תקינות: {result.get('invalid_rows', 0)}",
            f"שגיאות נתונים: {result.get('error_count', 0)}",
            f"שגיאות תיקיות ישנות: {result.get('old_folder_error_count', 0)}",
        ]

        summary_text = "\n".join(summary_lines)

        # מוסיפים את הסיכום ישירות לתוך ה-ZIP הקיים, כדי שהוא יירד יחד עם שאר הקבצים
        if zip_path and Path(zip_path).exists():
            with zipfile.ZipFile(zip_path, mode="a", compression=zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr("סיכום_תהליך.txt", summary_text.encode("utf-8-sig"))

        update_job(job_id, zip_path=str(zip_path) if zip_path else None, status=JobStatus.DONE)

    except Exception as error:
        update_job(job_id, status=JobStatus.FAILED, error=str(error))
        shutil.rmtree(work_root, ignore_errors=True)
   
    #יצירת סטיקרים - פותחת job ברקע ומחזירה מיידית job_id

@app.post("/api/products/create-pdfs")
async def create_product_pdfs(
    background_tasks: BackgroundTasks,
    excel_file: UploadFile = File(...),
):
    excel_name = excel_file.filename or ""

    if not excel_name.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="יש להעלות קובץ Excel מסוג XLSX או XLS.",
        )

    # במקום tempfile.mkdtemp() (שכותב ל-/tmp, מוגבל ל-2GB) -
    # יוצרים תיקייה בתוך הדיסק הקבוע (10GB)
    work_root = PERSISTENT_STORAGE / f"job_{uuid.uuid4()}"
    work_root.mkdir(parents=True, exist_ok=True)

    excel_dir = work_root / "excel"
    output_dir = work_root / "output"

    excel_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_excel_name = Path(excel_name).name
    excel_path = excel_dir / safe_excel_name

    with excel_path.open("wb") as destination:
        while chunk := await excel_file.read(1024 * 1024):
            destination.write(chunk)

    job_id = create_pdf_job()

    background_tasks.add_task(
        run_create_pdfs_job,
        job_id=job_id,
        excel_path=excel_path,
        output_dir=output_dir,
        work_root=work_root,
    )

    return {"job_id": job_id}


#בדיקת סטטוס יצירת הסטיקרים
@app.get("/api/products/create-pdfs/status/{job_id}")
def get_create_pdfs_status(job_id: str):
    job = read_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job לא נמצא")

    response = {
        "status": job["status"],
        "progress": job["progress"],
        "total": job["total"],
    }

    if job["status"] == JobStatus.FAILED:
        response["error"] = job["error"]

    return response

'''
#הורדת קובץ ה-ZIP המוכן
@app.get("/api/products/create-pdfs/download/{job_id}")
def download_create_pdfs_zip(job_id: str):
    job = read_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job לא נמצא")

    if job["status"] != JobStatus.DONE:
        raise HTTPException(status_code=409, detail="הקובץ עדיין לא מוכן")

    zip_path = job["zip_path"]

    if not zip_path or not Path(zip_path).exists():
        raise HTTPException(status_code=404, detail="קובץ ה-ZIP לא נמצא")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename="product_pdfs.zip",
    )
 '''
@app.get("/api/products/create-pdfs/download/{job_id}")
def download_create_pdfs_zip(job_id: str, background_tasks: BackgroundTasks):
    job = read_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job לא נמצא")

    if job["status"] != JobStatus.DONE:
        raise HTTPException(status_code=409, detail="הקובץ עדיין לא מוכן")

    zip_path = job["zip_path"]

    if not zip_path or not Path(zip_path).exists():
        raise HTTPException(status_code=404, detail="קובץ ה-ZIP לא נמצא")

    work_root = job.get("work_root")

    def cleanup_after_download():
        if work_root and Path(work_root).exists():
            shutil.rmtree(work_root, ignore_errors=True)

        _job_file(job_id).unlink(missing_ok=True)

    background_tasks.add_task(cleanup_after_download)

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename="product_pdfs.zip",
        background=background_tasks,
    )
@app.post("/api/login")
def login(data: LoginRequest):
    username = data.username.strip()
    password = data.password.strip()
    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail="יש להזין שם משתמש וסיסמה",
        )
    try:
        user_record = get_airtable_user(username)
    except Exception as error:
        print("Login error:", error)
        raise HTTPException(
            status_code=500,
            detail="שגיאה בחיבור לשרת",
        )
    if not user_record:
        raise HTTPException(
            status_code=401,
            detail="שם המשתמש או הסיסמה שגויים",
        )
    fields = user_record.get("fields", {})
    saved_password = str(
        fields.get("סיסמא", "")
    ).strip()
    print(saved_password)
    if saved_password != password:
        raise HTTPException(
            status_code=401,
            detail="שם המשתמש או הסיסמה שגויים",
        )
    if not fields.get("פעיל", False):
        raise HTTPException(
            status_code=403,
            detail="המשתמש אינו פעיל",
        )
    return {
        "success": True,
        "user": {
            "username": fields.get("שם משתמש", ""),
            "name": fields.get("שם", ""),
            "role": fields.get("תפקיד", ""),
            "id": user_record["id"]
        },
    }
#הדפסת מדבקות להזמנות להיום
@app.get(
    "/api/labels/today",
    response_class=PlainTextResponse,
)
def print_today_labels():
    return create_today_orders_zpl()
@app.get("/api/chat/messages")
def api_get_chat_messages(
    limit: int = Query(100, ge=1, le=200),
):
    return get_chat_messages(limit=limit)
@app.post("/api/chat/messages")
def api_create_chat_message(
    data: ChatMessageCreate,
):
    created_record = create_chat_message(
        user_id=data.user_id,
        message=data.message,
    )
    return {
        "success": True,
        "id": created_record["id"],
        "message": "ההודעה נשלחה בהצלחה",
    }
#הדפסת מדבקות לפי מספר הזמנה
@app.get("/api/labels/order/{order_number}")
def get_order_label(order_number: str):
    records = get_all_airtable_records(
        AIRTABLE_ORDERS_TABLE,
        filter_formula=f'{{מספר הזמנה}}="{order_number}"'
    )
    if not records:
        raise HTTPException(
            status_code=404,
            detail="הזמנה לא נמצאה",
        )
    order = records[0]
    return Response(
        content=create_today_orders_zpl(order),
        media_type="text/plain",
    )
    
#החזרת התאריכים החסומים
@app.get("/api/workdays/blocked-dates")
def get_blocked_workday_dates():

    records = get_all_airtable_records(
        table_name=AIRTABLE_WORKERS_TABLE,
        filter_formula='{מלא לגמרי}=TRUE',
        fields=[
            "תאריך ליקוט מינימלי",
            "מלא לגמרי",
        ],
    )

    blocked_dates = []

    for record in records:
        fields = record.get("fields", {})

        blocked_date = fields.get(
            "תאריך ליקוט מינימלי"
        )

        if blocked_date:
            blocked_dates.append(
                str(blocked_date)[:10]
            )

    return {
        "blocked_dates": blocked_dates
    }
#נתוני ליקוט

@app.get("/api/dashboard/picking-summary")
def get_picking_summary():

    records = get_all_airtable_records(
        AIRTABLE_ORDERS_TABLE,
     filter_formula=(
    'OR('
        '{בצפי}=1,'
        'AND('
            'IS_SAME({תאריך אספקה}, TODAY(), "day"),'
            '{קו הפצה}!="סוסנא"'
        ')'
    ')'
),
        fields=[
            "שורות ליקוט",
            "סטטוס",
            "יום עבודה",
            "שעת התחלה"
        ],
    )

    total_today = 0
    picked_today = 0

    for record in records:
        fields = record.get("fields", {})

        picking_rows = int(
            fields.get("שורות ליקוט", 0) or 0
        )

        status = fields.get("סטטוס", "")

        # כל השורות שתוכננו להיום
        total_today += picking_rows

        # הזמנה שכבר סיימה ליקוט
        end_time = fields.get("שעת סיום")

        if end_time:
            end_datetime = datetime.fromisoformat(
                end_time.replace("Z", "+00:00")
            )

            end_date_israel = end_datetime.astimezone(
                ZoneInfo("Asia/Jerusalem")
            ).date()

            today_israel = datetime.now(
                ZoneInfo("Asia/Jerusalem")
            ).date()

            if end_date_israel == today_israel:
                picked_today += picking_rows

    remaining_today = max(
                total_today - picked_today,
                0
            )

    return {
        "picked_today": picked_today,
        "remaining_today": remaining_today,
        "total_today": total_today,
    }