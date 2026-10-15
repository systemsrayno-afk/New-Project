# NSE Multi-Market Analyzer (prototype)

A Windows-friendly browser dashboard and FastAPI backend for technical analysis, historical CSV downloads, basic historical backtesting, and paper-trading calculations. **This project never places live orders.** Signals are educational rule-based examples, not investment advice or profit guarantees.

## Features
- NSE equities and indices, selected international futures tickers via Yahoo Finance where available.
- Technical indicators: EMA 9/21, RSI 14, MACD, ATR 14, VWAP approximation, volume, and recent support/resistance.
- BUY / SELL / HOLD / WAIT rule-based signal with entry, stop, target, quantity and planned risk.
- Download available history to CSV and record each request in `historical_data/download_report.csv`.
- Simple historical backtest endpoint.
- Paper trading is a calculation/simulation only; no broker integration or live execution.

## Windows 10/11 setup
Install Python 3.11+ from https://www.python.org/downloads/ and enable “Add Python to PATH”.

Open PowerShell in this folder:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```
Open a second PowerShell window in this folder:
```powershell
python -m http.server 5500
```
Open http://127.0.0.1:5500/index.html and http://127.0.0.1:5500/history.html.

API docs: http://127.0.0.1:8000/docs

## Data limitations
- Yahoo Finance access and symbols can change and may be delayed; availability is not guaranteed.
- Free intraday history is limited (often around 60 days for 5-minute bars). A one-year 5-minute archive generally requires an authorized paid data provider.
- Yahoo Finance futures tickers (for example GC=F, CL=F, NG=F) are not the same as MCX contracts.
- MCX data is intentionally not fabricated: use an authorized provider or licensed CSV.
- Historical chart widgets, if added, may use a different data source than this backend.
- Backtests here are basic examples and do not guarantee future performance.

## Endpoints
- GET `/api/health`
- GET `/api/analyze?symbol=RELIANCE`
- POST `/api/download-history` JSON: `{"symbol":"RELIANCE","market":"NSE","period":"1y","interval":"5m"}`
- GET `/api/backtest?symbol=RELIANCE&period=60d&interval=5m`

## Risk defaults
Account ₹25,000, planned risk 0.5% (₹125) per trade. Quantity is capped by the available cash approximation and should be reviewed for lot sizes, transaction costs, slippage and gaps before use. Paper trading only.
