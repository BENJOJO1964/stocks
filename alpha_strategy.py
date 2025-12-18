"""
AlphaStrategy: 股票選股策略
基於趨勢、動量、籌碼面、基本面和風險管理的多因子選股策略
"""
import pandas as pd
import numpy as np
from typing import Optional


class AlphaStrategy:
    """
    多因子選股策略類
    結合技術面、籌碼面和基本面進行選股
    """
    
    def __init__(self, 
                 atr_period: int = 14,
                 ma_short: int = 20,
                 ma_long: int = 60,
                 vol_ma_period: int = 5,
                 vol_multiplier: float = 1.5,
                 min_revenue_yoy: float = 10.0,
                 stop_loss_atr_multiplier: float = 2.0):
        """
        初始化策略參數
        
        Parameters:
        -----------
        atr_period : int
            ATR計算週期，預設14
        ma_short : int
            短期均線週期，預設20
        ma_long : int
            長期均線週期，預設60
        vol_ma_period : int
            成交量均線週期，預設5
        vol_multiplier : float
            成交量倍數，預設1.5（成交量需大於1.5倍均量）
        min_revenue_yoy : float
            最低營收年增率，預設10%
        stop_loss_atr_multiplier : float
            停損ATR倍數，預設2.0（停損價 = 買入價 - 2*ATR）
        """
        self.atr_period = atr_period
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.vol_ma_period = vol_ma_period
        self.vol_multiplier = vol_multiplier
        self.min_revenue_yoy = min_revenue_yoy
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算所有技術指標
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含OHLCV數據的DataFrame
        
        Returns:
        --------
        pd.DataFrame
            加入技術指標後的DataFrame
        """
        df = df.copy()
        
        # 計算移動平均線
        df['MA20'] = df['Close'].rolling(window=self.ma_short).mean()
        df['MA60'] = df['Close'].rolling(window=self.ma_long).mean()
        
        # 計算成交量移動平均
        df['MA5_Vol'] = df['Volume'].rolling(window=self.vol_ma_period).mean()
        
        # 計算ATR (Average True Range)
        df['High_Low'] = df['High'] - df['Low']
        df['High_Close'] = abs(df['High'] - df['Close'].shift(1))
        df['Low_Close'] = abs(df['Low'] - df['Close'].shift(1))
        df['True_Range'] = df[['High_Low', 'High_Close', 'Low_Close']].max(axis=1)
        df['ATR'] = df['True_Range'].rolling(window=self.atr_period).mean()
        
        # 清理臨時欄位
        df.drop(['High_Low', 'High_Close', 'Low_Close', 'True_Range'], axis=1, inplace=True)
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成買入信號
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含指標和數據的DataFrame
        
        Returns:
        --------
        pd.DataFrame
            加入信號欄位的DataFrame
        """
        df = df.copy()
        
        # 確保指標已計算
        if 'MA20' not in df.columns:
            df = self.calculate_indicators(df)
        
        # 1. Trend Condition: Close > MA20 > MA60（使用真實價格數據）
        df['Trend_Condition'] = (
            (df['Close'] > df['MA20']) & 
            (df['MA20'] > df['MA60'])
        )
        
        # 2. Momentum Condition: Volume > 倍數 * MA5_Vol（使用真實成交量數據）
        df['Momentum_Condition'] = (
            df['Volume'] > (self.vol_multiplier * df['MA5_Vol'])
        )
        
        # 注意：以下條件因無法獲取真實數據而暫時移除
        # 只使用可獲取的真實數據進行選股（趨勢 + 動量）
        # 如果未來有真實數據源，可以重新加入
        
        # 綜合條件生成買入信號（僅基於真實數據）
        # 只使用趨勢和動量兩個真實數據條件
        df['Signal_Entry'] = (
            df['Trend_Condition'] & 
            df['Momentum_Condition']
        )
        
        # 計算停損價（基於ATR，使用真實價格數據）
        # 停損價 = 當前收盤價 - (ATR * multiplier)
        df['Stop_Loss_Price'] = np.nan
        signal_mask = df['Signal_Entry'] & df['ATR'].notna()
        if signal_mask.any():
            df.loc[signal_mask, 'Stop_Loss_Price'] = (
                df.loc[signal_mask, 'Close'] - 
                (df.loc[signal_mask, 'ATR'] * self.stop_loss_atr_multiplier)
            )
        
        # 計算風險報酬比（簡單估算）
        df['Risk_Reward_Ratio'] = np.nan
        signal_mask = df['Signal_Entry'] & df['ATR'].notna()
        if signal_mask.any():
            # 假設目標價為當前價 + 2*ATR（風險報酬比約1:1）
            target_price = df.loc[signal_mask, 'Close'] + (df.loc[signal_mask, 'ATR'] * 2)
            risk = df.loc[signal_mask, 'Close'] - df.loc[signal_mask, 'Stop_Loss_Price']
            reward = target_price - df.loc[signal_mask, 'Close']
            df.loc[signal_mask, 'Risk_Reward_Ratio'] = reward / risk
        
        return df
    
    def analyze_stock(self, df: pd.DataFrame, stock_id: Optional[str] = None) -> pd.DataFrame:
        """
        完整分析單支股票
        
        Parameters:
        -----------
        df : pd.DataFrame
            原始股票數據
        stock_id : str, optional
            股票代號（用於標記）
        
        Returns:
        --------
        pd.DataFrame
            包含所有指標和信號的DataFrame
        """
        # 計算指標
        df_with_indicators = self.calculate_indicators(df)
        
        # 生成信號
        df_with_signals = self.generate_signals(df_with_indicators)
        
        # 如果需要，加入股票代號
        if stock_id:
            df_with_signals['Stock_ID'] = stock_id
        
        return df_with_signals
    
    def get_signals_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        獲取信號摘要（僅包含有買入信號的日期）
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含信號的DataFrame
        
        Returns:
        --------
        pd.DataFrame
            僅包含Signal_Entry為True的行的DataFrame
        """
        if 'Signal_Entry' not in df.columns:
            raise ValueError("DataFrame中未找到Signal_Entry欄位，請先運行generate_signals()")
        
        signals_df = df[df['Signal_Entry'] == True].copy()
        
        return signals_df

