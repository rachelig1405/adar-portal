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
    "factory": ("Factory",),
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
