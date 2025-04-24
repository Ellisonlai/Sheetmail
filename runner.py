
import os
import subprocess
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------------------------------- #
# 1) 載入 .env
# ------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / ".env")  # 把值直接寫進 os.environ

# ------------------------------------------------------------------- #
# 2) 啟動 Streamlit
# ------------------------------------------------------------------- #
env = os.environ.copy()  # 傳同一組環境給所有子行程
streamlit_proc = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT,
    env=env,
)

print("🚀 Streamlit 已啟動（port 8501）…")
time.sleep(5)  # 給它一點時間起服務

# ------------------------------------------------------------------- #
# 3) 啟動 localtunnel
# ------------------------------------------------------------------- #
try:
    lt_proc = subprocess.Popen(
        ["npx", "localtunnel", "--port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    # 讀取第一行輸出拿到 URL
    for line in lt_proc.stdout:
        if "your url is:" in line.lower():
            public_url = line.split()[-1].strip()
            print(f"🌍 Public URL: {public_url}")
            break
    else:
        print("⚠️  無法取得 localtunnel URL，請檢查 network。")

    print("按 Ctrl+C 可結束所有服務。")
    lt_proc.wait()  # 阻塞直到使用者手動中斷

except KeyboardInterrupt:
    print("\n💨 收到中斷訊號，關閉服務…")

finally:
    for p in (lt_proc, streamlit_proc):
        if p and p.poll() is None:
            p.terminate()