"""Technical indicators in Python (pandas/numpy) — never LLM math."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    if avg_loss.iloc[-1] == 0:
        return 100.0
    rs = avg_gain.iloc[-1] / avg_loss.iloc[-1]
    return float(100 - 100 / (1 + rs))


def _macd(close: pd.Series) -> tuple[float | None, float | None, float | None]:
    if len(close) < 35:
        return None, None, None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal
    return float(macd_line.iloc[-1]), float(signal.iloc[-1]), float(histogram.iloc[-1])


def compute_all(df: pd.DataFrame, indicators: list[str]) -> dict[str, float | None]:
    """Compute the requested indicators; missing data yields None, never NaN."""
    close = df["CloseAdj"].astype(float) if "CloseAdj" in df else df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    vol = df["Volume"].astype(float)
    out: dict[str, float | None] = {}

    for ind in indicators:
        key = ind.upper().replace("-", "_")
        if key == "SMA_20" and len(close) >= 20:
            out[key] = float(close.rolling(20).mean().iloc[-1])
        elif key == "SMA_50" and len(close) >= 50:
            out[key] = float(close.rolling(50).mean().iloc[-1])
        elif key == "SMA_200" and len(close) >= 200:
            out[key] = float(close.rolling(200).mean().iloc[-1])
        elif key == "EMA_12" and len(close) >= 12:
            out[key] = float(close.ewm(span=12, adjust=False).mean().iloc[-1])
        elif key == "EMA_26" and len(close) >= 26:
            out[key] = float(close.ewm(span=26, adjust=False).mean().iloc[-1])
        elif key == "RSI_14":
            out[key] = _rsi(close, 14)
        elif key == "MACD":
            m, s, h = _macd(close)
            out[key] = m
            out["MACD_SIGNAL"] = s
            out["MACD_HISTOGRAM"] = h
        elif key == "BOLLINGER" and len(close) >= 20:
            mid = float(close.rolling(20).mean().iloc[-1])
            std = float(close.rolling(20).std().iloc[-1])
            if np.isfinite(mid) and np.isfinite(std):
                out["BOLLINGER_MID"] = mid
                out["BOLLINGER_UPPER"] = mid + 2 * std
                out["BOLLINGER_LOWER"] = mid - 2 * std
        elif key == "ATR_14" and len(close) >= 15:
            prev = close.shift(1)
            tr = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            out[key] = float(atr) if np.isfinite(atr) else None
        elif key == "VWAP" and len(close) >= 1 and vol.sum() > 0:
            tp = (high + low + close) / 3
            out[key] = float((tp * vol).sum() / vol.sum()) if vol.sum() > 0 else None
        else:
            out.setdefault(key, None)

    # Always include SMA_200 when enough data for the trend field
    if "SMA_200" not in out and len(close) >= 200:
        out["SMA_200"] = float(close.rolling(200).mean().iloc[-1])
    return out


__all__ = ["compute_all"]
