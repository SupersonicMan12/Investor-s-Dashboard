import math

from app.services import analysis
from app.services.market_data import Quote


def make_quote(closes: list[float], symbol: str = "TEST") -> Quote:
    return Quote(
        symbol=symbol,
        name="Test Asset",
        timestamps=list(range(len(closes))),
        closes=closes,
        volumes=[1000] * len(closes),
        price=closes[-1],
        previous_close=closes[-2] if len(closes) > 1 else closes[-1],
    )


def uptrend_closes(n: int = 120) -> list[float]:
    return [100 * (1.004**i) for i in range(n)]


def downtrend_closes(n: int = 120) -> list[float]:
    return [100 * (0.996**i) for i in range(n)]


def test_simple_return():
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    result = analysis.simple_return(closes, 5)
    assert result is not None
    assert math.isclose(result, 5.0)


def test_simple_return_insufficient_history():
    assert analysis.simple_return([100.0, 101.0], 5) is None


def test_sma():
    closes = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert analysis.sma(closes, 5) == 3.0
    assert analysis.sma(closes, 10) is None


def test_rsi_bounds():
    up = analysis.rsi(uptrend_closes())
    down = analysis.rsi(downtrend_closes())
    assert up is not None and down is not None
    assert 0 <= down < 50 < up <= 100


def test_rsi_all_gains_is_100():
    assert analysis.rsi([float(i) for i in range(1, 30)]) == 100.0


def test_annualized_volatility_positive():
    vol = analysis.annualized_volatility(uptrend_closes())
    assert vol is not None
    assert vol >= 0


def test_annualized_volatility_insufficient():
    assert analysis.annualized_volatility([100.0] * 5) is None


def test_trend_labels():
    assert analysis._trend_label(uptrend_closes()) == "Uptrend"
    assert analysis._trend_label(downtrend_closes()) == "Downtrend"
    assert analysis._trend_label([100.0] * 10) == "Insufficient data"


def test_score_quote_uptrend_beats_downtrend():
    up_signal = analysis.score_quote(make_quote(uptrend_closes(), "UP"))
    down_signal = analysis.score_quote(make_quote(downtrend_closes(), "DOWN"))
    assert up_signal.score > down_signal.score
    assert 0 <= down_signal.score <= 100
    assert 0 <= up_signal.score <= 100
    assert up_signal.trend == "Uptrend"
    assert down_signal.trend == "Downtrend"
    assert up_signal.thesis


def test_score_quote_short_history_is_neutral():
    signal = analysis.score_quote(make_quote([100.0, 101.0]))
    assert signal.confidence in {"High", "Medium", "Low"}
    assert signal.trend == "Insufficient data"


def test_rank_signals_sorted():
    quotes = {
        "UP": make_quote(uptrend_closes(), "UP"),
        "DOWN": make_quote(downtrend_closes(), "DOWN"),
    }
    ranked = analysis.rank_signals(quotes)
    assert [s.symbol for s in ranked] == ["UP", "DOWN"]
