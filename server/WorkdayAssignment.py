import os
import requests
from fastapi import FastAPI, HTTPException

from datetime import datetime, timezone,date
from Models import OrderCreate
from zoneinfo import ZoneInfo
from DB import get_all_airtable_records,find_workday_record_id,update_order_workflow,get_order_by_record_id,create_workday_record
from datetime import date, timedelta
from urllib.parse import quote

import holidays
import requests
from fastapi import HTTPException


def create_workdays_until(target_date: date):
    """
    מייצרת רשומות בטבלת ימי העבודה מהתאריך האחרון שקיים בטבלה
    ועד target_date כולל.

    לא נוצרים:
    - ימי חמישי
    - ימי שישי
    - שבתות
    - חגים רשמיים בישראל
    """

    if target_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="תאריך היעד לא יכול להיות בעבר",
        )

    # מביאים את הרשומה האחרונה לפי ה-View.
    # חשוב שה-View יהיה ממוין לפי 'יום עבודה' מהחדש לישן.
    records = get_all_airtable_records(
        table_name=AIRTABLE_WORKDAY_TABLE,
        fields=["יום עבודה"],
        view="Grid view",
    )

    if not records:
        raise HTTPException(
            status_code=400,
            detail="לא נמצאה רשומה אחרונה בטבלת ימי העבודה",
        )

    last_workday_value = (
        records[0]
        .get("fields", {})
        .get("יום עבודה")
    )

    if not last_workday_value:
        raise HTTPException(
            status_code=400,
            detail="ברשומה האחרונה חסר השדה יום עבודה",
        )

    try:
        last_workday = date.fromisoformat(
            str(last_workday_value)[:10]
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="תאריך יום העבודה האחרון אינו תקין",
        )

    if last_workday >= target_date:
        return {
            "success": True,
            "created_count": 0,
            "created_dates": [],
            "message": "כל ימי העבודה עד התאריך המבוקש כבר קיימים",
        }

    years = range(
        last_workday.year,
        target_date.year + 1,
    )

    israel_holidays = holidays.country_holidays(
        "IL",
        years=years,
        observed=True,
    )

    created_dates = []
    skipped_dates = []

    current_date = last_workday + timedelta(days=1)

    while current_date <= target_date:

        # weekday:
        # שני=0, שלישי=1, רביעי=2,
        # חמישי=3, שישי=4, שבת=5, ראשון=6
        is_excluded_weekday = current_date.weekday() in (3, 4, 5)
        is_holiday = current_date in israel_holidays

        if is_excluded_weekday:
            skipped_dates.append({
                "date": current_date.isoformat(),
                "reason": "חמישי/שישי/שבת",
            })

        elif is_holiday:
            skipped_dates.append({
                "date": current_date.isoformat(),
                "reason": israel_holidays.get(current_date),
            })

        else:
            create_workday_record(current_date)
            created_dates.append(current_date.isoformat())

        current_date += timedelta(days=1)

    return {
        "success": True,
        "created_count": len(created_dates),
        "created_dates": created_dates,
        "skipped_count": len(skipped_dates),
        "skipped_dates": skipped_dates,
        "message": (
            f"נוצרו {len(created_dates)} רשומות ימי עבודה בהצלחה"
        ),
    }
AIRTABLE_WORKDAY_TABLE=os.getenv("AIRTABLE_WORKDAY_TABLE")
def workday_assignment(max_date:date,order_id:str):
    while(1):
    #מציאת היום הפוי הראשון עד תאריך ליקוט מקסימלי
        records_view_shibuts=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula=  f'OR('
        f'IS_BEFORE({{יום עבודה}}, "{max_date}"),'
        f'IS_SAME({{יום עבודה}}, "{max_date}", "day")'
        f')',view="ימים בשיבוץ")
        #רשומות של כל הימים כולל המלאים מהיום ועד ליום העבודה המקסימלי
        records=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula=  f'OR('
            f'IS_BEFORE({{יום עבודה}}, "{max_date}"),'
            f'IS_SAME({{יום עבודה}}, "{max_date}", "day")'
            f')',view="Grid view")
        workday=None
        if records_view_shibuts:
            workday=records_view_shibuts[0].get("id")
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
            print("else נכנסתי ל")
            #חיפוש יום עבודה בתצוגה המציגה את כל הימים
            orders=None
            order=None
            #במידה ולא קיימת בכלל רשומה מתאימה בטבלת ימי עבודה 
            if records:
                last_record = records[-1]

                last_workday = date.fromisoformat(
                last_record["fields"]["יום עבודה"]
                )

                if last_workday < max_date:
                    create_workdays_until(target_date=max_date)
                    continue
        
            print("רשומות של כל הימים המתאימים",records)
            
            #מעבר על כל יום מתאים
            for record in records:
                orders = record["fields"].get("הזמנות 2", [])
                print("הזמנות ליום עבודה",orders)
                #מעבר על כל הזמנה והזמנה לבדוק אם אפשר להזיז אותה
                for order in orders:
                    order1=get_order_by_record_id(order)
                    print(order1)
                    max_order_day = order1["fields"].get("תאריך ליקוט מקסימילי")

                    
                    #בדיקה אם יש להזמנות האחרות יום פנוי
                    records_of_worksday=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula=  f'OR('
                        f'IS_BEFORE({{יום עבודה}}, "{max_order_day}"),'
                        f'IS_SAME({{יום עבודה}}, "{max_order_day}", "day")'
                        f')',view="ימים בשיבוץ")
                    
                    #במידה ואפשר להזיז את ההזמנה - להזיז אותה ולבץ במקומה את ההזמנה ההחדשה
                    if records_of_worksday:
                        print("if שני")
                        update_order_workflow(order_id=order,workday_id=records_of_worksday[0].get("id"))
                        #עדכון ההזמנה החדשה
                        result=update_order_workflow(order_id=order_id,workday_id=record["id"])
                        return {
                            "success": True,
                            "record": result,
                        }
                
        print("send message to agents")
        return {"success": False,"message": "לא נמצא יום עבודה פנוי"}
    

                
    return {"success": False,"message": "לא נמצא יום עבודה פנוי"}













