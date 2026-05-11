"""Peter Lynch stock screening criteria and scoring."""

from dataclasses import dataclass, field


# Thresholds from Lynch's books
PEG_MAX = 1.0
PE_MIN = 0.0
EARNINGS_GROWTH_MIN = 0.0
DEBT_TO_EQUITY_MAX = 0.5
FAIR_VALUE_RATIO_MIN = 1.5


@dataclass
class LynchResult:
    # Identification
    ticker: str
    name: str
    sector: str
    industry: str

    # Price
    price: float | None
    market_cap: float | None

    # Fundamentals
    pe: float
    earnings_growth_pct: float
    peg: float
    debt_to_equity: float | None
    free_cash_flow: float | None
    dividend_yield_pct: float
    fair_value_ratio: float | None
    category: str
    passes_all: bool

    # Technical (populated after fetch_history + compute_technical)
    rsi: float | None = field(default=None)
    macd_histogram: float | None = field(default=None)
    price_vs_sma50: float | None = field(default=None)
    price_vs_sma200: float | None = field(default=None)

    # Combined signal
    signal: str = field(default="PENDIENTE")
    signal_reason: str = field(default="")


def _classify(growth_pct: float) -> str:
    if growth_pct >= 20:
        return "Fast Grower"
    if growth_pct >= 10:
        return "Stalwart"
    return "Slow Grower"


def _fair_value_ratio(growth_pct: float, div_yield_pct: float, pe: float) -> float | None:
    if pe <= 0:
        return None
    return (growth_pct + div_yield_pct) / pe


def apply_lynch_filters(data: dict) -> LynchResult | None:
    """
    Apply all Lynch criteria. Returns LynchResult (passes_all may be False)
    or None if PE/growth data is missing and can't compute PEG.
    """
    pe = data.get("pe")
    growth = data.get("earnings_growth")

    if pe is None or growth is None:
        return None
    if pe <= 0 or growth <= 0:
        return None

    growth_pct = growth * 100
    peg = pe / growth_pct
    div_yield_pct = (data.get("dividend_yield") or 0.0) * 100
    fvr = _fair_value_ratio(growth_pct, div_yield_pct, pe)
    d_e = data.get("debt_to_equity")
    fcf = data.get("free_cash_flow")

    passes = (
        peg <= PEG_MAX
        and pe > PE_MIN
        and growth > EARNINGS_GROWTH_MIN
        and (d_e is None or d_e < DEBT_TO_EQUITY_MAX)
        and (fcf is None or fcf > 0)
        and (fvr is None or fvr >= FAIR_VALUE_RATIO_MIN)
    )

    return LynchResult(
        ticker=data["ticker"],
        name=data["name"],
        sector=data.get("sector", ""),
        industry=data.get("industry", ""),
        price=data.get("price"),
        market_cap=data.get("market_cap"),
        pe=round(pe, 2),
        earnings_growth_pct=round(growth_pct, 2),
        peg=round(peg, 3),
        debt_to_equity=round(d_e, 3) if d_e is not None else None,
        free_cash_flow=fcf,
        dividend_yield_pct=round(div_yield_pct, 2),
        fair_value_ratio=round(fvr, 3) if fvr is not None else None,
        category=_classify(growth_pct),
        passes_all=passes,
    )


def apply_lynch_filters_watchlist(data: dict) -> LynchResult:
    """
    Lenient version for watchlist mode: returns a result even without full
    fundamental data, marking passes_all=False when data is incomplete.
    Technical fields (RSI, MACD, signal) are filled in later by signals.py.
    """
    pe = data.get("pe")
    growth = data.get("earnings_growth")

    if pe is not None and growth is not None and pe > 0 and growth > 0:
        result = apply_lynch_filters(data)
        if result is not None:
            return result

    # Partial data — create a stub result
    return LynchResult(
        ticker=data["ticker"],
        name=data.get("name", data["ticker"]),
        sector=data.get("sector", ""),
        industry=data.get("industry", ""),
        price=data.get("price"),
        market_cap=data.get("market_cap"),
        pe=pe or 0.0,
        earnings_growth_pct=((growth or 0.0) * 100),
        peg=0.0,
        debt_to_equity=data.get("debt_to_equity"),
        free_cash_flow=data.get("free_cash_flow"),
        dividend_yield_pct=(data.get("dividend_yield") or 0.0) * 100,
        fair_value_ratio=None,
        category="Sin datos",
        passes_all=False,
    )
