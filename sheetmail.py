from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Mapping, Optional

import gspread
import pytz
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------------------------------------------------------------
# 環境設定
# ---------------------------------------------------------------------------
load_dotenv()

SHEET_URL: str | None = os.getenv("SHEET_URL")
SENDER_EMAIL: str | None = os.getenv("SENDER_EMAIL")
APP_PASSWORD: str | None = os.getenv("APP_PASSWORD")
ATTACH_PATH: str = os.getenv("ATTACH_PATH", "./sample.pdf")
SENDER_NAME: str = os.getenv("SENDER_NAME", "Your Name Here")

if not all([SHEET_URL, SENDER_EMAIL, APP_PASSWORD]):
    raise EnvironmentError("SHEET_URL / SENDER_EMAIL / APP_PASSWORD 必填，請檢查 .env")

# ---------------------------------------------------------------------------
# Google Sheets helpers
# ---------------------------------------------------------------------------

def connect_sheet(sheet_url: Optional[str] = None, creds_file: str = "credentials.json") -> gspread.Worksheet:
    """連上 Google Sheet 並回傳 *第一個* worksheet。

    Parameters
    ----------
    sheet_url : str | None
        目標試算表 URL；若為 ``None``，將使用環境變數 ``SHEET_URL``。
    creds_file : str
        Service‑account 憑證路徑。
    """
    target_url = sheet_url or SHEET_URL
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(target_url).sheet1


def fetch_recipients(ws: gspread.Worksheet) -> List[Mapping[str, str]]:
    """讀取 Sheet 全部資料並以 List[dict] 返還。"""
    return ws.get_all_records()

# ---------------------------------------------------------------------------
# Mail helpers
# ---------------------------------------------------------------------------

def _build_message(name: str, email: str, body: str, attachment_path: str | None = None) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = email
    msg["Subject"] = f"給 {name} 的重要文件"
    msg.attach(MIMEText(body, "plain"))

    if attachment_path and os.path.isfile(attachment_path):
        with open(attachment_path, "rb") as fh:
            part = MIMEApplication(fh.read(), Name=os.path.basename(attachment_path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)

    return msg


def send_email(name: str, email: str, body: str, attachment_path: str | None = ATTACH_PATH) -> None:
    """透過 Gmail SMTP 傳送郵件。"""
    msg = _build_message(name, email, body, attachment_path)

    # 使用 context manager 確保連線正常釋放
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)

# ---------------------------------------------------------------------------
# Sheet 回寫
# ---------------------------------------------------------------------------

def update_status(ws: gspread.Worksheet, row_idx: int, status: str, sent_at: str) -> None:
    ws.update_cell(row_idx, 3, status)  # 第 3 欄 Status
    ws.update_cell(row_idx, 4, sent_at)  # 第 4 欄 Timestamp

# ---------------------------------------------------------------------------
# CLI flow
# ---------------------------------------------------------------------------

def main(dry_run: bool = False) -> None:
    """批次寄信主程式。

    Parameters
    ----------
    dry_run : bool, optional
        若為 ``True`` 則僅列印動作，不實際寄信／寫回。預設 ``False``。
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    ws = connect_sheet()
    recipients = fetch_recipients(ws)
    tz = pytz.timezone("Asia/Taipei")

    for idx, row in enumerate(recipients, start=2):  # sheet 換算到列編號
        name, email, status = row["Name"], row["Email"], row["Status"]
        if str(status).lower().strip() != "pending":
            continue

        body = f"Dear {name},\n\n附件請查閱。\n\n{SENDER_NAME} 敬上"
        logging.info("準備寄信給 %s", email)

        if dry_run:
            logging.info("[dry‑run] 跳過實際寄送與回寫")
            continue

        try:
            send_email(name, email, body)
            sent_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            update_status(ws, idx, "Sent", sent_at)
            logging.info(" 已寄給 %s", email)
        except Exception as exc:  # pylint: disable=broad-except
            logging.error(" 寄信失敗 %s: %s", email, exc)


if __name__ == "__main__":
    main()
