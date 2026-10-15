"""Local-only FastAPI API. Does not place live orders."""
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from indicators import analyze_frame

ROOT = Path(__file__).resolve().parent
HISTORY_DIR = ROOT / "historical_data"
HISTORY_DIR.mkdir(exist_ok=True)
ACCOUNT_SIZE = 25000.0
RISK_PERCENT = 0.5

app = FastAPI(title="NSE Multi-Market Analyzer", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"], allow_methods=["*"], allow_headers=["*"])

ALIASES = {
    "NIFTY 50": "^NSEI", "NIFTY": "^NSEI", "BANK NIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS",
    "INFOSYS": "INFY.NS", "HDFCBANK": "HDFCBANK.NS", "ICICIBANK": "ICICIBANK.NS",
    "GOLD": "GC=F", "INTERNATIONAL GOLD": "GC=F", "CRUDE": "CL=F",
    "CRUDE OIL": "CL=F", "BRENT": "BZ=F", "NATURAL GAS": "NG=F"
}
PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "60d", "5d"}
INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1d", "1wk", "1mo"}

def resolve_symbol(symbol: str, market: str = "auto") -> str:
    raw = symbol.strip()
    if not raw:
        raise ValueError("Please enter an instrument symbol.")
    upper = raw.upper()
    if market.upper() == "MCX" or upper.startswith("MCX_"):
        raise ValueError("MCX data needs an authorized MCX data provider or licensed CSV; it is not substituted with another market.")
    if upper in ALIASES:
        return ALIASES[upper]
    if upper.startswith("^") or "=" in upper or upper.endswith(".NS") or upper.endswith(".BO"):
        return upper
    if market.upper() in {"NSE", "AUTO", "INDEX"}:
        return upper + ".NS"
    if market.upper() == "INTERNATIONAL":
        return upper
    return upper

def fetch_history(symbol: str, period: str = "5d", interval: str = "5m", market: str = "auto") -> pd.DataFrame:
    if period not in PERIODS:
        raise ValueError(f"Unsupported period: {period}")
    if interval not in INTERVALS:
        raise ValueError(f"Unsupported interval: {interval}")
    ticker = resolve_symbol(symbol, market)
    data = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
    if data is None or data.empty:
        raise ValueError(f"No data returned for {ticker}. Check symbol, provider availability, interval and period.")
    data.columns = [str(c).title() for c in data.columns]
    return data.dropna(subset=["Close"])

class DownloadRequest(BaseModel):
    symbol: str
    market: str = "auto"
    period: str = "1y"
    interval: str = "5m"

@app.get("/api/health")
def health():
    return {"status": "ok", "paper_trading_only": True, "account_size": ACCOUNT_SIZE, "risk_percent": RISK_PERCENT}

@app.get("/api/analyze")
def analyze(symbol: str = "RELIANCE", market: str = "auto", period: str = "5d", interval: str = "5m"):
    try:
        df = fetch_history(symbol, period, interval, market)
        result = analyze_frame(df, ACCOUNT_SIZE, RISK_PERCENT)
        result.update({"requested_symbol": symbol, "provider_symbol": resolve_symbol(symbol, market), "market": market, "period": period, "interval": interval})
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/download-history")
def download_history(request: DownloadRequest):
    started = datetime.now(timezone.utc).isoformat()
    try:
        df = fetch_history(request.symbol, request.period, request.interval, request.market)
        provider_symbol = resolve_symbol(request.symbol, request.market)
        safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in provider_symbol)
        path = HISTORY_DIR / f"{safe_name}_{request.period}_{request.interval}.csv"
        df.to_csv(path)
        start = str(df.index.min())
        end = str(df.index.max())
        coverage_days = max(0, (pd.Timestamp(df.index.max()) - pd.Timestamp(df.index.min())).total_seconds() / 86400)
        report_path = HISTORY_DIR / "download_report.csv"
        report_row = pd.DataFrame([{
            "requested_at_utc": started, "symbol": request.symbol, "provider_symbol": provider_symbol,
            "market": request.market, "requested_period": request.period, "interval": request.interval,
            "rows": len(df), "first_candle": start, "last_candle": end, "coverage_days": round(coverage_days, 2),
            "csv_path": str(path.relative_to(ROOT)), "status": "downloaded_available_data"
        }])
        report_row.to_csv(report_path, mode="a", header=not report_path.exists(), index=False)
        return {"status": "downloaded_available_data", "symbol": provider_symbol, "rows": len(df), "first_candle": start, "last_candle": end, "coverage_days": round(coverage_days, 2), "csv_file": str(path.relative_to(ROOT)), "report_file": str(report_path.relative_to(ROOT)), "note": "This reports available provider data; it does not guarantee full requested-period coverage. Free intraday history may be limited."}
    except Exception as exc:
        report_path = HISTORY_DIR / "download_report.csv"
        pd.DataFrame([{"requested_at_utc": started, "symbol": request.symbol, "market": request.market, "requested_period": request.period, "interval": request.interval, "status": "error", "error": str(exc)}]).to_csv(report_path, mode="a", header=not report_path.exists(), index=False)
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/api/backtest")
def backtest(symbol: str = "RELIANCE", market: str = "auto", period: str = "60d", interval: str = "5m"):
    try:
        df = fetch_history(symbol, period, interval, market)
        from indicators import add_indicators
        x = add_indicators(df).dropna(subset=["EMA9", "EMA21", "Close"])
        x["position"] = (x["EMA9"] > x["EMA21"]).astype(int)
        x["market_return"] = x["Close"].pct_change().fillna(0)
        x["strategy_return"] = x["position"].shift(1).fillna(0) * x["market_return"]
        x["equity"] = (1 + x["strategy_return"]).cumprod()
        peak = x["equity"].cummax()
        drawdown = (x["equity"] / peak) - 1
        total = float(x["equity"].iloc[-1] - 1) if len(x) else 0.0
        trades = int(x["position"].diff().abs().fillna(0).sum())
        win_rate = float((x.loc[x["strategy_return"] != 0, "strategy_return"] > 0).mean() * 100) if (x["strategy_return"] != 0).any() else 0.0
        return {"symbol": resolve_symbol(symbol, market), "period": period, "interval": interval, "candles": len(x), "total_return_pct": round(total * 100, 2), "max_drawdown_pct": round(float(drawdown.min()) * 100, 2), "win_rate_pct_on_nonzero_bars": round(win_rate, 2), "position_changes": trades, "assumptions": "Illustrative EMA9/21 long-only bar-close backtest; no brokerage, taxes, slippage, corporate actions or realistic order simulation. Not a prediction."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/candles")
def candles(symbol: str = "RELIANCE", market: str = "auto", period: str = "5d", interval: str = "5m", limit: int = 100):
    """Return real provider candles for rendering; never generates synthetic prices."""
    try:
        df = fetch_history(symbol, period, interval, market).tail(max(10, min(limit, 300)))
        from indicators import add_indicators
        df = add_indicators(df)
        rows = []
        for stamp, row in df.iterrows():
            def num(key):
                value = row.get(key)
                return None if pd.isna(value) else float(value)
            rows.append({"time": str(stamp), "open": num("Open"), "high": num("High"), "low": num("Low"), "close": num("Close"), "volume": num("Volume"), "ema9": num("EMA9"), "ema21": num("EMA21"), "vwap": num("VWAP")})
        return {"symbol": resolve_symbol(symbol, market), "candles": rows, "count": len(rows), "interval": interval, "note": "Provider-returned historical candles; may be delayed or incomplete."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
