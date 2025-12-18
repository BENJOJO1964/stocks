#!/usr/bin/env python3
"""
簡單測試腳本：檢查Streamlit應用是否能正常啟動
"""
import subprocess
import sys
import time

print("正在測試Streamlit應用...")
print("-" * 50)

try:
    # 檢查streamlit是否安裝
    import streamlit
    print(f"✓ Streamlit已安裝: {streamlit.__version__}")
except ImportError:
    print("✗ Streamlit未安裝，正在安裝...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    print("✓ Streamlit安裝完成")

# 檢查依賴
try:
    import pandas
    import numpy
    import yfinance
    print("✓ 所有依賴已安裝")
except ImportError as e:
    print(f"✗ 缺少依賴: {e}")

print("-" * 50)
print("正在啟動Streamlit應用...")
print("請等待瀏覽器自動打開...")
print("如果沒有自動打開，請訪問: http://localhost:8501")
print("-" * 50)

# 啟動streamlit
subprocess.run([
    sys.executable, "-m", "streamlit", "run", 
    "app_streamlit.py",
    "--server.headless", "true"
])


