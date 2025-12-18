"""
打包腳本：將Python應用打包成macOS .app文件
"""
import PyInstaller.__main__
import os

# 應用信息
APP_NAME = "台灣股票選股系統"
SCRIPT_NAME = "app.py"
ICON_FILE = None  # 可以添加圖標文件路徑

# PyInstaller參數
args = [
    SCRIPT_NAME,
    '--name=%s' % APP_NAME,
    '--windowed',  # 無控制台窗口
    '--onefile',   # 打包成單一文件（改為False則打包成目錄）
    '--noconfirm', # 覆蓋輸出目錄
    '--clean',     # 清理臨時文件
    '--add-data=data_fetcher.py:.',
    '--add-data=alpha_strategy.py:.',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=yfinance',
    '--hidden-import=tkinter',
]

# 如果需要打包成.app目錄結構（推薦）
args_dir = [
    SCRIPT_NAME,
    '--name=%s' % APP_NAME,
    '--windowed',
    '--onedir',    # 打包成目錄
    '--noconfirm',
    '--clean',
    '--add-data=data_fetcher.py:.',
    '--add-data=alpha_strategy.py:.',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=yfinance',
    '--hidden-import=tkinter',
]

if __name__ == '__main__':
    print("開始打包應用...")
    print("這可能需要幾分鐘時間...")
    PyInstaller.__main__.run(args_dir)

