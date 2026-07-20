import os
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from NewOrder import import_orders_excel
from fastapi import Query

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

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
        notes=data.notes
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