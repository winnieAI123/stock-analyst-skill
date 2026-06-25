"""
A-Share Data Fetcher

Fetches Chinese A-share stock data using AkShare.
AkShare provides free access to Chinese stock market data from Eastmoney and other sources.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

# Try to import AkShare
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

# Try to load .env from skill directory
_SKILL_DIR = Path(__file__).parent.parent
_ENV_FILE = _SKILL_DIR / ".env"
if _ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE)
    except ImportError:
        with open(_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


class AShareFetcher:
    """Fetches Chinese A-share stock data using AkShare."""

    # Market codes for AkShare
    MARKETS = {
        "SH": "sh",  # Shanghai Stock Exchange (上交所)
        "SZ": "sz",  # Shenzhen Stock Exchange (深交所)
        "BJ": "bj",  # Beijing Stock Exchange (北交所)
    }

    # Stock code prefixes
    CODE_PREFIXES = {
        "6": "SH",      # 600xxx, 601xxx, 603xxx, 605xxx → Shanghai
        "0": "SZ",      # 000xxx, 001xxx, 002xxx, 003xxx → Shenzhen
        "3": "SZ",      # 300xxx, 301xxx → ChiNext (创业板)
        "8": "BJ",      # 8xxxxx, 4xxxxx → Beijing
        "4": "BJ",
    }

    def __init__(self):
        """Initialize the A-share fetcher."""
        self.cache = {}
        self.cache_expiry = {}

    def _is_cached(self, key: str, ttl_minutes: int = 5) -> bool:
        """Check if data is cached and still valid."""
        if key not in self.cache:
            return False
        if key in self.cache_expiry:
            if datetime.now() > self.cache_expiry[key]:
                del self.cache[key]
                del self.cache_expiry[key]
                return False
        return True

    def _set_cache(self, key: str, data: Any, ttl_minutes: int = 5):
        """Cache data with expiration."""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + timedelta(minutes=ttl_minutes)

    def _normalize_code(self, symbol: str) -> str:
        """
        Normalize stock code to 6-digit format.

        Args:
            symbol: Stock code (can be 600519, 600519.SS, sh600519, etc.)

        Returns:
            Normalized 6-digit code
        """
        # Remove suffixes and prefixes
        code = symbol.upper().replace(".SS", "").replace(".SZ", "")
        code = code.replace("SH", "").replace("SZ", "").replace("sh", "").replace("sz", "")
        return code.zfill(6)

    def _detect_market(self, code: str) -> str:
        """
        Detect market from stock code.

        Args:
            code: 6-digit stock code

        Returns:
            Market code (SH, SZ, BJ)
        """
        prefix = code[0]
        return self.CODE_PREFIXES.get(prefix, "SH")

    def get_stock_info(self, symbol: str) -> Dict:
        """
        Get basic stock information.

        Args:
            symbol: Stock code (e.g., 600519, 000858, 002594)

        Returns:
            Dictionary with stock information
        """
        if not HAS_AKSHARE:
            return {"error": "AkShare not installed. Run: python -m pip install akshare"}

        code = self._normalize_code(symbol)
        market = self._detect_market(code)

        cache_key = f"info_{code}"
        if self._is_cached(cache_key, ttl_minutes=60):
            return self.cache[cache_key]

        try:
            # Get individual stock info
            df = ak.stock_individual_info_em(symbol=code)

            if df.empty:
                return {"error": f"Stock {code} not found"}

            # Convert DataFrame to dict
            info = {}
            for _, row in df.iterrows():
                info[row['item']] = row['value']

            result = {
                "symbol": code,
                "market": market,
                "name": info.get("股票简称", "N/A"),
                "industry": info.get("行业", "N/A"),
                "list_date": info.get("上市时间", "N/A"),
                "total_shares": float(info.get("总股本", 0)) if info.get("总股本") else None,
                "float_shares": float(info.get("流通股", 0)) if info.get("流通股") else None,
                "total_market_cap": float(info.get("总市值", 0)) if info.get("总市值") else None,
                "float_market_cap": float(info.get("流通市值", 0)) if info.get("流通市值") else None,
                "latest_price": float(info.get("最新", 0)) if info.get("最新") else None,
                "fetched_at": datetime.now().isoformat()
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            return {"error": f"Failed to fetch stock info: {str(e)}"}

    def get_stock_quote(self, symbol: str) -> Dict:
        """
        Get real-time stock quote.

        Args:
            symbol: Stock code

        Returns:
            Dictionary with quote data
        """
        if not HAS_AKSHARE:
            return {"error": "AkShare not installed"}

        code = self._normalize_code(symbol)
        market = self._detect_market(code)
        full_code = f"{market}{code}"

        cache_key = f"quote_{code}"
        if self._is_cached(cache_key, ttl_minutes=1):  # 1 minute cache for quotes
            return self.cache[cache_key]

        try:
            # Get real-time quote
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == code]

            if stock_data.empty:
                return {"error": f"Stock {code} not found in real-time data"}

            row = stock_data.iloc[0]

            result = {
                "symbol": code,
                "full_code": full_code,
                "name": row.get("名称", "N/A"),
                "latest_price": float(row.get("最新价", 0)) if row.get("最新价") else None,
                "change_pct": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                "change_amount": float(row.get("涨跌额", 0)) if row.get("涨跌额") else None,
                "open_price": float(row.get("今开", 0)) if row.get("今开") else None,
                "prev_close": float(row.get("昨收", 0)) if row.get("昨收") else None,
                "high_price": float(row.get("最高", 0)) if row.get("最高") else None,
                "low_price": float(row.get("最低", 0)) if row.get("最低") else None,
                "volume": int(row.get("成交量", 0)) if row.get("成交量") else None,
                "amount": float(row.get("成交额", 0)) if row.get("成交额") else None,
                "amplitude": float(row.get("振幅", 0)) if row.get("振幅") else None,
                "total_market_cap": float(row.get("总市值", 0)) if row.get("总市值") else None,
                "circulating_market_cap": float(row.get("流通市值", 0)) if row.get("流通市值") else None,
                "pe_ratio": float(row.get("市盈率-动态", 0)) if row.get("市盈率-动态") else None,
                "pe_ratio_static": float(row.get("市盈率-静态", 0)) if row.get("市盈率-静态") else None,
                "pb_ratio": float(row.get("市净率", 0)) if row.get("市净率") else None,
                "turnover_rate": float(row.get("换手率", 0)) if row.get("换手率") else None,
                "volume_ratio": float(row.get("量比", 0)) if row.get("量比") else None,
                "fetched_at": datetime.now().isoformat()
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            # Fallback to individual info if real-time quote fails
            try:
                info = self.get_stock_info(symbol)
                if "error" not in info:
                    return {
                        **info,
                        "fallback": "Using basic info, real-time quote unavailable"
                    }
            except:
                pass
            return {"error": f"Failed to fetch quote: {str(e)}"}

    def get_historical_data(self, symbol: str, period: str = "daily", adjust: str = "qfq") -> Dict:
        """
        Get historical price data.

        Args:
            symbol: Stock code
            period: daily, weekly, monthly
            adjust: qfq (前复权), hfq (后复选), "" (不复权)

        Returns:
            Dictionary with historical data
        """
        if not HAS_AKSHARE:
            return {"error": "AkShare not installed"}

        code = self._normalize_code(symbol)
        market = self._detect_market(code)
        full_code = f"{market}{code}"

        cache_key = f"hist_{code}_{period}_{adjust}"
        if self._is_cached(cache_key, ttl_minutes=60):
            return self.cache[cache_key]

        try:
            # Get historical data
            if period == "daily":
                df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust=adjust)
            elif period == "weekly":
                df = ak.stock_zh_a_hist(symbol=code, period="weekly", adjust=adjust)
            elif period == "monthly":
                df = ak.stock_zh_a_hist(symbol=code, period="monthly", adjust=adjust)
            else:
                return {"error": f"Invalid period: {period}"}

            if df.empty:
                return {"error": f"No historical data for {code}"}

            # Convert to list of dicts
            data = []
            for _, row in df.tail(252).iterrows():  # Last 252 trading days (1 year)
                data.append({
                    "date": row["日期"].strftime("%Y-%m-%d"),
                    "open": float(row["开盘"]),
                    "high": float(row["最高"]),
                    "low": float(row["最低"]),
                    "close": float(row["收盘"]),
                    "volume": int(row["成交量"]),
                    "amount": float(row["成交额"]) if "成交额" in row else None,
                    "amplitude": float(row["振幅"]) if "振幅" in row else None,
                    "change_pct": float(row["涨跌幅"]) if "涨跌幅" in row else None,
                    "change_amount": float(row["涨跌额"]) if "涨跌额" in row else None,
                    "turnover": float(row["换手率"]) if "换手率" in row else None,
                })

            result = {
                "symbol": code,
                "full_code": full_code,
                "period": period,
                "adjust": adjust,
                "data": data,
                "fetched_at": datetime.now().isoformat()
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            return {"error": f"Failed to fetch historical data: {str(e)}"}

    def get_financial_indicators(self, symbol: str) -> Dict:
        """
        Get key financial indicators.

        Args:
            symbol: Stock code

        Returns:
            Dictionary with financial indicators
        """
        if not HAS_AKSHARE:
            return {"error": "AkShare not installed"}

        code = self._normalize_code(symbol)

        cache_key = f"financial_{code}"
        if self._is_cached(cache_key, ttl_minutes=1440):  # Daily cache
            return self.cache[cache_key]

        try:
            # Get financial indicators
            df = ak.stock_financial_analysis_indicator(symbol=code)

            if df.empty:
                return {"error": f"No financial data for {code}"}

            # Get latest data
            latest = df.iloc[-1]

            result = {
                "symbol": code,
                "date": latest.get("日期", "N/A"),
                "roe": float(latest.get("净资产收益率", 0)) if pd.notna(latest.get("净资产收益率")) else None,
                "roa": float(latest.get("总资产净利率", 0)) if pd.notna(latest.get("总资产净利率")) else None,
                "gross_margin": float(latest.get("销售毛利率", 0)) if pd.notna(latest.get("销售毛利率")) else None,
                "net_margin": float(latest.get("销售净利率", 0)) if pd.notna(latest.get("销售净利率")) else None,
                "debt_to_asset": float(latest.get("资产负债率", 0)) if pd.notna(latest.get("资产负债率")) else None,
                "current_ratio": float(latest.get("流动比率", 0)) if pd.notna(latest.get("流动比率")) else None,
                "quick_ratio": float(latest.get("速动比率", 0)) if pd.notna(latest.get("速动比率")) else None,
                "revenue_growth": float(latest.get("营业总收入同比增长", 0)) if pd.notna(latest.get("营业总收入同比增长")) else None,
                "profit_growth": float(latest.get("归属母公司股东的净利润同比增长", 0)) if pd.notna(latest.get("归属母公司股东的净利润同比增长")) else None,
                "eps": float(latest.get("基本每股收益", 0)) if pd.notna(latest.get("基本每股收益")) else None,
                "bps": float(latest.get("每股净资产", 0)) if pd.notna(latest.get("每股净资产")) else None,
                "fetched_at": datetime.now().isoformat()
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            return {"error": f"Failed to fetch financial indicators: {str(e)}"}

    def get_stock_overview(self, symbol: str) -> Dict:
        """
        Get comprehensive stock overview combining multiple data sources.

        Args:
            symbol: Stock code

        Returns:
            Complete stock data dictionary
        """
        result = {
            "symbol": self._normalize_code(symbol),
            "sources": [],
            "market": "CN_ASHARE"
        }

        # Get real-time quote
        quote = self.get_stock_quote(symbol)
        if "error" not in quote:
            result.update(quote)
            result["sources"].append("akshare_quote")

        # Get basic info
        info = self.get_stock_info(symbol)
        if "error" not in info:
            for key, value in info.items():
                if key not in result or result.get(key) is None:
                    result[key] = value
            result["sources"].append("akshare_info")

        # Get financial indicators
        financial = self.get_financial_indicators(symbol)
        if "error" not in financial:
            result["financial_indicators"] = financial
            result["sources"].append("akshare_financial")

        if result["sources"]:
            return result
        return {"error": f"Unable to fetch data for {symbol}"}


# Import pandas for null checks
try:
    import pandas as pd
except ImportError:
    pd = None


def main():
    """CLI interface for A-share data fetching."""
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fetch_ashare.py <CODE> [--info] [--quote] [--historical] [--financial]")
        print("Example: python fetch_ashare.py 600519")
        print("         python fetch_ashare.py 000858 --historical")
        sys.exit(1)

    symbol = sys.argv[1]
    show_info = "--info" in sys.argv
    show_quote = "--quote" in sys.argv
    show_hist = "--historical" in sys.argv
    show_fin = "--financial" in sys.argv

    fetcher = AShareFetcher()

    print(f"Fetching A-share data for {symbol}...\n")

    # Overview (default)
    if not (show_info or show_quote or show_hist or show_fin):
        overview = fetcher.get_stock_overview(symbol)
        print("=" * 70)
        print("A-SHARE OVERVIEW")
        print("=" * 70)
        # Remove nested financial for cleaner output
        output = overview.copy()
        if "financial_indicators" in output:
            del output["financial_indicators"]
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Specific data
        if show_info:
            info = fetcher.get_stock_info(symbol)
            print("\n" + "=" * 70)
            print("STOCK INFO")
            print("=" * 70)
            print(json.dumps(info, indent=2, ensure_ascii=False))

        if show_quote:
            quote = fetcher.get_stock_quote(symbol)
            print("\n" + "=" * 70)
            print("REAL-TIME QUOTE")
            print("=" * 70)
            print(json.dumps(quote, indent=2, ensure_ascii=False))

        if show_hist:
            hist = fetcher.get_historical_data(symbol)
            print("\n" + "=" * 70)
            print("HISTORICAL DATA (Recent 30 days)")
            print("=" * 70)
            if "error" not in hist:
                hist["data"] = hist["data"][-30:]  # Show last 30 days
            print(json.dumps(hist, indent=2, ensure_ascii=False))

        if show_fin:
            fin = fetcher.get_financial_indicators(symbol)
            print("\n" + "=" * 70)
            print("FINANCIAL INDICATORS")
            print("=" * 70)
            print(json.dumps(fin, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
