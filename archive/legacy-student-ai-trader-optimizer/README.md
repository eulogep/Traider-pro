# 🤖 AI Trader Optimizer

> AI-assisted system for trading signal analysis and semi-automated strategy optimization.  
> *Personal project — educational purposes only. Not financial advice.*

## What it does
- Fetches historical stock/crypto data (via yfinance)
- Computes technical indicators: RSI, MACD, Bollinger Bands
- Generates buy/sell signals using rule-based + ML approach
- Backtests the strategy on 1 year of historical data
- Visualizes results with matplotlib

## Tech Stack
Python · Scikit-learn · Pandas · yfinance · Matplotlib · TA-Lib

## Setup
```bash
pip install -r requirements.txt
python main.py --ticker AAPL --period 1y
```

## Results (example — AAPL 2023)
| Metric | Value |
|---|---|
| Total signals | 47 |
| Win rate | 58% |
| Best trade | +12.4% |
| Worst trade | -6.1% |

## Project structure
```
ai-trader-optimizer/
│
├── data/
│   └── fetch_data.py          # Récupère les données via yfinance
│
├── analysis/
│   ├── indicators.py          # RSI, MACD, Bollinger Bands
│   └── signals.py             # Génère des signaux buy/sell
│
├── model/
│   ├── train.py               # Entraîne un modèle ML simple (Random Forest)
│   └── predict.py             # Prédit la tendance sur les prochaines sessions
│
├── backtest/
│   └── backtest.py            # Simule la stratégie sur données historiques
│
├── main.py                    # Point d'entrée principal
├── requirements.txt
└── README.md
```

## Disclaimer
This project is for educational purposes only.  
Do not use it for real trading decisions.
