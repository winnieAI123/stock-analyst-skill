# Stock Evaluation Framework

This document defines the 8-dimension evaluation framework used by the stock-analyst skill for comprehensive stock analysis.

## Dimension 1: Undervalued Screener

**Objective**: Identify fundamentally sound companies trading below intrinsic value.

**Evaluation Criteria**:
- **P/E Ratio**: Below industry average, preferably < 15 for value stocks
- **PEG Ratio**: < 1.0 (growth-adjusted valuation)
- **Debt-to-Equity**: < 0.5 (conservative leverage)
- **Free Cash Flow**: Positive and growing
- **ROIC**: > 10% (efficient capital allocation)
- **Price-to-Book**: < 3.0, ideally < 1.5 for deep value

**Output Format**:
```
Business Overview:
- Core business segments
- Competitive moats
- Recent developments

Undervaluation Justification:
- P/E vs industry: X vs Y
- FCF yield: X%
- Discount to intrinsic value: X%

Key Risks:
- [Risk 1]
- [Risk 2]

Intrinsic Value Range: $XX - $XX
Current Margin of Safety: X%
```

---

## Dimension 2: Insider Trading Analysis

**Objective**: Track insider buying patterns as confidence signals.

**Evaluation Criteria**:
- **Insider Buys**: Open market purchases (not options exercises)
- **Buyer Identity**: CEO, CFO, or Board members with >10% stake
- **Purchase Amount**: > $100K for meaningful skin in the game
- **Cluster Buying**: Multiple insiders buying within 30 days
- **Historical Accuracy**: Past buys preceded positive returns

**Output Format**:
```
Recent Insider Activity:
- Buyer: [Name/Title], Purchase: X shares at $XX
- Date: [Date], Total Value: $XXK

Historical Impact:
- Previous similar buys resulted in X% avg gain
- Timeframe analyzed: [Period]

Confidence Signal:
- [Bullish/Bearish/Neutral]
- Reasoning: [Explanation]
```

---

## Dimension 3: Sentiment vs Reality

**Objective**: Identify opportunities where negative sentiment disconnects from fundamentals.

**Evaluation Criteria**:
- **Sentiment Indicators**: Social media mentions, news sentiment, analyst ratings
- **Fundamental Reality**: Revenue growth, earnings, margins, cash flow
- **Valuation Disconnect**: Stock price decline vs business stability
- **Catalyst Potential**: Upcoming events that could reset perception

**Output Format**:
```
Current Narrative:
- Negative headlines: [Summary]
- Social sentiment: [X% bearish]

Fundamental Reality:
- Revenue growth: X% (last 4 quarters)
- EPS: $X.XX vs expectations
- Operating margin: X%

Valuation Comparison:
- P/E: X (historical avg: Y)
- Price change: -X% vs fundamentals: +X%

Opportunity Assessment:
- [Compelling/Moderate/Weak]
```

---

## Dimension 4: Dividend Aristocrat

**Objective**: Evaluate sustainable dividend-paying companies.

**Evaluation Criteria**:
- **Dividend History**: 25+ years of consecutive increases (Aristocrat standard)
- **Payout Ratio**: < 65% (sustainable)
- **Dividend Yield**: 2-5% sweet spot
- **Dividend Growth Rate**: 5-10% annually
- **Total Return**: Dividend + price appreciation over 10 years

**Output Format**:
```
Dividend Profile:
- Years of increases: XX
- Current yield: X.X%
- 5-year CAGR: X.X%

Financial Health:
- Payout ratio: X%
- FCF coverage: X.x times
- Debt/FCF: X

10-Year Total Return Analysis:
- Price appreciation: X%
- Dividend reinvestment return: X%
- Combined total return: X%

Sustainability Assessment: [Strong/Moderate/Weak]
```

---

## Dimension 5: Tech Hype vs Fundamentals

**Objective**: Distinguish between sustainable tech growth and speculative hype.

**Evaluation Criteria**:
- **Revenue Growth**: Real product-driven growth vs customer acquisition spending
- **Valuation Multiples**: P/S vs growth rate, EV/Revenue
- **Profitability**: Gross margin, operating margin, path to GAAP profitability
- **Free Cash Flow**: Positive vs burning cash
- **Capital Efficiency**: ROIC, invested capital growth

**Output Format**:
```
Growth Profile:
- Revenue growth: X% YoY
- Driver: [Product innovation/Market expansion/Acquisition]
- Organic vs inorganic: X%

Valuation Analysis:
- P/S: X (industry: Y)
- EV/Revenue growth ratio: X
- Premium/discount to peers: X%

Profitability Assessment:
- Gross margin: X%
- Operating margin: X% (improving/declining)
- FCF margin: X%

Capital Efficiency:
- ROIC: X%
- Revenue per invested dollar: $X

Assessment: [Sustainable Growth/Hype/Overvalued]
```

---

## Dimension 6: Sector Rotation

**Objective**: Identify sectors positioned to outperform based on macroeconomic indicators.

**Evaluation Criteria**:
- **Economic Cycle Position**: Early/mid/late cycle, recession indicators
- **Interest Rate Environment**: Rising/falling rates impact by sector
- **Relative Strength**: Sector vs S&P 500 performance (3/6/12 months)
- **Earnings Momentum**: Sector-wide earnings estimate revisions
- **Valuation**: Sector P/E vs historical average

**Output Format**:
```
Macro Environment:
- Economic cycle phase: [Description]
- Interest rate trend: [Rising/Falling/Stable]
- Key indicators: [GDP, inflation, unemployment]

Sector Performance:
- 3M: X% vs S&P: Y%
- 6M: X% vs S&P: Y%
- 12M: X% vs S&P: Y%

Economic Logic:
- Why this sector should [outperform/underperform]
- Historical context: [Similar periods]

Top Picks in Sector:
- [Ticker]: [Rationale]
- [Ticker]: [Rationale]

Risk Factors:
- [Risk 1]
- [Risk 2]
```

---

## Dimension 7: Small Cap Growth

**Objective**: Identify high-growth small-cap companies with scalable business models.

**Evaluation Criteria**:
- **Market Cap**: $300M - $2B
- **Revenue Growth**: > 20% annually
- **Business Model**: Scalable, defensible moat
- **Execution Risk**: Management track record, capital needs
- **Liquidity**: Minimum daily trading volume > $1M

**Output Format**:
```
Company Profile:
- Market cap: $XB
- Revenue growth: X% YoY
- Primary business: [Description]

Growth Drivers:
- [Driver 1]: [Explanation]
- [Driver 2]: [Explanation]

Competitive Position:
- Moat: [Brand/Technology/Network Effect/Switching Costs]
- Market share: X% (growing/stable)

Execution Risks:
- [Risk 1]: Mitigation
- [Risk 2]: Mitigation

Financial Health:
- Cash position: $XM
- Burn rate: $XM/quarter
- Runway: X quarters

Recommendation: [Strong Buy/Buy/Hold/Sell]
```

---

## Dimension 8: Risk-Adjusted Portfolio

**Objective**: Construct optimized portfolios balancing risk and return.

**Evaluation Criteria**:
- **Asset Allocation**: Stocks, bonds, cash, alternatives by risk profile
- **Diversification**: Sector, geography, market cap distribution
- **Expected Return**: Based on historical risk premiums
- **Volatility Target**: Portfolio standard deviation
- **Rebalancing Rules**: Deviation thresholds

**Risk Profiles**:

| Profile | Stock Allocation | Bond Allocation | Expected Volatility |
|---------|------------------|-----------------|---------------------|
| Conservative | 30-40% | 60-70% | 8-10% |
| Moderate | 60-70% | 30-40% | 12-15% |
| Aggressive | 90-100% | 0-10% | 18-25% |

**Output Format**:
```
Portfolio Parameters:
- Capital: $XX,XXX
- Risk tolerance: [Conservative/Moderate/Aggressive]
- Time horizon: X years

Asset Allocation:
- US Large Cap: X% ($XX,XXX) - ETF: [VOO/IVV]
- US Small Cap: X% ($XX,XXX) - ETF: [IJR/SLY]
- International: X% ($XX,XXX) - ETF: [VEA/IXUS]
- Bonds: X% ($XX,XXX) - ETF: [BND/AGG]
- Cash/Alternatives: X% ($XX,XXX)

Individual Holdings (if applicable):
- [Ticker] - X% ($XX,XXX) - Rationale: [Explanation]
- [Ticker] - X% ($XX,XXX) - Rationale: [Explanation]

Expected Performance:
- Annual return: X%
- Volatility: X%
- Sharpe ratio: X.XX

Rebalancing Rules:
- Trigger: Allocation drift > X%
- Frequency: [Quarterly/Semi-annual]
- Tax considerations: [Note]
```

---

## Usage Guidelines

1. **Single Stock Analysis**: Apply all 8 dimensions when user asks about a specific stock
2. **Stock Screening**: Default to Dimensions 1, 2, 3 for initial filtering
3. **Portfolio Construction**: Use Dimension 8 as framework, fill with stocks from other dimensions
4. **Context Adaptation**: Prioritize dimensions based on user's stated goals and risk tolerance
