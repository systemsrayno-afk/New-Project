"""Bulk-download available history for symbols.csv using Yahoo Finance where available."""
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "historical_data"
OUT.mkdir(exist_ok=True)

def provider_symbol(symbol: str, market: str) -> str:
    s = symbol.strip().upper()
    if market == "NSE_STOCK" and not s.endswith(".NS"):
        return s + ".NS"
    return s

def main(period: str = "60d", interval: str = "5m") -> None:
    watchlist = pd.read_csv(ROOT / "symbols.csv")
    report = []
    for _, item in watchlist.iterrows():
        symbol, market = str(item["symbol"]), str(item["market"])
        ticker = provider_symbol(symbol, market)
        if market == "MCX_COMMODITY":
            report.append({"symbol": symbol, "status": "skipped", "reason": "Configure authorized MCX provider or licensed CSV."})
            print(f"SKIP {symbol}: MCX requires authorized data.")
            continue
        try:
            frame = yf.Ticker(ticker).history(period=period, interval=interval)
            if frame.empty:
                report.append({"symbol": symbol, "provider_symbol": ticker, "status": "no_data"})
                print(f"NO DATA {ticker}")
                continue
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in ticker)
            path = OUT / f"{safe}_{period}_{interval}.csv"
            frame.to_csv(path)
            report.append({"symbol": symbol, "provider_symbol": ticker, "status": "downloaded_available_data", "rows": len(frame), "first_candle": str(frame.index.min()), "last_candle": str(frame.index.max()), "file": str(path.relative_to(ROOT))})
            print(f"OK {ticker}: {len(frame)} rows -> {path}")
        except Exception as exc:
            report.append({"symbol": symbol, "provider_symbol": ticker, "status": "error", "reason": str(exc)})
            print(f"ERROR {ticker}: {exc}")
    pd.DataFrame(report).to_csv(OUT / "bulk_download_report.csv", index=False)

if __name__ == "__main__":
    main()
