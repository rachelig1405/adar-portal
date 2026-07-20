from pydantic import BaseModel
from datetime import datetime, timezone,date
class CustomerCreate(BaseModel):
    customer_number: str | None = ""
    customer_name: str
    contact_name: str | None = ""
    phone: str | None = ""
    address: str | None = ""
    city: str | None = ""
    segment: bool = False
    mikasa: bool = False

class PickingStart(BaseModel):
    order_id:str
    employee_id: str
class OrderCreate(BaseModel):
    order_number: str
    customer_id: str
    agent_id: str | None = ""
    delivery_date: str | None = ""
    picking_rows: int | None = None
    goes_with_us: bool | None = False
    line: str | None = ""
    delivery_notes: str | None = ""
    warehouse_notes:str | None = ""
class PickingEnd(BaseModel):
    order_id: str
    amount:float |None=None
    notes: str |None=None
    warehouse_notes: str | None = ""
class WorkdayAssignmentRequest(BaseModel):
    max_date: date
    order_id: str