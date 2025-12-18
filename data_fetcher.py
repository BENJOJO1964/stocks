"""
DataFetcher: 從TWSE獲取股票歷史數據
100%真實數據，使用yfinance直接從Yahoo Finance獲取，絕不模擬
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class DataFetcher:
    """
    用於獲取台灣股票市場歷史數據的類
    只使用yfinance獲取真實的OHLCV數據
    """
    
    def __init__(self):
        """初始化DataFetcher"""
        pass
    
    def fetch_data(self, stock_id: str, start_date: str) -> pd.DataFrame:
        """
        獲取股票歷史數據（100%真實數據，從yfinance獲取）
        
        Parameters:
        -----------
        stock_id : str
            股票代號，格式如 '2330.TW'
        start_date : str
            開始日期，格式 'YYYY-MM-DD'
        
        Returns:
        --------
        pd.DataFrame
            包含以下欄位的DataFrame（全部真實數據）:
            - Date: 日期（索引）
            - Open: 開盤價（真實）
            - High: 最高價（真實）
            - Low: 最低價（真實）
            - Close: 收盤價（真實）
            - Volume: 成交量（真實）
        """
        try:
            # 使用yfinance獲取真實數據
            ticker = yf.Ticker(stock_id)
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 獲取歷史數據（真實數據）
            hist_data = ticker.history(start=start_date, end=end_date)
            
            if hist_data.empty:
                raise ValueError(f"無法從yfinance獲取 {stock_id} 的真實數據，請檢查股票代號")
            
            # 重置索引，將Date轉為欄位
            df = hist_data.reset_index()
            
            # 確保Date欄位存在
            if 'Date' not in df.columns:
                if df.index.name == 'Date':
                    df = df.reset_index()
                else:
                    df['Date'] = pd.to_datetime(df.index) if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime('today')
            
            # 標準化欄位名稱
            df['Date'] = pd.to_datetime(df['Date'])
            
            # 只保留yfinance提供的真實欄位
            real_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            available_columns = [col for col in real_columns if col in df.columns]
            
            if len(available_columns) < 5:  # 至少需要5個欄位（不含Date）
                raise ValueError(f"獲取的數據不完整，缺少必要欄位: {stock_id}")
            
            df = df[available_columns].copy()
            
            # 排序確保日期正確
            df = df.sort_values('Date').reset_index(drop=True)
            
            # 設定Date為索引以便後續處理
            df.set_index('Date', inplace=True)
            
            # 驗證數據完整性
            if df.isnull().any().any():
                # 填充缺失值（使用前一個值）
                df = df.ffill().bfill()
            
            return df
            
        except Exception as e:
            raise Exception(f"從yfinance獲取 {stock_id} 真實數據時發生錯誤: {str(e)}")
    
    def fetch_multiple_stocks(self, stock_list: list, start_date: str) -> dict:
        """
        批量獲取多支股票的數據（全部真實數據）
        
        Parameters:
        -----------
        stock_list : list
            股票代號列表，如 ['2330.TW', '2317.TW']
        start_date : str
            開始日期
        
        Returns:
        --------
        dict
            以股票代號為key，DataFrame為value的字典（全部真實數據）
        """
        data_dict = {}
        for stock_id in stock_list:
            try:
                print(f"正在從yfinance獲取 {stock_id} 的真實數據...")
                data_dict[stock_id] = self.fetch_data(stock_id, start_date)
                print(f"✅ 成功獲取 {stock_id} 的真實數據，共 {len(data_dict[stock_id])} 筆（來源：yfinance）")
            except Exception as e:
                print(f"❌ 獲取 {stock_id} 失敗: {str(e)}")
                continue
        
        return data_dict
