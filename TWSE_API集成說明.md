# TWSE API 集成說明

## ✅ 答案：不會影響現有的yfinance功能

### 核心原則：**並行使用，各司其職**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 數據來源分工
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### yfinance（繼續使用）
✅ **價格數據（OHLCV）**
  - 開盤價、最高價、最低價、收盤價
  - 成交量
  - 歷史K線數據

✅ **技術指標計算的基礎數據**
  - MA5, MA20, MA60
  - ATR
  - RSI
  - 都需要yfinance的價格數據

✅ **基本資訊**
  - 股票名稱（部分支持）
  - 公司資訊（部分支持）

### TWSE API（新增，補充yfinance不足的部分）
✅ **籌碼面數據（yfinance不支持）**
  - 外資買賣超
  - 投信買賣超
  - 自營商買賣超
  - 融資融券餘額

✅ **更完整的財務數據（可選）**
  - 月營收
  - 財報數據
  - 更詳細的財務指標

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 集成方式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 方案：混合數據源（推薦）

```
價格數據：yfinance（繼續使用）
    ↓
技術指標計算：基於yfinance價格數據
    ↓
籌碼面數據：TWSE API（新增，補充）
    ↓
評分系統：結合兩者數據
```

### 代碼實現示例

```python
# 1. 使用yfinance獲取價格數據（不變）
df = self.fetch_stock_data(stock_id, years=1)  # yfinance

# 2. 使用yfinance計算技術指標（不變）
df = self.calculate_indicators(df)  # 基於yfinance數據

# 3. 新增：從TWSE API獲取籌碼面數據
institutional_data = self.get_twse_institutional_data(stock_id)  # TWSE API

# 4. 結合兩者進行評分（新增籌碼面分數）
# 價格、技術指標：基於yfinance
# 籌碼面評分：基於TWSE API
score = calculate_score(..., institutional_data=institutional_data)
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 實際影響分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ✅ 不會受影響的部分

1. **所有價格數據獲取**
   - 繼續使用yfinance
   - 不改變現有邏輯

2. **所有技術指標計算**
   - 繼續使用yfinance的價格數據
   - MA5, MA20, MA60, ATR, RSI都基於yfinance數據
   - 完全不變

3. **相對強度計算**
   - 繼續使用yfinance的價格數據
   - 不變

4. **基本面數據獲取**
   - 可以繼續使用yfinance（如果支持）
   - 也可以改用TWSE API（更完整）
   - 但不影響價格數據部分

### ✅ 新增的部分（不影響現有功能）

1. **籌碼面數據**
   - 新增TWSE API調用
   - 只在評分時使用
   - 不影響價格數據獲取

2. **機構資金評分**
   - 從固定50分改為基於真實買賣超數據
   - 這只是評分邏輯的改進
   - 不影響其他部分

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 技術實現建議
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 推薦架構

```python
class TaiwanStockScanner:
    def __init__(self, use_twse_api=False):
        self.use_twse_api = use_twse_api
        # yfinance相關的初始化（不變）
        ...
    
    def fetch_stock_data(self, stock_id, years=1):
        # 繼續使用yfinance（不變）
        return yf.Ticker(stock_id).history(period='1y')
    
    def get_institutional_data(self, stock_id):
        # 優先使用TWSE API（如果啟用）
        if self.use_twse_api:
            return self.get_twse_data(stock_id)
        else:
            # 回退到yfinance（現有邏輯）
            return self.get_yfinance_institutional_data(stock_id)
    
    def get_twse_data(self, stock_id):
        # 新增：從TWSE API獲取買賣超數據
        # 這部分是新功能，不影響現有的yfinance調用
        ...
```

### 優點

1. **向後兼容**
   - 如果不使用TWSE API，完全使用yfinance（現有行為）
   - 如果使用TWSE API，只是在評分時補充數據

2. **模塊化設計**
   - 價格數據：yfinance模塊
   - 籌碼面數據：TWSE API模塊
   - 兩者獨立，互不影響

3. **錯誤容錯**
   - 如果TWSE API失敗，回退到yfinance
   - 如果yfinance失敗，籌碼面數據依然可以獲取

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TWSE API 資訊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### API端點

1. **三大法人買賣超**
   - URL: `https://www.twse.com.tw/rwd/zh/fund/T86`
   - 提供：外資、投信、自營商買賣超

2. **融資融券餘額**
   - URL: `https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN`

### 使用方式

```python
import requests
import pandas as pd

def get_twse_institutional_data(stock_code, date=None):
    """
    從TWSE API獲取三大法人買賣超數據
    stock_code: 如 '2330'（不含.TW）
    """
    url = 'https://www.twse.com.tw/rwd/zh/fund/T86'
    params = {
        'date': date or datetime.now().strftime('%Y%m%d'),
        'selectType': 'ALLBUT0999'
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # 解析數據，找到指定股票
    # 返回：外資買賣超、投信買賣超、自營商買賣超
    ...
```

### 注意事項

1. **API限制**
   - TWSE API可能有請求頻率限制
   - 建議添加緩存機制

2. **數據格式**
   - TWSE API返回JSON格式
   - 需要解析和轉換

3. **錯誤處理**
   - API可能暫時不可用
   - 需要容錯機制

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 集成步驟（未來可選）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 步驟1：添加TWSE API模組
- 創建新文件：`twse_api.py`
- 實現數據獲取和解析

### 步驟2：修改掃描器
- 在`get_institutional_data`中添加TWSE API調用
- 保持yfinance作為後備方案

### 步驟3：更新評分邏輯
- 使用真實的買賣超數據計算機構資金評分
- 不再使用固定50分

### 步驟4：添加開關
- 在UI中添加「使用TWSE API」選項
- 讓用戶選擇是否使用

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 總結
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **不會影響現有yfinance功能**

- yfinance繼續負責所有價格數據
- 所有技術指標計算基於yfinance數據
- 完全不變

✅ **TWSE API只是補充**

- 只用於獲取yfinance不支持的数据（買賣超）
- 不替代yfinance的任何功能
- 兩者並行使用，互不影響

✅ **設計原則**

- **價格數據**：yfinance（不變）
- **技術指標**：基於yfinance價格數據（不變）
- **籌碼面數據**：TWSE API（新增，可選）
- **評分系統**：結合兩者（改進，不破壞現有邏輯）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


