# API Guide for Stock Analyst

This guide provides configuration and usage instructions for the data sources used by the stock-analyst skill.

## AkShare (A-Share Data Source)

### Overview
AkShare is a free, open-source Python library that provides Chinese stock market data. It scrapes data from Eastmoney (东方财富), Sina Finance, and other Chinese financial websites.

### Installation
```bash
python -m pip install akshare
```

### Supported Markets

| Market | Code Pattern | Exchange | Examples |
|--------|--------------|----------|----------|
| Shanghai | 600xxx, 601xxx, 603xxx, 605xxx | SSE | 600519 (茅台), 600036 (招商银行) |
| Shenzhen | 000xxx, 001xxx, 002xxx, 003xxx | SZSE | 000858 (五粮液), 002594 (比亚迪) |
| ChiNext | 300xxx, 301xxx | ChiNext | 300750 (宁德时代), 300059 (东方财富) |
| Beijing | 8xxxxx, 4xxxxx | BSE | 832566 (梓撞科技) |

### A-Share Code Format

A-share stocks are identified by 6-digit codes:
- **600xxx**: Shanghai Main Board (沪市主板)
- **601xxx**: Shanghai Main Board
- **603xxx**: Shanghai Main Board
- **605xxx**: Shanghai Main Board
- **000xxx**: Shenzhen Main Board (深市主板)
- **001xxx**: Shenzhen Main Board
- **002xxx**: Shenzhen SME Board (中小板)
- **003xxx**: Shenzhen Main Board
- **300xxx**: ChiNext (创业板)
- **301xxx**: ChiNext
- **8xxxxx**: Beijing Stock Exchange (北交所)
- **4xxxxx**: Beijing Stock Exchange

### Python API Usage

```python
import akshare as ak

# Get individual stock info
info = ak.stock_individual_info_em(symbol="600519")
print(info)

# Get real-time quotes (all A-shares)
spot = ak.stock_zh_a_spot_em()
moutai = spot[spot['代码'] == '600519']
print(moutai[['名称', '最新价', '涨跌幅', '市盈率-动态']])

# Get historical data
hist = ak.stock_zh_a_hist(symbol="600519", period="daily", adjust="qfq")

# Get financial indicators
financial = ak.stock_financial_analysis_indicator(symbol="600519")
```

### Data Fields

| Field | Description |
|-------|-------------|
| 代码 | Stock code |
| 名称 | Stock name |
| 最新价 | Latest price |
| 涨跌幅 | Change percentage |
| 涨跌额 | Change amount |
| 今开/昨收/最高/最低 | Open/Prev Close/High/Low |
| 成交量/成交额 | Volume/Amount |
| 市盈率-动态 | P/E ratio (TTM) |
| 市净率 | P/B ratio |
| 总市值/流通市值 | Total/Float market cap |
| 换手率 | Turnover rate |

### No API Key Required
AkShare is completely free and does not require any API key. Data is scraped from public websites.

---

## Alpha Vantage

### Overview
Alpha Vantage provides free and premium APIs for stock data, including company fundamentals, historical prices, and technical indicators.

### Registration
- **Sign Up**: https://www.alphavantage.co/support/#api-key
- **Free Tier Limits**:
  - 25 requests per day
  - 5 requests per minute
  - No credit card required

### Key Endpoints

#### 1. Company Overview
```
GET https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={key}
```

**Returns**: Symbol, Name, Description, Exchange, Sector, Industry, MarketCap, PERatio, PEGRatio, BookValue, DividendPerShare, DividendYield, EPS, Beta, 52WeekHigh, 52WeekLow, 50DayMA, 200DayMA, SharesOutstanding

#### 2. Income Statement
```
GET https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ticker}&apikey={key}
```

**Returns**: Annual and quarterly reports with revenue, gross profit, EBITDA, net income, EPS

#### 3. Balance Sheet
```
GET https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol={ticker}&apikey={key}
```

**Returns**: Assets, liabilities, equity, cash, debt, retained earnings

#### 4. Cash Flow
```
GET https://www.alphavantage.co/query?function=CASH_FLOW&symbol={ticker}&apikey={key}
```

**Returns**: Operating cash flow, capital expenditures, free cash flow, dividends paid

#### 5. Earnings
```
GET https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={key}
```

**Returns**: Quarterly and annual earnings, surprise percentage

### Python Implementation

```python
import requests

def get_alpha_vantage_data(symbol, api_key):
    """Fetch company overview from Alpha Vantage."""
    base_url = "https://www.alphavantage.co/query"
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": api_key
    }
    response = requests.get(base_url, params=params)
    return response.json()
```

---

## Yahoo Finance (yfinance)

### Overview
Yahoo Finance provides comprehensive market data through the unofficial `yfinance` Python library. No API key required.

### Installation
```bash
python -m pip install yfinance
```

### Usage

#### 1. Company Info
```python
import yfinance as yf

ticker = yf.Ticker("AAPL")
info = ticker.info

# Key fields
print(info.get("forwardPE"))
print(info.get("priceToBook"))
print(info.get("returnOnEquity"))
```

#### 2. Historical Data
```python
hist = ticker.history(period="1y")
# Returns: Open, High, Low, Close, Volume, Dividends, Splits
```

#### 3. Financial Statements
```python
# Income Statement
income_stmt = ticker.financials

# Balance Sheet
balance_sheet = ticker.balance_sheet

# Cash Flow
cash_flow = ticker.cashflow
```

#### 4. Key Metrics
```python
# P/E Ratio
pe = info.get("forwardPE") or info.get("trailingPE")

# Market Cap
market_cap = info.get("marketCap")

# Beta
beta = info.get("beta")

# 52 Week Range
week_52_high = info.get("fiftyTwoWeekHigh")
week_52_low = info.get("fiftyTwoWeekLow")
```

### Full Data Fetch Function

```python
import yfinance as yf

def get_yahoo_data(symbol):
    """Fetch comprehensive stock data from Yahoo Finance."""
    ticker = yf.Ticker(symbol)

    # Get basic info
    info = ticker.info

    data = {
        "symbol": symbol,
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("forwardPE") or info.get("trailingPE"),
        "pb_ratio": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "eps": info.get("epsTrailingTwelveMonths"),
        "revenue": info.get("totalRevenue"),
        "profit_margin": info.get("profitMargins"),
        "return_on_equity": info.get("returnOnEquity"),
        "debt_to_equity": info.get("debtToEquity"),
        "free_cash_flow": info.get("freeCashflow"),
    }

    return data
```

---

## DeepSeek AI (Analysis Engine)

### Overview
DeepSeek provides advanced AI models optimized for reasoning and analysis. DeepSeek-R1 (reasoner) excels at financial analysis and investment thesis generation with visible chain-of-thought reasoning.

### Registration
- **Sign Up**: https://platform.deepseek.com/api_keys
- **Pricing**: Very affordable (~$1 per million input tokens, ~$2 per million output tokens)
- **Free Tier**: Limited free credits available for testing

### Models

| Model | Use Case | Strength |
|-------|----------|----------|
| `deepseek-chat` | General analysis | Fast, good for quick insights |
| `deepseek-reasoner` | Investment analysis | Advanced reasoning, visible thinking process |

### API Endpoints

#### Chat Completions
```
POST https://api.deepseek.com/v1/chat/completions
```

**Request Body**:
```json
{
  "model": "deepseek-reasoner",
  "messages": [
    {"role": "system", "content": "You are an expert stock analyst."},
    {"role": "user", "content": "Analyze AAPL stock..."}
  ],
  "temperature": 0.7,
  "max_tokens": 4000
}
```

**Response with Reasoning** (deepseek-reasoner):
```json
{
  "choices": [{
    "message": {
      "content": "<analysis result>\n\n<deepthink>\n<thought process>\n</deepthink>"
    }
  }]
}
```

### Python Implementation

```python
import requests
import os

class DeepSeekAnalyzer:
    API_BASE = "https://api.deepseek.com/v1"

    def __init__(self, api_key=None, model="deepseek-reasoner"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def analyze_stock(self, symbol, stock_data):
        system_prompt = "You are an expert stock analyst..."
        user_prompt = f"Analyze {symbol} with data: {stock_data}"

        response = requests.post(
            f"{self.API_BASE}/chat/completions",
            headers=self.headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
        )
        return response.json()
```

### Why DeepSeek for Stock Analysis?

1. **Visible Reasoning**: The `deepseek-reasoner` model shows its thought process, allowing you to understand HOW it reaches conclusions
2. **Cost-Effective**: Extremely low API costs compared to other reasoning models
3. **Strong Financial Knowledge**: Trained on extensive financial data and excels at investment analysis
4. **Probability Weighting**: Good at generating bull/bear cases with probability-weighted scenarios

### Environment Setup

```bash
# Windows
set DEEPSEEK_API_KEY=your_key_here

# Linux/Mac
export DEEPSEEK_API_KEY=your_key_here
```

### Usage Patterns

#### Investment Thesis Generation
Request structured output with:
- Bull case (3-5 catalysts)
- Bear case (3-5 risks)
- Base case with probability weighting
- Price targets for each scenario

#### Comparative Analysis
Compare multiple stocks with:
- Metrics comparison table
- Ranking by value/growth/dividend
- Best pick for different investor profiles

---

## Web Search Fallback

When API data is unavailable or insufficient, use web search to supplement:

### Search Queries

**For Current Price**: `{ticker} stock price today`

**For News**: `{ticker} recent news earnings`

**For Fundamentals**: `{ticker} PE ratio revenue growth`

**For Insider Trading**: `{ticker} insider trading Form 4`

### Sources to Prioritize
- Yahoo Finance (finance.yahoo.com)
- Seeking Alpha (seekingalpha.com)
- MarketWatch (marketwatch.com)
- CNBC (cnbc.com)
- SEC Edgar (sec.gov)

---

## Rate Limiting Strategy

1. **Alpha Vantage Priority**: Use first for fundamentals (limited to 5 calls/min)
2. **Yahoo Finance Fallback**: Unlimited, use for price checks
3. **Cache Results**: Store data locally to reduce API calls
4. **Batch Requests**: Group queries when possible

---

## Error Handling

```python
def safe_api_call(func, *args, **kwargs):
    """Wrapper to handle API errors gracefully."""
    try:
        return func(*args, **kwargs)
    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        return None
    except KeyError as e:
        print(f"Data parsing error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

---

## API Key Configuration

Store your API keys in environment variables:

```bash
# Windows
set ALPHA_VANTAGE_API_KEY=your_key_here
set DEEPSEEK_API_KEY=your_deepseek_key_here

# Linux/Mac
export ALPHA_VANTAGE_API_KEY=your_key_here
export DEEPSEEK_API_KEY=your_deepseek_key_here
```

Or in a `.env` file (never commit this):
```
ALPHA_VANTAGE_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
```

Load in Python:
```python
import os
from dotenv import load_dotenv

load_dotenv()
av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
ds_key = os.getenv("DEEPSEEK_API_KEY")
```
