"""
台灣股票選股系統 - Streamlit Web應用
使用Streamlit創建的清晰、可靠的界面
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from data_fetcher import DataFetcher
from alpha_strategy import AlphaStrategy

# 頁面配置
st.set_page_config(
    page_title="台灣股票選股系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化session state
if 'results' not in st.session_state:
    st.session_state.results = None

# 標題
st.title("📈 台灣股票選股系統")
st.markdown("---")

# === 左側邊欄：設定參數 ===
with st.sidebar:
    st.header("⚙️ 設定參數")
    
    # 股票列表輸入
    st.subheader("📊 股票列表")
    stock_input = st.text_input(
        "輸入股票代號",
        value="2330.TW 2317.TW",
        help="多個股票用空格或逗號分隔，例如：2330.TW 2317.TW 2454.TW",
        key="stock_input"
    )
    st.caption("範例: 2330.TW 2317.TW 2454.TW")
    
    st.markdown("---")
    
    # 日期範圍
    st.subheader("📅 日期範圍")
    days_back = st.number_input(
        "過去天數",
        min_value=30,
        max_value=3650,
        value=365,
        step=30,
        help="分析過去多少天的數據"
    )
    
    st.markdown("---")
    
    # 策略參數
    st.subheader("🎯 策略參數")
    
    with st.expander("📖 選股策略說明（點擊查看）", expanded=False):
        st.markdown("""
        ### 選股策略公式
        
        系統會同時檢查以下**5個條件**，全部滿足才產生買入信號：
        
        **1. 趨勢條件（技術面）**
        ```
        收盤價 > 短期均線 > 長期均線
        ```
        - 表示股票處於上升趨勢
        - 例：收盤價1100元 > MA20(1050元) > MA60(1000元) ✅
        
        **2. 動量條件（成交量）**
        ```
        當日成交量 > 成交量倍數 × 過去5日均量
        ```
        - 表示市場關注度高，有資金流入
        - 例：當日成交量5萬張 > 1.5 × 3萬張(均量) ✅
        
        **3. 籌碼條件（資金面）**
        ```
        投信買超 > 0
        ```
        - 投信（投顧公司）正在買入，表示機構看好
        
        **4. 基本面條件（財務）**
        ```
        營收年增率 > 最低年增率%
        ```
        - 公司營收成長，基本面良好
        - 例：營收年增率15% > 10% ✅
        
        **5. 風險管理（停損價）**
        ```
        停損價 = 買入價 - (ATR × 停損ATR倍數)
        ```
        - 自動計算停損價格，控制風險
        """)
    
    col1, col2 = st.columns(2)
    with col1:
        ma_short = st.number_input(
            "短期均線週期", 
            min_value=5, max_value=100, value=20, step=5,
            help="例如20表示20日均線，用來判斷短期趨勢"
        )
        vol_mult = st.number_input(
            "成交量倍數", 
            min_value=1.0, max_value=5.0, value=1.5, step=0.1,
            help="成交量需大於均量的幾倍才算有動量（建議1.5-2.0）"
        )
        atr_period = st.number_input(
            "ATR週期", 
            min_value=5, max_value=30, value=14, step=1,
            help="平均真實波幅的計算天數（用來計算停損價）"
        )
    
    with col2:
        ma_long = st.number_input(
            "長期均線週期", 
            min_value=20, max_value=200, value=60, step=5,
            help="例如60表示60日均線，用來判斷長期趨勢"
        )
        # 移除營收年增率參數（無法獲取真實數據）
        # revenue_min = st.number_input(...)
        stop_loss_mult = st.number_input(
            "停損ATR倍數", 
            min_value=1.0, max_value=5.0, value=2.0, step=0.1,
            help="停損價 = 買入價 - (ATR × 此倍數)，越大停損越遠（建議2.0）"
        )
    
    st.markdown("---")
    
    # 運行按鈕
    run_button = st.button(
        "🚀 運行選股策略",
        type="primary",
        use_container_width=True,
        help="點擊開始分析"
    )
    
    # 重置按鈕
    if st.button("🔄 重置為預設值", use_container_width=True):
        st.rerun()

# === 主區域：顯示結果 ===
if not stock_input.strip():
    st.info("👈 請在左側邊欄輸入股票代號，然後點擊「運行選股策略」開始分析")
    
    # 顯示使用說明
    st.markdown("---")
    st.header("📖 使用說明")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 快速開始（3步驟）")
        st.markdown("""
        1. **輸入股票代號**
           - 在左側「股票列表」輸入
           - 例如：`2330.TW 2317.TW`
           - 多個股票用空格分隔
        
        2. **使用預設參數或調整**
           - 可以直接使用預設值
           - 或根據需求調整策略參數
        
        3. **點擊「運行選股策略」**
           - 等待分析完成
           - 查看買入信號結果
        """)
        
        st.subheader("📊 常見台股代號")
        st.markdown("""
        - **2330.TW** - 台積電
        - **2317.TW** - 鴻海
        - **2454.TW** - 聯發科
        - **2308.TW** - 台達電
        - **2412.TW** - 中華電
        - **2303.TW** - 聯電
        """)
    
    with col2:
        st.subheader("🎯 選股策略公式詳解")
        st.markdown("""
        系統會同時檢查以下**2個真實數據條件**：
        
        ⚠️ **重要說明**：系統僅使用yfinance可獲取的真實數據（價格和成交量）進行分析。
        
        以下條件因無法獲取真實數據源而暫時移除：
        - 籌碼條件（投信買超）- 需要TWSE API
        - 基本面條件（營收年增率）- 需要財務報表API
        
        如需這些條件，請使用付費API或手動輸入數據。
        
        **✅ 1. 趨勢條件（真實價格數據）**
        ```
        收盤價 > 短期均線 > 長期均線
        ```
        - 使用真實的收盤價、MA20、MA60（全部從yfinance獲取）
        - 表示股票處於上升趨勢
        
        **✅ 2. 動量條件（真實成交量數據）**
        ```
        當日成交量 > 倍數 × 過去5日均量
        ```
        - 使用真實的成交量數據（從yfinance獲取）
        - 表示有大量資金流入，市場關注度高
        
        **✅ 3. 風險管理**
        ```
        停損價 = 買入價 - (ATR × 倍數)
        ```
        自動設定停損點
        """)
        
        st.info("💡 **提示**：所有真實數據條件都滿足時才會產生買入信號！")
        st.warning("⚠️ **數據說明**：本系統100%使用yfinance提供的真實數據，絕不模擬。")

elif run_button:
    # 解析股票列表
    stocks = stock_input.replace(',', ' ').split()
    stocks = [s.strip().upper() for s in stocks if s.strip()]
    
    # 確保格式正確
    formatted_stocks = []
    for stock in stocks:
        if '.' not in stock:
            formatted_stocks.append(f"{stock}.TW")
        else:
            formatted_stocks.append(stock)
    
    if not formatted_stocks:
        st.error("❌ 請輸入有效的股票代號")
    else:
        # 顯示進度
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 初始化組件
            fetcher = DataFetcher()
            
            # 計算日期範圍
            end_date = datetime.now()
            start_date = (end_date - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            status_text.text(f"📥 正在獲取 {len(formatted_stocks)} 支股票的數據...")
            progress_bar.progress(10)
            
            # 獲取數據
            data_dict = {}
            success_count = 0
            for i, stock_id in enumerate(formatted_stocks):
                try:
                    status_text.text(f"📥 正在從yfinance獲取 {stock_id} 的數據... ({i+1}/{len(formatted_stocks)})")
                    df = fetcher.fetch_data(stock_id, start_date)
                    data_dict[stock_id] = df
                    success_count += 1
                    st.success(f"✅ {stock_id}: 成功獲取 {len(df)} 筆真實數據（來源：yfinance）")
                    progress_bar.progress(30 + (i + 1) * 20 // len(formatted_stocks))
                except Exception as e:
                    st.error(f"❌ 獲取 {stock_id} 失敗: {str(e)}\n\n請確認：\n- 股票代號格式正確（例如：2330.TW）\n- 股票在TWSE交易\n- 網絡連接正常")
                    continue
            
            if success_count > 0:
                st.info(f"📊 成功獲取 {success_count}/{len(formatted_stocks)} 支股票的數據")
            
            if not data_dict:
                st.error("❌ 未能獲取任何股票數據，請檢查股票代號是否正確")
            else:
                # 創建策略
                status_text.text("🔍 正在運行選股策略...")
                progress_bar.progress(60)
                
                # 只使用真實數據參數（移除無法獲取真實數據的參數）
                strategy = AlphaStrategy(
                    atr_period=int(atr_period),
                    ma_short=int(ma_short),
                    ma_long=int(ma_long),
                    vol_multiplier=float(vol_mult),
                    min_revenue_yoy=0.0,  # 不再使用，因為無法獲取真實數據
                    stop_loss_atr_multiplier=float(stop_loss_mult)
                )
                
                # 運行策略
                all_results = []
                for stock_id, df in data_dict.items():
                    analyzed_df = strategy.analyze_stock(df, stock_id)
                    signals = strategy.get_signals_summary(analyzed_df)
                    if len(signals) > 0:
                        all_results.append(signals)
                
                progress_bar.progress(90)
                
                # 顯示結果
                if all_results:
                    final_report = pd.concat(all_results, ignore_index=False)
                    final_report = final_report.sort_index()
                    
                    # 只顯示真實數據欄位
                    output_columns = [
                        'Stock_ID', 'Open', 'High', 'Low', 'Close', 'Volume',
                        'MA20', 'MA60', 'ATR', 'Stop_Loss_Price', 'Risk_Reward_Ratio'
                    ]
                    
                    available_columns = [col for col in output_columns if col in final_report.columns]
                    final_report = final_report[available_columns].reset_index()
                    
                    st.session_state.results = final_report
                    
                    progress_bar.progress(100)
                    status_text.text("✅ 分析完成！")
                    
                    # 顯示統計
                    st.success(f"🎉 找到 {len(final_report)} 個買入信號！")
                    
                    # 顯示摘要
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("買入信號數量", len(final_report))
                    with col2:
                        st.metric("涉及股票", final_report['Stock_ID'].nunique() if 'Stock_ID' in final_report.columns else 0)
                    with col3:
                        if 'Risk_Reward_Ratio' in final_report.columns:
                            avg_rr = final_report['Risk_Reward_Ratio'].mean()
                            st.metric("平均風險報酬比", f"{avg_rr:.2f}")
                    
                    # 各股票信號數量
                    if 'Stock_ID' in final_report.columns:
                        st.subheader("📊 各股票信號分布")
                        stock_summary = final_report.groupby('Stock_ID').size().reset_index(name='信號數量')
                        st.bar_chart(stock_summary.set_index('Stock_ID'))
                    
                    st.markdown("---")
                    st.subheader("📋 買入信號詳情")
                    
                    # 顯示表格
                    st.dataframe(
                        final_report,
                        use_container_width=True,
                        height=400
                    )
                    
                    # 導出按鈕
                    csv = final_report.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="💾 導出CSV報告",
                        data=csv,
                        file_name=f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                else:
                    progress_bar.progress(100)
                    status_text.text("ℹ️ 未找到買入信號")
                    st.info("ℹ️ 未找到符合條件的買入信號，請嘗試：\n"
                           "- 調整策略參數\n"
                           "- 選擇其他股票\n"
                           "- 擴大日期範圍")
        
        except Exception as e:
            progress_bar.progress(100)
            status_text.text("❌ 發生錯誤")
            st.error(f"❌ 運行過程中發生錯誤: {str(e)}")
            st.exception(e)

# 如果有之前的結果，顯示它們
elif st.session_state.results is not None:
    st.subheader("📋 上次分析結果")
    st.dataframe(st.session_state.results, use_container_width=True, height=400)
    
    csv = st.session_state.results.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="💾 導出CSV報告",
        data=csv,
        file_name=f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

