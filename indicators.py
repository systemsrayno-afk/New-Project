"""Simple, transparent technical indicators for educational analysis."""
import numpy as np
import pandas as pd


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    df = frame.copy()
    df.columns = [str(c).title() for c in df.columns]
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in df:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    close, high, low = df["Close"], df["High"], df["Low"]
    df["EMA9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA21"] = close.ewm(span=21, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACDSignal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    previous_close = close.shift(1)
    tr = pd.concat([(high-low), (high-previous_close).abs(), (low-previous_close).abs()], axis=1).max(axis=1)
    df["ATR14"] = tr.rolling(14, min_periods=1).mean()
    typical = (high + low + close) / 3
    volume = df["Volume"].fillna(0)
    cumulative_volume = volume.cumsum().replace(0, np.nan)
    df["VWAP"] = (typical * volume).cumsum() / cumulative_volume
    df["Support"] = low.rolling(20, min_periods=1).min()
    df["Resistance"] = high.rolling(20, min_periods=1).max()
    return df


def analyze_frame(frame: pd.DataFrame, account_size: float = 25000, risk_pct: float = 0.5) -> dict:
    df = add_indicators(frame)
    if len(df) < 30:
        raise ValueError("Not enough candles. At least 30 candles are required.")
    row = df.iloc[-1]
    previous = df.iloc[-2]
    price = float(row["Close"])
    atr = float(row["ATR14"]) if pd.notna(row["ATR14"]) else price * 0.01
    rsi = float(row["RSI14"]) if pd.notna(row["RSI14"]) else 50.0
    bullish = row["EMA9"] > row["EMA21"] and row["MACD"] > row["MACDSignal"] and rsi >= 50
    bearish = row["EMA9"] < row["EMA21"] and row["MACD"] < row["MACDSignal"] and rsi <= 50
    if bullish:
        signal = "BUY"
    elif bearish:
        signal = "SELL"
    else:
        signal = "HOLD"
    stop_distance = max(atr * 1.5, price * 0.002)
    entry = price
    stop = price - stop_distance if signal == "BUY" else price + stop_distance
    target = price + 2 * stop_distance if signal == "BUY" else price - 2 * stop_distance
    risk_budget = max(0.0, account_size * risk_pct / 100.0)
    risk_qty = int(risk_budget / stop_distance) if stop_distance > 0 else 0
    cash_qty = int(account_size / price) if price > 0 else 0
    quantity = max(0, min(risk_qty, cash_qty))
    if signal == "HOLD":
        quantity = 0
    return {
        "signal": signal, "price": round(price, 2), "entry": round(entry, 2),
        "stop_loss": round(stop, 2), "target_1": round(target, 2),
        "quantity": quantity, "planned_risk": round(quantity * stop_distance, 2),
        "risk_budget": round(risk_budget, 2), "rsi14": round(rsi, 2),
        "ema9": round(float(row["EMA9"]), 2), "ema21": round(float(row["EMA21"]), 2),
        "macd": round(float(row["MACD"]), 4), "macd_signal": round(float(row["MACDSignal"]), 4),
        "atr14": round(atr, 2), "vwap": round(float(row["VWAP"]), 2) if pd.notna(row["VWAP"]) else None,
        "support": round(float(row["Support"]), 2), "resistance": round(float(row["Resistance"]), 2),
        "candles": int(len(df)), "last_candle": str(df.index[-1]),
        "note": "Rule-based educational signal, not financial advice. Verify data freshness, fees, slippage and lot sizes."
    }
