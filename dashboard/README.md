# 🔮 orderflow-alpha

**AI-Powered Polymarket Trading Engine with On-Chain Signal Intelligence**

> Built for [Orderflow 001](https://devpost.com/) — 48-hour build sprint for on-chain trading systems.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

`orderflow-alpha` is a complete trading system that combines **on-chain orderflow analysis**, **AI-driven event probability modeling**, and **quantitative strategy execution** to find and exploit mispricings on Polymarket.

### The Edge

Most Polymarket participants trade on gut feeling. This system trades on **data**:

1. **On-Chain Signals** — Tracks wallet clustering, smart money flow, and trade velocity on Polymarket's CLOB to detect informed positioning before odds move.
2. **AI Probability Engine** — Generates independent event probability estimates using news sentiment and event context, then compares against live market odds to find mispricings.
3. **Strategy Core** — Combines signals through a weighted ensemble, applies Kelly criterion sizing with risk guardrails, and generates executable trade decisions.
4. **Backtesting Engine** — Full historical backtester with realistic slippage, fees, and position tracking — producing Sharpe, max drawdown, win rate, and PnL curves.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   orderflow-alpha                     │
├──────────────┬──────────────┬────────────────────────┤
│  DATA LAYER  │ SIGNAL LAYER │    STRATEGY LAYER      │
│              │              │                        │
│ Polymarket   │ Orderflow    │ Signal Aggregation     │
│ CLOB API     │ Analyzer     │ Kelly Criterion Sizer  │
│              │              │ Risk Manager           │
│ News/Event   │ AI Prob      │ Trade Executor         │
│ Feeds        │ Estimator    │                        │
│              │              │                        │
│ On-Chain     │ Momentum     │ Portfolio Tracker      │
│ Wallet Data  │ Detector     │                        │
├──────────────┴──────────────┴────────────────────────┤
│                 BACKTEST ENGINE                       │
│  Historical replay · Slippage model · Performance    │
├──────────────────────────────────────────────────────┤
│                 LIVE DASHBOARD                        │
│  Real-time signals · PnL tracking · Risk metrics     │
└──────────────────────────────────────────────────────┘
```

---

## Performance (Backtest)

| Metric | Value |
|---|---|
| **Total Return** | Varies by market set |
| **Sharpe Ratio** | Reported per run |
| **Max Drawdown** | Reported per run |
| **Win Rate** | Reported per run |
| **Avg Trade Duration** | Reported per run |
| **Markets Traded** | Configurable |

> All performance metrics are generated from the backtesting engine against historical Polymarket data with realistic transaction costs and slippage modeling.

---

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/orderflow-alpha.git
cd orderflow-alpha

# Install
pip install -r requirements.txt

# Run backtest
python -m src.backtest.engine --config config.yaml

# Launch dashboard
python -m src.dashboard.app

# Run with live signals (paper trading mode)
python -m src.main --mode paper
```

---

## Project Structure

```
orderflow-alpha/
├── src/
│   ├── data/           # Data fetchers (Polymarket API, on-chain, news)
│   ├── signals/        # Signal generators (orderflow, AI prob, momentum)
│   ├── strategy/       # Strategy engine (aggregation, sizing, risk)
│   ├── backtest/       # Backtesting framework
│   └── utils/          # Helpers, config, logging
├── dashboard/          # React live monitoring dashboard
├── tests/              # Unit and integration tests
├── scripts/            # Data collection and utility scripts
├── config.yaml         # Strategy configuration
└── requirements.txt
```

---

## How It Works

### 1. Data Collection
The system pulls from multiple sources:
- **Polymarket CLOB API** — Live orderbook, trades, market metadata
- **On-chain data** — Wallet activity, trade sizes, position changes via Polygon
- **News/Events** — Event context for AI probability estimation

### 2. Signal Generation
Three independent signal streams:

- **Orderflow Signal**: Analyzes trade flow imbalance, large order detection, and smart wallet tracking to identify informed positioning.
- **AI Probability Signal**: Uses LLM-based analysis to generate independent probability estimates for events, then compares against market odds to find mispricings.
- **Momentum Signal**: Detects odds velocity and acceleration patterns that predict short-term price movement.

### 3. Strategy Execution
- Signals are combined via weighted ensemble
- Position sizes determined by fractional Kelly criterion (half-Kelly for risk reduction)
- Hard risk limits: max position size, max portfolio exposure, stop-loss levels
- Paper trading mode for live signal validation

### 4. Backtesting
- Event-driven backtester with realistic market simulation
- Configurable slippage model and fee structure
- Generates full performance report with equity curves

---

## Configuration

```yaml
strategy:
  kelly_fraction: 0.5          # Half-Kelly for conservative sizing
  max_position_pct: 0.15       # Max 15% of bankroll per position
  max_portfolio_exposure: 0.6  # Max 60% total exposure
  min_edge_threshold: 0.05     # Minimum 5% edge to trade
  
signals:
  orderflow_weight: 0.35
  ai_prob_weight: 0.40
  momentum_weight: 0.25

risk:
  stop_loss_pct: 0.25          # 25% stop loss per position
  max_drawdown_pct: 0.20       # Halt trading at 20% drawdown
```

---

## Tech Stack

- **Python 3.10+** — Core engine
- **NumPy / Pandas** — Data processing and analytics
- **Groq API (Llama 3.3 70B)** — Ultra-fast LLM inference for live probability estimation
- **React** — Live monitoring dashboard
- **Polymarket CLOB API** — Market data
- **asyncio** — Concurrent data collection

### Groq Integration

The AI probability signal uses Groq for sub-second LLM inference in live trading mode:

```bash
export GROQ_API_KEY="gsk_your_key_here"
python -m src.main --mode paper  # Uses Groq for live probability estimates
```

In backtest mode, a calibrated simulation model is used instead (no API calls needed).
Groq was chosen over alternatives for its inference speed — critical for real-time trading decisions.

---

## License

MIT

---

*Built in 48 hours for Orderflow 001.*
