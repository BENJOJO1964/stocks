"""
TWSE API 集成範例（未來可選）
這個模組展示了如何集成TWSE API獲取買賣超數據
而不影響現有的yfinance功能
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
import time


class TWSEDataFetcher:
    """
    TWSE API 數據獲取器
    用於補充yfinance不支持的買賣超數據
    """
    
    def __init__(self):
        """初始化TWSE數據獲取器"""
        self.base_url = "https://www.twse.com.tw/rwd/zh/fund/T86"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def get_institutional_trading(self, stock_code: str, date: Optional[str] = None) -> Optional[Dict]:
        """
        獲取三大法人買賣超數據
        
        Parameters:
        -----------
        stock_code : str
            股票代號，如 '2330'（不含.TW或.TWO）
        date : str, optional
            日期，格式 'YYYYMMDD'，默認為今天
        
        Returns:
        --------
        Dict: 包含外資、投信、自營商買賣超數據
            如果獲取失敗，返回None
        """
        try:
            # 轉換股票代號（去除.TW或.TWO後綴）
            code = stock_code.replace('.TW', '').replace('.TWO', '')
            
            # 如果沒有指定日期，使用今天
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            
            # 構建請求參數
            params = {
                'date': date,
                'selectType': 'ALLBUT0999'  # 查詢所有股票
            }
            
            # 發送請求（添加適當的延遲避免被封鎖）
            time.sleep(0.5)  # 避免請求過快
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # 解析數據
            if 'data' not in data or not data['data']:
                return None
            
            # 查找指定股票
            for row in data['data']:
                if len(row) > 0 and row[0] == code:
                    # 解析買賣超數據
                    # 格式：[股票代號, 股票名稱, 外資買賣超, 投信買賣超, 自營商買賣超, ...]
                    try:
                        foreign = int(row[4].replace(',', '')) if len(row) > 4 and row[4] else 0
                        trust = int(row[10].replace(',', '')) if len(row) > 10 and row[10] else 0
                        dealer = int(row[11].replace(',', '')) if len(row) > 11 and row[11] else 0
                        
                        return {
                            '外資買賣超': foreign,
                            '投信買賣超': trust,
                            '自營商買賣超': dealer,
                            '日期': date
                        }
                    except:
                        return None
            
            return None
            
        except Exception as e:
            print(f"獲取TWSE數據失敗 ({stock_code}): {str(e)}")
            return None
    
    def get_recent_institutional_trading(self, stock_code: str, days: int = 5) -> Dict:
        """
        獲取最近N天的買賣超數據（用於計算趨勢）
        
        Parameters:
        -----------
        stock_code : str
            股票代號
        days : int
            最近N天
        
        Returns:
        --------
        Dict: 包含最近N天的買賣超統計
        """
        results = []
        today = datetime.now()
        
        for i in range(days):
            check_date = today - timedelta(days=i)
            date_str = check_date.strftime('%Y%m%d')
            
            # 跳過週末
            if check_date.weekday() >= 5:
                continue
            
            data = self.get_institutional_trading(stock_code, date_str)
            if data:
                results.append(data)
            
            time.sleep(0.5)  # 避免請求過快
        
        if not results:
            return {
                '外資_5日累計': 0,
                '投信_5日累計': 0,
                '自營商_5日累計': 0,
                '總買賣超_5日累計': 0
            }
        
        # 計算累計
        foreign_total = sum(r['外資買賣超'] for r in results)
        trust_total = sum(r['投信買賣超'] for r in results)
        dealer_total = sum(r['自營商買賣超'] for r in results)
        
        return {
            '外資_5日累計': foreign_total,
            '投信_5日累計': trust_total,
            '自營商_5日累計': dealer_total,
            '總買賣超_5日累計': foreign_total + trust_total + dealer_total
        }


# 使用範例（集成到stock_scanner.py）
"""
# 在stock_scanner.py中添加：

from twse_api_example import TWSEDataFetcher

class TaiwanStockScanner:
    def __init__(self, ..., use_twse_api=False):
        ...
        self.use_twse_api = use_twse_api
        if use_twse_api:
            self.twse_fetcher = TWSEDataFetcher()
    
    def get_institutional_data(self, stock_id: str) -> dict:
        # 優先使用TWSE API（如果啟用）
        if self.use_twse_api:
            try:
                twse_data = self.twse_fetcher.get_recent_institutional_trading(stock_id, days=5)
                if twse_data:
                    # 計算機構資金評分（基於買賣超數據）
                    total_net = twse_data.get('總買賣超_5日累計', 0)
                    if total_net > 0:
                        return twse_data
            except:
                pass
        
        # 回退到yfinance（現有邏輯，不變）
        return self.get_yfinance_institutional_data(stock_id)
"""

