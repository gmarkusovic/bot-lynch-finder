"""
Combine Peter Lynch fundamental score with RSI/MACD to generate buy/sell signals.

Signal hierarchy:
  COMPRA_FUERTE  — Lynch OK + RSI oversold (<30) + MACD bullish
  COMPRA         — Lynch OK + RSI favorable (<45) OR MACD bullish crossover
  SEGUIMIENTO    — Lynch OK but technical neutral or mixed
  SOBRECOMPRADA  — RSI > 70 (caution regardless of fundamentals)
  VENTA          — RSI > 70 AND MACD bearish (histogram < 0)
  NEUTRAL        — doesn't meet Lynch criteria and no extreme technicals
"""

from dataclasses import replace
from technical import TechnicalData
from criteria import LynchResult

# RSI thresholds
RSI_OVERSOLD_STRONG = 30
RSI_OVERSOLD = 45
RSI_OVERBOUGHT = 70

# MACD: positive histogram = bullish momentum
def _macd_bullish(tech: TechnicalData) -> bool:
    return tech.macd_histogram is not None and tech.macd_histogram > 0

def _macd_bearish(tech: TechnicalData) -> bool:
    return tech.macd_histogram is not None and tech.macd_histogram < 0


def evaluate_signal(result: LynchResult, tech: TechnicalData) -> LynchResult:
    """Return a new LynchResult with signal, signal_reason, rsi, and macd fields set."""
    rsi = tech.rsi
    passes = result.passes_all
    bullish = _macd_bullish(tech)
    bearish = _macd_bearish(tech)

    # Sell warnings take priority regardless of fundamentals
    if rsi is not None and rsi > RSI_OVERBOUGHT:
        if bearish:
            signal = "VENTA"
            reason = f"RSI={rsi} (sobrecomprada) + MACD bearish → posible corrección"
        else:
            signal = "SOBRECOMPRADA"
            reason = f"RSI={rsi} > 70 → cautela, posible techo"

    elif passes:
        if rsi is not None and rsi < RSI_OVERSOLD_STRONG and bullish:
            signal = "COMPRA_FUERTE"
            reason = (
                f"Lynch OK + RSI={rsi} (zona sobreventa fuerte) + MACD alcista"
            )
        elif (rsi is not None and rsi < RSI_OVERSOLD) or bullish:
            signal = "COMPRA"
            parts = []
            if rsi is not None and rsi < RSI_OVERSOLD:
                parts.append(f"RSI={rsi} (favorable)")
            if bullish:
                parts.append("MACD alcista")
            reason = "Lynch OK + " + " + ".join(parts)
        else:
            signal = "SEGUIMIENTO"
            rsi_str = f"RSI={rsi}" if rsi is not None else "RSI=N/D"
            reason = f"Lynch OK pero técnico neutro ({rsi_str}, MACD {'alcista' if bullish else 'bajista' if bearish else 'neutro'})"

    else:
        signal = "NEUTRAL"
        rsi_str = f"RSI={rsi}" if rsi is not None else ""
        reason = f"No cumple criterios Lynch. {rsi_str}".strip()

    macd_hist_str = (
        round(tech.macd_histogram, 4) if tech.macd_histogram is not None else None
    )

    return replace(
        result,
        rsi=rsi,
        macd_histogram=macd_hist_str,
        price_vs_sma50=tech.price_vs_sma50,
        price_vs_sma200=tech.price_vs_sma200,
        signal=signal,
        signal_reason=reason,
    )
