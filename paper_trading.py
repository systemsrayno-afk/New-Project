"""In-memory paper trade helper; no broker connection and no live orders."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

@dataclass
class PaperTrade:
    symbol: str
    side: str
    quantity: int
    entry: float
    stop_loss: float
    target: float
    opened_at: str

def create_paper_trade(symbol: str, side: str, quantity: int, entry: float, stop_loss: float, target: float) -> dict:
    side = side.upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError("Side must be BUY or SELL.")
    if quantity <= 0 or min(entry, stop_loss, target) <= 0:
        raise ValueError("Quantity, entry, stop-loss and target must be positive.")
    if side == "BUY" and not stop_loss < entry < target:
        raise ValueError("For BUY, expected stop-loss < entry < target.")
    if side == "SELL" and not target < entry < stop_loss:
        raise ValueError("For SELL, expected target < entry < stop-loss.")
    trade = PaperTrade(symbol=symbol, side=side, quantity=quantity, entry=entry, stop_loss=stop_loss, target=target, opened_at=datetime.now(timezone.utc).isoformat())
    return asdict(trade)

def mark_to_market(trade: dict, current_price: float) -> dict:
    if current_price <= 0:
        raise ValueError("Current price must be positive.")
    direction = 1 if trade["side"].upper() == "BUY" else -1
    pnl = (current_price - float(trade["entry"])) * int(trade["quantity"]) * direction
    return {"symbol": trade["symbol"], "current_price": current_price, "unrealized_pnl": round(pnl, 2), "mode": "PAPER_ONLY"}
