"""Signal engine: technical indicators and a 1-week opportunity score."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app import config
from app.services.market_data import Quote


def simple_return(closes: list[float], days: int) -> float | None:
    """Percent return over the last ``days`` trading days."""
    if len(closes) <= days or closes[-days - 1] == 0:
        return None
    return (closes[-1] - closes[-days - 1]) / closes[-days - 1] * 100


def sma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def rsi(closes: list[float], period: int = 14) -> float | None:
    """Wilder's RSI."""
    if len(closes) <= period:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def annualized_volatility(closes: list[float], window: int = 20) -> float | None:
    """Annualized volatility (%) of daily log returns over ``window`` days."""
    if len(closes) < window + 1:
        return None
    recent = closes[-(window + 1):]
    returns = [
        math.log(recent[i] / recent[i - 1])
        for i in range(1, len(recent))
        if recent[i - 1] > 0
    ]
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252) * 100


@dataclass
class Signal:
    symbol: str
    name: str
    price: float
    change_pct: float
    week_return: float | None
    month_return: float | None
    rsi: float | None
    volatility: float | None
    trend: str
    score: int
    confidence: str
    thesis: str
    closes: list[float]
    is_stale: bool


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _trend_label(closes: list[float]) -> str:
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    if sma20 is None or sma50 is None:
        return "Insufficient data"
    price = closes[-1]
    if price > sma20 > sma50:
        return "Uptrend"
    if price < sma20 < sma50:
        return "Downtrend"
    return "Sideways"


def _build_thesis(
    name: str,
    week: float | None,
    month: float | None,
    rsi_value: float | None,
    vol: float | None,
    trend: str,
) -> str:
    parts: list[str] = []
    if week is not None:
        direction = "gained" if week >= 0 else "slipped"
        parts.append(f"{name} {direction} {abs(week):.1f}% over the past week")
    if trend == "Uptrend":
        parts.append("price is holding above its 20- and 50-day averages")
    elif trend == "Downtrend":
        parts.append("price remains below its key moving averages")
    if rsi_value is not None:
        if rsi_value >= 70:
            parts.append(f"RSI at {rsi_value:.0f} flags overbought risk")
        elif rsi_value <= 30:
            parts.append(f"RSI at {rsi_value:.0f} suggests an oversold rebound setup")
        else:
            parts.append(f"RSI at {rsi_value:.0f} leaves room to run")
    if vol is not None:
        if vol < 20:
            parts.append("volatility is subdued")
        elif vol > 40:
            parts.append("expect elevated volatility")
    if not parts:
        return "Not enough history to form a view."
    sentence = "; ".join(parts) + "."
    return sentence[0].upper() + sentence[1:]


def score_quote(quote: Quote) -> Signal:
    """Score a symbol for a 1-week horizon on a 0-100 scale.

    Blends short-term momentum (55%), trend alignment (20%), RSI positioning
    (15%), and volatility penalty (10%).
    """
    closes = quote.closes
    week = simple_return(closes, config.WEEK_DAYS)
    month = simple_return(closes, config.MONTH_DAYS)
    rsi_value = rsi(closes)
    vol = annualized_volatility(closes)
    trend = _trend_label(closes)

    momentum_score = 50.0
    if week is not None and month is not None:
        momentum_score = _clamp(50 + week * 6 + month * 1.5)
    elif week is not None:
        momentum_score = _clamp(50 + week * 7)

    trend_score = {"Uptrend": 100.0, "Sideways": 50.0, "Downtrend": 0.0}.get(
        trend, 50.0
    )

    rsi_score = 50.0
    if rsi_value is not None:
        # Sweet spot around 50-65: momentum without being overbought.
        rsi_score = _clamp(100 - abs(rsi_value - 57.5) * 2.75)

    vol_score = 50.0
    if vol is not None:
        vol_score = _clamp(100 - vol * 1.6)

    score = round(
        momentum_score * 0.55 + trend_score * 0.20 + rsi_score * 0.15 + vol_score * 0.10
    )

    if score >= 70:
        confidence = "High"
    elif score >= 50:
        confidence = "Medium"
    else:
        confidence = "Low"

    return Signal(
        symbol=quote.symbol,
        name=quote.name,
        price=quote.price,
        change_pct=quote.change_pct,
        week_return=week,
        month_return=month,
        rsi=rsi_value,
        volatility=vol,
        trend=trend,
        score=score,
        confidence=confidence,
        thesis=_build_thesis(quote.name, week, month, rsi_value, vol, trend),
        closes=closes,
        is_stale=quote.is_stale,
    )


def rank_signals(quotes: dict[str, Quote]) -> list[Signal]:
    signals = [score_quote(q) for q in quotes.values()]
    signals.sort(key=lambda s: s.score, reverse=True)
    return signals
