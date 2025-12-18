#!/usr/bin/env python3
"""
台灣股票選股系統 - 啟動腳本
雙擊此文件即可啟動GUI應用
"""
import sys
import os

# 添加當前目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import main
    main()
except ImportError as e:
    print(f"導入錯誤: {e}")
    print("請確保已安裝所有依賴: pip install -r requirements.txt")
    input("按Enter鍵退出...")
except Exception as e:
    print(f"啟動失敗: {e}")
    input("按Enter鍵退出...")

