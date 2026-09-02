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
        """
        raise HTTPException(
            status_code=400,
            detail="לא נמצאה רשומה אחרונה בטבלת ימי העבודה",
        )
       """
        last_workday_value = date.today() - timedelta(days=1)

    else:

        last_workday_value = (
            records[-1]
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

'''
def workday_assignment(max_date:date,order_id:str):
    for attempt in range(2):
    #מציאת היום הפוי הראשון עד תאריך ליקוט מקסימלי
        records_view_shibuts=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula = (
    f'AND('
     f'OR('
    f'IS_SAME({{יום עבודה}}, TODAY(), "day"),'
    f'IS_AFTER({{יום עבודה}}, TODAY())'
    f'),'
    f'OR('
    f'IS_BEFORE({{יום עבודה}}, "{max_date}"),'
    f'IS_SAME({{יום עבודה}}, "{max_date}", "day")'
    f'),'
        f'VALUE({{סהכ שורות ליקוט}} & "") < '
        f'VALUE({{שורות ליקוט ליום}} & "")'
    f')'
), sort=[
        ("יום עבודה", "asc")
    ],)
        #רשומות של כל הימים כולל המלאים מהיום ועד ליום העבודה המקסימלי
        records=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula=    f'AND('   f'OR('
                f'IS_SAME({{יום עבודה}}, TODAY(), "day"),'
                f'IS_AFTER({{יום עבודה}}, TODAY())'
            f'),'f'OR('
            f'IS_BEFORE({{יום עבודה}}, "{max_date}"),'
            f'IS_SAME({{יום עבודה}}, "{max_date}", "day")'
            f')' f')',sort=[
        ("יום עבודה", "asc")
    ],view="Grid view")
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
                    "message": "ההזמנה שובצה בהצלחה",
                    "workday id":workday
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
        
            print("רשומות של כל הימים המתאימים",records,flush=True)
            
            #מעבר על כל יום מתאים
            for record in records:
                orders = record["fields"].get("הזמנות 2", [])
                print("הזמנות ליום עבודה",orders,flush=True)
                #מעבר על כל הזמנה והזמנה לבדוק אם אפשר להזיז אותה
                for order in orders:
                    order1 = get_order_by_record_id(order)

                    if order1["fields"].get("סטטוס")=="לפני יצור":
                        print(order1,flush=True)
                        max_order_day = order1["fields"].get("תאריך ליקוט מקסימילי")
                        print("max_order_day:", max_order_day, flush=True)

                        
                        #בדיקה אם יש להזמנות האחרות יום פנוי
                        records_of_worksday=get_all_airtable_records(table_name=AIRTABLE_WORKDAY_TABLE,filter_formula=     f'AND('
                                    f'OR('
                                    f'IS_SAME({{יום עבודה}}, TODAY(), "day"),'
                                    f'IS_AFTER({{יום עבודה}}, TODAY())'
                                    f'),'                                 
                                    f'OR('
                                    f'IS_BEFORE({{יום עבודה}}, "{max_order_day}"),'
                                    f'IS_SAME({{יום עבודה}}, "{max_order_day}", "day")'
                                    f'),'
                                        f'VALUE({{סהכ שורות ליקוט}} & "") < '
                                        f'VALUE({{שורות ליקוט ליום}} & "")'
                                    f')',sort=[
        ("יום עבודה", "asc")]
                               )
                        print("records_of_worksday:", records_of_worksday, flush=True)
                        
                        #במידה ואפשר להזיז את ההזמנה - להזיז אותה ולבץ במקומה את ההזמנה ההחדשה
                        if records_of_worksday:
                            print("if שני",flush=True)
                            update_order_workflow(order_id=order,workday_id=records_of_worksday[0].get("id"))
                            #אם היום התפנה בעקבות הזזת ההזמנה
                            order = int(order1["fields"].get("שורות ליקוט", 0))
                            total = int(record["fields"].get("סהכ שורות ליקוט", 0))-order
                            
                            limit = int(record["fields"].get("שורות ליקוט ליום", 0))

                            if total  <= limit:
                            #עדכון ההזמנה החדשה
                                result=update_order_workflow(order_id=order_id,workday_id=record["id"])
                                return {
                                    "success": True,
                                    "record": result,
                                }
                            
                
        print("send message to agents")
        return {"success": False,"message": "לא נמצא יום עבודה פנוי"}
    

                
    return {"success": False,"message": "לא נמצא יום עבודה פנוי"}



def workday_assignment(max_date: date, order_id: str):
    #שמירת כל טבלת ימי עבודה בזיכרון במקום לקרוא לאירטבל שוב ושוב
    extended_records_cache: dict[str, list] = {}
    #פונקצית עזר המקבל תאריך יעד והופכת אותו למחרוזת ובודקת אם כבר שלפנו את הנתונים האלה בעבר בריצה הנוכחית. אם כן - מחזירה מהקאש מיד, בלי לקרוא שוב ל-Airtable.
    def get_extended_records(until_date: date):
        cache_key = until_date.isoformat()

        if cache_key in extended_records_cache:
            return extended_records_cache[cache_key]

        if until_date <= max_date:
            extended_records_cache[cache_key] = []
            return []

        extra_records = get_all_airtable_records(
            table_name=AIRTABLE_WORKDAY_TABLE,
            filter_formula=(
                f'AND('
                f'IS_AFTER({{יום עבודה}}, "{max_date}"),'
                f'OR('
                f'IS_BEFORE({{יום עבודה}}, "{until_date}"),'
                f'IS_SAME({{יום עבודה}}, "{until_date}", "day")'
                f')'
                f')'
            ),
            sort=[("יום עבודה", "asc")],
            view="Grid view",
        )

        extended_records_cache[cache_key] = extra_records
        return extra_records

    for attempt in range(2):
        #שליפת כל ימי העבודה מהיום ועד לתאריך ליקוט מקסימלי של ההזמנה אותה רוצים לשבץ
        records = get_all_airtable_records(
            table_name=AIRTABLE_WORKDAY_TABLE,
            filter_formula=(
                f'AND('
                f'OR('
                f'IS_SAME({{יום עבודה}}, TODAY(), "day"),'
                f'IS_AFTER({{יום עבודה}}, TODAY())'
                f'),'
                f'OR('
                f'IS_BEFORE({{יום עבודה}}, "{max_date}"),'
                f'IS_SAME({{יום עבודה}}, "{max_date}", "day")'
                f')'
                f')'
            ),
            sort=[("יום עבודה", "asc")],
            view="Grid view",
        )
        #פונקציית עזר לחישוב כמה שורות ליקוט נשארו ליום עבודה

        def remaining_capacity(record):
            total = int(record["fields"].get("סהכ שורות ליקוט", 0) or 0)
            limit = int(record["fields"].get("שורות ליקוט ליום", 0) or 0)
            return limit - total

        workday = None
        #חיפוש היום הראשון הפנוי שניתן לשבץ בו
        for record in records:
            if remaining_capacity(record) > 0:
                workday = record.get("id")
                break
        #במידה ונמצא יום פנוי עדכון ההזמנה ליום הפנוי
        if workday:
            if order_id:
                result = update_order_workflow(order_id=order_id, workday_id=workday)

                return {
                    "success": True,
                    "record": result,
                    "message": "ההזמנה שובצה בהצלחה",
                    "workday id": workday,
                }

        else:
            if records:
                last_record = records[-1]
                last_workday = date.fromisoformat(str(last_record["fields"]["יום עבודה"])[:10])

                if last_workday < max_date:
                    create_workdays_until(target_date=max_date)
                    continue

            for record in records:
                orders = record["fields"].get("הזמנות 2", [])

                for order in orders:
                    print(
        "ORDER LINK VALUE:",
        order,
        "TYPE:",
        type(order),
        flush=True
    )
                    order1 = get_order_by_record_id(order)

                    if order1.get("fields").get("סטטוס") != "לפני יצור":
                        continue

                    max_order_day_raw = order1.get("fields").get("תאריך ליקוט מקסימילי")

                    if not max_order_day_raw:
                        continue

                    max_order_day = date.fromisoformat(str(max_order_day_raw)[:10])

                    extended = get_extended_records(max_order_day)
                    candidates = records + extended

                    alternative_workday = None

                    for candidate in candidates:
                        candidate_date = date.fromisoformat(str(candidate["fields"]["יום עבודה"])[:10])

                        if candidate_date > max_order_day:
                            continue

                        if candidate.get("id") == record.get("id"):
                            continue

                        if remaining_capacity(candidate) > 0:
                            alternative_workday = candidate
                            break

                    if alternative_workday:
                        update_order_workflow(order_id=order, workday_id=alternative_workday["id"])

                        moved_rows = int(order1["fields"].get("שורות ליקוט", 0) or 0)

                        alternative_workday["fields"]["סהכ שורות ליקוט"] = (
                            int(alternative_workday["fields"].get("סהכ שורות ליקוט", 0) or 0) + moved_rows
                        )

                        record["fields"]["סהכ שורות ליקוט"] = (
                            int(record["fields"].get("סהכ שורות ליקוט", 0) or 0) - moved_rows
                        )

                        current_total = int(record["fields"].get("סהכ שורות ליקוט", 0) or 0)
                        current_limit = int(record["fields"].get("שורות ליקוט ליום", 0) or 0)

                        if current_total <= current_limit:
                            result = update_order_workflow(order_id=order_id, workday_id=record["id"])

                            return {
                                "success": True,
                                "record": result,
                            }

            print("send message to agents")
            return {
                "success": False,
                "message": "לא נמצא יום עבודה פנוי",
            }

    return {
        "success": False,
        "message": "לא נמצא יום עבודה פנוי",
    }
'''
MAX_RECURSION_DEPTH = 15  # הגנה נוספת מפני שרשראות ארוכות מדי


def workday_assignment(max_date: date, order_id: str):
    # קאש משותף לכל הקריאות הרקורסיביות - נמנע משליפות כפולות
    workdays_cache: dict[str, list] = {}

    def get_records_until(until_date: date):
        cache_key = until_date.isoformat()

        if cache_key in workdays_cache:
            return workdays_cache[cache_key]

        recs = get_all_airtable_records(
            table_name=AIRTABLE_WORKDAY_TABLE,
            filter_formula=(
                f'AND('
                f'OR('
                f'IS_SAME({{יום עבודה}}, TODAY(), "day"),'
                f'IS_AFTER({{יום עבודה}}, TODAY())'
                f'),'
                f'OR('
                f'IS_BEFORE({{יום עבודה}}, "{until_date}"),'
                f'IS_SAME({{יום עבודה}}, "{until_date}", "day")'
                f')'
                f')'
            ),
            sort=[("יום עבודה", "asc")],
            view="Grid view",
        )

        workdays_cache[cache_key] = recs
        return recs

    def remaining_capacity(record):
        total = int(record["fields"].get("סהכ שורות ליקוט", 0) or 0)
        limit = int(record["fields"].get("שורות ליקוט ליום", 0) or 0)
        return limit - total

    def try_find_day(target_order_id, target_max_date, visited, depth=0):
        if depth > MAX_RECURSION_DEPTH:
            return None

        records = get_records_until(target_max_date)

        for record in records:
            if remaining_capacity(record) > 0:
                return record

        for record in records:
            orders = record["fields"].get("הזמנות 2", [])

            for order in orders:
                if order in visited:
                    continue

                order1 = get_order_by_record_id(order)

                if order1.get("fields", {}).get("סטטוס") != "לפני יצור":
                    continue

                other_max_day_raw = order1.get("fields", {}).get("תאריך ליקוט מקסימילי")

                if not other_max_day_raw:
                    continue

                other_max_day = date.fromisoformat(str(other_max_day_raw)[:10])

                visited.add(order)

                new_home = try_find_day(order, other_max_day, visited, depth + 1)

                if new_home is not None:
                    update_order_workflow(order_id=order, workday_id=new_home["id"])

                    moved_rows = int(order1["fields"].get("שורות ליקוט", 0) or 0)

                    new_home["fields"]["סהכ שורות ליקוט"] = (
                        int(new_home["fields"].get("סהכ שורות ליקוט", 0) or 0) + moved_rows
                    )

                    record["fields"]["סהכ שורות ליקוט"] = (
                        int(record["fields"].get("סהכ שורות ליקוט", 0) or 0) - moved_rows
                    )

                    return record

                # התיקון - נסיגה: מסירים מ-visited כדי לאפשר ניסיון עתידי מהקשר אחר
                visited.discard(order)

        return None



    for attempt in range(2):
            records = get_records_until(max_date)

            if records:
                last_workday = date.fromisoformat(
                    str(records[-1]["fields"]["יום עבודה"])[:10]
                )

                if last_workday < max_date:
                    create_workdays_until(target_date=max_date)
                    workdays_cache.clear()
                    continue

            target_day = try_find_day(order_id, max_date, visited={order_id})

            if target_day:
                result = update_order_workflow(
                    order_id=order_id, workday_id=target_day["id"]
                )

                return {
                    "success": True,
                    "record": result,
                    "message": "ההזמנה שובצה בהצלחה",
                    "workday id": target_day["id"],
                }

            print("send message to agents")
            return {
                "success": False,
                "message": "לא נמצא יום עבודה פנוי",
            }

    return {
        "success": False,
        "message": "לא נמצא יום עבודה פנוי",
    }








