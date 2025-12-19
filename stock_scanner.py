"""
Taiwan Stock Market Scanner - 專業評分系統
使用多因子評分系統掃描全市場股票
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')


class TaiwanStockScanner:
    """台灣股市掃描器 - 使用評分系統"""
    
    # 台灣高Alpha股票列表（固定16支，不允許其他股票）
    # 注意：上市股票使用.TW，上櫃股票使用.TWO
    DEFAULT_TICKERS = {
        '2330.TW': '半導體/龍頭',
        '2317.TW': '鴻海組裝',
        '2382.TW': 'AI伺服器',
        '3231.TW': 'AI伺服器',
        '3017.TW': 'AI散熱',
        '2376.TW': 'AI伺服器',
        '3037.TW': '載板',
        '2881.TW': '金融/權值',
        '2882.TW': '金融/權值',
        '2603.TW': '航運',
        '1513.TW': '重電',
        '1504.TW': '重電',
        '3019.TW': '機器人',
        '4979.TWO': '光通訊(上櫃)',  # 上櫃股票必須使用.TWO後綴
        '6451.TW': '光通訊',
        '3450.TW': '光通訊'
    }
    
    # 股票名稱映射
    STOCK_NAMES = {
        '2330.TW': '台積電',
        '2317.TW': '鴻海',
        '2382.TW': '廣達',
        '3231.TW': '緯創',
        '3017.TW': '奇鋐',
        '2376.TW': '技嘉',
        '3037.TW': '欣興',
        '2881.TW': '富邦金',
        '2882.TW': '國泰金',
        '2603.TW': '長榮',
        '1513.TW': '中興電',
        '1504.TW': '東元',
        '3019.TW': '亞光',
        '4979.TWO': '華星光',  # 更新為.TWO
        '6451.TW': '訊芯-KY',
        '3450.TW': '聯鈞'
    }
    
    # 為了向後兼容，保留列表格式
    DEFAULT_STOCK_LIST = list(DEFAULT_TICKERS.keys())
    
    def __init__(self, 
                 trend_weight: float = 0.40,
                 momentum_weight: float = 0.30,
                 relative_strength_weight: float = 0.20,
                 institutional_weight: float = 0.10,
                 min_score: float = 70.0,
                 ma_short: int = 20,
                 ma_long: int = 60,
                 vol_multiplier: float = 1.2,
                 atr_period: int = 14,
                 stop_loss_atr_mult: float = 2.0,
                 min_avg_volume: float = 1000000.0,  # 最小日均成交量（排除流動性差的股票）
                 enable_fundamental_filter: bool = True,  # 啟用基本面篩選
                 enable_liquidity_check: bool = True):  # 啟用流動性檢查
        """
        初始化掃描器
        
        Parameters:
        -----------
        trend_weight : float
            趨勢權重（40%）
        momentum_weight : float
            動量權重（30%）
        relative_strength_weight : float
            相對強度權重（20%）
        institutional_weight : float
            機構資金權重（10%）
        min_score : float
            最低分數閾值（70分）
        """
        self.trend_weight = trend_weight
        self.momentum_weight = momentum_weight
        self.relative_strength_weight = relative_strength_weight
        self.institutional_weight = institutional_weight
        self.min_score = min_score
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.vol_multiplier = vol_multiplier
        self.atr_period = atr_period
        self.stop_loss_atr_mult = stop_loss_atr_mult
        self.min_avg_volume = min_avg_volume  # 最小日均成交量
        self.enable_fundamental_filter = enable_fundamental_filter
        self.enable_liquidity_check = enable_liquidity_check
        
        # 獲取TAIEX作為基準（用於相對強度計算）
        self.benchmark_ticker = '^TWII'  # 台灣加權指數
    
    def fetch_stock_data(self, stock_id: str, years: int = 1) -> pd.DataFrame:
        """
        獲取股票數據（使用2年數據以準確計算MA60和RS）
        智能處理上櫃股票：如果.TW找不到，自動嘗試.TWO
        
        Parameters:
        -----------
        stock_id : str
            股票代號
        years : int
            獲取多少年的數據（預設2年）
        
        Returns:
        --------
        pd.DataFrame
            包含OHLCV的真實數據
        """
        try:
            ticker = yf.Ticker(stock_id)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            
            # 優先使用period='1y'獲取最新數據（包含今天如果已收盤）
            # 如果失敗，再使用start/end方式
            hist_data = None
            try:
                hist_data = ticker.history(period='1y')
                if hist_data.empty:
                    hist_data = ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                                              end=end_date.strftime('%Y-%m-%d'))
            except Exception as e1:
                # 如果period方式失敗，使用start/end
                try:
                    hist_data = ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                                              end=end_date.strftime('%Y-%m-%d'))
                except Exception as e2:
                    # 如果.TW找不到，自動嘗試.TWO（針對上櫃股票）
                    if stock_id.endswith('.TW') and len(stock_id) == 8:  # 例如：4979.TW
                        alt_ticker_id = stock_id.replace('.TW', '.TWO')
                        try:
                            alt_ticker = yf.Ticker(alt_ticker_id)
                            try:
                                hist_data = alt_ticker.history(period='1y')
                                if hist_data.empty:
                                    hist_data = alt_ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                                                                  end=end_date.strftime('%Y-%m-%d'))
                                # 如果.TWO找到數據，更新stock_id以便後續處理
                                if hist_data is not None and not hist_data.empty:
                                    print(f"ℹ️ {stock_id} 在.TW找不到，自動切換到.TWO並成功獲取數據")
                                    stock_id = alt_ticker_id
                            except:
                                pass
                        except:
                            pass
                    
                    # 如果還是失敗，返回None
                    if hist_data is None or (hasattr(hist_data, 'empty') and hist_data.empty):
                        print(f"⚠️ Ticker {stock_id} not found on Yahoo Finance.")
                        print(f"   請確認：上市股票使用.TW，上櫃股票使用.TWO")
                        return None
            
            if hist_data is None or hist_data.empty:
                # 最後一次嘗試：如果是.TW，試試.TWO
                if stock_id.endswith('.TW') and len(stock_id) == 8:
                    alt_ticker_id = stock_id.replace('.TW', '.TWO')
                    try:
                        alt_ticker = yf.Ticker(alt_ticker_id)
                        try:
                            hist_data = alt_ticker.history(period='1y')
                            if hist_data.empty:
                                hist_data = alt_ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                                                              end=end_date.strftime('%Y-%m-%d'))
                            if hist_data is not None and not hist_data.empty:
                                print(f"ℹ️ {stock_id} 在.TW找不到，自動切換到.TWO並成功獲取數據")
                                stock_id = alt_ticker_id
                        except:
                            pass
                    except:
                        pass
                
                if hist_data is None or hist_data.empty:
                    print(f"⚠️ Ticker {stock_id} not found on Yahoo Finance (no data returned)")
                    return None
            
            df = hist_data.reset_index()
            if 'Date' not in df.columns:
                df['Date'] = pd.to_datetime(df.index)
            
            df['Date'] = pd.to_datetime(df['Date'])
            
            # 只保留真實數據欄位
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            available_cols = [col for col in required_cols if col in df.columns]
            
            if len(available_cols) < 6:
                return None
            
            df = df[available_cols].copy()
            df = df.sort_values('Date').reset_index(drop=True)
            df.set_index('Date', inplace=True)
            
            # 填充缺失值
            df = df.ffill().bfill()
            
            return df
            
        except Exception as e:
            print(f"獲取 {stock_id} 數據失敗: {str(e)}")
            return None
    
    def fetch_benchmark_data(self, years: int = 1) -> Optional[pd.DataFrame]:
        """獲取TAIEX基準數據"""
        try:
            ticker = yf.Ticker(self.benchmark_ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            
            hist_data = ticker.history(start=start_date.strftime('%Y-%m-%d'),
                                      end=end_date.strftime('%Y-%m-%d'))
            
            if hist_data.empty:
                return None
            
            df = hist_data[['Close']].copy()
            df.columns = ['Benchmark_Close']
            return df
            
        except Exception as e:
            print(f"獲取基準數據失敗: {str(e)}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算技術指標"""
        df = df.copy()
        
        # 移動平均線（價格）
        df['MA5'] = df['Close'].rolling(window=5).mean()  # 5日均線
        df['MA20'] = df['Close'].rolling(window=self.ma_short).mean()  # 短期均線
        df['MA50'] = df['Close'].rolling(window=50).mean()  # 中期均線（長期趨勢確認）
        df['MA60'] = df['Close'].rolling(window=self.ma_long).mean()  # 長期均線
        df['MA200'] = df['Close'].rolling(window=200).mean()  # 超長期均線（長期趨勢保護）
        
        # 成交量均線
        df['MA5_Vol'] = df['Volume'].rolling(window=5).mean()
        df['MA20_Vol'] = df['Volume'].rolling(window=20).mean()  # 20日均量（新增）
        
        # 計算RSI14（使用Wilder平滑方法 - 標準公式）
        def calculate_rsi_wilder(series, period=14):
            """
            計算RSI指標 - 使用Wilder的平滑方法（標準公式）
            Wilder使用指數移動平均（EMA）而非簡單移動平均
            """
            delta = series.diff()
            
            # 分離上漲和下跌
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            
            # 計算初始平均（前period天的簡單平均）
            avg_gain = gain.rolling(window=period, min_periods=period).mean()
            avg_loss = loss.rolling(window=period, min_periods=period).mean()
            
            # Wilder平滑方法：使用EMA（指數移動平均）
            # EMA公式：EMA_today = (Value_today × α) + (EMA_yesterday × (1-α))
            # 對於Wilder RSI，α = 1/period
            alpha = 1.0 / period
            
            # 計算平滑的平均收益和平均損失
            smoothed_gain = pd.Series(index=series.index, dtype=float)
            smoothed_loss = pd.Series(index=series.index, dtype=float)
            
            for i in range(len(series)):
                if i < period - 1:
                    smoothed_gain.iloc[i] = np.nan
                    smoothed_loss.iloc[i] = np.nan
                elif i == period - 1:
                    # 第一個值使用簡單平均
                    smoothed_gain.iloc[i] = avg_gain.iloc[i]
                    smoothed_loss.iloc[i] = avg_loss.iloc[i]
                else:
                    # 後續值使用Wilder平滑（EMA）
                    smoothed_gain.iloc[i] = (gain.iloc[i] * alpha) + (smoothed_gain.iloc[i-1] * (1 - alpha))
                    smoothed_loss.iloc[i] = (loss.iloc[i] * alpha) + (smoothed_loss.iloc[i-1] * (1 - alpha))
            
            # 計算RS（相對強度）
            rs = smoothed_gain / smoothed_loss.replace(0, np.nan)
            
            # 計算RSI
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        df['RSI14'] = calculate_rsi_wilder(df['Close'], period=14)
        
        # 計算60日高點（新增）
        df['High_60d'] = df['High'].rolling(window=60).max()
        
        # 計算自60日高點的回檔幅度（新增）
        df['Pullback_From_60d_High'] = np.where(
            df['High_60d'].notna() & (df['High_60d'] > 0),
            ((df['High_60d'] - df['Close']) / df['High_60d']) * 100,
            np.nan
        )
        
        # ATR
        df['High_Low'] = df['High'] - df['Low']
        df['High_Close'] = abs(df['High'] - df['Close'].shift(1))
        df['Low_Close'] = abs(df['Low'] - df['Close'].shift(1))
        df['True_Range'] = df[['High_Low', 'High_Close', 'Low_Close']].max(axis=1)
        df['ATR'] = df['True_Range'].rolling(window=self.atr_period).mean()
        df.drop(['High_Low', 'High_Close', 'Low_Close', 'True_Range'], axis=1, inplace=True)
        
        return df
    
    def check_market_environment(self) -> str:
        """
        判斷市場環境：多頭/空頭/盤整
        
        Returns:
        --------
        str: '多頭', '空頭', '盤整', '未知'
        """
        try:
            benchmark_df = self.fetch_benchmark_data(years=1)
            if benchmark_df is None or len(benchmark_df) < 60:
                return '未知'
            
            # 計算加權指數的趨勢
            benchmark_df['MA20'] = benchmark_df['Benchmark_Close'].rolling(window=20).mean()
            benchmark_df['MA60'] = benchmark_df['Benchmark_Close'].rolling(window=60).mean()
            
            if len(benchmark_df) < 60:
                return '未知'
            
            latest = benchmark_df.iloc[-1]
            recent_20d = benchmark_df.iloc[-20:]
            
            current_price = latest['Benchmark_Close']
            ma20 = latest['MA20']
            ma60 = latest['MA60']
            
            # 判斷條件
            price_above_ma20 = current_price > ma20 if pd.notna(ma20) else False
            price_above_ma60 = current_price > ma60 if pd.notna(ma60) else False
            ma20_above_ma60 = ma20 > ma60 if (pd.notna(ma20) and pd.notna(ma60)) else False
            
            # 計算最近20天的波動性（用於判斷盤整）
            volatility = recent_20d['Benchmark_Close'].std() / recent_20d['Benchmark_Close'].mean()
            price_change_20d = (current_price - recent_20d['Benchmark_Close'].iloc[0]) / recent_20d['Benchmark_Close'].iloc[0]
            
            # 判斷邏輯
            if price_above_ma20 and price_above_ma60 and ma20_above_ma60:
                # 如果波動性小且漲幅小，可能是盤整
                if abs(price_change_20d) < 0.03 and volatility < 0.02:
                    return '盤整'
                return '多頭'
            elif not price_above_ma20 and not price_above_ma60 and not ma20_above_ma60:
                return '空頭'
            elif abs(price_change_20d) < 0.02 and volatility < 0.015:
                return '盤整'
            else:
                return '未知'
                
        except Exception as e:
            print(f"判斷市場環境失敗: {str(e)}")
            return '未知'
    
    def check_liquidity(self, df: pd.DataFrame) -> bool:
        """
        檢查流動性：日均成交量是否足夠
        
        Parameters:
        -----------
        df : pd.DataFrame
            股票數據
        
        Returns:
        --------
        bool: True表示流動性充足，False表示流動性不足
        """
        if not self.enable_liquidity_check:
            return True
        
        if df is None or len(df) < 20:
            return False
        
        # 計算最近20天的平均成交量
        avg_volume = df['Volume'].tail(20).mean()
        
        # 檢查是否達到最低標準
        return avg_volume >= self.min_avg_volume
    
    def check_fundamental(self, stock_id: str) -> tuple:
        """
        檢查基本面：獲取財務數據並判斷是否健康
        
        Parameters:
        -----------
        stock_id : str
            股票代號
        
        Returns:
        --------
        tuple: (is_healthy: bool, reason: str, financial_data: dict)
        """
        if not self.enable_fundamental_filter:
            return (True, '基本面篩選已停用', {})
        
        try:
            ticker = yf.Ticker(stock_id)
            info = ticker.info
            
            # 嘗試獲取關鍵財務指標
            financial_data = {}
            issues = []
            
            # 檢查營收成長（如果可用）
            if 'revenueGrowth' in info and pd.notna(info['revenueGrowth']):
                revenue_growth = info['revenueGrowth'] * 100  # 轉換為百分比
                financial_data['營收成長率'] = f"{revenue_growth:.2f}%"
                if revenue_growth < -20:  # 營收大幅下降
                    issues.append(f"營收大幅下降({revenue_growth:.1f}%)")
            
            # 檢查EPS（如果可用）
            if 'trailingEps' in info and pd.notna(info['trailingEps']):
                eps = info['trailingEps']
                financial_data['EPS'] = f"{eps:.2f}"
                if eps < 0:  # 虧損
                    issues.append(f"EPS為負({eps:.2f})")
            
            # 檢查負債比率（如果可用）
            if 'debtToEquity' in info and pd.notna(info['debtToEquity']):
                debt_ratio = info['debtToEquity']
                financial_data['負債比率'] = f"{debt_ratio:.2f}"
                if debt_ratio > 100:  # 負債比率過高
                    issues.append(f"負債比率過高({debt_ratio:.1f})")
            
            # 檢查流動比率（如果可用）
            if 'currentRatio' in info and pd.notna(info['currentRatio']):
                current_ratio = info['currentRatio']
                financial_data['流動比率'] = f"{current_ratio:.2f}"
                if current_ratio < 1.0:  # 流動性不足
                    issues.append(f"流動比率不足({current_ratio:.2f})")
            
            # 判斷是否健康
            if issues:
                return (False, '; '.join(issues), financial_data)
            else:
                return (True, '財務狀況正常', financial_data)
                
        except Exception as e:
            # 如果無法獲取財務數據，不阻止（因為yfinance對台灣股票支持有限）
            return (True, f'無法獲取財務數據', {})
    
    def get_institutional_data(self, stock_id: str) -> dict:
        """
        獲取籌碼面數據（外資、投信、自營商買賣超）
        
        注意：yfinance對台灣股票的籌碼面數據支持有限
        這個功能主要作為佔位符，未來可以接入其他數據源
        
        Parameters:
        -----------
        stock_id : str
            股票代號
        
        Returns:
        --------
        dict: 包含籌碼面數據的字典
        """
        try:
            ticker = yf.Ticker(stock_id)
            info = ticker.info
            
            # yfinance對台灣股票的籌碼面數據支持有限
            # 這裡嘗試獲取可能存在的相關字段
            institutional_data = {}
            
            # 嘗試獲取機構持股比例（如果可用）
            if 'heldPercentInstitutions' in info and pd.notna(info['heldPercentInstitutions']):
                institutional_data['機構持股比例'] = f"{info['heldPercentInstitutions'] * 100:.2f}%"
            
            # 注意：yfinance通常不提供外資/投信/自營商買賣超數據
            # 這些數據需要從台灣證券交易所或專門的數據源獲取
            
            return institutional_data
            
        except Exception as e:
            return {}
    
    def calculate_relative_strength(self, stock_df: pd.DataFrame, 
                                   benchmark_df: Optional[pd.DataFrame]) -> pd.Series:
        """
        計算相對強度（相對於TAIEX）- 標準公式
        使用過去250個交易日的價格變化率
        
        Formula: (Stock_%_Change / Benchmark_%_Change) over 250 days
        
        Returns:
        --------
        pd.Series
            相對強度分數（0-100）
        """
        if benchmark_df is None:
            # 如果無法獲取基準，返回中性分數
            return pd.Series(50.0, index=stock_df.index)
        
        # 合併數據
        merged = pd.merge(
            stock_df[['Close']],
            benchmark_df,
            left_index=True,
            right_index=True,
            how='inner'
        )
        
        # 需要至少250個交易日，但如果數據不足，使用可用的最大長度
        min_days = min(250, len(merged))
        if min_days < 60:  # 至少需要60天才能計算
            return pd.Series(50.0, index=stock_df.index)
        
        # 標準RS公式：過去250天的價格變化率（每個時間點都使用其250天前的價格）
        # Stock_%_Change = (Current_Price / Price_250_days_ago - 1) * 100
        # Benchmark_%_Change = (Current_Benchmark / Benchmark_250_days_ago - 1) * 100
        # RS = Stock_%_Change / Benchmark_%_Change
        
        lookback_days = min(250, len(merged))  # 使用可用的最大天數（最多250天）
        
        # 計算每個時間點的250天變化率（使用rolling窗口）
        # 對於每個時間點，使用其250天前的價格作為起始點
        stock_pct_change = pd.Series(0.0, index=merged.index)
        benchmark_pct_change = pd.Series(0.0, index=merged.index)
        
        # 使用rolling窗口計算每個時間點相對於250天前的變化率
        for i in range(lookback_days, len(merged)):
            stock_start_price = merged['Close'].iloc[i - lookback_days]
            benchmark_start_price = merged['Benchmark_Close'].iloc[i - lookback_days]
            current_stock_price = merged['Close'].iloc[i]
            current_benchmark_price = merged['Benchmark_Close'].iloc[i]
            
            if stock_start_price > 0 and benchmark_start_price > 0:
                stock_pct_change.iloc[i] = ((current_stock_price / stock_start_price) - 1) * 100
                benchmark_pct_change.iloc[i] = ((current_benchmark_price / benchmark_start_price) - 1) * 100
        
        # 對於前250天的數據，使用可用的最大窗口
        if len(merged) < 250:
            for i in range(min(60, len(merged)), len(merged)):
                stock_start_price = merged['Close'].iloc[0]
                benchmark_start_price = merged['Benchmark_Close'].iloc[0]
                current_stock_price = merged['Close'].iloc[i]
                current_benchmark_price = merged['Benchmark_Close'].iloc[i]
                
                if stock_start_price > 0 and benchmark_start_price > 0:
                    stock_pct_change.iloc[i] = ((current_stock_price / stock_start_price) - 1) * 100
                    benchmark_pct_change.iloc[i] = ((current_benchmark_price / benchmark_start_price) - 1) * 100
        
        # 計算相對強度比率（避免除零）
        rs_ratio = stock_pct_change / benchmark_pct_change.replace(0, np.nan)
        rs_ratio = rs_ratio.fillna(1.0)  # 基準無變化時設為1.0
        
        # 轉換為分數（0-100）
        # RS_ratio > 1.5: 100分, > 1.2: 80分, > 1.0: 60分, > 0.8: 40分, < 0.8: 20分
        rs_scores = np.where(
            rs_ratio > 1.5, 100.0,
            np.where(rs_ratio > 1.2, 80.0,
            np.where(rs_ratio > 1.0, 60.0,
            np.where(rs_ratio > 0.8, 40.0, 20.0)))
        )
        rs_scores = pd.Series(rs_scores, index=merged.index)
        rs_scores = rs_scores.fillna(50.0)
        
        # 對齊索引
        result = pd.Series(50.0, index=stock_df.index)
        result.loc[rs_scores.index] = rs_scores
        
        return result
    
    def calculate_scores(self, df: pd.DataFrame, 
                        benchmark_df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        計算波段交易評分（Swing Trading - 持有2-4周）
        
        Returns:
        --------
        pd.DataFrame
            包含所有評分和總分的DataFrame
        """
        df = df.copy()
        
        # 計算指標
        df = self.calculate_indicators(df)
        
        # 數據驗證：檢查是否有NaN或空值
        critical_cols = ['Close', 'MA5', 'MA20', 'MA60', 'ATR']
        has_nan = df[critical_cols].isnull().any(axis=1)
        df['Data_Error'] = has_nan
        
        # ===== 長期趨勢保護（MA50/MA200）- 專業級確認 =====
        # 檢查長期趨勢：價格 > MA50 > MA200（確認長期上升趨勢）
        long_term_trend = (
            (df['Close'] > df['MA50']) & 
            (df['MA50'] > df['MA200']) &
            df['Close'].notna() & 
            df['MA50'].notna() & 
            df['MA200'].notna()
        )
        df['長期趨勢確認'] = long_term_trend  # 額外的長期趨勢保護
        
        # ===== 新增規則：觀察條件和進場觸發條件 =====
        # 觀察條件：自60日高點回檔 ≥ 20%（不是進場條件，只是觀察）
        pullback_20pct = df['Pullback_From_60d_High'] >= 20.0
        pullback_20pct = pullback_20pct & df['Pullback_From_60d_High'].notna()
        df['觀察條件_回檔20%'] = pullback_20pct
        
        # 進場必要條件（Trigger）- 三個必須同時成立：
        # 1. MA20 ≥ MA60（允許等於，與原有規則MA20 > MA60稍有不同，但為了新規則兼容）
        condition_ma20_ma60 = (df['MA20'] >= df['MA60']) & df['MA20'].notna() & df['MA60'].notna()
        
        # 2. RSI14 重新站上 50
        # 要求：當前RSI >= 50，且之前RSI < 50（重新站上）
        # 或者：當前RSI >= 50 且之前RSI >= 50（持續站上，也符合條件）
        rsi_current_above_50 = (df['RSI14'] >= 50) & df['RSI14'].notna()
        rsi_prev_below_50 = (df['RSI14'].shift(1) < 50) | df['RSI14'].shift(1).isna()
        rsi_cross_above = rsi_current_above_50 & rsi_prev_below_50  # 重新站上
        rsi_continuing_above = rsi_current_above_50 & (df['RSI14'].shift(1) >= 50) & df['RSI14'].shift(1).notna()  # 持續站上
        # 只要當前RSI >= 50，就視為符合條件（包括重新站上和持續站上）
        rsi_stand_above_50 = rsi_current_above_50
        
        # 3. 成交量 ≥ 20日均量
        volume_above_ma20 = (df['Volume'] >= df['MA20_Vol']) & df['Volume'].notna() & df['MA20_Vol'].notna()
        
        # 進場觸發條件：三個條件同時成立
        new_entry_trigger = condition_ma20_ma60 & rsi_stand_above_50 & volume_above_ma20
        df['新規則_進場觸發'] = new_entry_trigger
        
        # 1. 趨勢基礎（波段基石）- 必須滿足：Close > MA20 AND MA20 > MA60（原有規則）
        trend_foundation = (
            (df['Close'] > df['MA20']) & 
            (df['MA20'] > df['MA60']) &
            df['Close'].notna() & 
            df['MA20'].notna() & 
            df['MA60'].notna()
        )
        
        # 長期趨勢確認（額外加分項）：如果滿足 MA50/MA200 長期趨勢，額外加分
        # 注意：這是額外的確認，不作為必要條件（因為台股波段交易可能不需要嚴格滿足MA200）
        # 但如果滿足，代表長期趨勢更強，可以獲得更高評分
        
        # 合併原有規則和新規則：必須同時滿足原有趨勢基礎 AND 新進場觸發條件
        # 但為了兼容，我們將新規則作為額外的確認條件
        enhanced_entry_condition = trend_foundation & new_entry_trigger
        
        # 2. 進場點優化（Entry Trigger）
        # 2a. MA5 > MA20 (Golden Cross) - 加分
        golden_cross = (df['MA5'] > df['MA20']) & df['MA5'].notna() & df['MA20'].notna()
        
        # 2b. 當前價格在MA20的3%以內 - 加分（接近支撐線）
        price_near_ma20 = np.abs((df['Close'] - df['MA20']) / df['MA20']) <= 0.03
        price_near_ma20 = price_near_ma20 & df['Close'].notna() & df['MA20'].notna()
        
        # 趨勢評分（40%）：必須有趨勢基礎才能得分
        # 如果同時滿足長期趨勢（MA50/MA200），額外加分
        base_trend_score = np.where(
            trend_foundation,
            np.where(
                golden_cross & price_near_ma20, 100.0,  # 完美進場點
                np.where(golden_cross, 80.0,  # 有Golden Cross
                np.where(price_near_ma20, 70.0, 50.0))  # 接近MA20
            ),
            0.0  # 沒有趨勢基礎，不得分
        )
        
        # 長期趨勢確認加分：如果滿足 MA50 > MA200，額外加5分（最高100分）
        long_term_bonus = np.where(long_term_trend & trend_foundation, 5.0, 0.0)
        trend_score = np.minimum(base_trend_score + long_term_bonus, 100.0)
        
        df['Trend_Score'] = trend_score * self.trend_weight
        df['長期趨勢加分'] = long_term_bonus  # 記錄長期趨勢加分
        
        # 3. 動量評分（30%）
        momentum_score = np.where(
            (df['Volume'] > (self.vol_multiplier * df['MA5_Vol'])) & df['Volume'].notna(),
            100.0,
            0.0
        )
        df['Momentum_Score'] = momentum_score * self.momentum_weight
        
        # 4. 相對強度評分（20%）
        rs_scores = self.calculate_relative_strength(df, benchmark_df)
        df['RS_Score'] = rs_scores * self.relative_strength_weight
        
        # 5. 機構資金評分（10%）
        # 注意：yfinance對台灣股票的籌碼面數據（外資/投信/自營商買賣超）支持有限
        # 這裡嘗試從ticker.info獲取機構持股比例（如果可用）
        # 未來可以接入其他數據源（如TWSE API）獲取真實的買賣超數據
        institutional_score = pd.Series(50.0, index=df.index)  # 默認中性分數
        
        # 注意：這裡無法為每行數據獲取不同的籌碼面數據（因為需要為每支股票單獨調用API）
        # 實際的籌碼面數據應該在scan_stocks時獲取並傳入
        # 當前實現暫時使用固定分數
        df['Institutional_Score'] = institutional_score * self.institutional_weight
        
        # 計算總分（只有通過趨勢基礎檢查的才能得分）
        df['Total_Score'] = np.where(
            trend_foundation,
            df['Trend_Score'] + df['Momentum_Score'] + df['RS_Score'] + df['Institutional_Score'],
            0.0  # 沒有趨勢基礎，總分為0
        )
        
        # 計算停損價（ATR基礎，2.0倍）
        df['Stop_Loss_Price'] = np.nan
        valid_mask = df['ATR'].notna() & df['Close'].notna() & (df['ATR'] > 0)
        df.loc[valid_mask, 'Stop_Loss_Price'] = (
            df.loc[valid_mask, 'Close'] - 
            (df.loc[valid_mask, 'ATR'] * self.stop_loss_atr_mult)
        )
        
        # 計算移動停損（Trailing Stop）
        # 專業邏輯：買入前的移動停損價 = 初始停損價
        # 如果已經持有且價格上漲，移動停損價可以跟隨上移（鎖定利潤）
        df['Trailing_Stop_Price'] = df['Stop_Loss_Price'].copy()  # 默認等於初始停損價
        
        if len(df) > 1:
            # 計算最高價的移動窗口（用於追蹤最高點）
            df['Highest_Close_14d'] = df['Close'].rolling(window=14, min_periods=1).max()
            
            # 移動停損 = 最高價 - (ATR * 2.0)
            trailing_mask = df['Highest_Close_14d'].notna() & df['ATR'].notna() & (df['ATR'] > 0) & df['Stop_Loss_Price'].notna()
            trailing_stop_calc = df.loc[trailing_mask, 'Highest_Close_14d'] - (df.loc[trailing_mask, 'ATR'] * self.stop_loss_atr_mult)
            
            # 專業規則（向量化操作，提高性能）：
            # 1. 移動停損不能低於初始停損
            # 2. 移動停損不能高於當前價格（買入前建議）
            # 3. 只有在移動停損 > 初始停損 且 移動停損 < 當前價 時才使用
            condition1 = trailing_stop_calc > df.loc[trailing_mask, 'Stop_Loss_Price']  # 移動停損 > 初始停損
            condition2 = trailing_stop_calc < df.loc[trailing_mask, 'Close']  # 移動停損 < 當前價
            
            # 如果兩個條件都滿足，使用計算出的移動停損；否則使用初始停損
            valid_trailing_stop = trailing_stop_calc.where(condition1 & condition2, df.loc[trailing_mask, 'Stop_Loss_Price'])
            df.loc[trailing_mask, 'Trailing_Stop_Price'] = valid_trailing_stop
        
        # ===== 專業波段交易判斷邏輯（2-4周持有）=====
        # 核心原則：檢查更長時間的趨勢持續性和穩定性，而非只看單日或3天
        
        # 首先：如果不滿足趨勢基礎，直接標記為「不符合」
        df['波段狀態'] = np.where(trend_foundation, '', '不符合')
        
        # ===== 趨勢持續性檢查（專業標準）=====
        # 1. 趨勢基礎持續性：最近10天至少有7天滿足趨勢基礎（70%以上）
        trend_foundation_10d = pd.Series(False, index=df.index)
        if len(df) >= 10:
            for i in range(9, len(df)):
                recent_10d_trend = trend_foundation.iloc[i-9:i+1]
                trend_foundation_10d.iloc[i] = recent_10d_trend.sum() >= 7  # 至少7天滿足
        
        # 2. 均線排列穩定性：最近10天MA20>MA60的排列必須穩定
        ma_arrangement_stable = pd.Series(False, index=df.index)
        if len(df) >= 10:
            for i in range(9, len(df)):
                recent_ma20_ma60 = (df['MA20'].iloc[i-9:i+1] > df['MA60'].iloc[i-9:i+1])
                ma_arrangement_stable.iloc[i] = recent_ma20_ma60.sum() >= 8  # 至少8天穩定排列
        
        # 3. 突破確認：MA5突破MA20後，至少維持3-5天以上
        golden_cross_confirmed = pd.Series(False, index=df.index)
        if len(df) >= 5:
            for i in range(4, len(df)):
                recent_5d_golden = golden_cross.iloc[i-4:i+1]
                # 如果最近5天至少有3天滿足黃金交叉，視為確認
                golden_cross_confirmed.iloc[i] = recent_5d_golden.sum() >= 3
        
        # 4. 價格突破MA20的確認：最近10天價格突破MA20的穩定性
        price_above_ma20_stable = pd.Series(False, index=df.index)
        if len(df) >= 10:
            for i in range(9, len(df)):
                recent_price_above = (df['Close'].iloc[i-9:i+1] > df['MA20'].iloc[i-9:i+1])
                price_above_ma20_stable.iloc[i] = recent_price_above.sum() >= 7  # 至少7天在MA20之上
        
        # 5. 趨勢強度：最近10-20天的整體漲幅（考慮波段交易的2-4周周期）
        trend_strength_10d = pd.Series(0.0, index=df.index)
        trend_strength_20d = pd.Series(0.0, index=df.index)
        if len(df) >= 20:
            for i in range(19, len(df)):
                if df['Close'].iloc[i-10] > 0:
                    trend_strength_10d.iloc[i] = (df['Close'].iloc[i] - df['Close'].iloc[i-10]) / df['Close'].iloc[i-10]
                if df['Close'].iloc[i-20] > 0:
                    trend_strength_20d.iloc[i] = (df['Close'].iloc[i] - df['Close'].iloc[i-20]) / df['Close'].iloc[i-20]
        
        # 6. 成交量持續性：最近5天至少有3天成交量放大
        volume_sustained = pd.Series(False, index=df.index)
        if len(df) >= 5:
            volume_above_avg = (df['Volume'] > (self.vol_multiplier * df['MA5_Vol']))
            for i in range(4, len(df)):
                recent_5d_vol = volume_above_avg.iloc[i-4:i+1]
                volume_sustained.iloc[i] = recent_5d_vol.sum() >= 3  # 至少3天放量
        
        # 7. 短期回調檢查：最近5天是否出現明顯回調（超過3%）
        recent_pullback = pd.Series(False, index=df.index)
        if len(df) >= 5:
            for i in range(4, len(df)):
                recent_high = df['Close'].iloc[i-4:i+1].max()
                current_price = df['Close'].iloc[i]
                if recent_high > 0:
                    pullback_pct = (recent_high - current_price) / recent_high
                    recent_pullback.iloc[i] = pullback_pct > 0.03  # 回調超過3%
        
        # ===== 波段狀態判斷（專業標準）=====
        valid_mask = trend_foundation & trend_foundation_10d & ma_arrangement_stable & price_above_ma20_stable
        
        # 1. 初升段（專業標準）：
        #    - 趨勢基礎持續10天以上（70%時間滿足）
        #    - 黃金交叉已確認（維持3-5天）
        #    - 價格剛突破或接近MA20（在MA20的5%以內）
        #    - 最近10天整體上漲
        #    - 成交量持續放大
        #    - 沒有明顯回調
        initial_uptrend = (
            valid_mask & 
            golden_cross_confirmed & 
            (df['Close'] <= df['MA20'] * 1.05) &
            (trend_strength_10d > 0) &  # 最近10天上漲
            volume_sustained &
            ~recent_pullback
        )
        df.loc[initial_uptrend, '波段狀態'] = '初升段'
        
        # 2. 主升段（專業標準）：
        #    - 趨勢基礎持續且穩定
        #    - 價格遠高於MA20（>10%）
        #    - 最近10-20天強勢上漲（漲幅>5%）
        #    - 成交量持續放大
        strong_uptrend = (
            valid_mask & 
            (df['Close'] > df['MA20'] * 1.1) &
            (trend_strength_10d > 0.05) &  # 最近10天漲幅>5%
            volume_sustained &
            (df['波段狀態'] == '')  # 還沒有被其他狀態覆蓋
        )
        df.loc[strong_uptrend, '波段狀態'] = '主升段'
        
        # 3. 拉回找買點（專業標準）：
        #    - 趨勢基礎持續穩定
        #    - 價格接近MA20（3%以內）
        #    - 最近有回調（回調3-8%）
        #    - 但趨勢基礎未破壞
        #    - 成交量在回調時縮量
        pullback_buy = (
            valid_mask & 
            price_near_ma20 & 
            recent_pullback &  # 有回調
            (df['波段狀態'] == '')  # 還沒有被其他狀態覆蓋
        )
        df.loc[pullback_buy, '波段狀態'] = '拉回找買點'
        
        # 4. 趨勢轉弱（專業標準）：
        #    - 趨勢基礎仍滿足，但穩定性下降
        #    - 最近5-10天出現連續下跌或明顯回調
        #    - 成交量萎縮
        trend_weakening = (
            valid_mask & 
            ((trend_strength_10d < -0.03) | recent_pullback) &  # 最近10天下跌超過3%或有回調
            (df['波段狀態'] == '')  # 還沒有被其他狀態覆蓋
        )
        df.loc[trend_weakening, '波段狀態'] = '趨勢轉弱'
        
        # 5. 趨勢中（專業標準）：
        #    - 滿足趨勢基礎且持續性良好
        #    - 但不符合其他具體條件
        trend_ongoing = (
            valid_mask & 
            (df['波段狀態'] == '')  # 還沒有被其他狀態覆蓋
        )
        df.loc[trend_ongoing, '波段狀態'] = '趨勢中'
        
        # 建議持有天數（基於MA60趨勢強度）
        # 如果MA60向上且角度陡，建議持有更久
        if len(df) >= 60:
            ma60_slope = (df['MA60'].iloc[-1] - df['MA60'].iloc[-20]) / df['MA60'].iloc[-20] if df['MA60'].iloc[-20] > 0 else 0
            # 斜率 > 5%: 28天, > 3%: 21天, > 1%: 14天, else: 7天
            df['建議持有天數'] = np.where(
                ma60_slope > 0.05, 28,
                np.where(ma60_slope > 0.03, 21,
                np.where(ma60_slope > 0.01, 14, 7))
            )
        else:
            df['建議持有天數'] = 14  # 默認14天
        
        return df
    
    def scan_stocks(self, stock_list: List[str], 
                   progress_callback=None) -> pd.DataFrame:
        """
        掃描股票列表
        
        Parameters:
        -----------
        stock_list : List[str]
            股票代號列表
        progress_callback : callable, optional
            進度回調函數
            
        Returns:
        --------
        pd.DataFrame
            符合條件的股票結果（按分數排序）
        """
        # 獲取基準數據
        benchmark_df = self.fetch_benchmark_data()
        
        results = []
        total = len(stock_list)
        
        for i, stock_id in enumerate(stock_list):
            try:
                if progress_callback:
                    progress_callback(i + 1, total, stock_id)
                
                # 獲取族群分類（如果在預設列表中，使用預設分類；否則使用"其他"）
                sector = self.DEFAULT_TICKERS.get(stock_id, '其他')
                
                # 檢查市場環境（僅在第一次掃描時檢查，用於顯示警告）
                # 注意：用戶已確認只會在多頭市場使用，但我們還是繼續掃描並顯示警告
                if i == 0:  # 只在第一次掃描時檢查市場環境
                    market_env = self.check_market_environment()
                    # 不跳過掃描，讓用戶自行決定（因為用戶說只會在多頭市場使用）
                
                # 獲取數據（使用1年數據，100%真實數據）
                # 注意：系統會自動處理上櫃股票（如果.TW找不到，會自動嘗試.TWO）
                # 波段交易需要至少60個交易日（用於計算MA60和基本指標）
                # 使用2年數據以準確計算MA200（需要至少200個交易日）
                df = self.fetch_stock_data(stock_id, years=2)
                
                # 檢查流動性
                if df is not None and len(df) >= 20:
                    if not self.check_liquidity(df):
                        # 流動性不足，跳過
                        stock_name = self.STOCK_NAMES.get(stock_id, stock_id)
                        results.append({
                            '族群': sector,
                            '股票代碼': stock_id,
                            '股票名稱': stock_name,
                            '當前股價': np.nan,
                            '策略評分': 0.0,
                            '買入訊號': '流動性不足',
                            '建議停損價(ATR)': np.nan,
                            '移動停損價': np.nan,
                            '建議停利價': np.nan,
                            '數據日期': '流動性不足',
                            '波段狀態': '流動性不足',
                            '建議持有天數': 0,
                            'MA5': np.nan,
                            'MA20': np.nan,
                            'MA60': np.nan,
                        })
                        continue
                
                # 檢查基本面（如果啟用）
                is_fundamental_healthy, fundamental_reason, financial_data = self.check_fundamental(stock_id)
                if not is_fundamental_healthy and self.enable_fundamental_filter:
                    # 基本面不佳，跳過或標記
                    stock_name = self.STOCK_NAMES.get(stock_id, stock_id)
                    results.append({
                        '族群': sector,
                        '股票代碼': stock_id,
                        '股票名稱': stock_name,
                        '當前股價': np.nan,
                        '策略評分': 0.0,
                        '買入訊號': '基本面不佳',
                        '建議停損價(ATR)': np.nan,
                        '移動停損價': np.nan,
                        '建議停利價': np.nan,
                        '數據日期': fundamental_reason,
                        '波段狀態': '基本面不佳',
                        '建議持有天數': 0,
                        'MA5': np.nan,
                        'MA20': np.nan,
                        'MA60': np.nan,
                    })
                    continue
                
                if df is None or len(df) < 60:  # 至少需要60個交易日才能計算MA60和基本指標
                    # 如果.TW找不到，自動嘗試.TWO（針對上櫃股票）
                    if stock_id.endswith('.TW') and len(stock_id) == 8:
                        alt_stock_id = stock_id.replace('.TW', '.TWO')
                        df_alt = self.fetch_stock_data(alt_stock_id, years=2)
                        if df_alt is not None and len(df_alt) >= 60:
                            # .TWO成功獲取數據，使用.TWO的ticker
                            df = df_alt
                            stock_id = alt_stock_id
                    
                    if df is None or len(df) < 60:
                        # 即使無法獲取數據，也顯示在結果中（標記為無數據）
                        stock_name = self.STOCK_NAMES.get(stock_id, stock_id)
                    # 如果.TWO沒有在STOCK_NAMES中，嘗試.TW的映射
                    if stock_id.endswith('.TWO') and stock_name == stock_id:
                        tw_version = stock_id.replace('.TWO', '.TW')
                        stock_name = self.STOCK_NAMES.get(tw_version, stock_id)
                        # 如果.TWO有數據但STOCK_NAMES沒有，嘗試.TW的映射
                        if stock_id.endswith('.TWO') and stock_name == stock_id:
                            tw_version = stock_id.replace('.TWO', '.TW')
                            stock_name = self.STOCK_NAMES.get(tw_version, stock_id)
                    
                    # 檢查錯誤原因
                    error_msg = '無法獲取'
                    if df is None:
                        # 嘗試判斷是否需要切換後綴
                        if stock_id.endswith('.TW') and stock_id not in ['4979.TW']:
                            # 如果是.TW但找不到，可能是上櫃股票
                            pass
                        error_msg = 'Yahoo Finance未找到'
                    elif len(df) < 60:
                        error_msg = '數據不足'
                    
                    results.append({
                        '族群': sector,
                        '股票代碼': stock_id,
                        '股票名稱': stock_name,
                        '當前股價': np.nan,
                        '策略評分': 0.0,
                        '買入訊號': '無數據',
                        '建議停損價(ATR)': np.nan,
                        '移動停損價': np.nan,
                        '建議停利價': np.nan,
                        '數據日期': error_msg,
                        '波段狀態': '無數據',
                        '建議持有天數': 0,
                        'MA5': np.nan,
                        'MA20': np.nan,
                        'MA60': np.nan,
                        'Date': None,
                        'Volume': np.nan,
                        'ATR': np.nan,
                        'Trend_Score': 0.0,
                        'Momentum_Score': 0.0,
                        'RS_Score': 0.0,
                    })
                    continue
                
                # 計算評分（波段交易邏輯）
                scored_df = self.calculate_scores(df, benchmark_df)
                
                # 獲取最新數據（最後一個交易日）
                latest = scored_df.iloc[-1]
                
                # 數據驗證：檢查是否有數據錯誤
                if latest.get('Data_Error', False) or pd.isna(latest['Close']):
                    stock_name = self.STOCK_NAMES.get(stock_id, stock_id)
                    # 如果.TWO沒有在STOCK_NAMES中，嘗試.TW的映射
                    if stock_id.endswith('.TWO') and stock_name == stock_id:
                        tw_version = stock_id.replace('.TWO', '.TW')
                        stock_name = self.STOCK_NAMES.get(tw_version, stock_id)
                    results.append({
                        '族群': sector,
                        '股票代碼': stock_id,
                        '股票名稱': stock_name,
                        '當前股價': np.nan,
                        '策略評分': 0.0,
                        '買入訊號': 'Data Error',
                        '建議停損價(ATR)': np.nan,
                        '移動停損價': np.nan,
                        '建議停利價': np.nan,
                        '數據日期': 'Data Error',
                        '波段狀態': 'Data Error',
                        '建議持有天數': 0,
                        'MA5': np.nan,
                        'MA20': np.nan,
                        'MA60': np.nan,
                        'Date': None,
                        'Volume': np.nan,
                        'ATR': np.nan,
                        'Trend_Score': 0.0,
                        'Momentum_Score': 0.0,
                        'RS_Score': 0.0,
                    })
                    continue
                
                # 當前價格 = 最新的Close價格（確保是最新數據）
                current_price = latest['Close']
                
                # 計算建議停利價（買入價 + 2*ATR）
                take_profit_price = np.nan
                if pd.notna(current_price) and pd.notna(latest['ATR']) and latest['ATR'] > 0:
                    take_profit_price = current_price + (latest['ATR'] * 2)
                
                # 買入訊號（波段交易邏輯）- 結合策略評分、波段狀態和新規則
                swing_status = latest.get('波段狀態', '不符合')
                
                # 檢查新進場規則（三個條件必須同時成立）
                new_entry_trigger = latest.get('新規則_進場觸發', False)
                pullback_20pct = latest.get('觀察條件_回檔20%', False)
                
                # 優先級：新規則 > 原有規則
                # 如果新進場觸發條件不滿足，即使其他條件滿足，也只能是「觀察」或「無信號」
                if not new_entry_trigger:
                    # 新規則不滿足，最高只給「觀察」
                    if latest['Total_Score'] >= 70 and swing_status in ['初升段', '主升段', '拉回找買點']:
                        signal = '觀察'  # 原有規則滿足但新規則不滿足
                    elif latest['Total_Score'] >= 50:
                        signal = '觀察'
                    elif latest['Total_Score'] > 0:
                        signal = '觀察'
                    else:
                        signal = '無信號'
                else:
                    # 新規則滿足，再結合原有規則判斷
                    if swing_status in ['趨勢中', '趨勢轉弱']:
                        # 新規則滿足但波段狀態不佳，降級處理
                        if latest['Total_Score'] >= 70:
                            signal = '買入'  # 降級：趨勢中/趨勢轉弱時，最高只給「買入」
                        elif latest['Total_Score'] >= 50:
                            signal = '觀察'
                        elif latest['Total_Score'] > 0:
                            signal = '觀察'
                        else:
                            signal = '無信號'
                    else:
                        # 新規則滿足且波段狀態良好，按總分判斷
                        if latest['Total_Score'] >= 70:
                            signal = '強買入'
                        elif latest['Total_Score'] >= 50:
                            signal = '買入'
                        elif latest['Total_Score'] > 0:
                            signal = '觀察'
                        else:
                            signal = '無信號'
                
                # 獲取數據日期（最新交易日）
                data_date = latest.name
                if isinstance(data_date, pd.Timestamp):
                    # 處理時區問題
                    if hasattr(data_date, 'tz') and data_date.tz is not None:
                        data_date = data_date.tz_localize(None)
                    data_date_str = data_date.strftime('%Y-%m-%d')
                else:
                    data_date_str = str(data_date)[:10]
                
                # 獲取股票名稱（處理.TWO的情況）
                stock_name = self.STOCK_NAMES.get(stock_id, None)
                # 如果.TWO沒有在STOCK_NAMES中，嘗試.TW的映射
                if stock_name is None or stock_name == stock_id:
                    if stock_id.endswith('.TWO'):
                        tw_version = stock_id.replace('.TWO', '.TW')
                        stock_name = self.STOCK_NAMES.get(tw_version, None)
                
                # 如果還是沒有，嘗試從yfinance自動獲取股票名稱
                if stock_name is None or stock_name == stock_id:
                    try:
                        ticker = yf.Ticker(stock_id)
                        info = ticker.info
                        # 嘗試獲取中文名稱或英文名稱
                        if 'longName' in info and info['longName']:
                            stock_name = info['longName']
                        elif 'shortName' in info and info['shortName']:
                            stock_name = info['shortName']
                        else:
                            stock_name = stock_id  # 如果都獲取不到，使用股票代碼
                    except:
                        stock_name = stock_id  # 如果獲取失敗，使用股票代碼
                
                # 波段狀態和建議持有天數
                swing_status = latest.get('波段狀態', '不符合')
                # 只有當買入訊號為「買入」或「強買入」時，才顯示建議持有天數
                # 如果是「觀察」或「無信號」，則設為0（表示不需要持有）
                raw_holding_days = int(latest.get('建議持有天數', 14))
                if signal in ['買入', '強買入']:
                    holding_days = raw_holding_days
                else:
                    holding_days = 0  # 沒有買入訊號，不建議持有
                
                # 移動停損價
                trailing_stop = latest.get('Trailing_Stop_Price', latest['Stop_Loss_Price'])
                
                # 使用正確的列名（波段交易專用）
                results.append({
                    '族群': sector,
                    '股票代碼': stock_id,
                    '股票名稱': stock_name,
                    '當前股價': current_price,  # 確保是最新的Close價格
                    '策略評分': latest['Total_Score'],
                    '買入訊號': signal,
                    '建議停損價(ATR)': latest['Stop_Loss_Price'],
                    '移動停損價': trailing_stop,
                    '建議停利價': take_profit_price,
                    '數據日期': data_date_str,
                    '波段狀態': swing_status,
                    '建議持有天數': holding_days,
                    'MA5': latest.get('MA5', np.nan),
                    'MA20': latest['MA20'],
                    'MA60': latest['MA60'],
                    # 保留其他欄位用於內部處理
                    'Date': latest.name,
                    'Volume': latest['Volume'],
                    'ATR': latest['ATR'],
                    'Trend_Score': latest['Trend_Score'],
                    'Momentum_Score': latest['Momentum_Score'],
                    'RS_Score': latest['RS_Score'],
                })
                    
            except Exception as e:
                print(f"掃描 {stock_id} 時發生錯誤: {str(e)}")
                continue
        
        if not results:
            return pd.DataFrame()
        
        result_df = pd.DataFrame(results)
        
        # 按策略評分排序（降序）
        result_df = result_df.sort_values('策略評分', ascending=False).reset_index(drop=True)
        
        return result_df

