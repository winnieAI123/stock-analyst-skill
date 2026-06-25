# Stock Analyst Skill

一个用于 [Claude Code](https://claude.com/claude-code) 的股票分析 Skill：覆盖 **A股 / 美股 / 港股**，自动取数 + 用 DeepSeek 做八维度评分，输出带投资建议、目标价与风险提示的研究报告。

## 特性

- **多市场支持**：A股、美股、港股自动识别股票类型并选择数据源
- **稳健取数链路**：A股优先腾讯财经，失败自动回退新浪财经 → AkShare → 网络搜索（不会误用 Yahoo 导致"看似成功实则空数据"）
- **八维度评估框架**：估值、内部人交易、情绪 vs 基本面、股息、科技成长、板块轮动、小盘成长、风险调整组合
- **DeepSeek 深度推理**：用 `deepseek-reasoner` 生成评分与投资论点
- **标准化报告**：综合评分（满分 100）+ 八维度评分表 + 投资建议 + 12 个月目标价 + 风险提示 + 数据来源说明

## 数据源

| 股票类型 | 主数据源 | 备用（自动回退顺序） |
|---------|---------|---------------------|
| **A股** | 腾讯财经轻量行情 API | 新浪财经 API → AkShare 单股信息 → 网络搜索 |
| **美股** | Yahoo Finance | Alpha Vantage → 网络搜索 |
| **港股** | Yahoo Finance | 网络搜索 |

> ⚠️ A股不要用 Yahoo Finance 作为 fallback —— Yahoo 对 A股经常返回 404 或空字段。

## 目录结构

```
stock-analyst/
├── SKILL.md                      # Skill 主文件（执行流程规范 + 数据源经验）
├── scripts/
│   ├── fetch_stock_data.py       # 统一取数入口（A股/美股/港股）
│   ├── fetch_ashare.py           # A股行情链路
│   ├── analyze_metrics.py        # 财务指标计算
│   └── deepseek_analyzer.py      # DeepSeek 八维度分析引擎
├── references/
│   ├── api_guide.md              # 各数据源 API 用法
│   ├── evaluation_framework.md   # 八维度评估框架
│   └── prompts.md                # 分析提示词
├── .env.example                  # API Key 模板
└── .gitignore
```

## 安装与配置

1. 把整个目录放到 Claude Code 的 skills 目录下（如 `~/.claude/skills/stock-analyst`）

2. 配置 API Key：

   ```bash
   cp .env.example .env
   ```

   编辑 `.env` 填入你自己的 key：

   ```
   ALPHA_VANTAGE_API_KEY=你的_alpha_vantage_key   # https://www.alphavantage.co/support/#api-key
   DEEPSEEK_API_KEY=你的_deepseek_key             # https://platform.deepseek.com/api_keys
   ```

   > `.env` 已被 `.gitignore` 排除，不会被提交。

3. Python 依赖：`requests`、`yfinance`、`akshare`（按需）

## 命令行用法

脚本也可独立运行：

```bash
# A股取数
python scripts/fetch_stock_data.py 000534

# 美股取数（含历史 + 财务）
python scripts/fetch_stock_data.py AAPL --historical --financials

# DeepSeek 深度分析
python scripts/deepseek_analyzer.py 000534 --reasoner

# 生成投资论点
python scripts/deepseek_analyzer.py 000534 --thesis
```

## 在 Claude 里触发

直接问股票相关问题即可，例如：

- "帮我分析一下 000534"
- "AAPL 现在值得买吗？"
- "最近有什么被低估的价值股？"

## 八维度框架

1. **Undervalued Screener** —— 低估值优质公司（P/E、PEG、ROIC、FCF）
2. **Insider Trading** —— 内部人买入信号
3. **Sentiment vs Reality** —— 情绪与基本面背离机会
4. **Dividend Aristocrat** —— 可持续高股息
5. **Tech Hype vs Fundamentals** —— 区分真成长与炒作
6. **Sector Rotation** —— 宏观周期下的板块轮动
7. **Small Cap Growth** —— 高成长小盘股（$300M–$2B）
8. **Risk-Adjusted Portfolio** —— 风险调整组合构建

## 局限性

- Yahoo Finance 不支持 A股
- AkShare 接口变化频繁，需验证可用性
- 免费 API 有速率限制，A股数据可能有延迟
- 不覆盖加密货币、外汇、大宗商品

## 免责声明

本工具仅用于研究与学习，输出内容不构成投资建议。投资有风险，决策需自负。

---

**Data**: AkShare / 新浪财经 / 腾讯财经 / Yahoo Finance · **Engine**: DeepSeek-R1 · **Framework**: 8-dimension evaluation
