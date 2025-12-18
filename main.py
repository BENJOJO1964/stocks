"""
台灣股票選股系統 - 互動式主程式
支援自定義股票列表、策略參數和日期範圍
"""
import pandas as pd
from datetime import datetime, timedelta
from data_fetcher import DataFetcher
from alpha_strategy import AlphaStrategy
import os


class StockSelector:
    """股票選股系統主類"""
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.strategy = None
        self.stock_list = []
        self.start_date = None
        self.end_date = None
    
    def show_main_menu(self):
        """顯示主選單"""
        print("\n" + "=" * 60)
        print("台灣股票選股系統")
        print("=" * 60)
        print("\n【主選單】")
        print("1. 設定股票列表")
        print("2. 設定日期範圍")
        print("3. 設定策略參數")
        print("4. 運行選股策略")
        print("5. 查看當前設定")
        print("6. 使用預設設定快速開始")
        print("0. 退出")
        print("=" * 60)
    
    def set_stock_list(self):
        """設定股票列表"""
        print("\n【設定股票列表】")
        print("請輸入股票代號，多個股票請用逗號或空格分隔")
        print("格式範例: 2330.TW 2317.TW 或 2330.TW,2317.TW")
        print("常見台股範例: 2330.TW(台積電), 2317.TW(鴻海), 2454.TW(聯發科)")
        print("輸入 'q' 返回主選單\n")
        
        user_input = input("請輸入股票代號: ").strip()
        
        if user_input.lower() == 'q':
            return
        
        # 解析輸入
        stocks = user_input.replace(',', ' ').split()
        stocks = [s.strip().upper() for s in stocks if s.strip()]
        
        # 確保格式正確（添加.TW後綴如果沒有）
        formatted_stocks = []
        for stock in stocks:
            if '.' not in stock:
                formatted_stocks.append(f"{stock}.TW")
            else:
                formatted_stocks.append(stock)
        
        if formatted_stocks:
            self.stock_list = formatted_stocks
            print(f"\n✓ 已設定股票列表: {', '.join(self.stock_list)}")
        else:
            print("\n✗ 未輸入有效股票代號")
    
    def set_date_range(self):
        """設定日期範圍"""
        print("\n【設定日期範圍】")
        print("1. 過去N天（預設365天）")
        print("2. 自訂起始和結束日期")
        print("3. 返回主選單")
        
        choice = input("\n請選擇 (1-3): ").strip()
        
        if choice == '1':
            days = input("請輸入天數（預設365）: ").strip()
            try:
                days = int(days) if days else 365
                self.end_date = datetime.now()
                self.start_date = (self.end_date - timedelta(days=days)).strftime('%Y-%m-%d')
                print(f"\n✓ 日期範圍: {self.start_date} 至 {self.end_date.strftime('%Y-%m-%d')} (過去{days}天)")
            except ValueError:
                print("\n✗ 輸入格式錯誤")
        
        elif choice == '2':
            start = input("請輸入起始日期 (YYYY-MM-DD): ").strip()
            end = input("請輸入結束日期 (YYYY-MM-DD，留空為今天): ").strip()
            try:
                self.start_date = start
                self.end_date = datetime.strptime(end, '%Y-%m-%d') if end else datetime.now()
                print(f"\n✓ 日期範圍: {self.start_date} 至 {self.end_date.strftime('%Y-%m-%d')}")
            except ValueError:
                print("\n✗ 日期格式錯誤，請使用 YYYY-MM-DD")
    
    def set_strategy_parameters(self):
        """設定策略參數"""
        print("\n【設定策略參數】")
        print("當前策略條件:")
        print("  - 趨勢: Close > MA20 > MA60")
        print("  - 動量: Volume > 倍數 * MA5_Vol")
        print("  - 籌碼: Trust_Net_Buy > 0")
        print("  - 基本面: Revenue_YoY > 最低值")
        print("  - 停損: 基於ATR")
        print()
        
        print("請輸入參數（直接按Enter使用預設值）:")
        
        # 短期均線
        ma_short = input("短期均線週期 (預設20): ").strip()
        ma_short = int(ma_short) if ma_short else 20
        
        # 長期均線
        ma_long = input("長期均線週期 (預設60): ").strip()
        ma_long = int(ma_long) if ma_long else 60
        
        # 成交量倍數
        vol_mult = input("成交量倍數 (預設1.5): ").strip()
        vol_mult = float(vol_mult) if vol_mult else 1.5
        
        # 營收年增率最低值
        revenue_min = input("最低營收年增率% (預設10.0): ").strip()
        revenue_min = float(revenue_min) if revenue_min else 10.0
        
        # ATR週期
        atr_period = input("ATR計算週期 (預設14): ").strip()
        atr_period = int(atr_period) if atr_period else 14
        
        # 停損ATR倍數
        stop_loss_mult = input("停損ATR倍數 (預設2.0): ").strip()
        stop_loss_mult = float(stop_loss_mult) if stop_loss_mult else 2.0
        
        # 創建策略實例
        self.strategy = AlphaStrategy(
            atr_period=atr_period,
            ma_short=ma_short,
            ma_long=ma_long,
            vol_multiplier=vol_mult,
            min_revenue_yoy=revenue_min,
            stop_loss_atr_multiplier=stop_loss_mult
        )
        
        print("\n✓ 策略參數已設定:")
        print(f"  - 短期均線: {ma_short}日")
        print(f"  - 長期均線: {ma_long}日")
        print(f"  - 成交量倍數: {vol_mult}")
        print(f"  - 最低營收年增率: {revenue_min}%")
        print(f"  - ATR週期: {atr_period}日")
        print(f"  - 停損ATR倍數: {stop_loss_mult}")
    
    def show_current_settings(self):
        """顯示當前設定"""
        print("\n【當前設定】")
        print("-" * 60)
        
        if self.stock_list:
            print(f"股票列表: {', '.join(self.stock_list)}")
        else:
            print("股票列表: 未設定")
        
        if self.start_date and self.end_date:
            print(f"日期範圍: {self.start_date} 至 {self.end_date.strftime('%Y-%m-%d')}")
        else:
            print("日期範圍: 未設定")
        
        if self.strategy:
            print(f"策略參數:")
            print(f"  - 短期均線: {self.strategy.ma_short}日")
            print(f"  - 長期均線: {self.strategy.ma_long}日")
            print(f"  - 成交量倍數: {self.strategy.vol_multiplier}")
            print(f"  - 最低營收年增率: {self.strategy.min_revenue_yoy}%")
            print(f"  - ATR週期: {self.strategy.atr_period}日")
            print(f"  - 停損ATR倍數: {self.strategy.stop_loss_atr_multiplier}")
        else:
            print("策略參數: 使用預設值")
        
        print("-" * 60)
    
    def use_default_settings(self):
        """使用預設設定"""
        print("\n【使用預設設定】")
        self.stock_list = ['2330.TW', '2317.TW']
        self.end_date = datetime.now()
        self.start_date = (self.end_date - timedelta(days=365)).strftime('%Y-%m-%d')
        self.strategy = AlphaStrategy()
        
        print("✓ 已套用預設設定:")
        print(f"  - 股票: {', '.join(self.stock_list)}")
        print(f"  - 日期範圍: 過去365天")
        print(f"  - 策略參數: 全部預設值")
    
    def run_strategy(self):
        """運行選股策略"""
        # 檢查設定
        if not self.stock_list:
            print("\n✗ 錯誤: 請先設定股票列表")
            return
        
        if not self.start_date or not self.end_date:
            print("\n✗ 錯誤: 請先設定日期範圍")
            return
        
        if not self.strategy:
            print("\n⚠ 使用預設策略參數")
            self.strategy = AlphaStrategy()
        
        print("\n" + "=" * 60)
        print("開始運行選股策略")
        print("=" * 60)
        print(f"\n股票列表: {', '.join(self.stock_list)}")
        print(f"日期範圍: {self.start_date} 至 {self.end_date.strftime('%Y-%m-%d')}")
        print()
        
        # 獲取數據
        print("【步驟1】獲取股票數據...")
        data_dict = self.fetcher.fetch_multiple_stocks(self.stock_list, self.start_date)
        
        if not data_dict:
            print("\n✗ 錯誤: 未能獲取任何股票數據")
            return
        
        # 運行策略
        print("\n【步驟2】運行選股策略...")
        all_results = []
        
        for stock_id, df in data_dict.items():
            print(f"\n分析 {stock_id}...")
            analyzed_df = self.strategy.analyze_stock(df, stock_id)
            signals = self.strategy.get_signals_summary(analyzed_df)
            
            if len(signals) > 0:
                print(f"  ✓ 找到 {len(signals)} 個買入信號")
                all_results.append(signals)
            else:
                print(f"  ✗ 未找到買入信號")
        
        # 生成報告
        if all_results:
            print("\n【步驟3】生成報告...")
            final_report = pd.concat(all_results, ignore_index=False)
            final_report = final_report.sort_index()
            
            output_columns = [
                'Stock_ID', 'Open', 'High', 'Low', 'Close', 'Volume',
                'MA20', 'MA60', 'ATR', 'Foreign_Net_Buy', 'Trust_Net_Buy',
                'Revenue_YoY', 'Stop_Loss_Price', 'Risk_Reward_Ratio',
                'Trend_Condition', 'Momentum_Condition', 'Chips_Condition',
                'Fundamental_Condition', 'Signal_Entry'
            ]
            
            available_columns = [col for col in output_columns if col in final_report.columns]
            final_report = final_report[available_columns].reset_index()
            
            # 顯示結果
            print("\n" + "=" * 60)
            print("買入信號報告")
            print("=" * 60)
            
            # 簡化顯示（只顯示關鍵欄位）
            display_columns = ['Date', 'Stock_ID', 'Close', 'Volume', 'MA20', 'MA60', 
                             'Trust_Net_Buy', 'Revenue_YoY', 'Stop_Loss_Price']
            display_cols = [col for col in display_columns if col in final_report.columns]
            
            print(final_report[display_cols].to_string(index=False))
            print(f"\n總共找到 {len(final_report)} 個買入信號")
            
            # 統計摘要
            if 'Stock_ID' in final_report.columns:
                summary = final_report.groupby('Stock_ID').size()
                print("\n各股票買入信號數量:")
                for stock, count in summary.items():
                    print(f"  {stock}: {count} 個信號")
            
            # 儲存報告
            output_file = 'daily_report.csv'
            final_report.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n✓ 完整報告已儲存至: {output_file}")
            print(f"  (包含所有 {len(available_columns)} 個欄位)")
            
        else:
            print("\n✗ 未找到任何買入信號")
            empty_df = pd.DataFrame(columns=['Date', 'Stock_ID', 'Signal_Entry'])
            empty_df.to_csv('daily_report.csv', index=False, encoding='utf-8-sig')
            print("已創建空的報告文件: daily_report.csv")
        
        print("\n" + "=" * 60)
        input("\n按Enter鍵返回主選單...")
    
    def run(self):
        """運行主程式"""
        while True:
            self.show_main_menu()
            choice = input("\n請選擇功能 (0-6): ").strip()
            
            if choice == '0':
                print("\n感謝使用！再見！")
                break
            elif choice == '1':
                self.set_stock_list()
            elif choice == '2':
                self.set_date_range()
            elif choice == '3':
                self.set_strategy_parameters()
            elif choice == '4':
                self.run_strategy()
            elif choice == '5':
                self.show_current_settings()
                input("\n按Enter鍵返回主選單...")
            elif choice == '6':
                self.use_default_settings()
                print("\n現在可以選擇【4. 運行選股策略】開始分析")
            else:
                print("\n✗ 無效選項，請重新選擇")


def main():
    """主函數"""
    selector = StockSelector()
    selector.run()


if __name__ == "__main__":
    main()
