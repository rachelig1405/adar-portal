

import base64
import platform
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
from jinja2 import Template
from openpyxl import load_workbook
from playwright.async_api import async_playwright


# =========================
# שמות עמודות באקסל
# =========================
COL_SKU = "CUSTOMER ITEM NO"          # מק"ט / קוד פנימי

COL_PCS = "OUTER"                  # PCS

COL_BARCODE = "BARCODE"            # ברקוד EAN13 - 12/13 ספרות
COL_PHOTO = "PHOTO" 
COL_NAME="NAME"
               # נתיב תמונת מוצר במחשב

LOGO_PATH = Path(__file__).parent / "לוג"

# העמודות שחייב להיות בהן ערך בכל שורת מוצר
REQUIRED_VALUE_COLUMNS = {
    COL_SKU: "מק״ט",
   
    COL_BARCODE: "ברקוד",
   
   
}
# =========================================================
# מידות הברקוד בשלושת סוגי ה-PDF
# קובעים רק רוחב. הגובה מחושב אוטומטית בלי עיוות.
# =========================================================

BARCODE_WIDTH_MR_MM = 68.0
BARCODE_WIDTH_HTS_MM = 25.0
BARCODE_WIDTH_ST_MM = 31.0

# =========================================================
# שלוש תיקיות קבועות שבהן מחפשים תיקייה ישנה בשם המק"ט.
# החליפי את הנתיבים כאן בנתיבים האמיתיים אצלך.
# החיפוש מתבצע לפי הסדר: 1, אחר כך 2, אחר כך 3.
# =========================================================
OLD_PRODUCTS_ROOT_1 = Path(r"E:\Adar Shmuel 26 ltd Dropbox\tetroashvili shmuel\A תיק מוצר לכל המוצרים\0מוצרים ללא הזמנה")
OLD_PRODUCTS_ROOT_2 = Path(r"E:\OLD_PRODUCTS_2")
OLD_PRODUCTS_ROOT_3 = Path(r"E:\Adar Shmuel 26 ltd Dropbox\tetroashvili shmuel\A תיק מוצר לכל המוצרים\0מקטים שנבדקו")

OLD_PRODUCTS_ROOTS = [
    OLD_PRODUCTS_ROOT_1,
    OLD_PRODUCTS_ROOT_2,
    OLD_PRODUCTS_ROOT_3,
]
def get_zint_executable() -> str:
    if platform.system() == "Windows":
        return str(
            Path(__file__).parent
            / "zint-2.16.0"
            / "zint.exe"
        )

    return "zint"
def validate_product_row(row, excel_row_number: int) -> list[str]:
    """
    בודקת שורת מוצר אחת ומחזירה רשימת שגיאות.
    אם הרשימה ריקה, השורה תקינה.
    """

    errors = []

    sku = val(row, COL_SKU)
    row_identifier = sku if sku else f"שורת Excel מספר {excel_row_number}"

    # בדיקת ערכים חסרים
    for column_name, display_name in REQUIRED_VALUE_COLUMNS.items():
        value = val(row, column_name)

        if not value:
            errors.append(
                f"מק״ט {row_identifier}: חסר ערך בעמודה '{display_name}'"
            )

    # בדיקת הברקוד
    barcode_original = val(row, COL_BARCODE)
    barcode_digits = clean_digits(barcode_original)

    if not barcode_original:
        # כבר תועדה שגיאת "חסר ברקוד"
        pass

    elif not barcode_original.replace(" ", "").replace("-", "").isdigit():
        errors.append(
            f"מק״ט {row_identifier}: הברקוד מכיל תווים שאינם ספרות "
            f"(הערך שהתקבל: {barcode_original})"
        )

    elif len(barcode_digits) not in (12, 13):
        errors.append(
        f"מק״ט {row_identifier}: הברקוד חייב להכיל 12 או 13 ספרות "
        f"(התקבלו {len(barcode_digits)} ספרות: {barcode_digits})"
    )

    return errors
def write_validation_report(
    output_root: Path,
    errors: list[str]
) -> Path:
    """
    יוצרת קובץ טקסט עם כל השגיאות.
    UTF-8-SIG מאפשר פתיחה תקינה בעברית גם בפנקס הרשימות של Windows.
    """

    report_path = output_root / "שגיאות_נתונים.txt"

    lines = [
        "דוח שגיאות בקובץ האקסל",
        "=" * 40,
        "",
        f"סה״כ שגיאות: {len(errors)}",
        "",
    ]

    lines.extend(errors)

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8-sig"
    )

    return report_path
def safe_name(value: str) -> str:
    value = str(value).strip()
    value = re.sub(r'[\\/:*?"<>|]', "_", value)
    return value or "item"


def val(row, col, default=""):
    if col in row and pd.notna(row[col]):
        value = row[col]
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value).strip()
    return default



def clean_digits(value: str) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if value.endswith(".0"):
        value = value[:-2]
    return re.sub(r"\D", "", value)


def sticker_dimension_mm(row, column_name: str, default_mm: float) -> float:
    """
    קורא מידה מהאקסל במילימטרים.
    תומך גם בקבצים ישנים שבהם נכתב 6/4 במקום 60/40.
    """
    raw = val(row, column_name, "")

    if not raw:
        return default_mm

    try:
        number = float(str(raw).replace(",", "."))
    except (TypeError, ValueError):
        return default_mm

    if number <= 0:
        return default_mm

    # תאימות לאקסלים ישנים שנכתבו בסנטימטרים: 6×4, 8×4 וכו'.
    if number <= 20:
        number *= 10

    return number




def copy_old_sku_folder(
    sku: str,
    product_dir: Path,
    source_roots: list[Path] | None = None,
) -> tuple[bool, str]:
    """
    מחפשת תיקייה ישנה בשם המק"ט בשלוש תיקיות מקור, לפי הסדר.

    אם נמצאה:
    - מעתיקה אותה לתוך תיקיית המוצר החדשה.
    - משנה את שם התיקייה המועתקת ל:
          <SKU> ישן
    """

    clean_sku = safe_name(sku)

    if not clean_sku:
        return False, "לא הוזן מק״ט"

    roots = source_roots or OLD_PRODUCTS_ROOTS
    source_folder = None

    raw_sku = str(sku).strip()
    possible_folder_names = []

    if raw_sku:
        possible_folder_names.append(raw_sku)

    if clean_sku not in possible_folder_names:
        possible_folder_names.append(clean_sku)

    for root in roots:
        if not root.exists() or not root.is_dir():
            continue

        for folder_name in possible_folder_names:
            candidate = root / folder_name

            if candidate.exists() and candidate.is_dir():
                source_folder = candidate
                break

        if source_folder is not None:
            break

    if source_folder is None:
        searched_paths = ", ".join(str(path) for path in roots)

        return (
            False,
            f"לא נמצאה תיקייה ישנה בשם המק״ט {sku}. "
            f"חיפוש בוצע בתיקיות: {searched_paths}",
        )

    destination_folder = product_dir / f"{clean_sku} ישן"

# בריצה שנייה: אם התיקייה כבר קיימת, מדלגים ולא מוחקים
    if destination_folder.exists():
        return (
            True,
            f"תיקיית היעד כבר קיימת, לא הועתקה מחדש: {destination_folder}"
    )

    shutil.copytree(
        source_folder,
        destination_folder,
)

    return True, str(destination_folder)


def normalize_certificate_number(value: str) -> str:
    """מנקה מספר תעודה שמגיע מאקסל."""
    if value is None:
        return ""

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value


def copy_certificate_pdf(
    certificate_folder: Path,
    certificate_number: str,
    product_dir: Path,
    sku: str,
) -> tuple[bool, str]:
    """
    מחפשת PDF ששמו זהה למספר התעודה,
    מעתיקה אותו לתיקיית המק"ט ומשנה את שמו ל:
    EN <SKU>.pdf
    """

    certificate_number = normalize_certificate_number(
        certificate_number
    )

    if not certificate_number:
        return False, "לא הוזן מספר תעודה"

    if not certificate_folder.exists():
        return False, f"תיקיית התעודות לא קיימת: {certificate_folder}"

    candidates = [
        certificate_folder / f"{certificate_number}.pdf",
        certificate_folder / f"{certificate_number}.PDF",
    ]

    source_pdf = next(
        (path for path in candidates if path.exists()),
        None,
    )

    if source_pdf is None:
        target_stem = certificate_number.casefold()

        for path in certificate_folder.iterdir():
            if (
                path.is_file()
                and path.suffix.casefold() == ".pdf"
                and path.stem.casefold() == target_stem
            ):
                source_pdf = path
                break

    if source_pdf is None:
        return False, f"לא נמצא PDF עבור תעודה {certificate_number}"

    destination_pdf = product_dir / f"EN {safe_name(sku)}.pdf"
    shutil.copy2(source_pdf, destination_pdf)

    return True, str(destination_pdf)


def local_file_to_data_uri(path_value: str) -> str:
    if not path_value:
        return ""

    path = Path(str(path_value).strip().strip('"'))
    if not path.exists():
        return ""

    ext = path.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    if ext not in ["png", "jpeg", "webp", "gif"]:
        ext = "png"

    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{ext};base64,{data}"
def get_logo_data_uri():
    logo_path = Path(__file__).parent / "לוגו.jpeg"
    return local_file_to_data_uri(str(logo_path))
def barcode_url(barcode_value: str) -> str:
    """
    יוצר ברקוד EAN-13 באמצעות Zint ומחזיר Data URI מסוג SVG.
    עובד עם zint.exe ב-Windows ועם zint ב-Linux/Render.
    """
    digits = clean_digits(barcode_value)

    if len(digits) == 12:
        barcode_type = "UPCA"

    elif len(digits) == 13:
        barcode_type = "EANX"

    else:
        raise ValueError(
            f"הברקוד חייב להכיל 12 או 13 ספרות. התקבל: {digits}"
        )

    barcode_folder = Path(__file__).parent / "_barcodes"
    barcode_folder.mkdir(parents=True, exist_ok=True)
    svg_path = barcode_folder / f"{digits}_h39_g5_t1.svg"

    if not svg_path.exists():
        zint_exe = get_zint_executable()
        command = [
            str(zint_exe),
            f"--barcode={barcode_type}",
            f"--data={digits}",
            f"--output={svg_path}",
            "--height=50",
            "--guarddescent=5",
            "--textgap=1",
            "--quietzones",
            "--embedfont",
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"לא נמצא Zint להפעלה: {zint_exe}"
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                "Zint נכשל ביצירת הברקוד:\n"
                f"פקודה: {' '.join(command)}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        if not svg_path.exists():
            raise RuntimeError(f"Zint לא יצר את הקובץ: {svg_path}")

    encoded = base64.b64encode(svg_path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


async def html_to_pdf(html: str, output_pdf: Path, browser) -> None:
    """מייצר PDF מעמוד HTML באמצעות דפדפן Playwright קיים."""
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    page = await browser.new_page(device_scale_factor=1)

    try:
        await page.emulate_media(media="print")
        await page.set_content(html, wait_until="load")

        await page.evaluate("""
        async () => {
            if (document.fonts && document.fonts.ready) {
                await document.fonts.ready;
            }
            const images = Array.from(document.images);
            await Promise.all(images.map(async (img) => {
                if (img.complete) return;
                try { await img.decode(); } catch (error) {}
            }));
        }
        """)

        await page.evaluate("""
        () => {
            const MM_TO_PX = 96 / 25.4;
            const elements = document.querySelectorAll(".auto-fit-text");
            elements.forEach((element) => {
                const computed = window.getComputedStyle(element);
                let fontSizePx = parseFloat(computed.fontSize);
                const minimumMm = parseFloat(element.dataset.minFontMm || "1");
                const minimumPx = minimumMm * MM_TO_PX;
                const stepPx = 0.15;
                while (
                    element.scrollWidth > element.clientWidth + 0.25 &&
                    fontSizePx > minimumPx
                ) {
                    fontSizePx = Math.max(minimumPx, fontSizePx - stepPx);
                    element.style.fontSize = fontSizePx + "px";
                }
            });
        }
        """)

        await page.pdf(
            path=str(output_pdf),
            print_background=True,
            prefer_css_page_size=True,
            scale=1,
        )
    finally:
        await page.close()


def extract_excel_images_by_sku(excel_path: Path, output_folder: Path):
    wb = load_workbook(excel_path)
    ws = wb.active

    output_folder.mkdir(parents=True, exist_ok=True)

    image_map = {}

    # עמודת המק"ט אצלך היא A
    sku_column = 1

    for img in ws._images:
        anchor = img.anchor._from
        excel_row = anchor.row + 1

        sku = ws.cell(row=excel_row, column=sku_column).value
        if not sku:
            continue

        sku = safe_name(str(sku).replace(".0", ""))

        img_path = output_folder / f"{sku}.jpeg"

        with open(img_path, "wb") as f:
            f.write(img._data())

        image_map[sku] = img_path

    return image_map



CARTON_HTML = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">

<style>
@page {
    size: 200mm 200mm;
    margin: 0;
}

* {
    box-sizing: border-box;
}

html, body {
    width: 200mm;
    height: 200mm;
    margin: 0;
    padding: 0;
    background: #fff;
    color: #222;
    font-family: Arial, sans-serif;
    overflow: hidden;
}

.sheet {
    position: relative;
    width: 200mm;
    height: 200mm;
}

/* לוגו עוז והדר – במרכז למעלה */

.reference-logo {
    position: absolute;
    top: 12mm;
    left: 50%;
    transform: translateX(-50%);
    width: 58mm;
    height: 55mm;
    object-fit: contain;
}

/* תיאור המוצר */

.description {
    position: absolute;
    top: 78mm;
    right: 18mm;
    left: 18mm;
    max-height: 37mm;
    text-align: right;
    direction: rtl;
    font-size: 9mm;
    line-height: 1.2;
    overflow: hidden;
    overflow-wrap: break-word;
}

/* מק"ט בצד ימין */

.sku {
    position: absolute;
    top: 137mm;
    right: 18mm;
    width: 82mm;
    text-align: right;
    direction: rtl;
    font-size: 10mm;
    white-space: nowrap;
}

/* אזור הברקוד בצד שמאל */

.barcode-area {
    position: absolute;
    top: 130mm;
    left: 13mm;
    width: 76mm;
    text-align: center;
    direction: ltr;
}

.mini-sku {
    font-size: 3.5mm;
    line-height: 1.15;
    white-space: nowrap;
}

.mini-name {
    font-size: 2.8mm;
    line-height: 1.15;
    direction: rtl;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 0.5mm;
    margin-bottom: 1mm;
}

.barcode {
    display: block;
    width: {{ barcode_width_mr }}mm;
    max-width: 100%;
    height: auto;
    margin: 0 auto;
}
/* כמות - מתחת למק"ט בצד ימין */
.quantity {
    position: absolute;
    top: 163mm;
    right: 18mm;
    width: 82mm;
    text-align: right;
    direction: rtl;
    font-size: 10mm;
    white-space: nowrap;
}
</style>
</head>

<body>
<div class="sheet">

    <!-- לוגו עוז והדר -->
    {% if logo%}
    <img
        class="reference-logo"
        src="{{ logo }}"
        alt="עוז והדר">
    {% endif %}

    <!-- שם הספר -->
    <div class="description">
        שם הספר: {{ name }}
    </div>

    <!-- מק"ט -->
    <div class="sku">
        מק״ט - {{ sku }}
    </div>
    <div class="quantity">
         כמות: {{ pcs }}
    </div>

    <!-- ברקוד -->
    <div class="barcode-area">

        <div class="mini-sku">
            {{ sku }}
        </div>

        <div class="mini-name">
            {{ name }}
        </div>

        <img
            class="barcode"
            src="{{ barcode_url }}"
            alt="Barcode">

    </div>

</div>
</body>
</html>
"""





WARNING_HTML = """

<!doctype html>
<html lang="he">
<head>
<meta charset="utf-8">
<style>
@page {
    size: {{width_warning}}mm {{height_warning}}mm;
    margin: 0;
}

* { box-sizing: border-box; }

html, body {
    width: {{width_warning}}mm;
    height: {{height_warning}}mm;
    margin: 0;
    font-family: Arial, sans-serif;
    background: white;
    overflow: hidden;
}

.label {
    width: 100%;
    height: 100%;
    text-align: center;
    padding: 1.1mm;
}

.sku {
    font-size: calc({{height_warning}}mm * .064);
    white-space: nowrap;
}

.description {
    direction: rtl;
    font-size: calc({{height_warning}}mm * .051);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: .3mm;
}

.barcode {
    display: block;
    width: {{barcode_width_st}}mm;
    max-width: 92%;
    height: auto;
    max-height: calc({{height_warning}}mm * .80);
    margin: .35mm auto 0;
    object-fit: contain;
}
</style>
</head>
<body>
<div class="label">
    <div class="sku">{{ sku }}</div>
    <div class="description">{{ name }}</div>
    <img class="barcode" src="{{ barcode_url }}">
</div>
</body>
</html>

"""



async def render_templates(row, product_dir: Path, browser, photo_data: str = ""):
    sku = val(row, COL_SKU)
    
    pcs = val(row, COL_PCS)
    
    barcode_value = val(row, COL_BARCODE)
   
    # המידות נלקחות מהאקסל; ברירת המחדל היא 60×40 מ"מ.
    # נתמך גם פורמט ישן של 6×4.
    x_html = 38
    Y_html = 25
    barcode_digits = clean_digits(barcode_value)
   
    name= val(row, COL_NAME)
    if len(barcode_digits) != 13:
        raise ValueError(
           f"ברקוד לא תקין למק״ט {sku}: {barcode_digits}"
        )
    
    scale_x = 1
    scale_y = 1   
    scale = (scale_x + scale_y) / 2
    
   
    context = {
        "sku": sku,
        
        "pcs": pcs,
        
        "barcode": clean_digits(barcode_value),
        "barcode_url": barcode_url(barcode_value),
      
        "photo_data": photo_data,
        "range": range,
        "logo": local_file_to_data_uri(str(LOGO_PATH)),
        "width_warning":x_html,
        "height_warning":Y_html,

        
        "scale_x": scale_x,
        "scale_y": scale_y,
        "scale": scale,
        "name":name,
        "barcode_width_mr": BARCODE_WIDTH_MR_MM,
        
        "barcode_width_st": BARCODE_WIDTH_ST_MM,
       
    }
    
   

    await html_to_pdf(
        Template(CARTON_HTML).render(**context),
        product_dir / f"{safe_name(sku)}_MR.pdf",
        browser,
    )
   
    await html_to_pdf(
        Template(WARNING_HTML).render(**context),
        product_dir / f"{safe_name(sku)}_ST.pdf",
        browser,
    )


import zipfile   # <-- להוסיף בראש הקובץ, ליד שאר ה-imports


def zip_output_folder(output_root: Path, zip_name: str = "כל_המוצרים") -> Path:
    """
    דוחסת את כל תוכן תיקיית הפלט לקובץ ZIP אחד, ומחזירה את הנתיב אליו.
    """
    zip_path = output_root.parent / f"{zip_name}.zip"

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in output_root.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(output_root)
                zf.write(file_path, arcname)

    return zip_path

async def process_excel(
    excel_path: str,
    output_root: str,
    certificate_folder: str = "",
    progress_callback=None
):
    excel_path = Path(excel_path)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    barcode_cache_folder = Path(__file__).parent / "_barcodes"
    if barcode_cache_folder.exists():
        shutil.rmtree(barcode_cache_folder, ignore_errors=True)

    old_folder_errors = []

    df = pd.read_excel(excel_path, dtype=str)

    df.columns = [
        str(column)
        .replace("\ufeff", "")
        .replace("\xa0", " ")
        .strip()
        for column in df.columns
 ]

    required_columns = [
        COL_SKU, COL_BARCODE,
        COL_NAME
    ]

    missing_columns = [c for c in required_columns if c not in df.columns]

    if missing_columns:
        raise ValueError("חסרות עמודות באקסל: " + ", ".join(missing_columns))

    all_errors = []
    valid_row_indexes = []

    for index, row in df.iterrows():
        excel_row_number = index + 2
        row_errors = validate_product_row(row, excel_row_number)

        if row_errors:
            all_errors.extend(row_errors)
        else:
            valid_row_indexes.append(index)

    report_path = None

    if all_errors:
        report_path = write_validation_report(output_root, all_errors)
    else:
        old_report = output_root / "שגיאות_נתונים.txt"
        if old_report.exists():
            old_report.unlink()

    if not valid_row_indexes:
        raise ValueError(
            "לא נמצאו מוצרים תקינים ליצירת PDF.\n"
            f"דוח השגיאות נוצר כאן:\n{report_path}"
        )

    extracted_images_dir = output_root / "_excel_images"
    image_map = extract_excel_images_by_sku(excel_path, extracted_images_dir)

    total = len(valid_row_indexes)
    created_products = 0

    # ה-ZIP נפתח *מיד* בהתחלה, ונכתב אליו מוצר-מוצר במקום בסוף בבת אחת
    zip_path = output_root.parent / "כל_המוצרים.zip"
    if zip_path.exists():
        zip_path.unlink()

    BROWSER_RECYCLE_EVERY = 150

    async def launch_browser(p):
        return await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        async with async_playwright() as p:
            browser = await launch_browser(p)

            try:
                for progress_index, dataframe_index in enumerate(
                    valid_row_indexes, start=1,
                ):
                    if progress_index > 1 and (progress_index - 1) % BROWSER_RECYCLE_EVERY == 0:
                        await browser.close()
                        browser = await launch_browser(p)

                    row = df.loc[dataframe_index]
                    sku = val(row, COL_SKU)
                   
                    clean_sku = safe_name(sku)

                    folder_name = (
                        clean_sku or  f"row_{dataframe_index + 2}"
                    )

                    product_dir = output_root / folder_name
                    product_dir.mkdir(parents=True, exist_ok=True)

                   

                    photo_path = image_map.get(clean_sku)
                    photo_data = (
                        local_file_to_data_uri(str(photo_path)) if photo_path else ""
                    )

                    await render_templates(row, product_dir, browser, photo_data=photo_data)
                    created_products += 1
              

                    # *** החדש - כותבים את קבצי המוצר הזה ל-ZIP מיד,
                    # ואז מוחקים אותם מהדיסק - לפני שעוברים למוצר הבא ***
                    for file_path in product_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(output_root)
                            zf.write(file_path, arcname)

                    shutil.rmtree(product_dir, ignore_errors=True)

                    if progress_callback:
                        progress_callback(progress_index, total)
            finally:
                await browser.close()

        # תמונות שחולצו מהאקסל - גם אלה נכתבות לזיפ ואז נמחקות
        if extracted_images_dir.exists():
            for file_path in extracted_images_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(output_root)
                    zf.write(file_path, arcname)
            shutil.rmtree(extracted_images_dir, ignore_errors=True)

        old_folder_report_path = None

        

        if report_path and report_path.exists():
            zf.write(report_path, "שגיאות_נתונים.txt")

    shutil.rmtree(output_root, ignore_errors=True)

    return {
        "created_products": created_products,
        "invalid_rows": len(df) - total,
        "error_count": len(all_errors),
        "report_path": report_path,
       
        "zip_path": zip_path,
    }