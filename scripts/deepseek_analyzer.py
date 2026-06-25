"""
DeepSeek Stock Analyzer

Uses DeepSeek API for advanced stock analysis.
DeepSeek excels at financial reasoning and investment thesis generation.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

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


class DeepSeekAnalyzer:
    """Stock analysis using DeepSeek API."""

    # DeepSeek API endpoint
    API_BASE = "https://api.deepseek.com/v1"
    CHAT_ENDPOINT = f"{API_BASE}/chat/completions"

    # Available models
    MODELS = {
        "deepseek-chat": "DeepSeek-V3 - General purpose, fast",
        "deepseek-reasoner": "DeepSeek-R1 - Advanced reasoning for complex analysis"
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-reasoner"):
        """
        Initialize the DeepSeek analyzer.

        Args:
            api_key: DeepSeek API key. If None, reads from DEEPSEEK_API_KEY environment variable.
            model: Model to use (default: deepseek-reasoner for better analysis)
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        } if self.api_key else {}

    def _call_api(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 4000) -> Dict:
        """
        Call DeepSeek API with the given messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            API response as dictionary
        """
        if not HAS_REQUESTS:
            return {"error": "requests library not installed. Run: python -m pip install requests"}

        if not self.api_key:
            return {"error": "DeepSeek API key not configured. Set DEEPSEEK_API_KEY environment variable."}

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Adjust timeout based on model (reasoner takes longer due to chain-of-thought)
        timeout = 300 if self.model == "deepseek-reasoner" else 120

        try:
            response = requests.post(
                self.CHAT_ENDPOINT,
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            return {"error": f"API request timed out after {timeout} seconds. Try using 'deepseek-chat' for faster response."}
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}

    def analyze_stock(
        self,
        symbol: str,
        stock_data: Dict,
        dimensions: Optional[List[str]] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict:
        """
        Analyze a stock using DeepSeek.

        Args:
            symbol: Stock ticker symbol
            stock_data: Stock data dictionary (from fetch_stock_data.py)
            dimensions: List of dimensions to analyze (1-8). If None, analyze all.
            custom_prompt: Optional custom analysis prompt

        Returns:
            Analysis result with DeepSeek's response
        """
        # Default to all dimensions if not specified
        if dimensions is None:
            dimensions = ["1", "2", "3", "4", "5", "6", "7", "8"]

        # Build the system prompt
        system_prompt = self._build_system_prompt()

        # Build the user prompt with stock data
        user_prompt = self._build_analysis_prompt(symbol, stock_data, dimensions, custom_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self._call_api(messages, temperature=0.7)

        if "error" in response:
            return response

        # Extract the analysis content
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse reasoning if using deepseek-reasoner
        reasoning = None
        if self.model == "deepseek-reasoner":
            # DeepSeek-R1 returns reasoning in a specific format
            if "<think>" in content:
                parts = content.split("<think>")
                if len(parts) > 1:
                    reasoning_part = parts[1].split("</think>")[0] if "</think>" in parts[1] else parts[1]
                    reasoning = reasoning_part.strip()
                    content = parts[0].strip()

        return {
            "symbol": symbol,
            "model": self.model,
            "analysis": content,
            "reasoning": reasoning,
            "dimensions_analyzed": dimensions,
            "timestamp": datetime.now().isoformat()
        }

    def _build_system_prompt(self) -> str:
        """Build the system prompt for DeepSeek."""
        return """You are an expert stock analyst with deep knowledge of fundamental analysis, technical analysis, and market psychology. Your role is to provide thorough, well-reasoned investment analysis.

**Analysis Principles:**
1. **Objective Analysis**: Present both bullish and bearish cases fairly
2. **Data-Driven**: Base conclusions on financial metrics, not narratives
3. **Risk-Aware**: Always highlight key risks and downside scenarios
4. **Clear Recommendations**: End with specific actionability (Buy/Hold/Sell)
5. **Margin of Safety**: Emphasize the difference between price and value

**Output Format:**
```
## Executive Summary
[2-3 sentence overview]

## Dimension Analysis
[Analysis for each requested dimension]

## Key Metrics Table
| Metric | Value | Assessment |

## Risk Factors
- Risk 1
- Risk 2

## Recommendation
[Strong Buy / Buy / Hold / Sell]

## Price Target
12-month target: $XX with reasoning
```"""

    def _build_analysis_prompt(
        self,
        symbol: str,
        stock_data: Dict,
        dimensions: List[str],
        custom_prompt: Optional[str] = None
    ) -> str:
        """Build the user prompt for stock analysis."""

        # Format stock data for the prompt
        data_section = f"""
**Stock Data for {symbol}:**
- Company: {stock_data.get('company_name', 'N/A')}
- Sector: {stock_data.get('sector', 'N/A')}
- Industry: {stock_data.get('industry', 'N/A')}
- Current Price: ${stock_data.get('current_price', 'N/A')}
- Market Cap: ${stock_data.get('market_cap', 0) / 1e9:.2f}B

**Valuation Metrics:**
- P/E Ratio: {stock_data.get('pe_ratio', 'N/A')}
- P/B Ratio: {stock_data.get('pb_ratio', 'N/A')}
- PEG Ratio: {stock_data.get('peg_ratio', 'N/A')}
- EV/EBITDA: {stock_data.get('ev_to_ebitda', 'N/A')}

**Profitability:**
- Profit Margin: {stock_data.get('profit_margin', 0) * 100:.2f}%
- Operating Margin: {stock_data.get('operating_margin', 0) * 100:.2f}%
- ROE: {stock_data.get('return_on_equity', 0) * 100:.2f}%

**Financial Health:**
- Total Cash: ${stock_data.get('total_cash', 0) / 1e6:.2f}M
- Total Debt: ${stock_data.get('total_debt', 0) / 1e6:.2f}M
- Debt/Equity: {stock_data.get('debt_to_equity', 'N/A')}
- Free Cash Flow: ${stock_data.get('free_cash_flow', 0) / 1e6:.2f}M

**Dividend Info:**
- Dividend Yield: {stock_data.get('dividend_yield', 0) * 100:.2f}%
- Payout Ratio: {stock_data.get('payout_ratio', 0) * 100:.2f}%

**Trading Data:**
- 52W High: ${stock_data.get('fifty_two_week_high', 'N/A')}
- 52W Low: ${stock_data.get('fifty_two_week_low', 'N/A')}
- Beta: {stock_data.get('beta', 'N/A')}
"""

        # Dimension-specific analysis instructions
        dimension_instructions = {
            "1": "Dimension 1 - Undervalued Screener: Assess if the stock is undervalued based on P/E, PEG, FCF, and ROIC metrics.",
            "2": "Dimension 2 - Insider Trading: Note if insider trading data is available. If not, mention this limitation.",
            "3": "Dimension 3 - Sentiment vs Reality: Analyze current valuation vs historical averages and fundamentals.",
            "4": "Dimension 4 - Dividend Analysis: Evaluate dividend sustainability based on payout ratio and FCF coverage.",
            "5": "Dimension 5 - Tech/ fundamentals: Assess growth quality, margin trends, and capital efficiency.",
            "6": "Dimension 6 - Sector Rotation: Note sector context and positioning.",
            "7": "Dimension 7 - Small Cap Growth: Evaluate growth prospects and execution risks.",
            "8": "Dimension 8 - Risk Assessment: Provide risk category and portfolio fit analysis."
        }

        requested_dims = "\n".join([dimension_instructions.get(d, "") for d in dimensions if d in dimension_instructions])

        prompt = f"""Please analyze {symbol} based on the following data:

{data_section}

**Analysis Focus:**
{requested_dims}

"""

        if custom_prompt:
            prompt += f"\n**Additional Context:**\n{custom_prompt}\n"

        prompt += """

Please provide a comprehensive analysis with:
1. Executive Summary
2. Analysis for each requested dimension
3. Key metrics summary table
4. Risk factors (prioritize by severity)
5. Clear recommendation (Strong Buy/Buy/Hold/Sell)
6. 12-month price target with reasoning

Be specific with numbers and provide clear rationale for your assessment."""

        return prompt

    def compare_stocks(self, symbols: List[str], stocks_data: Dict[str, Dict]) -> Dict:
        """
        Compare multiple stocks using DeepSeek.

        Args:
            symbols: List of stock symbols
            stocks_data: Dictionary mapping symbols to their stock data

        Returns:
            Comparison analysis
        """
        comparison_prompt = "Please compare the following stocks:\n\n"

        for symbol in symbols:
            data = stocks_data.get(symbol, {})
            comparison_prompt += f"""
**{symbol}** ({data.get('company_name', 'N/A')}):
- Price: ${data.get('current_price', 'N/A')}
- P/E: {data.get('pe_ratio', 'N/A')}
- Market Cap: ${data.get('market_cap', 0) / 1e9:.1f}B
- Dividend Yield: {data.get('dividend_yield', 0) * 100:.2f}%
- ROE: {data.get('return_on_equity', 0) * 100:.2f}%
- Debt/Equity: {data.get('debt_to_equity', 'N/A')}
- Sector: {data.get('sector', 'N/A')}

"""

        comparison_prompt += """
Please provide:
1. Comparison table with key metrics
2. Ranking by value (1 = best value)
3. Ranking by growth
4. Ranking by dividend safety
5. Overall recommendation ranking
6. Best pick for different investor profiles (value, growth, income)
"""

        messages = [
            {"role": "system", "content": "You are an expert stock analyst specializing in comparative analysis."},
            {"role": "user", "content": comparison_prompt}
        ]

        response = self._call_api(messages, temperature=0.5)

        if "error" in response:
            return response

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        return {
            "symbols": symbols,
            "comparison": content,
            "model": self.model,
            "timestamp": datetime.now().isoformat()
        }

    def generate_investment_thesis(
        self,
        symbol: str,
        stock_data: Dict,
        time_horizon: str = "12 months"
    ) -> Dict:
        """
        Generate a comprehensive investment thesis using DeepSeek's reasoning capabilities.

        Args:
            symbol: Stock ticker
            stock_data: Stock data dictionary
            time_horizon: Investment time horizon

        Returns:
            Investment thesis with bull/bear cases
        """
        prompt = f"""Generate a comprehensive investment thesis for {symbol} ({stock_data.get('company_name', 'N/A')}) for a {time_horizon} time horizon.

**Current Data:**
- Price: ${stock_data.get('current_price', 'N/A')}
- P/E: {stock_data.get('pe_ratio', 'N/A')}
- Market Cap: ${stock_data.get('market_cap', 0) / 1e9:.1f}B
- Sector: {stock_data.get('sector', 'N/A')}

Please structure your thesis as:

## Investment Thesis: {symbol}

### Bull Case
[3-5 key reasons why the stock could go higher, with specific catalysts and price targets]

### Bear Case
[3-5 key risks and reasons why the thesis could fail]

### Base Case
[Most likely scenario with probability-weighted outcome]

### Key Catalysts
- [Catalyst 1 with timeframe]
- [Catalyst 2 with timeframe]

### Probability-Weighted Returns
| Scenario | Probability | Price Target | Return |
|----------|-------------|--------------|--------|
| Bull | X% | $XX | X% |
| Base | X% | $XX | X% |
| Bear | X% | $XX | X% |
| **Expected** | 100% | **$XX** | **X%** |

### Position Sizing Recommendation
Based on risk/reward, recommend position size (e.g., "2-3% of portfolio for moderate risk")"""

        messages = [
            {"role": "system", "content": "You are an expert investment analyst with deep experience in thesis generation and risk assessment."},
            {"role": "user", "content": prompt}
        ]

        response = self._call_api(messages, temperature=0.7)

        if "error" in response:
            return response

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Extract reasoning if available
        reasoning = None
        if self.model == "deepseek-reasoner" and "<think>" in content:
            parts = content.split("<think>")
            if len(parts) > 1:
                reasoning_part = parts[1].split("</think>")[0] if "</think>" in parts[1] else parts[1]
                reasoning = reasoning_part.strip()

        return {
            "symbol": symbol,
            "thesis": content,
            "reasoning": reasoning,
            "time_horizon": time_horizon,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """CLI interface for DeepSeek analysis."""
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python deepseek_analyzer.py <SYMBOL> [--model MODEL] [--thesis]")
        sys.exit(1)

    symbol = sys.argv[1]
    model = "deepseek-reasoner" if "--reasoner" in sys.argv or "-r" in sys.argv else "deepseek-chat"
    thesis_only = "--thesis" in sys.argv or "-t" in sys.argv

    # Import dependencies
    try:
        from fetch_stock_data import StockDataFetcher
    except ImportError:
        print("Error: fetch_stock_data.py must be in the same directory")
        sys.exit(1)

    # Initialize
    fetcher = StockDataFetcher()
    analyzer = DeepSeekAnalyzer(model=model)

    # Fetch data
    print(f"Fetching data for {symbol}...")
    stock_data = fetcher.get_yahoo_finance(symbol)

    if "error" in stock_data:
        print(f"Error fetching data: {stock_data['error']}")
        sys.exit(1)

    # Analyze
    if thesis_only:
        print(f"\nGenerating investment thesis using {model}...\n")
        result = analyzer.generate_investment_thesis(symbol, stock_data)
    else:
        print(f"\nAnalyzing {symbol} using {model}...\n")
        result = analyzer.analyze_stock(symbol, stock_data)

    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    # Output
    print("=" * 70)
    if thesis_only:
        print(f"INVESTMENT THESIS: {symbol}")
    else:
        print(f"DEEPSEEK ANALYSIS: {symbol}")
    print("=" * 70)
    print(result.get("thesis" if thesis_only else "analysis"))

    if result.get("reasoning"):
        print("\n" + "=" * 70)
        print("DEEPSEEK REASONING PROCESS:")
        print("=" * 70)
        print(result["reasoning"])


if __name__ == "__main__":
    main()
