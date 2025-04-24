# app.py  ── SheetMail Web UI
import os
import tempfile
from datetime import datetime

import pytz
import streamlit as st
import sheetmail as sm  # 直接引用，等等要動態覆寫常數
from sheetmail import connect_sheet, fetch_recipients, send_email, update_status

st.set_page_config(page_title="SheetMail Web App")
st.title("📬 SheetMail Web App")

# ---------- 使用者輸入 ----------
sheet_url      = st.text_input("Google Sheet URL")
credentials    = st.file_uploader("上傳 service-account credentials.json", type="json")
app_password   = st.text_input("Gmail App Password", type="password")
pdf_file       = st.file_uploader("上傳 PDF 附件", type="pdf")
sender_name    = st.text_input("Sender Name", value="Your Name")

# ---------- 送出 ----------
if st.button("開始寄信"):
    if not all([sheet_url, credentials, app_password, pdf_file, sender_name]):
        st.error("請補齊所有欄位！")
        st.stop()

    # 1) 儲存 credentials.json（供 gspread 使用）
    with open("credentials.json", "wb") as fh:
        fh.write(credentials.getbuffer())

    # 2) 把使用者輸入塞進環境變數 ＆ sheetmail 常數
    os.environ["SHEET_URL"]   = sheet_url
    os.environ["APP_PASSWORD"] = app_password
    os.environ["SENDER_NAME"]  = sender_name
    sm.SHEET_URL    = sheet_url
    sm.APP_PASSWORD = app_password
    sm.SENDER_NAME  = sender_name

    # 3) 建立 Sheet 連線
    try:
        ws = connect_sheet(sheet_url)
    except Exception as exc:
        st.error(f"無法連線 Google Sheet：{exc}")
        st.stop()

    # 4) 將上傳的 PDF 先存成暫存檔
    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_pdf.write(pdf_file.getbuffer())
    tmp_pdf.close()

    # 5) 批次寄信
    recs = fetch_recipients(ws)
    tz   = pytz.timezone("Asia/Taipei")

    for idx, row in enumerate(recs, start=2):
        name, email, status = row["Name"], row["Email"], row["Status"]
        if str(status).lower().strip() != "pending":
            continue

        body = f"Dear {name},\n\n附件請查閱。\n\n{sender_name} 敬上"

        try:
            send_email(name, email, body, tmp_pdf.name)
            sent_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            update_status(ws, idx, "Sent", sent_at)
            st.success(f"✅ 已寄 {email}")
        except Exception as exc:
            st.error(f"❌ 寄信給 {email} 失敗：{exc}")

    os.unlink(tmp_pdf.name)  # 刪掉暫存檔
    st.balloons()
