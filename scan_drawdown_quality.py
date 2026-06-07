"""
檢視回落 -20% 品質自動選股系統

自動掃描台股上市櫃股票，不需要手動輸入股票代號。
資料來源：
- 股票清單：TWSE / TPEx 官方 OpenAPI
- 股價資料：yfinance 真實 OHLCV

如果資料不足或抓取失敗，只標示「資料不足」，不使用假資料。
"""
from __future__ import annotations

import argparse
import json
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional
from urllib.request import Request, urlopen

import pandas as pd
import requests

from data_fetcher import DataFetcher


TWSE_LISTED_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_OTC_URL = "http://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
DEFAULT_OUTPUT_FILE = "drawdown_quality_report.csv"


TPEX_INDUSTRY_NAMES = {
    "02": "食品工業",
    "03": "塑膠工業",
    "04": "紡織纖維",
    "05": "電機機械",
    "06": "電器電纜",
    "08": "玻璃陶瓷",
    "10": "鋼鐵工業",
    "11": "橡膠工業",
    "14": "建材營造",
    "15": "航運業",
    "16": "觀光餐旅",
    "17": "金融業",
    "20": "其他",
    "21": "化學工業",
    "22": "生技醫療",
    "23": "油電燃氣業",
    "24": "半導體業",
    "25": "電腦及週邊設備業",
    "26": "光電業",
    "27": "通信網路業",
    "28": "電子零組件業",
    "29": "電子通路業",
    "30": "資訊服務業",
    "31": "其他電子業",
    "32": "文化創意業",
    "33": "農業科技業",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活",
    "80": "管理股票",
}


MAINSTREAM_INDUSTRIES = [
    "AI Server",
    "PCB",
    "CCL",
    "記憶體",
    "半導體",
    "IC 設計",
    "光通訊",
    "散熱",
    "伺服器電源",
    "ASIC",
    "封裝測試",
    "低軌衛星",
]


# 人工主流產業清單。可依研究需求持續擴充，不代表投資建議。
MAINSTREAM_STOCK_THEMES: Dict[str, List[str]] = {
    "AI Server": [
        "2317", "2324", "2356", "2376", "2382", "2395", "3013", "3231",
        "3706", "6669", "8114",
    ],
    "PCB": [
        "2313", "2367", "2383", "2402", "3037", "3044", "3189", "4958",
        "5469", "6213", "6269", "6274", "8358",
    ],
    "CCL": [
        "1802", "2383", "6213", "6274", "6672", "8358",
    ],
    "記憶體": [
        "2344", "2408", "3006", "3260", "4967", "5351", "6239", "8271",
    ],
    "半導體": [
        "2303", "2330", "2337", "2401", "2408", "2454", "3034", "3105",
        "3443", "3661", "3711", "5347", "5483", "6488", "6770", "6789",
    ],
    "IC 設計": [
        "2379", "2401", "2454", "3034", "3227", "3443", "3529", "3661",
        "4966", "5274", "5278", "6415", "6531", "6643", "6789", "8081",
    ],
    "光通訊": [
        "3163", "3363", "3450", "4908", "4977", "4979", "5234", "6245",
        "6451", "6510", "6546", "6530",
    ],
    "散熱": [
        "2421", "3017", "3324", "3653", "6230", "6275", "8996",
    ],
    "伺服器電源": [
        "2308", "2317", "2327", "2352", "6412", "6409", "6781", "8110",
    ],
    "ASIC": [
        "2330", "2454", "3034", "3443", "3661", "3665", "5274", "6415",
        "6531", "6770",
    ],
    "封裝測試": [
        "2329", "2441", "2449", "3264", "3374", "3711", "6239", "6257",
        "6271", "6510", "8150",
    ],
    "低軌衛星": [
        "2314", "2321", "2345", "2419", "2455", "3019", "3045", "3491",
        "3596", "4906", "5388", "6285", "6442", "8048",
    ],
}


MAINSTREAM_CODES: Dict[str, List[str]] = {}
for theme, codes in MAINSTREAM_STOCK_THEMES.items():
    for code in codes:
        MAINSTREAM_CODES.setdefault(code, []).append(theme)


@dataclass
class StockInfo:
    code: str
    name: str
    market: str
    industry: str

    @property
    def ticker(self) -> str:
        suffix = ".TWO" if self.market == "上櫃" else ".TW"
        return f"{self.code}{suffix}"


def fetch_json(url: str, timeout: int = 20) -> List[dict]:
    headers = {"User-Agent": "stocks-drawdown-quality-scanner/1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        request = Request(url, headers=headers)
        context = ssl.create_default_context()
        with urlopen(request, timeout=timeout, context=context) as response:
            raw = response.read().decode("utf-8-sig")
        data = json.loads(raw)

    if not isinstance(data, list):
        raise ValueError(f"API 回傳格式不是清單: {url}")
    return data


def pick_value(row: dict, candidates: Iterable[str]) -> str:
    for key in candidates:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_code(code: str) -> str:
    return "".join(ch for ch in code.strip() if ch.isdigit())


def parse_stock_rows(rows: List[dict], market: str) -> List[StockInfo]:
    stocks: List[StockInfo] = []
    for row in rows:
        code = normalize_code(
            pick_value(row, ["公司代號", "股票代號", "證券代號", "SecuritiesCompanyCode", "Code", "stockNo"])
        )
        name = pick_value(row, ["公司名稱", "股票名稱", "證券名稱", "CompanyAbbreviation", "CompanyName", "Name", "公司簡稱"])
        industry = pick_value(row, ["產業別", "產業名稱", "industry", "Industry"])
        industry_code = pick_value(row, ["SecuritiesIndustryCode"])
        if not industry and industry_code:
            industry = TPEX_INDUSTRY_NAMES.get(industry_code, industry_code)

        if len(code) != 4:
            continue
        if not name:
            name = code
        stocks.append(StockInfo(code=code, name=name, market=market, industry=industry))
    return stocks


def fetch_taiwan_stock_list() -> List[StockInfo]:
    """自動抓取上市櫃股票清單。"""
    all_stocks: List[StockInfo] = []
    sources = [
        (TWSE_LISTED_URL, "上市"),
        (TPEX_OTC_URL, "上櫃"),
    ]

    for url, market in sources:
        rows = fetch_json(url)
        all_stocks.extend(parse_stock_rows(rows, market))

    unique: Dict[str, StockInfo] = {}
    for stock in all_stocks:
        unique[stock.ticker] = stock
    return sorted(unique.values(), key=lambda item: item.code)


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [str(col[0]) for col in df.columns]
    return df


def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
    df = flatten_columns(df)
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"缺少欄位: {', '.join(missing)}")

    cleaned = df[required].copy()
    cleaned = cleaned.apply(pd.to_numeric, errors="coerce")
    cleaned = cleaned.dropna(subset=["High", "Low", "Close"])
    cleaned = cleaned[cleaned["Close"] > 0]
    return cleaned.sort_index()


def pct_change(current: float, reference: float) -> Optional[float]:
    if reference is None or pd.isna(reference) or reference == 0:
        return None
    return (current - reference) / reference * 100


def format_percent(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "資料不足"
    return round(float(value), 2)


def judge_rise_risk(rise_pct: Optional[float]) -> str:
    if rise_pct is None or pd.isna(rise_pct):
        return "資料不足"
    if rise_pct < 100:
        return "正常"
    if rise_pct <= 200:
        return "偏熱"
    return "危險"


def detect_vertical_rise(recent_df: pd.DataFrame) -> str:
    """
    判斷是否出現垂直拉升。
    暫定規則：最近 3 個月任一 5 日漲幅 >= 30%，或任一 10 日漲幅 >= 50%。
    """
    if len(recent_df) < 10:
        return "資料不足"

    close = recent_df["Close"]
    five_day = close.pct_change(5).max() * 100
    ten_day = close.pct_change(10).max() * 100
    return "是" if five_day >= 30 or ten_day >= 50 else "否"


def get_mainstream_theme(stock: StockInfo) -> str:
    themes = MAINSTREAM_CODES.get(stock.code, [])
    if themes:
        return "、".join(themes)

    # 粗略補強：官方產業別若屬於半導體，直接視為主流。
    if "半導體" in stock.industry:
        return "半導體"
    return "否"


def final_rating(risk: str, vertical_rise: str, mainstream_theme: str) -> str:
    is_mainstream = mainstream_theme != "否"
    if risk == "危險" or vertical_rise == "是":
        return "C級：不買"
    if risk == "正常" and vertical_rise == "否" and is_mainstream:
        return "A級：品質較好，可買"
    return "B級：只觀察"


def insufficient_row(stock: StockInfo, reason: str) -> dict:
    mainstream_theme = get_mainstream_theme(stock)
    return {
        "股票代號": stock.ticker,
        "股票名稱": stock.name,
        "最新收盤價": "資料不足",
        "60日最高價": "資料不足",
        "距離60日高點回落百分比": "資料不足",
        "最近3個月低點": "資料不足",
        "最近3個月高點": "資料不足",
        "最近3個月從低點到高點上漲百分比": "資料不足",
        "上漲風險判斷": "資料不足",
        "是否出現垂直拉升": "資料不足",
        "是否屬於主流產業": mainstream_theme,
        "最終評級": "資料不足",
        "資料狀態": f"資料不足: {reason}",
    }


def analyze_stock(stock: StockInfo, fetcher: DataFetcher, sleep_seconds: float = 0.0) -> Optional[dict]:
    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

    try:
        df = fetcher.fetch_data(stock.ticker, start_date=start_date)
        df = clean_price_data(df)
    except Exception as exc:
        return insufficient_row(stock, str(exc))
    finally:
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    if len(df) < 90:
        return insufficient_row(stock, f"只有 {len(df)} 個交易日，少於 90 個交易日")

    last_90 = df.tail(90)
    last_60 = df.tail(60)
    latest_close = float(last_90["Close"].iloc[-1])
    high_60 = float(last_60["High"].max())
    drawdown_pct = pct_change(latest_close, high_60)

    if drawdown_pct is None or drawdown_pct > -20:
        return None

    low_3m = float(last_90["Low"].min())
    high_3m = float(last_90["High"].max())
    rise_pct = pct_change(high_3m, low_3m)
    risk = judge_rise_risk(rise_pct)
    vertical_rise = detect_vertical_rise(last_90)
    mainstream_theme = get_mainstream_theme(stock)

    return {
        "股票代號": stock.ticker,
        "股票名稱": stock.name,
        "最新收盤價": round(latest_close, 2),
        "60日最高價": round(high_60, 2),
        "距離60日高點回落百分比": format_percent(drawdown_pct),
        "最近3個月低點": round(low_3m, 2),
        "最近3個月高點": round(high_3m, 2),
        "最近3個月從低點到高點上漲百分比": format_percent(rise_pct),
        "上漲風險判斷": risk,
        "是否出現垂直拉升": vertical_rise,
        "是否屬於主流產業": mainstream_theme,
        "最終評級": final_rating(risk, vertical_rise, mainstream_theme),
        "資料狀態": "OK",
    }


def scan_drawdown_quality(
    output_file: str = DEFAULT_OUTPUT_FILE,
    limit: Optional[int] = None,
    include_insufficient: bool = False,
    sleep_seconds: float = 0.0,
) -> pd.DataFrame:
    print("【步驟1】自動抓取台股上市櫃股票清單...")
    stocks = fetch_taiwan_stock_list()
    if limit:
        stocks = stocks[:limit]
    print(f"共取得 {len(stocks)} 檔股票")

    fetcher = DataFetcher()
    rows: List[dict] = []

    print("【步驟2-4】下載最近至少90個交易日資料，檢查 -20% 回落與品質...")
    for index, stock in enumerate(stocks, start=1):
        print(f"[{index}/{len(stocks)}] 掃描 {stock.ticker} {stock.name}")
        row = analyze_stock(stock, fetcher, sleep_seconds=sleep_seconds)
        if row is None:
            continue
        if row["資料狀態"].startswith("資料不足") and not include_insufficient:
            continue
        rows.append(row)

    columns = [
        "股票代號",
        "股票名稱",
        "最新收盤價",
        "60日最高價",
        "距離60日高點回落百分比",
        "最近3個月低點",
        "最近3個月高點",
        "最近3個月從低點到高點上漲百分比",
        "上漲風險判斷",
        "是否出現垂直拉升",
        "是否屬於主流產業",
        "最終評級",
        "資料狀態",
    ]
    report = pd.DataFrame(rows, columns=columns)

    if not report.empty and "距離60日高點回落百分比" in report.columns:
        sort_key = pd.to_numeric(report["距離60日高點回落百分比"], errors="coerce")
        report = report.assign(_sort_drawdown=sort_key).sort_values(
            ["_sort_drawdown", "股票代號"], ascending=[True, True]
        )
        report = report.drop(columns=["_sort_drawdown"])

    report.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"已輸出 CSV：{output_file}")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="檢視回落 -20% 品質自動選股系統")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="CSV 輸出檔名")
    parser.add_argument("--limit", type=int, default=None, help="只掃描前 N 檔，用於測試")
    parser.add_argument(
        "--include-insufficient",
        action="store_true",
        help="把資料不足的股票也寫入報告",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="每檔股票抓取後暫停秒數，避免請求過快",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = scan_drawdown_quality(
        output_file=args.output,
        limit=args.limit,
        include_insufficient=args.include_insufficient,
        sleep_seconds=args.sleep,
    )

    print("\n【範例輸出前10筆】")
    if report.empty:
        print("沒有符合條件的股票。")
    else:
        print(report.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
