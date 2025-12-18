"""
台灣股票選股系統 - GUI應用程式
使用tkinter創建的圖形界面應用
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import pandas as pd
from datetime import datetime, timedelta
import threading
from data_fetcher import DataFetcher
from alpha_strategy import AlphaStrategy


class StockSelectorApp:
    """股票選股系統GUI應用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("台灣股票選股系統")
        self.root.geometry("1300x900")
        self.root.minsize(1200, 700)
        self.root.configure(bg='#f0f0f0')
        
        # 初始化組件
        self.fetcher = DataFetcher()
        self.strategy = None
        self.current_results = None
        
        # 創建界面
        self.create_widgets()
        
        # 載入預設值
        self.load_defaults()
    
    def create_widgets(self):
        """創建所有界面組件"""
        
        # 標題
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="台灣股票選股系統", 
            font=('Microsoft JhengHei', 18, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=15)
        
        # 主容器
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側面板容器
        left_container = tk.Frame(main_container, bg='#f0f0f0', width=520)
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5), pady=5)
        left_container.pack_propagate(False)
        
        # 創建可滾動的Frame
        canvas = tk.Canvas(left_container, bg='#f0f0f0', highlightthickness=0, width=520)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white', relief=tk.RAISED, bd=2)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        canvas.bind('<Configure>', on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        left_panel = scrollable_frame
        
        # 右側面板 - 結果區域
        right_panel = tk.Frame(main_container, bg='white', relief=tk.RAISED, bd=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        
        # === 左側設定區域 ===
        settings_label = tk.Label(
            left_panel,
            text="【設定參數】",
            font=('Microsoft JhengHei', 12, 'bold'),
            bg='white',
            fg='#2c3e50'
        )
        settings_label.pack(pady=(15, 10))
        
        # 股票列表設定
        stock_frame = tk.LabelFrame(
            left_panel,
            text="股票列表",
            font=('Microsoft JhengHei', 10),
            bg='white',
            padx=10,
            pady=10
        )
        stock_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            stock_frame,
            text="輸入股票代號（用空格或逗號分隔）:",
            bg='white',
            font=('Microsoft JhengHei', 9)
        ).pack(anchor=tk.W)
        
        self.stock_entry = tk.Entry(stock_frame, font=('Microsoft JhengHei', 10))
        self.stock_entry.pack(fill=tk.X, pady=5)
        
        tk.Label(
            stock_frame,
            text="範例: 2330.TW 2317.TW 2454.TW",
            bg='white',
            fg='gray',
            font=('Microsoft JhengHei', 8)
        ).pack(anchor=tk.W)
        
        # 日期範圍設定
        date_frame = tk.LabelFrame(
            left_panel,
            text="日期範圍",
            font=('Microsoft JhengHei', 10),
            bg='white',
            padx=10,
            pady=10
        )
        date_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            date_frame,
            text="過去天數:",
            bg='white',
            font=('Microsoft JhengHei', 9)
        ).pack(anchor=tk.W)
        
        self.days_entry = tk.Entry(date_frame, font=('Microsoft JhengHei', 10))
        self.days_entry.pack(fill=tk.X, pady=5)
        
        # 策略參數設定
        strategy_frame = tk.LabelFrame(
            left_panel,
            text="策略參數",
            font=('Microsoft JhengHei', 10),
            bg='white',
            padx=10,
            pady=10
        )
        strategy_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 創建參數輸入框
        params = [
            ("短期均線週期", "ma_short", 20),
            ("長期均線週期", "ma_long", 60),
            ("成交量倍數", "vol_mult", 1.5),
            ("最低營收年增率 (%)", "revenue_min", 10.0),
            ("ATR週期", "atr_period", 14),
            ("停損ATR倍數", "stop_loss", 2.0),
        ]
        
        self.param_entries = {}
        for i, (label, key, default) in enumerate(params):
            row = tk.Frame(strategy_frame, bg='white')
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(
                row,
                text=label + ":",
                bg='white',
                font=('Microsoft JhengHei', 9),
                width=18,
                anchor=tk.W
            ).pack(side=tk.LEFT)
            
            entry = tk.Entry(row, font=('Microsoft JhengHei', 9), width=10)
            entry.insert(0, str(default))
            entry.pack(side=tk.LEFT, padx=5)
            self.param_entries[key] = entry
        
        # 按鈕區域
        button_frame = tk.Frame(left_panel, bg='white')
        button_frame.pack(fill=tk.X, padx=10, pady=(20, 15))
        
        self.run_button = tk.Button(
            button_frame,
            text="🚀 運行選股策略",
            font=('Microsoft JhengHei', 11, 'bold'),
            bg='#27ae60',
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self.run_strategy_threaded,
            cursor='hand2'
        )
        self.run_button.pack(fill=tk.X, pady=5)
        
        self.export_button = tk.Button(
            button_frame,
            text="💾 導出CSV報告",
            font=('Microsoft JhengHei', 10),
            bg='#3498db',
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            command=self.export_csv,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.export_button.pack(fill=tk.X, pady=5)
        
        self.reset_button = tk.Button(
            button_frame,
            text="🔄 重置為預設值",
            font=('Microsoft JhengHei', 10),
            bg='#95a5a6',
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            command=self.load_defaults,
            cursor='hand2'
        )
        self.reset_button.pack(fill=tk.X, pady=5)
        
        # === 右側結果區域 ===
        result_label = tk.Label(
            right_panel,
            text="【分析結果】",
            font=('Microsoft JhengHei', 12, 'bold'),
            bg='white',
            fg='#2c3e50'
        )
        result_label.pack(pady=10)
        
        # 狀態標籤
        self.status_label = tk.Label(
            right_panel,
            text="請設定參數後點擊「運行選股策略」開始分析",
            font=('Microsoft JhengHei', 10),
            bg='white',
            fg='gray'
        )
        self.status_label.pack(pady=5)
        
        # 結果表格
        table_frame = tk.Frame(right_panel, bg='white')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 創建Treeview和Scrollbar
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        self.result_tree = ttk.Treeview(
            table_frame,
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            show='headings'
        )
        
        scrollbar_y.config(command=self.result_tree.yview)
        scrollbar_x.config(command=self.result_tree.xview)
        
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 結果統計
        self.summary_label = tk.Label(
            right_panel,
            text="",
            font=('Microsoft JhengHei', 10),
            bg='white',
            fg='#27ae60',
            justify=tk.LEFT
        )
        self.summary_label.pack(pady=10, padx=10, anchor=tk.W)
    
    def load_defaults(self):
        """載入預設值"""
        self.stock_entry.delete(0, tk.END)
        self.stock_entry.insert(0, "2330.TW 2317.TW")
        
        self.days_entry.delete(0, tk.END)
        self.days_entry.insert(0, "365")
        
        # 重置參數
        defaults = {
            "ma_short": 20,
            "ma_long": 60,
            "vol_mult": 1.5,
            "revenue_min": 10.0,
            "atr_period": 14,
            "stop_loss": 2.0
        }
        
        for key, value in defaults.items():
            self.param_entries[key].delete(0, tk.END)
            self.param_entries[key].insert(0, str(value))
    
    def get_stock_list(self):
        """獲取股票列表"""
        stock_input = self.stock_entry.get().strip()
        if not stock_input:
            return []
        
        stocks = stock_input.replace(',', ' ').split()
        stocks = [s.strip().upper() for s in stocks if s.strip()]
        
        formatted_stocks = []
        for stock in stocks:
            if '.' not in stock:
                formatted_stocks.append(f"{stock}.TW")
            else:
                formatted_stocks.append(stock)
        
        return formatted_stocks
    
    def get_strategy_params(self):
        """獲取策略參數"""
        try:
            return {
                "atr_period": int(self.param_entries["atr_period"].get()),
                "ma_short": int(self.param_entries["ma_short"].get()),
                "ma_long": int(self.param_entries["ma_long"].get()),
                "vol_multiplier": float(self.param_entries["vol_mult"].get()),
                "min_revenue_yoy": float(self.param_entries["revenue_min"].get()),
                "stop_loss_atr_multiplier": float(self.param_entries["stop_loss"].get())
            }
        except ValueError:
            messagebox.showerror("錯誤", "策略參數格式不正確，請輸入數字")
            return None
    
    def run_strategy_threaded(self):
        """在後台線程運行策略"""
        self.run_button.config(state=tk.DISABLED, text="分析中...")
        self.status_label.config(text="正在分析中，請稍候...", fg='#3498db')
        
        thread = threading.Thread(target=self.run_strategy)
        thread.daemon = True
        thread.start()
    
    def run_strategy(self):
        """運行選股策略"""
        try:
            # 獲取設定
            stock_list = self.get_stock_list()
            if not stock_list:
                self.root.after(0, lambda: messagebox.showerror("錯誤", "請輸入股票代號"))
                self.root.after(0, self.reset_run_button)
                return
            
            try:
                days = int(self.days_entry.get())
            except ValueError:
                self.root.after(0, lambda: messagebox.showerror("錯誤", "日期天數必須是數字"))
                self.root.after(0, self.reset_run_button)
                return
            
            params = self.get_strategy_params()
            if params is None:
                self.root.after(0, self.reset_run_button)
                return
            
            # 更新狀態
            self.root.after(0, lambda: self.status_label.config(
                text=f"正在獲取 {len(stock_list)} 支股票的數據...",
                fg='#3498db'
            ))
            
            # 獲取數據
            end_date = datetime.now()
            start_date = (end_date - timedelta(days=days)).strftime('%Y-%m-%d')
            
            data_dict = {}
            for i, stock_id in enumerate(stock_list):
                try:
                    self.root.after(0, lambda s=stock_id: self.status_label.config(
                        text=f"正在獲取 {s} 的數據...",
                        fg='#3498db'
                    ))
                    df = self.fetcher.fetch_data(stock_id, start_date)
                    data_dict[stock_id] = df
                except Exception as e:
                    self.root.after(0, lambda e=str(e): messagebox.showwarning("警告", f"獲取 {stock_id} 失敗: {e}"))
                    continue
            
            if not data_dict:
                self.root.after(0, lambda: messagebox.showerror("錯誤", "未能獲取任何股票數據"))
                self.root.after(0, self.reset_run_button)
                return
            
            # 創建策略
            strategy = AlphaStrategy(**params)
            
            # 運行策略
            self.root.after(0, lambda: self.status_label.config(
                text="正在運行選股策略...",
                fg='#3498db'
            ))
            
            all_results = []
            for stock_id, df in data_dict.items():
                analyzed_df = strategy.analyze_stock(df, stock_id)
                signals = strategy.get_signals_summary(analyzed_df)
                if len(signals) > 0:
                    all_results.append(signals)
            
            # 顯示結果
            if all_results:
                final_report = pd.concat(all_results, ignore_index=False)
                final_report = final_report.sort_index()
                
                output_columns = [
                    'Stock_ID', 'Open', 'High', 'Low', 'Close', 'Volume',
                    'MA20', 'MA60', 'ATR', 'Trust_Net_Buy', 'Revenue_YoY',
                    'Stop_Loss_Price', 'Risk_Reward_Ratio'
                ]
                
                available_columns = [col for col in output_columns if col in final_report.columns]
                final_report = final_report[available_columns].reset_index()
                
                self.current_results = final_report
                
                # 更新UI
                self.root.after(0, lambda: self.display_results(final_report))
            else:
                self.root.after(0, lambda: self.display_no_results())
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("錯誤", f"運行過程中發生錯誤: {str(e)}"))
        finally:
            self.root.after(0, self.reset_run_button)
    
    def display_results(self, df):
        """顯示結果"""
        # 清除舊數據
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 設置列
        columns = list(df.columns)
        self.result_tree['columns'] = columns
        
        # 配置列
        for col in columns:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=100, anchor=tk.CENTER)
        
        # 插入數據（限制顯示，避免過多）
        for idx, row in df.iterrows():
            values = [str(row[col])[:20] if pd.notna(row[col]) else '' for col in columns]
            self.result_tree.insert('', tk.END, values=values)
        
        # 更新狀態和統計
        stock_count = df['Stock_ID'].nunique() if 'Stock_ID' in df.columns else 0
        signal_count = len(df)
        
        self.status_label.config(
            text=f"✓ 分析完成！找到 {signal_count} 個買入信號",
            fg='#27ae60'
        )
        
        summary = f"找到 {signal_count} 個買入信號 | 涉及 {stock_count} 支股票"
        if 'Stock_ID' in df.columns:
            stock_summary = df.groupby('Stock_ID').size()
            summary += "\n各股票信號數量: " + " | ".join([f"{s}: {c}個" for s, c in stock_summary.items()])
        
        self.summary_label.config(text=summary)
        self.export_button.config(state=tk.NORMAL)
    
    def display_no_results(self):
        """顯示無結果"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        self.status_label.config(
            text="未找到任何買入信號，請調整策略參數或選擇其他股票",
            fg='#e74c3c'
        )
        self.summary_label.config(text="")
        self.export_button.config(state=tk.DISABLED)
    
    def reset_run_button(self):
        """重置運行按鈕"""
        self.run_button.config(state=tk.NORMAL, text="🚀 運行選股策略")
    
    def export_csv(self):
        """導出CSV"""
        if self.current_results is None:
            messagebox.showwarning("警告", "沒有可導出的結果")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                self.current_results.to_csv(filename, index=False, encoding='utf-8-sig')
                messagebox.showinfo("成功", f"報告已導出至:\n{filename}")
            except Exception as e:
                messagebox.showerror("錯誤", f"導出失敗: {str(e)}")


def main():
    """主函數"""
    root = tk.Tk()
    app = StockSelectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

