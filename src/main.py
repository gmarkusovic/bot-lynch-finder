"""
LynchFinder — Peter Lynch stock screener with technical analysis
Usage:
  python src/main.py --mode screener --market [usa|europe|chile|all]
  python src/main.py --mode watchlist
  python src/main.py --mode all --market chile
"""

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from universe import get_sp500_tickers, EUROPE_TICKERS, CHILE_TICKERS
from fetcher import fetch_fundamentals, fetch_fundamentals_lenient, fetch_history
from criteria import apply_lynch_filters, apply_lynch_filters_watchlist, LynchResult
from technical import compute_technical
from signals import evaluate_signal
from reporter import save_results, print_summary, print_watchlist_summary
from notifier import send_telegram
from html_reporter import save_html_report

_MARKETS: dict[str, list[str]] = {
    "usa": [],
    "europe": EUROPE_TICKERS,
    "chile": CHILE_TICKERS,
}

_WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "watchlist.json")


def _load_watchlist() -> list[str]:
    try:
        with open(_WATCHLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("tickers", [])
    except FileNotFoundError:
        print("[watchlist] watchlist.json not found.")
        return []


def _process_ticker(ticker: str, lenient: bool = False) -> LynchResult | None:
    if lenient:
        data = fetch_fundamentals_lenient(ticker)
        if data is None:
            return None
        result = apply_lynch_filters_watchlist(data)
    else:
        data = fetch_fundamentals(ticker)
        if data is None:
            return None
        result = apply_lynch_filters(data)
        if result is None:
            return None

    hist = fetch_history(ticker)
    if hist is not None:
        tech = compute_technical(hist)
        result = evaluate_signal(result, tech)

    return result


def _screen_market(tickers: list[str], market: str, lenient: bool = False) -> list[LynchResult]:
    results: list[LynchResult] = []
    total = len(tickers)
    print(f"[{market}] Analizando {total} tickers (fundamental + técnico)…")

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_process_ticker, t, lenient): t for t in tickers}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0 or done == total:
                print(f"[{market}] {done}/{total} procesados", flush=True)
            result = future.result()
            if result is not None:
                results.append(result)

    return results


def run_screener(markets: list[str]) -> dict[str, list[LynchResult]]:
    if "usa" in markets:
        print("[usa] Obteniendo lista S&P 500…")
        _MARKETS["usa"] = get_sp500_tickers()

    all_results: dict[str, list[LynchResult]] = {}
    for market in markets:
        tickers = _MARKETS[market]
        if not tickers:
            print(f"[{market}] Sin tickers, omitiendo.")
            continue
        results = _screen_market(tickers, market)
        path = save_results(results, market)
        print_summary(results, market)
        print(f"[{market}] Resultados guardados → {path}")
        all_results[market] = results

    return all_results


def run_watchlist() -> dict[str, list[LynchResult]]:
    tickers = _load_watchlist()
    if not tickers:
        print("[watchlist] La watchlist está vacía.")
        return {}

    print(f"[watchlist] Analizando {len(tickers)} tickers en seguimiento…")
    results: list[LynchResult] = []
    for ticker in tickers:
        result = _process_ticker(ticker, lenient=True)
        if result is not None:
            results.append(result)
        else:
            print(f"[watchlist] Sin datos para {ticker}")

    if results:
        path = save_results(results, "watchlist")
        print_watchlist_summary(results)
        print(f"[watchlist] Resultados guardados → {path}")

    return {"watchlist": results} if results else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="LynchFinder — screener + técnico")
    parser.add_argument(
        "--mode",
        choices=["screener", "watchlist", "all"],
        default="all",
        help="Modo de operación (default: all)",
    )
    parser.add_argument(
        "--market",
        default="usa,chile",
        help="Mercado(s) a analizar: usa, chile, europe o combinados con coma (default: usa,chile)",
    )
    args = parser.parse_args()

    _valid = {"usa", "europe", "chile"}
    if args.market == "all":
        markets = ["usa", "chile"]
    else:
        markets = [m.strip() for m in args.market.split(",") if m.strip() in _valid]

    all_results: dict[str, list[LynchResult]] = {}

    if args.mode in ("screener", "all"):
        all_results.update(run_screener(markets))

    if args.mode in ("watchlist", "all"):
        all_results.update(run_watchlist())

    # Generate HTML report and send Telegram notification
    if all_results:
        html_path = save_html_report(all_results)
        print(f"[html] Reporte guardado → {html_path}")
        send_telegram(all_results, date.today().isoformat())


if __name__ == "__main__":
    main()
