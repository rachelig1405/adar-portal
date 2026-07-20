import os
import requests
from fastapi import FastAPI, HTTPException

from datetime import datetime, timezone,date
from Models import OrderCreate
from zoneinfo import ZoneInfo
from DB import get_all_airtable_records,find_workday_record_id,update_order_workflow,get_order_by_record_id

AIRTABLE_WORKDAY_TABLE=os.getenv("AIRTABLE_WORKDAY_TABLE")
def workday_assignment(max_date:date,order_id:str):
    #מציאת היום הפוי הראשון עד תאריך ליקוט מקסימלי
    records=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula=  f'OR('
    f'IS_BEFORE({{יום עבודה}}, "{max_date}"),'
    f'IS_SAME({{יום עבודה}}, "{max_date}", "day")'
    f')',view="ימים בשיבוץ")
    workday=None
    if records:
        workday=records[0].get("id")
        if order_id:
            result = update_order_workflow(
            order_id=order_id,
            workday_id=workday
            )

            return {
                "success": True,
                "record": result,
                 "message": "ההזמנה שובצה בהצלחה"
            }
    #במידה ולא נמצא יום פנוי
    else:
        #חיפוש יום עבודה בתצוגה המציגה את כל הימים
        orders=None
        order=None
        records=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula=  f'OR('
        f'IS_BEFORE({{יום עבודה}}, "{max_date}"),'
        f'IS_SAME({{יום עבודה}}, "{max_date}", "day")'
        f')',view="Grid view")
        #מעבר על כל יום מתאים
        for record in records:
            orders=record["fields"].get("הזמנות", [])
            #מעבר על כל הזמנה והזמנה לבדוק אם אפשר להזיז אותה
            for order in orders:
                order1=get_order_by_record_id(order)
                max_order_day=order1["fields"].get("יום עבודה בפועל")
                #בדיקה אם יש להזמנות האחרות יום פנוי
                records_of_worksday=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula=  f'OR('
                    f'IS_BEFORE({{יום עבודה}}, "{max_order_day}"),'
                    f'IS_SAME({{יום עבודה}}, "{max_order_day}", "day")'
                    f')',view="ימים בשיבוץ")
                #במידה ואפשר להזיז את ההזמנה - להזיז אותה ולבץ במקומה את ההזמנה ההחדשה
                if records_of_worksday:
                    update_order_workflow(order_id=order,workday_id=records_of_worksday[0].get("id"))
                    #עדכון ההזמנה החדשה
                    result=update_order_workflow(order_id=order_id,workday_id=record["id"])
                    return {
                        "success": True,
                        "record": result,
                     }
    print("send message to agents")
                
    return {"success": False,"message": "לא נמצא יום עבודה פנוי"}













