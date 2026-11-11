"""Technical indicators on plain Python lists (no numpy/pandas).

Every series function returns a list aligned with the input closes;
entries are None where there is not enough data yet. Textbook
formulas only.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

FloatSeries = List[Optional[float]]


def ema_series(values: Sequence[float], period: int) -> FloatSeries:
    """Exponential moving average, seeded with the SMA of the first
    `period` values; k = 2/(period+1)."""
    n = len(values)
    out: FloatSeries = [None] * n
    if period <= 0 or n < period:
        return out
    k = 2.0 / (period + 1.0)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, n):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def sma(values: Sequence[float], period: int) -> FloatSeries:
    n = len(values)
    out: FloatSeries = [None] * n
    if period <= 0 or n < period:
        return out
    window = sum(values[:period])
    out[period - 1] = window / period
    for i in range(period, n):
        window += values[i] - values[i - period]
        out[i] = window / period
    return out


def rsi_series(closes: Sequence[float], period: int = 14) -> FloatSeries:
    """Wilder's RSI. First value at index `period` uses the simple
    average of the first `period` gains/losses; afterwards Wilder
    smoothing: avg = (avg*(period-1) + current)/period."""
    n = len(closes)
    out: FloatSeries = [None] * n
    if n <= period:
        return out
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    def _rsi(ag: float, al: float) -> float:
        if al == 0:
            return 100.0 if ag > 0 else 50.0
        rs = ag / al
        return 100.0 - 100.0 / (1.0 + rs)

    out[period] = _rsi(avg_gain, avg_loss)
    for i in range(period + 1, n):
        d = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(d, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0.0)) / period
        out[i] = _rsi(avg_gain, avg_loss)
    return out


def macd_series(closes: Sequence[float], fast: int = 12, slow: int = 26,
                signal_period: int = 9) -> Tuple[FloatSeries, FloatSeries, FloatSeries]:
    """MACD = EMA(fast) - EMA(slow); signal = EMA of MACD (seeded once
    enough MACD values exist); hist = MACD - signal."""
    n = len(closes)
    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    macd: FloatSeries = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd[i] = ema_fast[i] - ema_slow[i]  # type: ignore[operator]
    signal: FloatSeries = [None] * n
    hist: FloatSeries = [None] * n
    # EMA over the non-None MACD segment.
    idxs = [i for i in range(n) if macd[i] is not None]
    if len(idxs) >= signal_period:
        seg = [macd[i] for i in idxs]  # type: ignore[misc]
        seg_ema = ema_series(seg, signal_period)  # type: ignore[arg-type]
        for j, i in enumerate(idxs):
            if seg_ema[j] is not None:
                signal[i] = seg_ema[j]
                hist[i] = macd[i] - seg_ema[j]  # type: ignore[operator]
    return macd, signal, hist


def bollinger(closes: Sequence[float], period: int = 20,
              mult: float = 2.0) -> Tuple[FloatSeries, FloatSeries, FloatSeries]:
    """Returns (upper, mid, lower); mid = SMA, bands = mid +/- mult*stdev
    (population stdev, the standard Bollinger convention)."""
    n = len(closes)
    upper: FloatSeries = [None] * n
    mid: FloatSeries = [None] * n
    lower: FloatSeries = [None] * n
    if n < period:
        return upper, mid, lower
    for i in range(period - 1, n):
        window = closes[i - period + 1:i + 1]
        m = sum(window) / period
        var = sum((x - m) ** 2 for x in window) / period
        sd = math.sqrt(var)
        mid[i] = m
        upper[i] = m + mult * sd
        lower[i] = m - mult * sd
    return upper, mid, lower


def atr_series(candles, period: int = 14) -> FloatSeries:
    """Wilder ATR over candle objects with .high/.low/.close.
    TR = max(H-L, |H-prevC|, |L-prevC|); first ATR = SMA of first
    `period` TRs, then Wilder smoothing."""
    n = len(candles)
    out: FloatSeries = [None] * n
    if n <= period:
        return out
    trs: List[float] = []
    for i in range(1, n):
        h, low, pc = candles[i].high, candles[i].low, candles[i - 1].close
        trs.append(max(h - low, abs(h - pc), abs(low - pc)))
    # trs[j] corresponds to candle index j+1
    atr = sum(trs[:period]) / period
    out[period] = atr
    for j in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[j]) / period
        out[j + 1] = atr
    return out


def adx_series(candles, period: int = 14) -> FloatSeries:
    """Wilder ADX over candle objects with .high/.low/.close.

    +DM/-DM and TR are Wilder-smoothed; DX = 100*|+DI - -DI| /
    (+DI + -DI); ADX is the Wilder average of DX. Values are None
    until enough data exists (first ADX at index 2*period - 1).
    ADX measures trend STRENGTH only (0-100), never direction.
    """
    n = len(candles)
    out: FloatSeries = [None] * n
    if n < 2 * period:
        return out
    trs: List[float] = []
    pdms: List[float] = []
    mdms: List[float] = []
    # index j in these lists corresponds to candle index j+1
    for i in range(1, n):
        h, low = candles[i].high, candles[i].low
        ph, pl, pc = (candles[i - 1].high, candles[i - 1].low,
                      candles[i - 1].close)
        up = h - ph
        down = pl - low
        pdms.append(up if (up > down and up > 0) else 0.0)
        mdms.append(down if (down > up and down > 0) else 0.0)
        trs.append(max(h - low, abs(h - pc), abs(low - pc)))

    def _wilder(vals):
        sm = [None] * len(vals)
        s = sum(vals[:period])
        sm[period - 1] = s
        for j in range(period, len(vals)):
            s = s - s / period + vals[j]
            sm[j] = s
        return sm

    s_tr, s_p, s_m = _wilder(trs), _wilder(pdms), _wilder(mdms)
    dxs = {}  # candle index -> DX
    for j in range(period - 1, len(trs)):
        if not s_tr[j]:
            continue
        pdi = 100.0 * s_p[j] / s_tr[j]
        mdi = 100.0 * s_m[j] / s_tr[j]
        tot = pdi + mdi
        dxs[j + 1] = (100.0 * abs(pdi - mdi) / tot) if tot else 0.0
    keys = sorted(dxs)
    if len(keys) < period:
        return out
    adx = sum(dxs[k] for k in keys[:period]) / period
    out[keys[period - 1]] = adx
    for k in keys[period:]:
        adx = (adx * (period - 1) + dxs[k]) / period
        out[k] = adx
    return out
