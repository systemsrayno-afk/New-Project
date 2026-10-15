import pandas as pd
from indicators import add_indicators, analyze_frame


def sample_data(n=80):
    idx = pd.date_range("2025-01-01", periods=n, freq="5min")
    close = [100 + i * 0.2 for i in range(n)]
    return pd.DataFrame({
        "Open": close, "High": [x + 1 for x in close],
        "Low": [x - 1 for x in close], "Close": close,
        "Volume": [1000] * n
    }, index=idx)


def test_indicators_added():
    result = add_indicators(sample_data())
    for name in ["EMA9", "EMA21", "RSI14", "MACD", "MACDSignal", "ATR14", "VWAP", "Support", "Resistance"]:
        assert name in result.columns
    assert len(result) == 80


def test_analysis_has_risk_fields():
    result = analyze_frame(sample_data())
    assert result["signal"] in {"BUY", "SELL", "HOLD"}
    assert result["risk_budget"] == 125.0
    assert result["quantity"] >= 0


def test_insufficient_data_rejected():
    try:
        analyze_frame(sample_data(10))
    except ValueError as exc:
        assert "30 candles" in str(exc)
    else:
        raise AssertionError("Expected insufficient-data validation")
