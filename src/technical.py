"""RSI and MACD calculations from daily price history."""

from dataclasses import dataclass
import pandas as pd


@dataclass
class TechnicalData:
    rsi: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    price_vs_sma50: float | None
    price_vs_sma200: float | None


def compute_rsi(closes: pd.Series, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()

    last_loss = loss.iloc[-1]
    if pd.isna(last_loss) or last_loss == 0:
        # No down moves → RSI = 100 (fully overbought)
        return 100.0

    rs  = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else None


def compute_macd(
    closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float | None, float | None, float | None]:
    """Return (macd_line, signal_line, histogram) for the last bar."""
    if len(closes) < slow + signal:
        return None, None, None

    ema_fast    = closes.ewm(span=fast,   adjust=False).mean()
    ema_slow    = closes.ewm(span=slow,   adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram   = macd_line - signal_line

    def _last(s: pd.Series) -> float | None:
        v = s.iloc[-1]
        return round(float(v), 4) if pd.notna(v) else None

    return _last(macd_line), _last(signal_line), _last(histogram)


def compute_sma_distance(closes: pd.Series, period: int) -> float | None:
    """Percentage distance of last price from its SMA. Positive = above SMA."""
    if len(closes) < period:
        return None
    sma   = closes.rolling(period).mean().iloc[-1]
    price = closes.iloc[-1]
    if pd.isna(sma) or pd.isna(price) or sma == 0:
        return None
    return round((price - sma) / sma * 100, 2)


def compute_technical(closes: pd.Series) -> TechnicalData:
    macd, macd_sig, macd_hist = compute_macd(closes)
    return TechnicalData(
        rsi             = compute_rsi(closes),
        macd            = macd,
        macd_signal     = macd_sig,
        macd_histogram  = macd_hist,
        price_vs_sma50  = compute_sma_distance(closes, 50),
        price_vs_sma200 = compute_sma_distance(closes, 200),
    )
