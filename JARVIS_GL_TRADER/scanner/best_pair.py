"""Pair scanner + BEST PAIR selection."""
from __future__ import annotations

import time

from .. import config
from ..engine import signal_engine
from ..strategies import indicators
from ..strategies.pine_minu import alert_message, pine_signal


def score_class(score: float, direction: str) -> str:
    """Spec classification buckets for the 0-100 signal score.

    Display/research labels only - NOT win probabilities. The
    engine's own classification field is left untouched."""
    if direction not in ("CALL", "PUT") or score < 50:
        return "No Trade"
    if score < 65:
        return "Weak"
    if score < 75:
        return "Moderate"
    if score < 85:
        return "Strong"
    return "Very Strong"


def _m15_context(feed, symbol):
    """M15 higher-timeframe context: EMA9 vs EMA21 trend label.

    Returns {"trend": UP/DOWN/FLAT/UNKNOWN, "agrees": bool|None}.
    Context only - it never overrides the M1 engine or M5 gate."""
    try:
        m15 = feed.get_candles(symbol, 40, timeframe="M15")
    except Exception:
        return {"trend": "UNKNOWN", "agrees": None}
    if not m15 or len(m15) < 21:
        return {"trend": "UNKNOWN", "agrees": None}
    closes = [c.close for c in m15]
    e9 = indicators.ema_series(closes, 9)[-1]
    e21 = indicators.ema_series(closes, 21)[-1]
    if e9 is None or e21 is None:
        return {"trend": "UNKNOWN", "agrees": None}
    trend = "UP" if e9 > e21 else ("DOWN" if e9 < e21 else "FLAT")
    return {"trend": trend, "agrees": None}


def scan_all(feed, candles_per_pair: int = 300, symbols=None) -> list:
    results = []
    for symbol in (symbols or config.PAIRS):
        try:
            candles = feed.get_candles(symbol, min(candles_per_pair,
                                                  config.MAX_CANDLES_PER_PAIR))
            try:
                m5 = feed.get_candles(symbol, 120, timeframe="M5")
            except Exception:
                m5 = None
            sig = signal_engine.analyse(symbol, candles, m5_candles=m5)
        except Exception as exc:
            results.append({"symbol": symbol, "signal": None,
                            "error": str(exc), "power": 0})
            continue
        # Owner's Pine Script rules - an independent ALERT channel.
        # A failure here must never break the main scan.
        pine = None
        try:
            if candles:
                hit = pine_signal(candles, symbol=symbol)
                if hit is not None:
                    pine = {
                        "direction": "UP" if hit.direction > 0 else "DOWN",
                        "time": candles[-1].time,
                        "price": candles[-1].close,
                        "rsi": hit.extra.get("rsi"),
                        "reasons": hit.reasons,
                        "message": alert_message(symbol, hit.direction),
                    }
        except Exception:
            pine = None
        # V5 display/context layer: score buckets, ADX, M15
        # context, spread + staleness. Engine decisions unchanged.
        m15 = _m15_context(feed, symbol)
        adx = None
        try:
            if candles:
                a = indicators.adx_series(candles)
                if a and a[-1] is not None:
                    adx = round(a[-1], 1)
        except Exception:
            adx = None
        spread = candles[-1].spread if candles else 0.0
        stale = bool(getattr(feed, "is_live", False)) and bool(candles) \
            and (time.time() - (candles[-1].time + 60)
                 > config.STALE_SECONDS)
        sig_dict = None
        if sig:
            sig_dict = sig.to_dict()
            score = int(round(sig.strength_pct))
            sig_dict["score"] = score
            sig_dict["score_class"] = score_class(score, sig.direction)
            sig_dict["components"] = {
                **(sig_dict.get("components") or {}),
                "adx": adx, "m15_trend": m15["trend"]}
            if sig.direction == "CALL":
                m15["agrees"] = (m15["trend"] == "UP")
            elif sig.direction == "PUT":
                m15["agrees"] = (m15["trend"] == "DOWN")
        results.append({
            "symbol": symbol,
            "signal": sig_dict,
            "power": sig.power_score if sig else 0,
            "price": candles[-1].close if candles else None,
            "pine": pine,
            "m15": m15,
            "adx": adx,
            "spread": spread,
            "stale": stale,
        })
    results.sort(key=lambda r: r["power"], reverse=True)
    return results


def best_pair(results) -> dict:
    """Only a qualifying setup wins: power >= threshold, not Weak,
    decision CALL/PUT, volatility OK. Else None + honest reason."""
    for r in results:
        sig = r.get("signal")
        if not sig:
            continue
        if r.get("stale"):
            continue  # never select on old market data
        spread = r.get("spread") or 0
        if spread and spread > config.MAX_SPREAD_POINTS:
            continue  # spread too wide for a 1-minute research trade
        if (sig["direction"] in ("CALL", "PUT")
                and sig["power_score"] >= config.MIN_POWER_FOR_BEST
                and sig["classification"] != "Weak"
                and sig.get("volatility_ok", True)):
            return {"best": r, "reason": "qualifying setup found"}
    return {"best": None, "reason": "no qualifying setup"}
