"""Pine Script port - "Minu - EURUSD 1min UP/DOWN Signal (Educational)".

Faithful Python port of the owner's TradingView Pine Script (v5):

    upSignal   = ta.crossover(emaFast, emaSlow)  and rsi > 50
                 and close > emaTrend
    downSignal = ta.crossunder(emaFast, emaSlow) and rsi < 50
                 and close < emaTrend

Lengths: the script's defaults were EMA 9 / 21, Trend 200, RSI 14;
the owner runs EMA FAST 2 / SLOW 6 on TradingView (his settings
screenshot, 2026-11-11), so the bot uses 2 / 6 / 200 / 14 - same
numbers on both sides, no confusion.

Porting notes (honest differences):
  * The Pine plots / labels / bgcolor are chart decoration - only
    the SIGNAL logic is ported.
  * The bot evaluates CLOSED candles only (its non-repainting
    rule), so a cross is confirmed at the candle close; on
    TradingView the same alert can fire intrabar. Same logic,
    slightly different timing.
  * The Pine title says EURUSD, but the rules are pair-agnostic;
    the bot runs them on every scanned pair and tags the alert
    with the pair that fired.

Returns AnalysisResult (direction +1 = UP, -1 = DOWN) or None.
This module is an ALERT channel: it never feeds the main signal
engine's scoring, paper trades or best-pair selection.
"""
from __future__ import annotations

from typing import Optional

from ..models import AnalysisResult
from . import indicators

EMA_FAST = 2
EMA_SLOW = 6
EMA_TREND = 200
RSI_LEN = 14


def pine_signal(candles, idx: Optional[int] = None,
                symbol: str = "") -> Optional[AnalysisResult]:
    """Evaluate the Pine rules at candle `idx` (default: last).

    Uses ONLY candles[:idx+1] - non-repainting, like every other
    strategy in this project.
    """
    if not candles:
        return None
    if idx is None:
        idx = len(candles) - 1
    if idx < EMA_TREND or idx >= len(candles):
        return None  # EMA 200 needs 200 prior values + a previous bar

    closes = [c.close for c in candles[:idx + 1]]
    ef = indicators.ema_series(closes, EMA_FAST)
    es = indicators.ema_series(closes, EMA_SLOW)
    et = indicators.ema_series(closes, EMA_TREND)
    rs = indicators.rsi_series(closes, RSI_LEN)

    f_prev, f_now = ef[idx - 1], ef[idx]
    s_prev, s_now = es[idx - 1], es[idx]
    trend_now, rsi_now, close_now = et[idx], rs[idx], closes[idx]
    if None in (f_prev, f_now, s_prev, s_now, trend_now, rsi_now):
        return None

    cross_up = f_prev <= s_prev and f_now > s_now
    cross_down = f_prev >= s_prev and f_now < s_now

    if cross_up and rsi_now > 50 and close_now > trend_now:
        return AnalysisResult(
            symbol=symbol, direction=1, name="pine_minu_up",
            strength=1.0,
            reasons=[
                f"Pine (Minu) UP: EMA {EMA_FAST}/{EMA_SLOW} cross UP",
                f"RSI {rsi_now:.0f} > 50",
                "Price above EMA 200 (trend up)",
            ],
            extra={"rsi": round(rsi_now, 1),
                   "ema_fast": f_now, "ema_slow": s_now,
                   "ema_trend": trend_now, "price": close_now})
    if cross_down and rsi_now < 50 and close_now < trend_now:
        return AnalysisResult(
            symbol=symbol, direction=-1, name="pine_minu_down",
            strength=1.0,
            reasons=[
                f"Pine (Minu) DOWN: EMA {EMA_FAST}/{EMA_SLOW} cross DOWN",
                f"RSI {rsi_now:.0f} < 50",
                "Price below EMA 200 (trend down)",
            ],
            extra={"rsi": round(rsi_now, 1),
                   "ema_fast": f_now, "ema_slow": s_now,
                   "ema_trend": trend_now, "price": close_now})
    return None


def alert_message(symbol: str, direction: int) -> str:
    """Mirror of the Pine alertcondition message, pair-tagged."""
    word = "UP" if direction > 0 else "DOWN"
    return (f"{symbol} 1min: {word} signal (EMA cross + RSI filter). "
            f"Educational only, not a guarantee.")
