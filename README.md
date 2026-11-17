# Empirical Analysis of Retail Equity Derivatives and Volatility Surfaces in India

An empirical study of options market microstructure, implied volatility dynamics, and systematic derivatives trading strategies on the National Stock Exchange of India (NSE) from 2020 through 2026.

## Overview

This research analyzes transaction-level contract data, volatility surfaces, participant flow, and systematic option trading strategies across Indian equity markets:

- **Dataset**: 450+ weekly sampled sessions, 7M+ contract records, participant positioning (Client, Proprietary, FII, DII), and equity price histories across 300+ underlying stocks.
- **Microstructure & Tenor**: Quantification of index and single-stock option notional growth, maturity distribution (0-7 DTE concentration), and volume-to-open-interest turnover ratios.
- **Volatility Dynamics**: Cross-sectional analysis of implied volatility surfaces, 25-delta skew, term structure, and the Volatility Risk Premium (VRP).
- **Excess Option Volume (EOV)**: Price impact modeling and forward-return mean reversion tests.
- **Regulatory Impact**: Event study analyzing the November 2024 SEBI contract size and expiry framework revisions.
- **Systematic Strategies**: Multi-factor volatility sorting (VolScore) delta-hedged straddles and retail-flow call spread backtests net of Indian statutory transaction costs (STT, exchange turnover fees, GST, stamp duty, slippage).

## Key Empirical Findings

### 1. Market Growth & Expiry Concentration
- Index option notional volume expanded ~12x from 2020 to peak levels.
- Over 95% of index option notional is concentrated in contracts expiring within 7 days.
- Single-stock options exhibit elevated turnover velocity with substantial client retail concentration in call open interest.

### 2. Implied Volatility Surface & Risk Premium
- High-activity retail-favored equities display a compressed Volatility Risk Premium (IV/RV ~ 1.13 vs. 1.18 in broader names).
- Volatility skew in single stocks is structurally flatter than index benchmarks.

### 3. Systematic Strategy Performance (2020–2026)

All returns are reported net of Indian exchange and statutory costs:

| Strategy | CAGR | Annualized Vol | Sharpe Ratio | Max Drawdown | Hit Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **VolScore Top 20 (Delta-Hedged Straddles)** | **21.59%** | **8.35%** | **2.40** | **-2.76%** | **85.0%** |
| **VolScore Top 20 (2x Slippage Stress)** | **18.04%** | **8.25%** | **2.06** | **-3.47%** | **81.25%** |
| **All Stocks Straddle Portfolio** | 8.09% | 5.18% | 1.53 | -4.08% | 75.0% |
| **NIFTY Delta-Hedged Straddle Benchmark** | 2.56% | 3.10% | 0.83 | -6.49% | 69.7% |
| **Contrarian Retail Call Spreads** | -0.97% | 11.62% | -0.03 | -16.40% | 43.4% |

## Repository Structure

```
├── config.py             # Global parameters, dates, and transaction cost schedules
├── run_all.py            # End-to-end pipeline execution script
├── requirements.txt      # Dependencies
├── src/
│   ├── data/             # Bhavcopy parsers and price feed downloaders
│   ├── analytics/        # Black-76 pricer, surface calculations, EOV models
│   ├── backtest/         # Delta-hedged straddle and spread simulation engines
│   └── report/           # Matplotlib figures and PDF build scripts
└── output/
    ├── figures/          # Generated analytical charts
    ├── tables/           # Output metrics, backtest statistics, results.json
    └── India_Retail_Options_Research.pdf # Compiled research paper
```

## Setup and Reproduction

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run complete pipeline
python run_all.py

# Re-run analytics and backtests from cached data
python run_all.py --skip-download
```

## License

MIT License.
