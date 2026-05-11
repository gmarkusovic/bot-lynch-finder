"""Format and persist screening results."""

import os
from datetime import date
from dataclasses import asdict

import pandas as pd

from criteria import LynchResult

_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

_SIGNAL_LABELS = {
    "COMPRA_FUERTE": "*** COMPRA FUERTE ***",
    "COMPRA":        "**  COMPRA          **",
    "SEGUIMIENTO":   "    SEGUIMIENTO      ",
    "SOBRECOMPRADA": "!!! SOBRECOMPRADA !!!",
    "VENTA":         "!!! VENTA/CAUTELA !!!",
    "NEUTRAL":       "    NEUTRAL          ",
    "PENDIENTE":     "    (sin técnico)    ",
}

_SIGNAL_ORDER = ["COMPRA_FUERTE", "COMPRA", "SEGUIMIENTO", "SOBRECOMPRADA", "VENTA", "NEUTRAL", "PENDIENTE"]


def _to_df(results: list[LynchResult]) -> pd.DataFrame:
    records = [asdict(r) for r in results]
    df = pd.DataFrame(records)
    if df.empty:
        return df
    # Sort: passes_all first, then by peg
    df["_passes_int"] = df["passes_all"].astype(int)
    df = df.sort_values(["_passes_int", "peg"], ascending=[False, True])
    df = df.drop(columns=["_passes_int"]).reset_index(drop=True)
    return df


def save_results(results: list[LynchResult], market: str) -> str:
    """Save full results to a dated CSV. Returns file path."""
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    today = date.today().isoformat()
    path = os.path.join(_RESULTS_DIR, f"{today}_{market}.csv")
    df = _to_df(results)
    df.to_csv(path, index=False)
    return path


def _signal_section(results: list[LynchResult], signal: str) -> list[LynchResult]:
    return [r for r in results if r.signal == signal]


def print_alerts(results: list[LynchResult], market: str) -> None:
    """Print buy/sell alerts prominently."""
    buy_strong = _signal_section(results, "COMPRA_FUERTE")
    buy = _signal_section(results, "COMPRA")
    overbought = _signal_section(results, "SOBRECOMPRADA")
    sell = _signal_section(results, "VENTA")

    if not any([buy_strong, buy, overbought, sell]):
        return

    width = 72
    print(f"\n{'#'*width}")
    print(f"#{'ALERTAS — ' + market.upper():^{width-2}}#")
    print(f"{'#'*width}")

    for group, label in [
        (buy_strong, "COMPRA FUERTE"),
        (buy, "ZONA DE COMPRA"),
        (sell, "ZONA DE VENTA"),
        (overbought, "SOBRECOMPRADA — CAUTELA"),
    ]:
        if not group:
            continue
        print(f"\n  [{label}]")
        for r in sorted(group, key=lambda x: x.peg):
            peg_str = f"PEG={r.peg:.3f}" if r.peg else ""
            rsi_str = f"RSI={r.rsi:.1f}" if r.rsi else ""
            print(f"    {r.ticker:<14} {r.name:<30} {peg_str:<12} {rsi_str}")
            print(f"    {'':14} {r.signal_reason}")

    print(f"{'#'*width}\n")


def print_summary(results: list[LynchResult], market: str, top_n: int = 20) -> None:
    """Print top N results ordered by Lynch pass + PEG, with signals."""
    passed = [r for r in results if r.passes_all]
    total = len(results)

    print(f"\n{'='*72}")
    print(f"  LYNCH FINDER — {market.upper()}  |  {date.today()}  |  Analizadas: {total}")
    print(f"  Pasan criterios Lynch: {len(passed)}")
    print(f"{'='*72}")

    if not passed:
        print("  Ninguna acción pasa todos los criterios Lynch hoy.")
        print(f"{'='*72}\n")
        print_alerts(results, market)
        return

    df = _to_df(passed).head(top_n)

    cols = [
        "ticker", "name", "signal", "category",
        "peg", "pe", "earnings_growth_pct",
        "rsi", "macd_histogram",
        "debt_to_equity", "fair_value_ratio",
    ]
    display = df[[c for c in cols if c in df.columns]].copy()
    if "signal" in display.columns:
        display["signal"] = display["signal"].map(_SIGNAL_LABELS).fillna(display["signal"])

    pd.set_option("display.max_colwidth", 20)
    pd.set_option("display.width", 120)
    print(display.to_string(index=True))
    print(f"\n  PEG<1=crecimiento barato | RSI<30=sobreventa | MACD hist>0=alcista")
    print(f"{'='*72}\n")

    print_alerts(results, market)


def print_watchlist_summary(results: list[LynchResult]) -> None:
    """Print watchlist analysis with signals prominently displayed."""
    width = 72
    print(f"\n{'='*width}")
    print(f"  WATCHLIST — {date.today()}")
    print(f"{'='*width}")

    for r in results:
        label = _SIGNAL_LABELS.get(r.signal, r.signal)
        peg_str = f"PEG={r.peg:.3f}" if r.peg and r.peg > 0 else "PEG=N/D"
        rsi_str = f"RSI={r.rsi:.1f}" if r.rsi is not None else "RSI=N/D"
        macd_str = f"MACD hist={r.macd_histogram:.4f}" if r.macd_histogram is not None else ""
        lynch_str = "Lynch: OK" if r.passes_all else "Lynch: NO"

        print(f"\n  {r.ticker:<12} {r.name}")
        print(f"  Señal: {label}")
        print(f"  {lynch_str} | {peg_str} | PE={r.pe:.1f} | Crec={r.earnings_growth_pct:.1f}%")
        print(f"  {rsi_str} | {macd_str}")
        if r.signal_reason:
            print(f"  Razón: {r.signal_reason}")
        if r.price_vs_sma50 is not None:
            sma50_str = f"+{r.price_vs_sma50:.1f}%" if r.price_vs_sma50 >= 0 else f"{r.price_vs_sma50:.1f}%"
            print(f"  vs SMA50: {sma50_str}", end="")
        if r.price_vs_sma200 is not None:
            sma200_str = f"+{r.price_vs_sma200:.1f}%" if r.price_vs_sma200 >= 0 else f"{r.price_vs_sma200:.1f}%"
            print(f"  |  vs SMA200: {sma200_str}", end="")
        print()

    print(f"\n{'='*width}\n")
