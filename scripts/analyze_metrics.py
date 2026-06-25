"""
Financial Metrics Analyzer

Calculates key financial ratios and metrics from stock data.
Provides analysis functions for the 8-dimension evaluation framework.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math


class MetricsAnalyzer:
    """Analyzes stock data and calculates financial metrics."""

    # Industry average P/E ratios (approximate, should be updated periodically)
    INDUSTRY_AVERAGE_PE = {
        "Technology": 28.0,
        "Healthcare": 22.0,
        "Financials": 12.0,
        "Consumer Cyclical": 20.0,
        "Consumer Defensive": 18.0,
        "Energy": 14.0,
        "Utilities": 16.0,
        "Real Estate": 35.0,
        "Industrials": 19.0,
        "Materials": 15.0,
        "Communication Services": 17.0,
    }

    # PEG benchmarks
    PEG_UNDervalued = 1.0
    PEG_FAIR_VALUE = 1.5

    # Value thresholds
    MAX_PB_VALUE = 3.0
    MAX_DEBT_TO_EQUITY_CONSERVATIVE = 0.5
    MAX_DEBT_TO_EQUITY_MODERATE = 1.0
    MIN_ROIC = 0.10  # 10%
    MIN_FCF_POSITIVE = 0

    @staticmethod
    def calculate_dcf(fcf: float, growth_rate: float, discount_rate: float, terminal_growth: float, years: int = 10) -> Dict:
        """
        Calculate Discounted Cash Flow (DCF) valuation.

        Args:
            fcf: Current free cash flow
            growth_rate: Expected growth rate for first period (as decimal, e.g., 0.10 for 10%)
            discount_rate: WACC or required return (as decimal)
            terminal_growth: Perpetual growth rate after projection period (as decimal)
            years: Number of projection years

        Returns:
            Dictionary with DCF results
        """
        try:
            pv_values = []
            projected_fcf = fcf

            # Project and discount cash flows
            for year in range(1, years + 1):
                projected_fcf *= (1 + growth_rate)
                # Gradually transition growth rate to terminal rate
                if year > 5:
                    growth_rate = growth_rate * 0.8 + terminal_growth * 0.2
                    if growth_rate < terminal_growth:
                        growth_rate = terminal_growth

                pv = projected_fcf / ((1 + discount_rate) ** year)
                pv_values.append(pv)

            # Terminal value
            terminal_fcf = projected_fcf * (1 + terminal_growth)
            terminal_value = terminal_fcf / (discount_rate - terminal_growth)
            pv_terminal = terminal_value / ((1 + discount_rate) ** years)

            enterprise_value = sum(pv_values) + pv_terminal

            return {
                "present_value_fcf": round(sum(pv_values), 2),
                "terminal_value": round(terminal_value, 2),
                "pv_terminal_value": round(pv_terminal, 2),
                "enterprise_value": round(enterprise_value, 2),
                "projected_fcfs": [round(v, 2) for v in pv_values],
            }

        except Exception as e:
            return {"error": f"DCF calculation failed: {str(e)}"}

    @staticmethod
    def calculate_intrinsic_value(
        fcf: float,
        net_debt: float,
        shares_outstanding: float,
        growth_rate: float,
        discount_rate: float = 0.10,
        terminal_growth: float = 0.025
    ) -> Dict:
        """
        Calculate intrinsic value per share using DCF.

        Args:
            fcf: Current free cash flow
            net_debt: Net debt (debt - cash)
            shares_outstanding: Number of shares outstanding
            growth_rate: Expected growth rate
            discount_rate: Discount rate (default 10%)
            terminal_growth: Terminal growth rate (default 2.5%)

        Returns:
            Dictionary with intrinsic value per share
        """
        dcf_result = MetricsAnalyzer.calculate_dcf(fcf, growth_rate, discount_rate, terminal_growth)

        if "error" in dcf_result:
            return dcf_result

        equity_value = dcf_result["enterprise_value"] - net_debt
        intrinsic_value = equity_value / shares_outstanding if shares_outstanding > 0 else 0

        return {
            **dcf_result,
            "equity_value": round(equity_value, 2),
            "intrinsic_value_per_share": round(intrinsic_value, 2),
        }

    @staticmethod
    def calculate_margin_of_safety(current_price: float, intrinsic_value: float) -> Dict:
        """
        Calculate margin of safety.

        Args:
            current_price: Current stock price
            intrinsic_value: Calculated intrinsic value

        Returns:
            Dictionary with margin of safety metrics
        """
        if intrinsic_value <= 0:
            return {"error": "Invalid intrinsic value"}

        mos = (intrinsic_value - current_price) / intrinsic_value

        return {
            "current_price": round(current_price, 2),
            "intrinsic_value": round(intrinsic_value, 2),
            "margin_of_safety_percent": round(mos * 100, 1),
            "safety_rating": "Excellent" if mos > 0.4 else "Good" if mos > 0.25 else "Fair" if mos > 0.1 else "Poor",
            "undervalued": mos > 0,
        }

    @staticmethod
    def analyze_value_metrics(stock_data: Dict) -> Dict:
        """
        Analyze value investing metrics (Dimension 1: Undervalued Screener).

        Args:
            stock_data: Stock data from fetch_stock_data.py

        Returns:
            Value analysis results
        """
        analysis = {
            "metrics": {},
            "scores": {},
            "summary": ""
        }

        # P/E Analysis
        pe = stock_data.get("pe_ratio")
        sector = stock_data.get("sector", "")
        industry_pe = MetricsAnalyzer.INDUSTRY_AVERAGE_PE.get(sector, 20.0)

        if pe:
            analysis["metrics"]["pe_ratio"] = {
                "value": round(pe, 2),
                "industry_average": industry_pe,
                "discount_to_industry": round((1 - pe / industry_pe) * 100, 1) if industry_pe else None,
                "pass": pe < industry_pe
            }

        # PEG Analysis
        peg = stock_data.get("peg_ratio")
        if peg:
            analysis["metrics"]["peg_ratio"] = {
                "value": round(peg, 2),
                "pass": peg < MetricsAnalyzer.PEG_UNDervalued
            }

        # P/B Analysis
        pb = stock_data.get("pb_ratio")
        if pb:
            analysis["metrics"]["pb_ratio"] = {
                "value": round(pb, 2),
                "pass": pb < MetricsAnalyzer.MAX_PB_VALUE
            }

        # Debt Analysis
        d_e = stock_data.get("debt_to_equity")
        if d_e is not None:
            analysis["metrics"]["debt_to_equity"] = {
                "value": round(d_e, 2),
                "conservative": d_e < MetricsAnalyzer.MAX_DEBT_TO_EQUITY_CONSERVATIVE,
                "moderate": d_e < MetricsAnalyzer.MAX_DEBT_TO_EQUITY_MODERATE,
            }

        # ROE Analysis (proxy for ROIC if ROIC not available)
        roe = stock_data.get("return_on_equity")
        if roe:
            analysis["metrics"]["return_on_equity"] = {
                "value": round(roe * 100, 2),
                "pass": roe > MetricsAnalyzer.MIN_ROIC
            }

        # FCF Analysis
        fcf = stock_data.get("free_cash_flow")
        if fcf:
            analysis["metrics"]["free_cash_flow"] = {
                "value": round(fcf / 1e6, 2),  # In millions
                "positive": fcf > 0,
                "pass": fcf > MetricsAnalyzer.MIN_FCF_POSITIVE
            }

        # Calculate overall score
        passes = sum(1 for m in analysis["metrics"].values() if isinstance(m, dict) and m.get("pass", False))
        total_value_metrics = sum(1 for m in analysis["metrics"].values() if isinstance(m, dict) and "pass" in m)
        analysis["scores"]["value_score"] = f"{passes}/{total_value_metrics}"

        # Summary
        if passes >= total_value_metrics * 0.75:
            analysis["summary"] = "Strong value candidate - most metrics indicate undervaluation."
        elif passes >= total_value_metrics * 0.5:
            analysis["summary"] = "Moderate value opportunity - mixed signals."
        else:
            analysis["summary"] = "Not a value play - metrics suggest overvaluation."

        return analysis

    @staticmethod
    def analyze_dividend_sustainability(stock_data: Dict, financials: Optional[Dict] = None) -> Dict:
        """
        Analyze dividend sustainability (Dimension 4: Dividend Aristocrat).

        Args:
            stock_data: Stock data from fetch_stock_data.py
            financials: Optional financial statements data

        Returns:
            Dividend analysis results
        """
        analysis = {
            "metrics": {},
            "sustainability_rating": "Unknown",
            "recommendation": ""
        }

        # Dividend yield
        yield_val = stock_data.get("dividend_yield")
        if yield_val:
            yield_pct = yield_val * 100
            analysis["metrics"]["dividend_yield"] = {
                "value": round(yield_pct, 2),
                "rating": "Attractive" if 2 <= yield_pct <= 5 else "Low" if yield_pct < 2 else "High (possibly risky)"
            }

        # Payout ratio
        payout = stock_data.get("payout_ratio")
        if payout:
            payout_pct = payout * 100 if payout < 1 else payout
            analysis["metrics"]["payout_ratio"] = {
                "value": round(payout_pct, 1),
                "rating": "Conservative" if payout_pct < 60 else "Moderate" if payout_pct < 75 else "High"
            }

        # FCF coverage
        fcf = stock_data.get("free_cash_flow")
        dividend_rate = stock_data.get("dividend_rate")
        if fcf and dividend_rate and stock_data.get("shares_outstanding"):
            annual_dividends = dividend_rate * stock_data["shares_outstanding"]
            coverage = fcf / annual_dividends if annual_dividends > 0 else float('inf')
            analysis["metrics"]["fcf_coverage"] = {
                "value": round(coverage, 2),
                "rating": "Strong" if coverage > 1.5 else "Adequate" if coverage > 1.2 else "Risky"
            }

        # Debt metrics
        total_debt = stock_data.get("total_debt")
        if fcf and total_debt:
            debt_to_fcf = abs(total_debt) / abs(fcf) if fcf != 0 else float('inf')
            analysis["metrics"]["debt_to_fcf"] = {
                "value": round(debt_to_fcf, 2),
                "rating": "Low" if debt_to_fcf < 3 else "Moderate" if debt_to_fcf < 5 else "High"
            }

        # Determine sustainability rating
        payout_rating = analysis["metrics"].get("payout_ratio", {}).get("rating", "")
        fcf_rating = analysis["metrics"].get("fcf_coverage", {}).get("rating", "")
        debt_rating = analysis["metrics"].get("debt_to_fcf", {}).get("rating", "")

        if payout_rating == "Conservative" and fcf_rating == "Strong":
            analysis["sustainability_rating"] = "Strong"
            analysis["recommendation"] = "Dividend appears sustainable with strong coverage."
        elif payout_rating in ["Conservative", "Moderate"] and fcf_rating in ["Strong", "Adequate"]:
            analysis["sustainability_rating"] = "Moderate"
            analysis["recommendation"] = "Dividend generally sustainable but monitor for changes."
        else:
            analysis["sustainability_rating"] = "Weak"
            analysis["recommendation"] = "Dividend may be at risk. High payout or weak cash flow coverage."

        return analysis

    @staticmethod
    def analyze_growth_metrics(stock_data: Dict, historical: Optional[Dict] = None) -> Dict:
        """
        Analyze growth metrics (Dimension 5 & 7: Tech/Small Cap Growth).

        Args:
            stock_data: Stock data from fetch_stock_data.py
            historical: Optional historical price data

        Returns:
            Growth analysis results
        """
        analysis = {
            "metrics": {},
            "growth_profile": "",
        }

        # Revenue growth
        revenue_growth = stock_data.get("quarterly_revenue_growth")
        if revenue_growth:
            growth_pct = revenue_growth * 100
            analysis["metrics"]["revenue_growth_quarterly"] = {
                "value": round(growth_pct, 2),
                "rating": "High" if growth_pct > 20 else "Moderate" if growth_pct > 10 else "Low"
            }

        # Earnings growth
        earnings_growth = stock_data.get("earnings_quarterly_growth")
        if earnings_growth:
            growth_pct = earnings_growth * 100
            analysis["metrics"]["earnings_growth_quarterly"] = {
                "value": round(growth_pct, 2),
                "rating": "High" if growth_pct > 15 else "Moderate" if growth_pct > 5 else "Low/Negative"
            }

        # Price performance (from historical data)
        if historical and "data" in historical and len(historical["data"]) > 1:
            first_price = historical["data"][0]["close"]
            last_price = historical["data"][-1]["close"]
            price_return = (last_price / first_price - 1) * 100
            analysis["metrics"]["price_return_period"] = {
                "value": round(price_return, 2),
                "period": historical.get("period", "unknown")
            }

        # Margins trend
        margins = {
            "gross_margin": stock_data.get("gross_margin"),
            "operating_margin": stock_data.get("operating_margin"),
            "profit_margin": stock_data.get("profit_margin"),
        }

        for name, value in margins.items():
            if value:
                analysis["metrics"][name] = {
                    "value": round(value * 100, 2)
                }

        # Growth profile assessment
        rev_growth = analysis["metrics"].get("revenue_growth_quarterly", {}).get("value", 0)
        if rev_growth > 20:
            analysis["growth_profile"] = "High Growth"
        elif rev_growth > 10:
            analysis["growth_profile"] = "Moderate Growth"
        else:
            analysis["growth_profile"] = "Low Growth / Mature"

        return analysis

    @staticmethod
    def calculate_risk_metrics(stock_data: Dict, historical: Optional[Dict] = None) -> Dict:
        """
        Calculate risk metrics for portfolio construction (Dimension 8).

        Args:
            stock_data: Stock data from fetch_stock_data.py
            historical: Optional historical price data

        Returns:
            Risk analysis results
        """
        analysis = {
            "metrics": {},
            "risk_category": "",
        }

        # Beta (systematic risk)
        beta = stock_data.get("beta")
        if beta:
            analysis["metrics"]["beta"] = {
                "value": round(beta, 2),
                "interpretation": "High volatility" if beta > 1.3 else "Moderate volatility" if beta > 0.8 else "Low volatility"
            }

        # Market cap (size risk)
        market_cap = stock_data.get("market_cap")
        if market_cap:
            if market_cap > 10e9:  # > $10B
                size = "Large Cap"
                risk_level = "Lower"
            elif market_cap > 2e9:  # > $2B
                size = "Mid Cap"
                risk_level = "Moderate"
            else:
                size = "Small Cap"
                risk_level = "Higher"

            analysis["metrics"]["market_cap"] = {
                "value": round(market_cap / 1e9, 2),
                "category": size,
                "risk_level": risk_level
            }

        # Short interest (sentiment risk)
        short_pct = stock_data.get("short_percent_of_float")
        if short_pct:
            analysis["metrics"]["short_interest"] = {
                "value": round(short_pct * 100, 2),
                "level": "High" if short_pct > 0.10 else "Moderate" if short_pct > 0.05 else "Low"
            }

        # Financial leverage
        d_e = stock_data.get("debt_to_equity")
        if d_e is not None:
            analysis["metrics"]["financial_leverage"] = {
                "value": round(d_e, 2),
                "level": "High" if d_e > 2 else "Moderate" if d_e > 1 else "Low"
            }

        # Calculate overall risk category
        beta_val = analysis["metrics"].get("beta", {}).get("value", 1)
        leverage = analysis["metrics"].get("financial_leverage", {}).get("level", "")

        if beta_val < 0.8 and leverage == "Low":
            analysis["risk_category"] = "Conservative"
        elif beta_val < 1.2 and leverage in ["Low", "Moderate"]:
            analysis["risk_category"] = "Moderate"
        else:
            analysis["risk_category"] = "Aggressive"

        return analysis

    @staticmethod
    def generate_full_analysis(
        stock_data: Dict,
        historical: Optional[Dict] = None,
        financials: Optional[Dict] = None
    ) -> Dict:
        """
        Generate comprehensive analysis combining all dimensions.

        Args:
            stock_data: Stock data from fetch_stock_data.py
            historical: Optional historical price data
            financials: Optional financial statements data

        Returns:
            Comprehensive analysis dictionary
        """
        return {
            "symbol": stock_data.get("symbol"),
            "company_name": stock_data.get("company_name"),
            "analysis_date": datetime.now().isoformat(),
            "value_analysis": MetricsAnalyzer.analyze_value_metrics(stock_data),
            "dividend_analysis": MetricsAnalyzer.analyze_dividend_sustainability(stock_data, financials),
            "growth_analysis": MetricsAnalyzer.analyze_growth_metrics(stock_data, historical),
            "risk_analysis": MetricsAnalyzer.calculate_risk_metrics(stock_data, historical),
        }


def main():
    """CLI interface for metrics analysis."""
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_metrics.py <SYMBOL> [--full]")
        sys.exit(1)

    symbol = sys.argv[1]
    full = "--full" in sys.argv

    # Import fetcher
    try:
        from fetch_stock_data import StockDataFetcher
    except ImportError:
        print("Error: fetch_stock_data.py must be in the same directory")
        sys.exit(1)

    fetcher = StockDataFetcher()

    # Fetch data
    print(f"Fetching data for {symbol}...\n")
    stock_data = fetcher.get_yahoo_finance(symbol)

    if "error" in stock_data:
        print(f"Error: {stock_data['error']}")
        sys.exit(1)

    historical = fetcher.get_historical_prices(symbol, "1y") if full else None

    # Analyze
    analyzer = MetricsAnalyzer()
    analysis = analyzer.generate_full_analysis(stock_data, historical)

    print("=" * 60)
    print(f"ANALYSIS FOR {symbol}")
    print("=" * 60)
    print(json.dumps(analysis, indent=2, default=str))


if __name__ == "__main__":
    main()
