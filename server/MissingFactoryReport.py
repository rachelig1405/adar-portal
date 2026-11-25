"""Generate an XLSX shortages report grouped by factory/station from Nutstore.

Requirements: pip install requests python-calamine XlsxWriter
SECURITY: Mount router ONLY with your existing authenticated/authorized portal dependency.
See accompanying README for main.py instructions.
"""
from __future__ import annotations

import os
import re
import io
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree as ET

import requests
import xlsxwriter
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from python_calamine import CalamineWorkbook

router = APIRouter(prefix="/api/reports", tags=["Reports"])

DAV_ORIGIN = "https://dav.jianguoyun.com"
DAV_FOLDER = (
    "/dav/EYAL/OZ%20VEHADAR/BA%20OZ%20VHADAR%20NISIM/"
    "BOOKS%20IN%20PRODUCTION/"
)
TARGET_SHEET = "Processing orders-生产中"
FILE_PREFIX = "EYAL-PRODUCTION FILE"
# Set to 'not_confirm' to replicate the uploaded example's original logic.
# Your current business instruction was: only genuinely blank cells are missing.
MISSING_RULE = "empty"  # 'empty' or 'not_confirm'
MISSING_COLUMNS = ("CONFIRM FILE", "COVER", "PORZAZ")
HEADER_ALIASES = {
    "item": ("FACTORY ITEM NO", "ITEM NUMBER"),
    "factory": ("עמדה",),
    "description": ("DESCRIPTION", "ITEM DESCRIPTION", "PRODUCT NAME", "תיאור"),
    "hard_soft": ("HARD/SOFT", "HARD SOFT"),
}


def _clean(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _key(v):
    return " ".join(_clean(v).upper().split())


def _is_missing(value):
    v = _key(value)
    return (not v) if MISSING_RULE == "empty" else (v != "CONFIRM")


def _find_latest_excel(session):
    listing_url = DAV_ORIGIN + DAV_FOLDER
    resp = session.request("PROPFIND", listing_url, headers={"Depth": "1"}, timeout=(15, 45))
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    choices = []
    for element in root.findall(".//{DAV:}response"):
        href = element.findtext("{DAV:}href")
        if not href:
            continue
        name = unquote(urlsplit(href).path).rstrip("/").split("/")[-1]
        if not (name.upper().startswith(FILE_PREFIX.upper()) and name.lower().endswith(".xlsx")):
            continue
        # Prevent a malicious DAV href from redirecting the credential-bearing request.
        absolute = urljoin(DAV_ORIGIN, href)
        parsed = urlsplit(absolute)
        if parsed.scheme != "https" or parsed.hostname != "dav.jianguoyun.com":
            continue
        if not parsed.path.lower().startswith(DAV_FOLDER.lower()):
            continue
        modified = element.findtext(".//{DAV:}getlastmodified") or ""
        try:
            from email.utils import parsedate_to_datetime
            ts = parsedate_to_datetime(modified).timestamp()
        except (ValueError, TypeError, OverflowError):
            ts = 0
        match = re.search(r"(\d{4}\.\d{2}\.\d{2})", name)
        try:
            name_date = datetime.strptime(match.group(1), "%Y.%m.%d").timestamp() if match else 0
        except ValueError:
            name_date = 0
        choices.append((ts, name_date, name, absolute))
    if not choices:
        raise ValueError("לא נמצא קובץ EYAL-PRODUCTION FILE בתיקייה")
    return max(choices)[2:]


def _find_col(headers, variants):
    for label in variants:
        if _key(label) in headers:
            return headers.index(_key(label))
    return None


def _extract_rows(workbook):
    if TARGET_SHEET not in workbook.sheet_names:
        raise ValueError("לא נמצא הגיליון: " + TARGET_SHEET)
    values = workbook.get_sheet_by_name(TARGET_SHEET).to_python(skip_empty_area=False)
    header_idx = None
    indices = None
    for i, row in enumerate(values[:80]):
        h = [_key(v) for v in row]
        m = {name: _find_col(h, (name,)) for name in MISSING_COLUMNS}
        item_col = _find_col(h, HEADER_ALIASES["item"])
        factory_col = _find_col(h, HEADER_ALIASES["factory"])
        if all(x is not None for x in m.values()) and item_col is not None and factory_col is not None:
            indices = dict(m, item=item_col, factory=factory_col,
                           description=_find_col(h, HEADER_ALIASES["description"]),
                           hard_soft=_find_col(h, HEADER_ALIASES["hard_soft"]))
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("לא נמצאו הכותרות הדרושות. יש לוודא שהעמודה 'עמדה' קיימת ושמות העמודות תואמים")

    records = []
    factory_counts = Counter()
    missing_by_factory = defaultdict(Counter)
    for ix, row in enumerate(values[header_idx + 1:], start=header_idx + 2):
        def read(field):
            pos = indices.get(field)
            return _clean(row[pos]) if pos is not None and pos < len(row) else ""
        item = read("item")
        if not item:
            continue
        factory = read("factory") or "לא משויך"
        factory_counts[factory] += 1
        missing = [c for c in MISSING_COLUMNS if _is_missing(read(c))]
        if not missing:
            continue
        for c in missing:
            missing_by_factory[factory][c] += 1
        records.append({
            "item": item, "description": read("description"), "factory": factory,
            "file": read("CONFIRM FILE"), "cover": read("COVER"), "porzaz": read("PORZAZ"),
            "missing": missing, "hard_soft": read("hard_soft"), "row": ix,
        })
    return records, factory_counts, missing_by_factory


def _export(records, factory_counts, missing_by_factory, source_name):
    out = io.BytesIO()
    wb = xlsxwriter.Workbook(out, {"in_memory": True, "strings_to_numbers": False})
    title = wb.add_format({"bold": True, "font_size": 16, "font_color": "#FFFFFF", "bg_color": "#17324D", "align": "right"})
    caption = wb.add_format({"font_color": "#64748B", "align": "right", "text_wrap": True})
    header = wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1A6288", "border": 1, "border_color": "#E1E8F0", "align": "right"})
    normal = wb.add_format({"align": "right", "valign": "top", "border": 1, "border_color": "#E7EDF3", "text_wrap": True})
    warn = wb.add_format({"align": "right", "font_color": "#AD2E24", "bg_color": "#FCE8E6", "border": 1, "border_color": "#E7EDF3"})
    totalfmt = wb.add_format({"bold": True, "bg_color": "#E5F1F8", "align": "right"})
    cols = ["מקט (FACTORY ITEM NO)", "תיאור", "מפעל / עמדה", "CONFIRM FILE", "COVER", "PORZAZ", "מה חסר", "HARD/SOFT", "שורה בגיליון"]
    def prep(ws, widths=(22, 43, 31, 20, 17, 17, 30, 17, 17)):
        ws.right_to_left()
        ws.hide_gridlines(2)
        for i, width in enumerate(widths):
            ws.set_column(i, i, width)
    def record_rows(ws, start, data):
        for idx, rec in enumerate(data, start=start):
            vals = [rec['item'], rec['description'], rec['factory'],
                    rec['file'] or 'חסר', rec['cover'] or 'חסר', rec['porzaz'] or 'חסר',
                    ', '.join(rec['missing']), rec['hard_soft'], rec['row']]
            for j, value in enumerate(vals):
                ws.write_string(idx, j, str(value), warn if j in (3, 4, 5) and cols[j] in rec['missing'] else normal)
    def tbl_header(ws, row):
        for j, name in enumerate(cols):
            ws.write(row, j, name, header)
        ws.freeze_panes(row + 1, 0)
    summary = wb.add_worksheet('Confirm Tracking')
    prep(summary)
    summary.merge_range('A1:I1', 'מעקב חוסרים — CONFIRM FILE / COVER / PORZAZ', title)
    summary.merge_range('A2:I2', f'מקור: {source_name} | גיליון: {TARGET_SHEET} | כלל חוסר: {"תא ריק" if MISSING_RULE == "empty" else "לא CONFIRM"}', caption)
    metrics = [
        ('שורות פריטים בסה"כ', sum(factory_counts.values())),
        ('שורות עם חוסר', len(records)),
        ('חסר CONFIRM FILE', sum('CONFIRM FILE' in r['missing'] for r in records)),
        ('חסר COVER', sum('COVER' in r['missing'] for r in records)),
        ('חסר PORZAZ', sum('PORZAZ' in r['missing'] for r in records)),
    ]
    for i, (label, val) in enumerate(metrics, start=3):
        summary.write(i, 0, label, totalfmt)
        summary.write_number(i, 2, val, totalfmt)
    summary.write_row(3, 10, ['מפעל', 'שורות', 'חסר FILE', 'חסר COVER', 'חסר PORZAZ'], header)
    for i, factory in enumerate(sorted(factory_counts), start=4):
        values = [factory, factory_counts[factory], missing_by_factory[factory]['CONFIRM FILE'],
                  missing_by_factory[factory]['COVER'], missing_by_factory[factory]['PORZAZ']]
        for j, val in enumerate(values, start=10):
            if isinstance(val, int): summary.write_number(i, j, val, normal)
            else: summary.write_string(i, j, val, normal)
    summary.set_column('K:K', 36)
    summary.set_column('L:O', 16)
    sorted_records = sorted(records, key=lambda r: (r['factory'].casefold(), r['item'], r['row']))
    tbl_header(summary, 10)
    record_rows(summary, 11, sorted_records)
    if records: summary.autofilter(10, 0, 10 + len(records), 8)

    used = {'Confirm Tracking'}
    for factory in sorted(factory_counts):
        # Prefer trailing code (XST, CMA etc.) for tab labels, as in sample workbook.
        code = factory.strip().split()[-1]
        candidate = re.sub(r'[\[\]:*?/\\]', '_', code)[:31] or 'Factory'
        if candidate.lower() in {s.lower() for s in used}:
            candidate = f'Factory_{len(used)}'
        used.add(candidate)
        ws = wb.add_worksheet(candidate)
        prep(ws)
        ws.merge_range('A1:I1', f'מעקב חוסרים — {factory}', title)
        ws.merge_range('A2:I2', 'שורות עם חוסר לפי מפעל / עמדה מתוך הקובץ העדכני', caption)
        factory_rows = [r for r in sorted_records if r['factory'] == factory]
        sums = [factory_counts[factory], len(factory_rows),
                missing_by_factory[factory]['CONFIRM FILE'],
                missing_by_factory[factory]['COVER'], missing_by_factory[factory]['PORZAZ']]
        for j, (lbl, value) in enumerate(zip(['שורות בסה"כ', 'שורות עם חוסר', 'חסר FILE', 'חסר COVER', 'חסר PORZAZ'], sums)):
            ws.write(2, j, lbl, header)
            ws.write_number(3, j, value, totalfmt)
        tbl_header(ws, 5)
        record_rows(ws, 6, factory_rows)
        if factory_rows: ws.autofilter(5, 0, 5 + len(factory_rows), 8)
        else: ws.write_string(6, 0, 'אין חוסרים למפעל זה', caption)
    wb.close()
    out.seek(0)
    return out


@router.get('/missing-factory-excel')
def download_missing_factory_excel():
    """IMPORTANT: protect router at registration using your portal auth dependency."""
    username = os.environ.get('NUTSTORE_EMAIL')
    password = os.environ.get('NUTSTORE_APP_PASSWORD')
    if not username or not password:
        raise HTTPException(500, 'Nutstore credentials not configured')
    try:
        with requests.Session() as sess:
            sess.auth = (username, password)
            name, url = _find_latest_excel(sess)
            response = sess.get(url, timeout=(15, 180), allow_redirects=False)
            response.raise_for_status()
            if len(response.content) > 90 * 1024 * 1024:
                raise ValueError('Excel exceeds 90 MB')
            book = CalamineWorkbook.from_filelike(io.BytesIO(response.content))
            rows, counts, missing = _extract_rows(book)
            result = _export(rows, counts, missing, name)
    except (requests.RequestException, ValueError, ET.ParseError, KeyError) as err:
        raise HTTPException(502, f'Failed to generate shortages report: {err}') from err
    filename = 'Missing_Factory_Orders_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M') + '.xlsx'
    return StreamingResponse(
        result,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"', 'Cache-Control': 'no-store'},
    )
