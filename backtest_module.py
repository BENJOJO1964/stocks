"""
簡化版歷史回測模組
使用1-2年數據進行快速驗證（而非3-5年）
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from stock_scanner import TaiwanStockScanner


class Backtester:
    """
    簡化版回測系統
    使用最近1-2年的數據進行快速驗證
    """
    
    def __init__(self, scanner: TaiwanStockScanner):
        """
        初始化回測系統
        
        Parameters:
        -----------
        scanner : TaiwanStockScanner
            股票掃描器實例
        """
        self.scanner = scanner
    
    def run_backtest(self, stock_list: List[str], years: int = 1) -> Dict:
        """
        執行簡化回測（使用1-2年數據）
        
        Parameters:
        -----------
        stock_list : List[str]
            股票代號列表
        years : int
            回測年數（1-2年，默認1年）
        
        Returns:
        --------
        Dict: 回測結果統計
        """
        results = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_return': 0.0,
            'avg_return_per_trade': 0.0,
            'win_rate': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'details': []
        }
        
        # 簡化版回測邏輯
        # 由於只使用1-2年數據，主要用於驗證策略邏輯是否合理
        # 而非完整的歷史表現分析
        
        try:
            benchmark_df = self.scanner.fetch_benchmark_data(years=years)
            
            for stock_id in stock_list:
                try:
                    df = self.scanner.fetch_stock_data(stock_id, years=years)
                    if df is None or len(df) < 60:
                        continue
                    
                    # 計算評分
                    scored_df = self.scanner.calculate_scores(df, benchmark_df)
                    
                    # 簡化分析：檢查買入信號的準確性
                    # 這裡只做簡單的統計，不做完整的交易模擬
                    buy_signals = scored_df[scored_df['Total_Score'] >= self.scanner.min_score]
                    
                    if len(buy_signals) > 0:
                        # 計算後續表現
                        for idx in buy_signals.index:
                            signal_idx = scored_df.index.get_loc(idx)
                            if signal_idx + 20 < len(scored_df):  # 假設持有20天
                                entry_price = scored_df.loc[idx, 'Close']
                                exit_price = scored_df.iloc[signal_idx + 20]['Close']
                                return_pct = (exit_price - entry_price) / entry_price * 100
                                
                                results['total_trades'] += 1
                                if return_pct > 0:
                                    results['winning_trades'] += 1
                                else:
                                    results['losing_trades'] += 1
                                
                                results['total_return'] += return_pct
                                
                                results['details'].append({
                                    'stock': stock_id,
                                    'entry_date': idx,
                                    'entry_price': entry_price,
                                    'exit_price': exit_price,
                                    'return_pct': return_pct
                                })
                
                except Exception as e:
                    print(f"回測 {stock_id} 時發生錯誤: {str(e)}")
                    continue
            
            # 計算統計指標
            if results['total_trades'] > 0:
                results['win_rate'] = results['winning_trades'] / results['total_trades'] * 100
                results['avg_return_per_trade'] = results['total_return'] / results['total_trades']
            
            return results
            
        except Exception as e:
            print(f"回測執行錯誤: {str(e)}")
            return results


