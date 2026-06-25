"""
Stock Data Fetcher

Fetches stock data from Alpha Vantage, Yahoo Finance, and AkShare (A-shares) APIs.
Supports both individual stocks and batch queries.
"""

import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import re

# Try to load .env from skill directory
_SKILL_DIR = Path(__file__).parent.parent
_ENV_FILE = _SKILL_DIR / ".env"
if _ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE)
    except ImportError:
        # dotenv not available, try manual parsing
        with open(_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

# Try to import optional dependencies
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import yfinance as yf
    # Health check: query2.finance.yahoo.com may be unreachable due to local proxy
    # Fake-IP hijack (198.18.x) or upstream WAF rejecting the TLS handshake.
    # If yfinance can't fetch a known good ticker, fall back to Tencent + AkShare.
    _yf_check = yf.Ticker('AAPL').fast_info
    if _yf_check.last_price is None:
        raise RuntimeError("yfinance returned no price for AAPL — Yahoo Finance unreachable")
    HAS_YFINANCE = True
except Exception as _yf_err:
    sys.path.insert(0, str(Path.home() / '.claude/shared'))
    try:
        import yf_fallback as yf
        HAS_YFINANCE = True
        print(f"[fetch_stock_data] yfinance unavailable ({type(_yf_err).__name__}); using yf_fallback (Tencent+AkShare)", file=sys.stderr)
    except ImportError:
        HAS_YFINANCE = False

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False


def is_ashare_symbol(symbol: str) -> bool:
    """
    Detect if a symbol is a Chinese A-share stock code.

    Args:
        symbol: Stock symbol (e.g., 600519, 000858, 600519.SS)

    Returns:
        True if A-share, False otherwise
    """
    # Remove suffixes
    code = symbol.upper().replace(".SS", "").replace(".SZ", "").replace(".SH", "")
    code = code.replace("SH", "").replace("SZ", "")

    # A-share codes are 6 digits
    if not re.match(r'^\d{6}$', code):
        return False

    # Check if it starts with A-share prefixes
    # Shanghai: 6xxxxx
    # Shenzhen: 000xxx, 001xxx, 002xxx, 003xxx
    # ChiNext: 300xxx, 301xxx
    # Beijing: 8xxxxx, 4xxxxx, 9xxxxx
    first_digit = code[0]
    return first_digit in ['0', '3', '6', '8', '4', '9']


def normalize_ashare_code(symbol: str) -> str:
    """Normalize A-share symbol to a bare six-digit code."""
    code = symbol.upper().replace(".SS", "").replace(".SZ", "").replace(".SH", "").replace(".BJ", "")
    code = code.replace("SH", "").replace("SZ", "").replace("BJ", "")
    return code.zfill(6)


def ashare_market_prefix(code: str) -> str:
    """Return quote API market prefix for an A-share code."""
    if code.startswith("6"):
        return "sh"
    if code.startswith(("0", "2", "3")):
        return "sz"
    if code.startswith(("4", "8", "9")):
        return "bj"
    return "sh"


def _to_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "--"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class StockDataFetcher:
    """Fetches stock data from multiple sources."""

    def __init__(self, alpha_vantage_key: Optional[str] = None):
        """
        Initialize the fetcher with API keys.

        Args:
            alpha_vantage_key: Alpha Vantage API key. If None, reads from environment.
        """
        self.alpha_vantage_key = alpha_vantage_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.alpha_vantage_base = "https://www.alphavantage.co/query"
        self.cache = {}
        self.cache_expiry = {}

    def _is_cached(self, key: str, ttl_minutes: int = 60) -> bool:
        """Check if data is cached and still valid."""
        if key not in self.cache:
            return False
        if key in self.cache_expiry:
            if datetime.now() > self.cache_expiry[key]:
                del self.cache[key]
                del self.cache_expiry[key]
                return False
        return True

    def _set_cache(self, key: str, data: Any, ttl_minutes: int = 60):
        """Cache data with expiration."""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + timedelta(minutes=ttl_minutes)

    def get_alpha_vantage(self, function: str, symbol: str, **kwargs) -> Dict:
        """
        Fetch data from Alpha Vantage API.

        Args:
            function: API function (OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET, etc.)
            symbol: Stock ticker symbol
            **kwargs: Additional API parameters

        Returns:
            JSON response as dictionary
        """
        if not HAS_REQUESTS:
            return {"error": "requests library not installed. Run: python -m pip install requests"}

        if not self.alpha_vantage_key:
            return {"error": "Alpha Vantage API key not configured. Set ALPHA_VANTAGE_API_KEY environment variable."}

        cache_key = f"av_{function}_{symbol}"
        if self._is_cached(cache_key, ttl_minutes=1440):  # 24 hour cache
            return self.cache[cache_key]

        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.alpha_vantage_key,
            **kwargs
        }

        try:
            response = requests.get(self.alpha_vantage_base, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Check for API messages
            if "Note" in data:
                return {"error": "Alpha Vantage rate limit exceeded (5 calls/minute for free tier)"}
            if "Error Message" in data:
                return {"error": f"Invalid symbol or API error: {data['Error Message']}"}

            self._set_cache(cache_key, data)
            return data

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

    def get_yahoo_finance(self, symbol: str) -> Dict:
        """
        Fetch comprehensive stock data from Yahoo Finance using yfinance.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with stock data
        """
        if not HAS_YFINANCE:
            return {"error": "yfinance library not installed. Run: python -m pip install yfinance"}

        cache_key = f"yf_{symbol}"
        if self._is_cached(cache_key, ttl_minutes=15):  # 15 minute cache for price data
            return self.cache[cache_key]

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Handle potential missing info
            if not info:
                return {"error": f"No data found for symbol {symbol}"}

            data = {
                "symbol": symbol.upper(),
                "company_name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "day_change": info.get("currentPrice") - info.get("previousClose") if info.get("currentPrice") and info.get("previousClose") else None,
                "day_change_percent": ((info.get("currentPrice") / info.get("previousClose")) - 1) * 100 if info.get("currentPrice") and info.get("previousClose") else None,

                # Valuation metrics
                "pe_ratio": info.get("forwardPE") or info.get("trailingPE"),
                "pe_ratio_trailing": info.get("trailingPE"),
                "pe_ratio_forward": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "peg_ratio": info.get("pegRatio"),
                "ev_to_ebitda": info.get("enterpriseToEbitda"),
                "enterprise_value": info.get("enterpriseValue"),

                # Dividend info
                "dividend_yield": info.get("dividendYield"),
                "dividend_rate": info.get("dividendRate"),
                "ex_dividend_date": info.get("exDividendDate"),
                "payout_ratio": info.get("payoutRatio"),
                "last_dividend": info.get("lastDividendValue"),

                # Profitability
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "gross_margin": info.get("grossMargins"),
                "return_on_equity": info.get("returnOnEquity"),
                "return_on_assets": info.get("returnOnAssets"),
                "ebitda": info.get("ebitda"),
                "ebitda_margins": info.get("ebitdaMargins"),

                # Financial health
                "total_cash": info.get("totalCash"),
                "total_cash_per_share": info.get("totalCashPerShare"),
                "total_debt": info.get("totalDebt"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "quick_ratio": info.get("quickRatio"),

                # Cash flow
                "operating_cash_flow": info.get("operatingCashflow"),
                "free_cash_flow": info.get("freeCashflow"),
                "cash_flow_per_share": info.get("operatingCashflow") / info.get("sharesOutstanding", 1) if info.get("operatingCashflow") and info.get("sharesOutstanding") else None,

                # Income statement
                "total_revenue": info.get("totalRevenue"),
                "revenue_per_share": info.get("revenuePerShare"),
                "quarterly_revenue_growth": info.get("revenueQuarterlyGrowth"),
                "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth"),

                # Per-share metrics
                "eps_trailing": info.get("epsTrailingTwelveMonths"),
                "eps_forward": info.get("forwardEps"),
                "eps_current": info.get("currentPrice") / info.get("forwardPE", 1) if info.get("currentPrice") and info.get("forwardPE") else None,

                # Trading ranges
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "fifty_day_average": info.get("fiftyDayAverage"),
                "two_hundred_day_average": info.get("twoHundredDayAverage"),

                # Risk & volatility
                "beta": info.get("beta"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "float_shares": info.get("floatShares"),
                "held_percent_insiders": info.get("heldPercentInsiders"),
                "held_percent_institutions": info.get("heldPercentInstitutions"),
                "short_ratio": info.get("shortRatio"),
                "short_percent_of_float": info.get("shortPercentOfFloat"),

                # Analyst data
                "target_mean_price": info.get("targetMeanPrice"),
                "target_high_price": info.get("targetHighPrice"),
                "target_low_price": info.get("targetLowPrice"),
                "recommendation_key": info.get("recommendationKey"),
                "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),

                # Business info
                "business_summary": info.get("longBusinessSummary"),
                "website": info.get("website"),
                "employees": info.get("fullTimeEmployees"),
                "headquarters": f"{info.get('city', '')}, {info.get('state', '')}" if info.get("city") else None,

                # Timestamp
                "fetched_at": datetime.now().isoformat()
            }

            self._set_cache(cache_key, data)
            return data

        except Exception as e:
            return {"error": f"Yahoo Finance fetch failed: {str(e)}"}

    def get_historical_prices(self, symbol: str, period: str = "1y") -> Dict:
        """
        Fetch historical price data from Yahoo Finance.

        Args:
            symbol: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            Dictionary with historical data
        """
        if not HAS_YFINANCE:
            return {"error": "yfinance library not installed"}

        cache_key = f"yf_hist_{symbol}_{period}"
        if self._is_cached(cache_key, ttl_minutes=60):
            return self.cache[cache_key]

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return {"error": f"No historical data for {symbol}"}

            data = {
                "symbol": symbol.upper(),
                "period": period,
                "data": [],
                "fetched_at": datetime.now().isoformat()
            }

            for date, row in hist.iterrows():
                data["data"].append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 2) if not __import__("math").isnan(row["Open"]) else None,
                    "high": round(float(row["High"]), 2) if not __import__("math").isnan(row["High"]) else None,
                    "low": round(float(row["Low"]), 2) if not __import__("math").isnan(row["Low"]) else None,
                    "close": round(float(row["Close"]), 2) if not __import__("math").isnan(row["Close"]) else None,
                    "volume": int(row["Volume"]) if not __import__("math").isnan(row["Volume"]) else None,
                    "dividends": round(float(row["Dividends"]), 4) if row["Dividends"] > 0 else None,
                })

            # Calculate basic stats
            closes = [d["close"] for d in data["data"] if d["close"]]
            if closes:
                first_close = closes[0]
                last_close = closes[-1]
                data["total_return"] = round((last_close / first_close - 1) * 100, 2)
                data["volatility_daily"] = round(
                    __import__("statistics").stdev(
                        [(closes[i] / closes[i-1] - 1) for i in range(1, len(closes))]
                    ) * 100, 2
                ) if len(closes) > 1 else None

            self._set_cache(cache_key, data)
            return data

        except Exception as e:
            return {"error": f"Historical data fetch failed: {str(e)}"}

    def get_financial_statements(self, symbol: str) -> Dict:
        """
        Fetch financial statements from Yahoo Finance.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with income statement, balance sheet, and cash flow
        """
        if not HAS_YFINANCE:
            return {"error": "yfinance library not installed"}

        cache_key = f"yf_fin_{symbol}"
        if self._is_cached(cache_key, ttl_minutes=1440):
            return self.cache[cache_key]

        try:
            ticker = yf.Ticker(symbol)

            # Get annual financial statements
            income_stmt = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow

            data = {
                "symbol": symbol.upper(),
                "income_statement": {},
                "balance_sheet": {},
                "cash_flow": {},
                "fetched_at": datetime.now().isoformat()
            }

            # Process income statement
            if not income_stmt.empty:
                for col in income_stmt.columns[:3]:  # Last 3 years
                    year = col.strftime("%Y") if hasattr(col, "strftime") else str(col)
                    data["income_statement"][year] = {
                        "revenue": float(income_stmt.loc["Total Revenue"][col]) if "Total Revenue" in income_stmt.index else None,
                        "gross_profit": float(income_stmt.loc["Gross Profit"][col]) if "Gross Profit" in income_stmt.index else None,
                        "operating_income": float(income_stmt.loc["Operating Income"][col]) if "Operating Income" in income_stmt.index else None,
                        "net_income": float(income_stmt.loc["Net Income"][col]) if "Net Income" in income_stmt.index else None,
                        "eps": float(income_stmt.loc["Basic EPS"][col]) if "Basic EPS" in income_stmt.index else None,
                    }

            # Process balance sheet
            if not balance_sheet.empty:
                for col in balance_sheet.columns[:3]:
                    year = col.strftime("%Y") if hasattr(col, "strftime") else str(col)
                    data["balance_sheet"][year] = {
                        "total_assets": float(balance_sheet.loc["Total Assets"][col]) if "Total Assets" in balance_sheet.index else None,
                        "total_liab": float(balance_sheet.loc["Total Liab"][col]) if "Total Liab" in balance_sheet.index else None,
                        "total_stockholder_equity": float(balance_sheet.loc["Total Stockholder Equity"][col]) if "Total Stockholder Equity" in balance_sheet.index else None,
                        "cash": float(balance_sheet.loc["Cash And Cash Equivalents"][col]) if "Cash And Cash Equivalents" in balance_sheet.index else None,
                        "net_debt": float(balance_sheet.loc["Net Debt"][col]) if "Net Debt" in balance_sheet.index else None,
                    }

            # Process cash flow
            if not cash_flow.empty:
                for col in cash_flow.columns[:3]:
                    year = col.strftime("%Y") if hasattr(col, "strftime") else str(col)
                    data["cash_flow"][year] = {
                        "operating_cash_flow": float(cash_flow.loc["Operating Cash Flow"][col]) if "Operating Cash Flow" in cash_flow.index else None,
                        "capital_expenditure": float(cash_flow.loc["Capital Expenditure"][col]) if "Capital Expenditure" in cash_flow.index else None,
                        "free_cash_flow": (float(cash_flow.loc["Operating Cash Flow"][col]) + float(cash_flow.loc["Capital Expenditure"][col])) if "Operating Cash Flow" in cash_flow.index and "Capital Expenditure" in cash_flow.index else None,
                        "dividends_paid": float(cash_flow.loc["Cash Flow From Dividends"][col]) if "Cash Flow From Dividends" in cash_flow.index else None,
                    }

            self._set_cache(cache_key, data)
            return data

        except Exception as e:
            return {"error": f"Financial statements fetch failed: {str(e)}"}

    def get_ashare_realtime_tencent(self, symbol: str) -> Dict:
        """Fetch A-share real-time quote from Tencent's lightweight API."""
        if not HAS_REQUESTS:
            return {"error": "requests library not installed. Run: python -m pip install requests"}

        code = normalize_ashare_code(symbol)
        market = ashare_market_prefix(code)
        full_code = f"{market}{code}"
        cache_key = f"tencent_{full_code}"
        if self._is_cached(cache_key, ttl_minutes=1):
            return self.cache[cache_key]

        session = requests.Session()
        session.trust_env = False
        url = f"https://qt.gtimg.cn/q={full_code}"
        headers = {"Referer": "https://gu.qq.com/", "User-Agent": "Mozilla/5.0"}

        try:
            resp = session.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
            text = resp.content.decode("gbk", errors="ignore")
            match = re.search(r'="(.*)"', text)
            if not match:
                return {"error": f"Tencent returned no quote for {full_code}"}

            fields = match.group(1).split("~")
            if len(fields) < 45 or not fields[3]:
                return {"error": f"Tencent returned incomplete quote for {full_code}"}

            market_cap_yi = _to_float(fields[44])
            float_market_cap_yi = _to_float(fields[45]) if len(fields) > 45 else None
            amount_wan = _to_float(fields[37]) if len(fields) > 37 else None

            data = {
                "symbol": code,
                "full_code": full_code,
                "company_name": fields[1],
                "market": "CN_ASHARE",
                "current_price": _to_float(fields[3]),
                "previous_close": _to_float(fields[4]),
                "open_price": _to_float(fields[5]),
                "volume": int(_to_float(fields[6]) or 0),
                "day_change": _to_float(fields[31]) if len(fields) > 31 else None,
                "day_change_percent": _to_float(fields[32]) if len(fields) > 32 else None,
                "high_price": _to_float(fields[33]) if len(fields) > 33 else None,
                "low_price": _to_float(fields[34]) if len(fields) > 34 else None,
                "amount": amount_wan * 10000 if amount_wan is not None else None,
                "turnover_rate": _to_float(fields[38]) if len(fields) > 38 else None,
                "market_cap": market_cap_yi * 100000000 if market_cap_yi is not None else None,
                "market_cap_yi": market_cap_yi,
                "float_market_cap": float_market_cap_yi * 100000000 if float_market_cap_yi is not None else None,
                "float_market_cap_yi": float_market_cap_yi,
                "pe_ratio_ttm": _to_float(fields[52]) if len(fields) > 52 else None,
                "pb_ratio": _to_float(fields[46]) if len(fields) > 46 else None,
                "total_shares": _to_float(fields[72]) if len(fields) > 72 else None,
                "float_shares": _to_float(fields[73]) if len(fields) > 73 else None,
                "quote_time": fields[30] if len(fields) > 30 else None,
                "source": "tencent_finance",
                "fetched_at": datetime.now().isoformat(),
            }
            self._set_cache(cache_key, data, ttl_minutes=1)
            return data
        except Exception as e:
            return {"error": f"Tencent Finance fetch failed: {str(e)}"}

    def get_ashare_realtime_sina(self, symbol: str) -> Dict:
        """Fetch A-share real-time quote from Sina as a secondary lightweight API."""
        if not HAS_REQUESTS:
            return {"error": "requests library not installed. Run: python -m pip install requests"}

        code = normalize_ashare_code(symbol)
        market = ashare_market_prefix(code)
        full_code = f"{market}{code}"
        cache_key = f"sina_{full_code}"
        if self._is_cached(cache_key, ttl_minutes=1):
            return self.cache[cache_key]

        session = requests.Session()
        session.trust_env = False
        url = f"https://hq.sinajs.cn/list={full_code}"
        headers = {"Referer": "https://finance.sina.com.cn/", "User-Agent": "Mozilla/5.0"}

        try:
            resp = session.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
            text = resp.content.decode("gbk", errors="ignore")
            match = re.search(r'="(.*)"', text)
            if not match:
                return {"error": f"Sina returned no quote for {full_code}"}

            fields = match.group(1).split(",")
            if len(fields) < 32 or not fields[3]:
                return {"error": f"Sina returned incomplete quote for {full_code}"}

            current_price = _to_float(fields[3])
            previous_close = _to_float(fields[2])
            day_change = current_price - previous_close if current_price is not None and previous_close else None
            day_change_percent = day_change / previous_close * 100 if day_change is not None and previous_close else None

            data = {
                "symbol": code,
                "full_code": full_code,
                "company_name": fields[0],
                "market": "CN_ASHARE",
                "current_price": current_price,
                "previous_close": previous_close,
                "open_price": _to_float(fields[1]),
                "high_price": _to_float(fields[4]),
                "low_price": _to_float(fields[5]),
                "volume": int(_to_float(fields[8]) or 0),
                "amount": _to_float(fields[9]),
                "day_change": day_change,
                "day_change_percent": day_change_percent,
                "quote_date": fields[30],
                "quote_time": fields[31],
                "source": "sina_finance",
                "fetched_at": datetime.now().isoformat(),
            }
            self._set_cache(cache_key, data, ttl_minutes=1)
            return data
        except Exception as e:
            return {"error": f"Sina Finance fetch failed: {str(e)}"}

    def get_ashare_data(self, symbol: str) -> Dict:
        """
        Fetch Chinese A-share data using AkShare.

        Args:
            symbol: Stock code (e.g., 600519, 000858)

        Returns:
            Dictionary with A-share data in unified format
        """
        if not HAS_AKSHARE:
            return {"error": "AkShare not installed. Run: python -m pip install akshare"}

        code = normalize_ashare_code(symbol)
        market = ashare_market_prefix(code)

        cache_key = f"aks_{code}"
        if self._is_cached(cache_key, ttl_minutes=5):
            return self.cache[cache_key]

        quote_data = self.get_ashare_realtime_tencent(code)
        if "error" in quote_data:
            quote_data = self.get_ashare_realtime_sina(code)

        if "error" in quote_data:
            quote_data = {}

        try:
            # Get individual stock info
            info_df = ak.stock_individual_info_em(symbol=code)
            if info_df.empty and not quote_data:
                return {"error": f"Stock {code} not found"}

            info = {}
            if not info_df.empty:
                for _, row in info_df.iterrows():
                    info[row['item']] = row['value']

            data = {
                "symbol": code,
                "full_code": f"{market}{code}",
                "company_name": info.get("股票简称", "") or quote_data.get("company_name", ""),
                "market": "CN_ASHARE",
                "sector": info.get("行业", ""),
                "industry": info.get("行业", ""),
                "list_date": info.get("上市时间", ""),
                "market_cap": _to_float(info.get("总市值")) or quote_data.get("market_cap"),
                "current_price": _to_float(info.get("最新")) or quote_data.get("current_price"),
                "previous_close": None,
                "day_change": None,
                "day_change_percent": None,
                "pe_ratio": None,
                "pb_ratio": None,
                "dividend_yield": None,
                "total_shares": _to_float(info.get("总股本")) or quote_data.get("total_shares"),
                "float_shares": _to_float(info.get("流通股")) or quote_data.get("float_shares"),
                "fetched_at": datetime.now().isoformat()
            }

            if quote_data:
                data.update({
                    key: value for key, value in quote_data.items()
                    if value is not None and key not in ("symbol", "full_code", "market")
                })
                data["pe_ratio"] = quote_data.get("pe_ratio_ttm") or data.get("pe_ratio")
                data["pb_ratio"] = quote_data.get("pb_ratio") or data.get("pb_ratio")

            self._set_cache(cache_key, data)
            return data

        except Exception as e:
            if quote_data:
                quote_data["pe_ratio"] = quote_data.get("pe_ratio_ttm")
                quote_data["akshare_warning"] = str(e)
                self._set_cache(cache_key, quote_data)
                return quote_data
            return {"error": f"A-share fetch failed: {str(e)}"}

    def get_stock_overview(self, symbol: str, use_alpha_vantage: bool = False) -> Dict:
        """
        Get a complete stock overview from available sources.

        Args:
            symbol: Stock ticker symbol
            use_alpha_vantage: If True, try Alpha Vantage first

        Returns:
            Complete stock data dictionary
        """
        result = {"symbol": symbol.upper(), "sources": []}

        # Check if this is an A-share stock - use AkShare first
        if is_ashare_symbol(symbol):
            aks_data = self.get_ashare_data(symbol)
            if "error" not in aks_data:
                result["ashare"] = aks_data
                result["akshare"] = aks_data  # Backward-compatible key for older prompts.
                result["sources"].append(aks_data.get("source", "ashare"))
                result["market"] = "CN_ASHARE"

                # Add summary metrics for quick analysis
                if aks_data.get("current_price"):
                    result["quick_metrics"] = {
                        "current_price": aks_data["current_price"],
                        "market_cap_yi": aks_data.get("market_cap_yi") or round(aks_data.get("market_cap", 0) / 1e8, 2),
                        "pe_ratio": aks_data.get("pe_ratio"),
                        "pb_ratio": aks_data.get("pb_ratio"),
                        "day_change_percent": aks_data.get("day_change_percent"),
                    }
                return result
            else:
                result["ashare_error"] = aks_data["error"]
                return result

        # Try Alpha Vantage first if requested (for US stocks)
        if use_alpha_vantage and self.alpha_vantage_key and not is_ashare_symbol(symbol):
            av_data = self.get_alpha_vantage("OVERVIEW", symbol)
            if "error" not in av_data:
                result["alpha_vantage"] = av_data
                result["sources"].append("alpha_vantage")
                return result

        # Try Yahoo Finance as primary/fallback
        yf_data = self.get_yahoo_finance(symbol)
        if "error" not in yf_data:
            result["yahoo_finance"] = yf_data
            result["sources"].append("yahoo_finance")

            # Add summary metrics for quick analysis
            if yf_data.get("current_price") and yf_data.get("eps_trailing"):
                result["quick_metrics"] = {
                    "current_price": yf_data["current_price"],
                    "market_cap_billions": round(yf_data.get("market_cap", 0) / 1e9, 2),
                    "pe_ratio": yf_data.get("pe_ratio"),
                    "pb_ratio": yf_data.get("pb_ratio"),
                    "dividend_yield_percent": round(yf_data.get("dividend_yield", 0) * 100, 2) if yf_data.get("dividend_yield") else None,
                    "beta": yf_data.get("beta"),
                    "debt_to_equity": yf_data.get("debt_to_equity"),
                }
            return result

        # If all sources failed
        if result["sources"]:
            return result
        return {"error": f"Unable to fetch data for {symbol}. Please check the symbol and ensure API keys are configured."}


def main():
    """CLI interface for stock data fetching."""
    import json

    if len(sys.argv) < 2:
        print("Usage: python fetch_stock_data.py <SYMBOL> [--alpha-vantage] [--historical] [--financials]")
        sys.exit(1)

    symbol = sys.argv[1]
    use_av = "--alpha-vantage" in sys.argv
    show_hist = "--historical" in sys.argv
    show_fin = "--financials" in sys.argv

    fetcher = StockDataFetcher()

    print(f"Fetching data for {symbol}...\n")

    # Overview
    overview = fetcher.get_stock_overview(symbol, use_alpha_vantage=use_av)
    print("=" * 60)
    print("STOCK OVERVIEW")
    print("=" * 60)
    print(json.dumps(overview, indent=2, default=str))

    # Historical
    if show_hist:
        hist = fetcher.get_historical_prices(symbol, "1y")
        print("\n" + "=" * 60)
        print("HISTORICAL PRICES (1Y)")
        print("=" * 60)
        print(json.dumps(hist, indent=2, default=str))

    # Financials
    if show_fin:
        fin = fetcher.get_financial_statements(symbol)
        print("\n" + "=" * 60)
        print("FINANCIAL STATEMENTS")
        print("=" * 60)
        print(json.dumps(fin, indent=2, default=str))


if __name__ == "__main__":
    main()
