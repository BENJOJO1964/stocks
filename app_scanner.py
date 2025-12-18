"""
台灣股市掃描器 - Streamlit應用
專業評分系統，掃描全市場股票
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from stock_scanner import TaiwanStockScanner
import threading
import time

# 頁面配置
st.set_page_config(
    page_title="台灣股市掃描器",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化session state
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'is_scanning' not in st.session_state:
    st.session_state.is_scanning = False
if 'stock_list' not in st.session_state:
    # 默認使用預設16支股票
    st.session_state.stock_list = list(TaiwanStockScanner.DEFAULT_TICKERS.keys())
if 'use_custom_list' not in st.session_state:
    st.session_state.use_custom_list = False

# 標題
st.title("📊 台灣股市掃描器")
st.markdown("**專業評分系統 - 全市場掃描**")
st.markdown("---")

# === 左側邊欄：設定參數 ===
with st.sidebar:
    st.header("⚙️ 掃描參數")
    
    # 股票列表選擇
    st.subheader("📋 股票列表")
    
    # 選擇模式：預設列表 或 手動輸入
    use_custom_list = st.checkbox("使用自定義股票列表", value=False, help="勾選後可以手動輸入股票代碼")
    
    if use_custom_list:
        # 手動輸入模式
        st.info("📝 請輸入股票代碼（每行一個，或使用逗號分隔）")
        
        # 顯示預設列表作為參考
        default_tickers = TaiwanStockScanner.DEFAULT_TICKERS
        default_list_text = '\n'.join(default_tickers.keys())
        
        custom_stocks = st.text_area(
            "股票代碼輸入",
            value="",
            height=150,
            help="範例：\n2330.TW\n2317.TW\n2382.TW\n\n或：2330.TW, 2317.TW, 2382.TW\n\n注意：上市股票使用.TW，上櫃股票使用.TWO",
            placeholder="每行輸入一個股票代碼，例如：\n2330.TW\n2317.TW\n2382.TW"
        )
        
        # 解析用戶輸入的股票代碼
        if custom_stocks.strip():
            # 處理多種輸入格式：換行分隔、逗號分隔、空格分隔
            lines = custom_stocks.strip().replace(',', '\n').replace('，', '\n').replace(' ', '\n').split('\n')
            custom_stock_list = []
            for line in lines:
                ticker = line.strip().upper()
                if ticker:
                    # 驗證格式：必須包含.TW或.TWO
                    if '.TW' in ticker or '.TWO' in ticker:
                        custom_stock_list.append(ticker)
                    elif ticker.isdigit() and len(ticker) == 4:
                        # 如果只輸入4位數字，先嘗試.TW（系統會自動處理上櫃股票）
                        # 如果.TW找不到，fetch_stock_data會自動嘗試.TWO
                        custom_stock_list.append(f"{ticker}.TW")
            
            stock_list = custom_stock_list
            if stock_list:
                st.session_state.stock_list = stock_list
                st.success(f"✅ 已輸入 {len(stock_list)} 支股票")
                # 顯示輸入的股票列表
                with st.expander("📊 查看自定義股票列表", expanded=True):
                    # 按族群分組顯示（如果有的話）
                    default_tickers = TaiwanStockScanner.DEFAULT_TICKERS
                    custom_by_sector = {}
                    custom_others = []
                    
                    for ticker in stock_list:
                        if ticker in default_tickers:
                            sector = default_tickers[ticker]
                            if sector not in custom_by_sector:
                                custom_by_sector[sector] = []
                            custom_by_sector[sector].append(ticker)
                        else:
                            custom_others.append(ticker)
                    
                    # 顯示有族群分類的股票
                    for sector in sorted(custom_by_sector.keys()):
                        st.markdown(f"**{sector}**: {', '.join(custom_by_sector[sector])}")
                    
                    # 顯示沒有族群分類的股票
                    if custom_others:
                        st.markdown(f"**其他**: {', '.join(custom_others)}")
            else:
                st.warning("⚠️ 未檢測到有效的股票代碼，將使用預設列表")
                default_tickers = TaiwanStockScanner.DEFAULT_TICKERS
                stock_list = list(default_tickers.keys())
                st.session_state.stock_list = stock_list
        else:
            st.info("💡 未輸入股票代碼，將使用預設16支股票")
            default_tickers = TaiwanStockScanner.DEFAULT_TICKERS
            stock_list = list(default_tickers.keys())
            st.session_state.stock_list = stock_list
    else:
        # 使用預設列表
        default_tickers = TaiwanStockScanner.DEFAULT_TICKERS
        stock_list = list(default_tickers.keys())
        st.session_state.stock_list = stock_list
        
        st.info(f"📋 預設掃描列表：{len(stock_list)} 支台灣高Alpha股票")
        
        # 顯示族群分類（只讀）
        with st.expander("📊 查看股票列表", expanded=False):
            for sector in sorted(set(default_tickers.values())):
                stocks_in_sector = [ticker for ticker, s in default_tickers.items() if s == sector]
                st.markdown(f"**{sector}**: {', '.join(stocks_in_sector)}")
    
    st.markdown("---")
    
    # 評分權重設定
    st.subheader("🎯 評分權重")
    
    col1, col2 = st.columns(2)
    with col1:
        trend_weight = st.slider("趨勢權重", 0.0, 1.0, 0.40, 0.05, help="趨勢條件權重（40%）")
        momentum_weight = st.slider("動量權重", 0.0, 1.0, 0.30, 0.05, help="動量條件權重（30%）")
    
    with col2:
        rs_weight = st.slider("相對強度權重", 0.0, 1.0, 0.20, 0.05, help="相對強度權重（20%）")
        inst_weight = st.slider("機構資金權重", 0.0, 1.0, 0.10, 0.05, help="機構資金權重（10%）")
    
    # 權重總和檢查
    total_weight = trend_weight + momentum_weight + rs_weight + inst_weight
    if abs(total_weight - 1.0) > 0.01:
        st.warning(f"⚠️ 權重總和應為100%，目前：{total_weight*100:.1f}%")
        # 自動正規化
        trend_weight = trend_weight / total_weight
        momentum_weight = momentum_weight / total_weight
        rs_weight = rs_weight / total_weight
        inst_weight = inst_weight / total_weight
    
    # 權重優化建議（基於統計分析）
    with st.expander("💡 權重優化建議（點擊查看）", expanded=False):
        st.markdown("""
        ### 當前權重設定
        - 趨勢權重：{:.0%}
        - 動量權重：{:.0%}
        - 相對強度權重：{:.0%}
        - 機構資金權重：{:.0%}
        
        ### 專業建議
        **波段交易（2-4周持有）的推薦權重：**
        - ✅ 趨勢權重：40-50%（最重要，因為波段交易依賴趨勢）
        - ✅ 動量權重：25-35%（成交量確認趨勢）
        - ✅ 相對強度權重：20-25%（相對大盤表現）
        - ⚠️ 機構資金權重：5-10%（yfinance支持有限，建議降低）
        
        **當前設定評估：**
        """.format(trend_weight, momentum_weight, rs_weight, inst_weight))
        
        # 給出評估
        suggestions = []
        if trend_weight < 0.35:
            suggestions.append("⚠️ 趨勢權重偏低，建議提高到40%以上")
        if momentum_weight > 0.35:
            suggestions.append("⚠️ 動量權重偏高，建議降低到30%以下")
        if inst_weight > 0.15:
            suggestions.append("⚠️ 機構資金權重偏高，建議降低到10%以下（yfinance數據支持有限）")
        
        if suggestions:
            for suggestion in suggestions:
                st.warning(suggestion)
        else:
            st.success("✅ 當前權重設定合理")
        
        st.info("💡 **注意**：權重優化需要歷史回測驗證。當前建議基於波段交易的專業經驗。")
    
    st.markdown("---")
    
    # 市場環境和篩選設定
    st.subheader("🌍 市場環境與篩選")
    
    # 市場環境顯示
    try:
        temp_scanner = TaiwanStockScanner()
        market_env = temp_scanner.check_market_environment()
        if market_env == '多頭':
            st.success(f"✅ 當前市場環境：**{market_env}**（適合使用掃描器）")
        elif market_env == '空頭':
            st.error(f"⚠️ 當前市場環境：**{market_env}**（建議暫停使用）")
        elif market_env == '盤整':
            st.warning(f"⚡ 當前市場環境：**{market_env}**（需謹慎使用）")
        else:
            st.info(f"❓ 當前市場環境：**{market_env}**")
    except:
        st.info("無法判斷市場環境")
    
    # 流動性和基本面篩選設定
    enable_liquidity = st.checkbox("啟用流動性檢查", value=True, help="排除日均成交量過低的股票")
    min_volume = st.number_input("最低日均成交量", min_value=100000, value=1000000, step=100000, 
                                 help="低於此成交量的股票將被排除（建議：100萬股）")
    enable_fundamental = st.checkbox("啟用基本面篩選", value=True, help="排除財務狀況惡化的股票")
    
    st.markdown("---")
    
    # 技術參數
    st.subheader("📈 技術參數")
    
    # 說明
    with st.expander("📖 技術參數說明（點擊查看詳細）", expanded=False):
        st.markdown("""
        ### 技術參數的意義和作用
        
        **1. 最低分數閾值（70分）**
        - **作用**：這是**評分門檻**（不是選股門檻）
        - **意義**：系統會顯示所有16支股票，但只有總分 >= 70分的會被標記為"強買入"或"買入"信號
        - **說明**：固定16支股票都會顯示，此參數用來判斷買入信號的強弱
        - **建議**：70分是較高標準，如果想要更多買入信號，可以降低到60-65分
        
        **2. 短期均線（20日）**
        - **作用**：計算20日移動平均線（MA20）
        - **意義**：代表**短期趨勢**方向
        - **判斷**：股價 > MA20 = 短期上漲趨勢
        - **用途**：用於趨勢評分（權重40%）
        
        **3. 長期均線（60日）**
        - **作用**：計算60日移動平均線（MA60）
        - **意義**：代表**長期趨勢**方向
        - **判斷**：MA20 > MA60 = 中長期上漲趨勢
        - **用途**：用於趨勢評分（權重40%）
        - **組合條件**：收盤價 > MA20 > MA60 = 強勢上升趨勢 ✅
        
        **4. 成交量倍數（1.2倍）**
        - **作用**：判斷是否有**動量**（資金流入）
        - **計算**：當日成交量 > 1.2 × 過去5日均量
        - **意義**：成交量放大 = 市場關注度高，有資金進場
        - **用途**：用於動量評分（權重30%）
        - **建議**：1.2-1.5倍是合理範圍，過高可能表示異常波動
        
        **5. ATR週期（14日）**
        - **作用**：計算平均真實波幅（Average True Range）
        - **意義**：衡量股票的**波動幅度**
        - **用途**：
          - 用於計算停損價（風險控制）
          - ATR越大 = 股票波動越大 = 停損距離要設遠一點
        
        **6. 停損ATR倍數（2.0倍）**
        - **作用**：計算**建議停損價**
        - **公式**：停損價 = 買入價 - (ATR × 2.0)
        - **意義**：風險控制，如果股價跌破停損價，應該出場
        - **建議**：
          - 1.5倍 = 緊停損（適合短線）
          - 2.0倍 = 標準停損（適合中線）
          - 3.0倍 = 寬停損（適合長線）
        
        ---
        
        **📌 總結**：這些參數控制選股策略的嚴格程度。參數越嚴格，選出的股票越少，但質量可能更高。
        """)
    
    min_score = st.number_input(
        "最低分數閾值",
        min_value=0.0,
        max_value=100.0,
        value=70.0,
        step=5.0,
        help="評分門檻：所有16支股票都會顯示，但會標記哪些股票符合此標準（分數>=此值標記為強買入/買入）"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        ma_short = st.number_input(
            "短期均線（日）", 
            min_value=5, max_value=50, value=20, step=5,
            help="計算20日移動平均線，判斷短期趨勢"
        )
        vol_mult = st.number_input(
            "成交量倍數", 
            min_value=1.0, max_value=3.0, value=1.2, step=0.1,
            help="當日成交量需大於均量的幾倍（1.2=120%）"
        )
    
    with col2:
        ma_long = st.number_input(
            "長期均線（日）", 
            min_value=20, max_value=200, value=60, step=5,
            help="計算60日移動平均線，判斷長期趨勢"
        )
        atr_period = st.number_input(
            "ATR週期（日）", 
            min_value=5, max_value=30, value=14, step=1,
            help="計算ATR的天數（衡量波動幅度）"
        )
    
    stop_loss_mult = st.number_input(
        "停損ATR倍數",
        min_value=1.0,
        max_value=5.0,
        value=2.0,
        step=0.1,
        help="停損價 = 買入價 - (ATR × 此倍數)。2.0倍是標準設定"
    )
    
    st.markdown("---")
    
    # 掃描按鈕
    scan_button = st.button(
        "🚀 開始掃描（全市場）",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.is_scanning,
        help="開始掃描所有股票"
    )

# === 主區域：顯示結果 ===
# 說明區域
with st.expander("📖 波段交易策略說明", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 波段交易策略（持有2-4周）
        
        **1. 趨勢基礎（必須滿足）**
        - 條件：收盤價 > MA20 > MA60
        - 意義：確認上升趨勢後才考慮買入
        
        **2. 進場點優化**
        - **Golden Cross**：MA5 > MA20（加分）
        - **接近支撐**：價格在MA20的3%以內（加分）
        - 邏輯：在支撐線附近買入，不是追高
        
        **3. 評分系統（總分100分）**
        - 趨勢評分（40%）：趨勢基礎 + 進場點
        - 動量評分（30%）：成交量放大
        - 相對強度（20%）：vs TAIEX（250天）
        - 機構資金（10%）：中性分數
        
        **4. 風險控制**
        - **初始停損**：買入價 - (ATR × 2.0)
        - **移動停損**：價格上漲時，停損價跟著上移（鎖定利潤）
        """)
    
    with col2:
        st.markdown("""
        ### 波段狀態說明
        
        **初升段**
        - 剛突破MA20
        - MA5剛上穿MA20
        - 適合：積極進場
        
        **主升段**
        - 強勢上漲
        - 價格遠高於MA20（>10%）
        - 適合：持有或部分獲利
        
        **拉回找買點**
        - 價格接近MA20（3%以內）
        - 等待支撐確認
        - 適合：觀察或小量試單
        
        ### 使用方式
        
        1. **點擊「開始掃描」**
        2. **查看「波段狀態」**判斷進場時機
        3. **查看「建議持有天數」**規劃出場時間
        4. **嚴格遵守「移動停損價」**
        """)
        
        st.info("💡 **波段交易原則**：趨勢確認 → 支撐買入 → 移動停損 → 持有2-4周")

# 掃描進度和結果
if scan_button and not st.session_state.is_scanning:
    # 使用側邊欄中設定的股票列表（可能是預設或自定義）
    if 'stock_list' not in st.session_state:
        # 如果側邊欄還沒有設定，使用預設列表
        stock_list = list(TaiwanStockScanner.DEFAULT_TICKERS.keys())
        st.session_state.stock_list = stock_list
    else:
        stock_list = st.session_state.stock_list
    
    if not stock_list:
        st.error("❌ 股票列表為空")
    else:
        st.session_state.is_scanning = True
        
        # 創建掃描器（包含新的篩選參數）
        scanner = TaiwanStockScanner(
            trend_weight=trend_weight,
            momentum_weight=momentum_weight,
            relative_strength_weight=rs_weight,
            institutional_weight=inst_weight,
            min_score=min_score,
            ma_short=ma_short,
            ma_long=ma_long,
            vol_multiplier=vol_mult,
            atr_period=atr_period,
            stop_loss_atr_mult=stop_loss_mult,
            min_avg_volume=min_volume,
            enable_fundamental_filter=enable_fundamental,
            enable_liquidity_check=enable_liquidity
        )
        
        # 進度顯示
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_placeholder = st.empty()
        
        # 執行掃描（使用線程以便實時更新）
        try:
            status_text.text(f"🚀 開始掃描 {len(stock_list)} 支股票...")
            
            # 存儲進度信息
            progress_info = {'current': 0, 'total': len(stock_list), 'stock': ''}
            
            def progress_callback(current, total, stock_id):
                progress_info['current'] = current
                progress_info['total'] = total
                progress_info['stock'] = stock_id
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"📊 掃描中... ({current}/{total}) - 當前：{stock_id}")
            
            # 執行掃描（暫時移除log_callback，先讓功能正常運行）
            results = scanner.scan_stocks(stock_list, progress_callback=progress_callback)
            
            progress_bar.progress(1.0)
            st.session_state.scan_results = results
            st.session_state.is_scanning = False
            
            # 顯示結果（顯示所有掃描到的股票，包括無信號的）
            if len(results) > 0:
                # 計算有信號的股票數（評分>0）
                signal_count = len(results[results['策略評分'] > 0]) if '策略評分' in results.columns else len(results)
                status_text.text(f"✅ 掃描完成！共掃描 {len(results)} 支股票，其中 {signal_count} 支有信號")
                
                # 顯示數據日期警告
                if '數據日期' in results.columns:
                    latest_data_date = results['數據日期'].max()
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    if latest_data_date < today_str:
                        st.warning(f"⚠️ **數據日期說明**：目前顯示的是 {latest_data_date} 的數據。台灣股市收盤後，yfinance數據更新通常需要15-20分鐘。當前日期：{today_str}")
                
                st.markdown("---")
                
                # 獲取並格式化數據日期（顯示在標題旁邊）
                data_date_display = ""
                if '數據日期' in results.columns:
                    latest_data_date = results['數據日期'].max()
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    if pd.notna(latest_data_date) and latest_data_date not in ['無數據', 'Data Error', 'Yahoo Finance未找到', '無法獲取']:
                        try:
                            date_part = str(latest_data_date)[:10] if len(str(latest_data_date)) >= 10 else str(latest_data_date)
                            if date_part == today_str:
                                data_date_display = f"✅ 數據日期：{date_part}（最新）"
                            else:
                                try:
                                    date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                                    today_obj = datetime.strptime(today_str, '%Y-%m-%d')
                                    days_diff = (today_obj - date_obj).days
                                    if days_diff == 1:
                                        data_date_display = f"📅 數據日期：{date_part}（昨天）"
                                    elif days_diff > 1:
                                        data_date_display = f"⚠️ 數據日期：{date_part}（{days_diff}天前）"
                                    else:
                                        data_date_display = f"📅 數據日期：{date_part}"
                                except:
                                    data_date_display = f"📅 數據日期：{date_part}"
                        except:
                            data_date_display = ""
                
                # 顯示標題和數據日期
                col_title, col_date = st.columns([3, 2])
                with col_title:
                    st.subheader("📊 股票訊號表（依評分排序）")
                with col_date:
                    if data_date_display:
                        st.markdown(f"<div style='margin-top: 1.5rem; font-size: 0.9rem;'>{data_date_display}</div>", unsafe_allow_html=True)
                
                # 準備顯示表格（波段交易專用）
                # 不再在表格中顯示數據日期（已移至標題旁）
                display_columns = [
                    '族群', '股票代碼', '股票名稱', '當前股價',
                    'MA5', 'MA20', 'MA60',
                    '策略評分', '買入訊號', '波段狀態', '建議持有天數',
                    '建議停損價(ATR)', '移動停損價', '建議停利價'
                ]
                
                # 只保留存在的欄位
                display_columns = [col for col in display_columns if col in results.columns]
                display_df = results[display_columns].copy()
                
                # 確保索引是唯一的（重置索引）
                display_df = display_df.reset_index(drop=True)
                
                # 合併股票名稱和股票代碼到同一列
                if '股票代碼' in display_df.columns and '股票名稱' in display_df.columns:
                    # 創建合併列：股票名稱 (股票代碼)
                    # 如果名稱和代碼一樣，只顯示一個
                    def format_stock_name(row):
                        stock_code = row['股票代碼'] if pd.notna(row['股票代碼']) else ''
                        stock_name = row['股票名稱'] if pd.notna(row['股票名稱']) else ''
                        
                        if not stock_code:
                            return ''
                        
                        # 如果名稱和代碼一樣，只顯示代碼
                        if stock_name == stock_code:
                            return stock_code
                        
                        # 如果名稱是空的或無效，只顯示代碼
                        if not stock_name or stock_name == '' or stock_name == stock_code:
                            return stock_code
                        
                        # 正常情況：名稱 (代碼)
                        return f"{stock_name} ({stock_code})"
                    
                    display_df['股票'] = display_df.apply(format_stock_name, axis=1)
                    # 移除原來的兩列
                    display_df = display_df.drop(columns=['股票代碼', '股票名稱'])
                    # 將合併列移到最前面（在族群之後）
                    cols = [col for col in display_df.columns if col != '股票']
                    display_df = display_df[['族群', '股票'] + cols]
                elif '股票代碼' in display_df.columns:
                    # 如果只有股票代碼，重命名為股票
                    display_df = display_df.rename(columns={'股票代碼': '股票'})
                    # 將股票列移到族群之後
                    cols = [col for col in display_df.columns if col != '股票']
                    display_df = display_df[['族群', '股票'] + cols]
                
                # 再次確保索引是唯一的（應用樣式前）
                display_df = display_df.reset_index(drop=True)
                
                # 刪除重複的族群列（更徹底的方法）
                # 找出所有族群相關的列（包括族群、族群_1、族群_2等）
                group_cols = [col for col in display_df.columns if '族群' in col]
                if len(group_cols) > 1:
                    # 只保留第一個'族群'列（如果存在），否則保留第一個族群相關列
                    if '族群' in group_cols:
                        cols_to_drop = [col for col in group_cols if col != '族群']
                    else:
                        # 如果沒有純'族群'列，只保留第一個
                        cols_to_drop = group_cols[1:]
                    display_df = display_df.drop(columns=cols_to_drop)
                
                # 如果還有重複的列名（非族群相關），也需要處理
                if display_df.columns.duplicated().any():
                    # 找出重複的列名
                    duplicated_cols = display_df.columns[display_df.columns.duplicated()].unique()
                    for col in duplicated_cols:
                        # 保留第一個，刪除其他重複的
                        cols_with_same_name = [c for c in display_df.columns if c == col]
                        if len(cols_with_same_name) > 1:
                            # 保留第一個，刪除其他的
                            indices_to_drop = []
                            found_first = False
                            for idx, c in enumerate(display_df.columns):
                                if c == col:
                                    if found_first:
                                        indices_to_drop.append(idx)
                                    else:
                                        found_first = True
                            if indices_to_drop:
                                display_df = display_df.drop(columns=display_df.columns[indices_to_drop])
                
                # 確保族群列在第一個位置（如果存在）
                if '族群' in display_df.columns:
                    other_cols = [c for c in display_df.columns if c != '族群']
                    display_df = display_df[['族群'] + other_cols]
                
                # 格式化數值
                if '當前股價' in display_df.columns:
                    display_df['當前股價'] = display_df['當前股價'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "Data Error")
                
                # 格式化均線數值（讓用戶看到計算結果）
                for ma_col in ['MA5', 'MA20', 'MA60']:
                    if ma_col in display_df.columns:
                        display_df[ma_col] = display_df[ma_col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "Data Error")
                
                if '策略評分' in display_df.columns:
                    display_df['策略評分'] = display_df['策略評分'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "0.0")
                
                # 格式化停損停利價格
                for price_col in ['建議停損價(ATR)', '移動停損價', '建議停利價']:
                    if price_col in display_df.columns:
                        display_df[price_col] = display_df[price_col].apply(
                            lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                        )
                
                # 格式化建議持有天數
                # 只有當買入訊號為「買入」或「強買入」時才顯示持有天數
                # 如果是「觀察」或「無信號」，顯示為"-"（表示不需要持有）
                if '建議持有天數' in display_df.columns and '買入訊號' in display_df.columns:
                    def format_holding_days(row):
                        signal = row.get('買入訊號', '')
                        days = row.get('建議持有天數', 0)
                        # 只有買入或強買入才顯示持有天數
                        if signal in ['買入', '強買入']:
                            if pd.notna(days) and days > 0:
                                return f"{int(days)}天"
                        # 其他情況（觀察、無信號、Data Error等）顯示"-"
                        return "-"
                    display_df['建議持有天數'] = display_df.apply(format_holding_days, axis=1)
                elif '建議持有天數' in display_df.columns:
                    # 如果沒有買入訊號列，使用原有邏輯
                    display_df['建議持有天數'] = display_df['建議持有天數'].apply(
                        lambda x: f"{int(x)}天" if pd.notna(x) and x > 0 else "-"
                    )
                
                # 應用樣式（突出顯示）
                def highlight_score(val):
                    if isinstance(val, str) and val != "N/A":
                        try:
                            score = float(val)
                            if score >= 80:
                                return 'background-color: #90EE90; font-weight: bold'  # 綠色
                            elif score >= 70:
                                return 'background-color: #FFE4B5; font-weight: bold'  # 黃色
                            elif score >= 50:
                                return 'background-color: #E6E6FA'  # 淺紫色
                        except:
                            pass
                    return ''
                
                def highlight_signal(val):
                    if val == '強買入':
                        return 'background-color: #90EE90; font-weight: bold; color: #006400'
                    elif val == '買入':
                        return 'background-color: #FFE4B5; font-weight: bold'
                    return ''
                
                def highlight_stop_loss(val):
                    if isinstance(val, str) and val != "N/A":
                        return 'background-color: #FFB6C1; font-weight: bold; color: #8B0000'  # 紅色
                    return ''
                
                # 確保在應用樣式前，DataFrame的索引是唯一的（重置索引）
                display_df = display_df.reset_index(drop=True)
                
                # 確保列名唯一（如果有重複列名，會導致樣式錯誤）
                if display_df.columns.duplicated().any():
                    # 如果有重複列名，為重複的列名添加後綴
                    new_columns = []
                    seen = {}
                    for col in display_df.columns:
                        if col in seen:
                            seen[col] += 1
                            new_columns.append(f"{col}_{seen[col]}")
                        else:
                            seen[col] = 0
                            new_columns.append(col)
                    display_df.columns = new_columns
                
                styled_df = display_df.style.applymap(
                    highlight_score, subset=['策略評分']
                ).applymap(
                    highlight_signal, subset=['買入訊號']
                ).applymap(
                    highlight_stop_loss, subset=['建議停損價(ATR)']
                )
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    height=500
                )
                
                # 統計摘要（確保數字準確，顯示所有16支）
                st.markdown("---")
                
                # 計算各種統計
                total_scanned = len(results)
                expected_count = len(TaiwanStockScanner.DEFAULT_TICKERS)  # 應該是16支
                
                if '策略評分' in results.columns:
                    signal_count = len(results[results['策略評分'] > 0])
                    no_data_count = len(results[results['買入訊號'] == '無數據']) if '買入訊號' in results.columns else 0
                    valid_count = total_scanned - no_data_count  # 有效數據的股票數
                    avg_score = results[results['策略評分'] > 0]['策略評分'].mean() if signal_count > 0 else 0
                else:
                    signal_count = 0
                    no_data_count = 0
                    valid_count = total_scanned
                    avg_score = 0
                
                if '買入訊號' in results.columns:
                    strong_buy = len(results[results['買入訊號'] == '強買入'])
                else:
                    strong_buy = 0
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("已掃描股票", total_scanned, delta=f"預期{expected_count}支")
                    if total_scanned < expected_count:
                        st.caption(f"⚠️ 缺少 {expected_count - total_scanned} 支")
                with col2:
                    st.metric("有效數據", valid_count)
                    if no_data_count > 0:
                        st.caption(f"⚠️ {no_data_count} 支無數據")
                with col3:
                    st.metric("有信號股票", signal_count)
                    if signal_count > 0:
                        st.metric("平均評分", f"{avg_score:.1f}")
                with col4:
                    st.metric("強買入", strong_buy)
                
                # 導出按鈕
                csv = results.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="💾 導出完整CSV報告",
                    data=csv,
                    file_name=f"stock_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # 視覺化
                st.markdown("---")
                st.subheader("📊 分數分布")
                
                col1, col2 = st.columns(2)
                with col1:
                    # 使用股票代碼或股票名稱作為索引（如果股票代碼列存在）
                    if '股票代碼' in results.columns and '策略評分' in results.columns:
                        chart_df = results.set_index('股票代碼')['策略評分'].head(20)
                    elif '股票名稱' in results.columns and '策略評分' in results.columns:
                        chart_df = results.set_index('股票名稱')['策略評分'].head(20)
                    elif '策略評分' in results.columns:
                        # 如果都沒有，使用索引
                        chart_df = results['策略評分'].head(20)
                        st.bar_chart(chart_df)
                
                with col2:
                    if '策略評分' in results.columns:
                        score_dist = pd.cut(results['策略評分'], bins=[0, 50, 70, 80, 100], labels=['50以下', '50-70', '70-80', '80以上'])
                        st.bar_chart(score_dist.value_counts().sort_index())
                
            else:
                status_text.text("ℹ️ 掃描完成，但未獲取到任何股票數據")
                st.error("❌ 未能掃描到任何股票數據。可能原因：\n"
                        "- 網絡連接問題\n"
                        "- yfinance API暫時無法訪問\n"
                        "- 數據獲取錯誤\n\n"
                        "請檢查網絡連接後重新掃描。")
        
        except Exception as e:
            st.session_state.is_scanning = False
            st.error(f"❌ 掃描過程中發生錯誤: {str(e)}")
            st.exception(e)

# 顯示上次掃描結果
elif st.session_state.scan_results is not None and not st.session_state.is_scanning:
    results = st.session_state.scan_results
    
    st.subheader("📋 上次掃描結果")
    st.info(f"找到 {len(results)} 支符合條件的股票")
    
    # 確保結果已按總分排序
    # 防守判斷：檢查 results 是否為空或是否存在 'Total_Score' 欄位
    if len(results) > 0 and 'Total_Score' in results.columns:
        results = results.sort_values('Total_Score', ascending=False).reset_index(drop=True)
    else:
        if len(results) == 0:
            st.warning("⚠️ 今日無符合條件股票")
        elif 'Total_Score' not in results.columns:
            st.warning("⚠️ 掃描結果缺少必要欄位，無法進行排序")
    
    # 確保族群欄位存在
    if '族群' not in results.columns:
        results['族群'] = results['Stock_ID'].map(TaiwanStockScanner.DEFAULT_TICKERS).fillna('其他')
    
    # 顯示結果表格（包含族群）
    display_cols = ['Stock_ID', '族群', 'Total_Score', 'Close', 'Trend_Score', 'Momentum_Score', 'RS_Score', 'Stop_Loss_Price', 'Risk_Percent']
    display_cols = [col for col in display_cols if col in results.columns]
    
    st.dataframe(
        results[display_cols],
        use_container_width=True,
        height=400
    )
    
    csv = results.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="💾 導出CSV報告",
        data=csv,
        file_name=f"stock_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# 掃描中的狀態
if st.session_state.is_scanning:
    st.warning("⏳ 正在掃描中，請稍候...")

# === 新增功能：把今天結果送到自動化系統 ===
# 檢查是否有掃描結果
if st.session_state.scan_results is not None and not st.session_state.is_scanning:
    st.markdown("---")
    st.markdown("### 自動化系統整合")
    
    # Webhook URL（佔位變數，未來可配置）
    WEBHOOK_URL = "https://your-webhook-url-here.com/api/stock-results"
    
    # 按鈕
    send_button = st.button(
        "📤 把今天結果送到自動化系統",
        type="primary",
        use_container_width=True,
        help="將當前掃描結果以JSON格式發送到自動化系統"
    )
    
    if send_button:
        try:
            # 讀取目前畫面已存在、已計算完成的結果
            results_df = st.session_state.scan_results.copy()
            
            # 將DataFrame轉換為JSON格式（records格式，每行一個字典）
            results_json = results_df.to_dict(orient='records')
            
            # 準備要發送的數據（包含時間戳和數據）
            payload = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "data": results_json
            }
            
            # 導入requests（如果尚未導入）
            try:
                import requests
            except ImportError:
                st.error("❌ 錯誤：缺少 requests 套件。請執行：pip install requests")
                st.stop()
            
            # 發送POST請求到webhook（目前為佔位URL）
            # 注意：實際使用時，請替換WEBHOOK_URL為真實的webhook地址
            with st.spinner("正在發送數據到自動化系統..."):
                try:
                    response = requests.post(
                        WEBHOOK_URL,
                        json=payload,
                        timeout=10,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code == 200:
                        st.success("✅ 成功發送數據到自動化系統！")
                        st.json(payload)  # 可選：顯示發送的數據預覽
                    else:
                        st.warning(f"⚠️ 伺服器回應：{response.status_code} - {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ 發送失敗：{str(e)}")
                    st.info("💡 提示：目前使用的是佔位URL，請先設定正確的webhook地址")
            
        except Exception as e:
            st.error(f"❌ 處理數據時發生錯誤：{str(e)}")
            st.exception(e)

