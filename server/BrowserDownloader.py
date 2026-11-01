import os
import re
import io
import asyncio
import socket
import ipaddress
from urllib.parse import urlparse, quote

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


router = APIRouter()

BROWSER_AUTOMATION_KEY = os.getenv("BROWSER_AUTOMATION_KEY", "")

PAGE_TIMEOUT = 60000


class BrowserRequest(BaseModel):
    url: str


def clean_filename(filename):
    filename = filename or "invoice.pdf"
    filename = re.sub(r'[\\/:*?"<>|]', "_", filename)

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    return filename


async def validate_url(url):

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Only HTTP/HTTPS URLs are allowed"
        )

    if not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="Invalid URL"
        )

    hostname = parsed.hostname

    if hostname.lower() == "localhost":
        raise HTTPException(
            status_code=400,
            detail="Local URLs are not allowed"
        )

    try:

        loop = asyncio.get_running_loop()

        infos = await loop.getaddrinfo(
            hostname,
            parsed.port or (
                443 if parsed.scheme == "https" else 80
            ),
            type=socket.SOCK_STREAM,
        )

        for info in infos:

            ip = ipaddress.ip_address(
                info[4][0]
            )

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Private/local URL blocked"
                )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not resolve URL: {str(e)}"
        )


async def open_url_and_get_pdf(url):

    await validate_url(url)

    loop = asyncio.get_running_loop()
    pdf_future = loop.create_future()

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            accept_downloads=True,
            locale="he-IL",
            viewport={
                "width": 1440,
                "height": 1200
            }
        )

        page = await context.new_page()

        # -----------------------------
        # תפיסת PDF שמגיע כ-HTTP Response
        # -----------------------------

        async def check_response(response):

            if pdf_future.done():
                return

            try:

                content_type = (
                    response.headers
                    .get("content-type", "")
                    .lower()
                )

                if "application/pdf" in content_type:

                    data = await response.body()

                    if not data:
                        return

                    filename = "invoice.pdf"

                    disposition = response.headers.get(
                        "content-disposition",
                        ""
                    )

                    match = re.search(
                        r'filename="?([^";]+)"?',
                        disposition,
                        re.IGNORECASE
                    )

                    if match:
                        filename = match.group(1)

                    filename = clean_filename(filename)

                    if not pdf_future.done():
                        pdf_future.set_result(
                            (
                                data,
                                filename,
                                "real-pdf"
                            )
                        )

            except Exception:
                pass


        def response_handler(response):
            asyncio.create_task(
                check_response(response)
            )


        page.on(
            "response",
            response_handler
        )

        # -----------------------------
        # תפיסת Download רגיל מהדפדפן
        # -----------------------------

        async def check_download(download):

            if pdf_future.done():
                return

            try:

                path = await download.path()

                if not path:
                    return

                with open(path, "rb") as f:
                    data = f.read()

                if not data.startswith(b"%PDF"):
                    return

                filename = clean_filename(
                    download.suggested_filename
                )

                if not pdf_future.done():
                    pdf_future.set_result(
                        (
                            data,
                            filename,
                            "browser-download"
                        )
                    )

            except Exception:
                pass


        def download_handler(download):
            asyncio.create_task(
                check_download(download)
            )


        page.on(
            "download",
            download_handler
        )

        # -----------------------------
        # פתיחת הקישור
        # -----------------------------

        try:

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=PAGE_TIMEOUT
            )

        except PlaywrightTimeoutError:
            pass

        except Exception as e:
            print(
                "Browser navigation warning:",
                str(e)
            )

        # מאפשר JavaScript / POST אוטומטי לעבוד
        await page.wait_for_timeout(6000)

        # -----------------------------
        # בודקים אם נתפס PDF אמיתי
        # -----------------------------

        if not pdf_future.done():

            try:

                result = await asyncio.wait_for(
                    asyncio.shield(pdf_future),
                    timeout=8
                )

                await context.close()
                await browser.close()

                return result

            except asyncio.TimeoutError:
                pass

        else:

            result = pdf_future.result()

            await context.close()
            await browser.close()

            return result

        # -----------------------------
        # אם זה עמוד אינטרנט ולא PDF
        # הופכים את העמוד ל-PDF
        # -----------------------------

        try:

            pdf_data = await page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True
            )

        except Exception as e:

            await context.close()
            await browser.close()

            raise HTTPException(
                status_code=500,
                detail=f"Could not generate PDF: {str(e)}"
            )

        await context.close()
        await browser.close()

        return (
            pdf_data,
            "invoice.pdf",
            "rendered-html"
        )


@router.post("/api/browser-pdf")
async def browser_pdf(
    request: BrowserRequest,
    x_browser_key: str = Header(default="")
):

    if not BROWSER_AUTOMATION_KEY:
        raise HTTPException(
            status_code=500,
            detail="BROWSER_AUTOMATION_KEY is missing"
        )

    if x_browser_key != BROWSER_AUTOMATION_KEY:
        raise HTTPException(
            status_code=401,
            detail="Wrong browser key"
        )

    data, filename, source = await open_url_and_get_pdf(
        request.url
    )

    encoded_filename = quote(filename)

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f"attachment; filename*=UTF-8''{encoded_filename}",

            "X-Browser-Source":
                source
        }
    )