---
name: stock-analyst
description: "Comprehensive stock analysis and recommendation system. Use when users ask about stock analysis, screening, or recommendations. Triggers on stock screening requests, specific ticker symbols (e.g., AAPL, TSLA), or portfolio construction. Performs 8-dimension analysis including valuation, insider trading, sentiment analysis, dividend analysis, sector rotation, tech fundamentals, small-cap growth, and risk-adjusted portfolio construction."
---

# Stock Analyst Skill

Comprehensive stock analysis and recommendation system using 8-dimension evaluation framework.

---

## ⚠️ 执行流程规范（必须严格遵守）

**禁止跳步！禁止自作主张！必须按以下顺序执行：**

### Step 1: 识别股票类型
```
输入代码 → 判断类型
├── 6位数字且以 0/3/6/8/4/9 开头 → A股
├── 纯英文字母 → 美股/港股
└── 其他 → 询问用户确认
```

### Step 2: 选择数据源（根据股票类型）
| 股票类型 | 主数据源 | 备用数据源（自动尝试顺序） | 补充数据 |
|---------|---------|---------------------------|---------|
| **A股** | 腾讯财经轻量行情API | ① 新浪财经API → ② AkShare 单股信息 → ③ 网络搜索 | 东方财富/同花顺/F10 |
| **美股** | Yahoo Finance | Alpha Vantage | 网络搜索 |
| **港股** | Yahoo Finance | 网络搜索 | - |

**重要**：A股不要使用 Yahoo Finance 作为 fallback。Yahoo 对 A股经常返回 404 或空字段，容易造成“看似成功但数据全空”。当腾讯/新浪实时行情失败时，再尝试 AkShare 单股信息和网络搜索。

### Step 3: 获取数据（等待完成再继续）
```bash
# A股
python scripts/fetch_stock_data.py 000534

# 美股
python scripts/fetch_stock_data.py AAPL --historical --financials
```
**必须等待数据获取完成后，才能进入下一步！**

### Step 4: 网络搜索补充信息
- 最新财报数据
- 行业新闻
- 分析师观点

### Step 5: 调用 DeepSeek API 进行八大维度分析
```python
# 使用 deepseek-reasoner 模型（深度推理）
analyzer = DeepSeekAnalyzer(model="deepseek-reasoner")
result = analyzer.analyze_stock(symbol, stock_data)
```

### Step 6: 输出完整报告
- 八维度评分表
- 综合评分（满分100）
- 明确投资建议
- 目标价位
- 风险提示

---

## 数据源选择经验

### Yahoo Finance (yfinance)
**适用**：美股、港股
**不适用**：A股（返回404错误）

```bash
# ✅ 正确用法 - 美股
python -c "import yfinance as yf; print(yf.Ticker('AAPL').info)"

# ❌ 错误用法 - A股（会返回404）
python -c "import yfinance as yf; print(yf.Ticker('000534.SZ').info)"
```

### A股实时行情链路（优先）

**适用**：A股实时价格、市值、涨跌幅、成交额、换手、PE/PB 等。

**推荐顺序**：
1. 腾讯财经轻量行情 API：单股/批量都快，字段包含总市值/流通市值等交易判断常用数据
2. 新浪财经 API：稳定获取价格、涨跌幅、成交额，作为腾讯失败时的兜底
3. AkShare：只做单股公司信息补充；避免为了一个代码调用 `stock_zh_a_spot_em()` 全市场分页行情

```bash
python scripts/fetch_stock_data.py 600552
python scripts/fetch_stock_data.py 920438
```

**注意**：
- 北交所代码可能以 `4`、`8`、`9` 开头，必须识别为 A股。
- A股链路如果拿不到有效 `current_price`，应返回错误或 warning，不要进入 Yahoo Finance。

### AkShare
**适用**：A股
**注意事项**：
1. **API 频繁变化**：调用前必须确认接口是否存在
2. **有速率限制**：需要延时，进度条会显示 58 个请求逐个完成
3. **部分接口已废弃**：
   - ❌ `stock_financial_abstract_em` - 已移除
   - ⚠️ `stock_zh_a_spot_em()` - 全市场实时行情，慢且易断连；只在确有必要时使用
   - ✅ `stock_individual_info_em(symbol='000534')` - 个股信息

```python
# ✅ 推荐用法 - 先测试接口
import akshare as ak

# 获取个股信息（可靠）
info = ak.stock_individual_info_em(symbol='000534')
```

### 新浪财经API（A股首选备选）
**适用**：A股实时行情、历史K线数据
**特点**：稳定、无需代理、响应快速

```python
import requests

# ⚠️ 关键：禁用代理，避免连接问题
session = requests.Session()
session.trust_env = False  # 不使用系统代理

# ===== 1. 获取实时行情 =====
def get_realtime_quote(codes):
    """
    codes: 股票代码列表，如 ['sh600989', 'sh600346']
    返回: 股票名称、现价、涨跌幅等
    """
    codes_str = ','.join(codes)
    url = f'https://hq.sinajs.cn/list={codes_str}'
    headers = {'Referer': 'https://finance.sina.com.cn/'}

    r = session.get(url, timeout=10, headers=headers)
    # 解析返回数据...
    return r.text

# 示例：获取宝丰能源、恒力石化实时行情
# sh6开头 = 上海，sz0/3开头 = 深圳
data = get_realtime_quote(['sh600989', 'sh600346'])

# ===== 2. 获取历史K线数据（计算均线） =====
def get_kline_data(code, days=100):
    """
    code: 带前缀的代码如 'sh600989'
    days: 获取多少天的数据
    返回: 日期、开盘、收盘、最高、最低、成交量
    """
    url = f'https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData'
    params = {
        'symbol': code,
        'scale': 240,  # 日线
        'datalen': days
    }
    headers = {'Referer': 'https://finance.sina.com.cn/'}

    r = session.get(url, params=params, timeout=15, headers=headers)
    return r.json()  # 返回列表，每个元素是一天的数据

# 计算MA60示例
kline = get_kline_data('sh600989', 100)
close_prices = [float(d['close']) for d in kline[-60:]]
ma60 = sum(close_prices) / 60
```

**代理问题解决**：
- 新浪API需要 `session.trust_env = False` 禁用代理
- 如果设置了系统代理（如 Clash），不设置 trust_env 会报 ProxyError

### 腾讯财经API（A股首选）
**适用**：A股实时行情、总市值、流通市值、成交额、换手率、PE/PB

```python
import requests

session = requests.Session()
session.trust_env = False

def get_tencent_quote(code):
    """
    code: 不带前缀的6位代码如 '600989'
    """
    # 腾讯用 sh/sz/bj 前缀
    if code.startswith('6'):
        prefix = 'sh'
    elif code.startswith(('0', '2', '3')):
        prefix = 'sz'
    else:
        prefix = 'bj'
    full_code = f'{prefix}{code}'

    url = f'https://web.sqt.gtimg.cn/q={full_code}'
    headers = {'Referer': 'https://gu.qq.com/'}

    r = session.get(url, timeout=10, headers=headers)
    return r.text

# 使用示例
data = get_tencent_quote('600989')
```

### 网络搜索（补充数据）
**何时使用**：
- API 数据不足时
- 需要最新财报数据时
- 需要分析师观点时

**搜索关键词**：
- `{股票名} {代码} 财报 业绩 2025`
- `{股票名} 投资价值 分析 研报`
- `{股票名} 主营业务 公司简介`

---

## AkShare API 兼容性表（2026年2月验证）

| 接口 | 状态 | 用途 |
|-----|------|-----|
| `stock_zh_a_spot_em()` | ✅ 可用 | A股实时行情 |
| `stock_individual_info_em(symbol)` | ✅ 可用 | 个股基本信息 |
| `stock_financial_abstract_em` | ❌ 已移除 | 财务指标（废弃） |
| `stock_balance_sheet_by_report_em` | ⚠️ 不稳定 | 资产负债表 |
| `stock_profit_statement_by_report_em` | ⚠️ 不稳定 | 利润表 |

**经验**：AkShare 接口变化频繁，如果报错 `has no attribute`，说明接口已废弃，需要：
1. 查看最新文档：https://akshare.akfamily.xyz/
2. 或改用网络搜索获取数据

---

## 常见错误及解决方案

### 错误1: Yahoo Finance 返回 404
```
HTTP Error 404: Quote not found for symbol: 000534
```
**原因**：Yahoo Finance 不支持A股
**解决**：改用 AkShare 或网络搜索

### 错误2: AkShare 接口不存在
```
Error: module 'akshare' has no attribute 'stock_financial_abstract_em'
```
**原因**：AkShare 版本更新，接口已废弃
**解决**：
1. 查看最新文档确认接口名称
2. 或改用网络搜索获取财务数据

### 错误3: 数据获取超时
**原因**：AkShare 有速率限制，58个请求需要约4分钟
**解决**：耐心等待，不要中断

### 错误4: AkShare 代理连接失败
```
ProxyError: Unable to connect to proxy
HTTPSConnectionPool(host='82.push2.eastmoney.com'): Max retries exceeded
```
**原因**：
- 系统代理（如 Clash/verge-mihomo）规则可能拦截东方财富API
- 即使代理本身正常工作，某些API域名会被特殊处理

**解决**（自动执行，无需等待用户确认）：
1. **立即切换到新浪财经API**（见上文代码示例）
2. 如果新浪也失败，尝试腾讯财经API
3. 记住：`session.trust_env = False` 是关键

**判断优先级**：当AkShare连续失败2次，直接跳到新浪API，不要反复尝试AkShare。

### 错误5: DeepSeek API 调用失败
**检查**：
1. `.env` 文件中 `DEEPSEEK_API_KEY` 是否配置
2. API Key 是否有效
3. 网络是否通畅

---

## When to Use This Skill

Activate this skill when users request:
- **Stock screening**: "What stocks should I watch?", "Best value stocks right now", "Undervalued stocks"
- **Single stock analysis**: Any mention of a stock ticker (AAPL, TSLA, NVDA, etc.)
- **Investment recommendations**: "Is XYZ stock a good buy?", "Should I invest in..."
- **Portfolio construction**: "Build a portfolio for $50k", "Help me allocate my investments"
- **Dividend analysis**: "Best dividend stocks", "Dividend aristocrats"
- **Sector analysis**: "Which sectors are hot right now?", "Tech sector outlook"

---

## Analysis Dimensions

### Dimension 1: Undervalued Screener
**Purpose**: Find fundamentally sound companies trading below intrinsic value
**Key Metrics**: P/E Ratio, PEG Ratio, Debt-to-Equity, Free Cash Flow, ROIC
**Output**: Business overview, undervaluation justification, risks, intrinsic value range

### Dimension 2: Insider Trading Analysis
**Purpose**: Track insider buying patterns as confidence signals
**Key Metrics**: Open market purchases, Key insiders, Purchase amounts, Cluster buying
**Output**: Recent insider activity, historical impact, confidence signal

### Dimension 3: Sentiment vs Reality
**Purpose**: Identify opportunities where negative sentiment disconnects from fundamentals
**Key Metrics**: Social/news sentiment, Fundamental performance, Valuation vs historical
**Output**: Narrative assessment, reality check, opportunity rating

### Dimension 4: Dividend Aristocrat
**Purpose**: Evaluate sustainable dividend-paying companies
**Key Metrics**: Dividend history, Payout ratio, Dividend yield, FCF coverage
**Output**: Dividend profile, sustainability rating, 10-year total return analysis

### Dimension 5: Tech Hype vs Fundamentals
**Purpose**: Distinguish sustainable tech growth from speculative hype
**Key Metrics**: Revenue growth, P/S vs growth rate, Profitability metrics, Capital efficiency
**Output**: Growth profile, valuation analysis, profitability assessment

### Dimension 6: Sector Rotation
**Purpose**: Identify sectors positioned to outperform based on macroeconomic indicators
**Key Metrics**: Economic cycle position, Interest rate trends, Sector relative strength
**Output**: Macro environment, sector performance, top picks, risks

### Dimension 7: Small Cap Growth
**Purpose**: Identify high-growth small-cap companies ($300M - $2B)
**Key Metrics**: Revenue growth, Scalable business model, Moat assessment, Cash runway
**Output**: Company profile, growth drivers, competitive position, recommendation

### Dimension 8: Risk-Adjusted Portfolio
**Purpose**: Construct optimized portfolios balancing risk and return
**Risk Profiles**: Conservative / Moderate / Aggressive
**Output**: Asset allocation, holding rationale, expected performance, rebalancing rules

---

## Scripts Usage

### fetch_stock_data.py
```bash
# A股（自动使用 AkShare）
python scripts/fetch_stock_data.py 000534

# 美股
python scripts/fetch_stock_data.py AAPL --historical --financials
```

### deepseek_analyzer.py
```bash
# 使用 DeepSeek-R1 进行深度分析
python scripts/deepseek_analyzer.py 000534 --reasoner

# 生成投资论点
python scripts/deepseek_analyzer.py 000534 --thesis
```

---

## Output Format（必须包含以下内容）

1. **综合评分**：满分100
2. **八维度评分表**：每个维度1-10分 + 理由
3. **投资建议**：强烈买入/买入/持有/卖出
4. **12个月目标价**：具体价位 + 理由
5. **最大风险提示**：至少3条
6. **数据来源说明**：列出使用了哪些数据源

---

## Limitations

- Yahoo Finance 不支持 A股
- AkShare API 频繁变化，需要验证接口可用性
- 免费API有速率限制
- A股数据可能有延迟
- 加密货币、外汇、大宗商品不在覆盖范围

---

## Credits

- **Data Sources**: AkShare (A股), 新浪财经API (A股备选), 腾讯财经API (A股备选), Yahoo Finance (美股/港股), 网络搜索
- **Analysis Engine**: DeepSeek-R1
- **Analysis Framework**: 8-dimension comprehensive evaluation
- **Design Philosophy**: Risk-adjusted returns with emphasis on margin of safety
