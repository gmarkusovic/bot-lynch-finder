"""
Telegram bot command handler — runs via GitHub Actions cron every 5 minutes.
Processes /add /remove /list /check /help commands.
/check fetches live data for a ticker and replies with full Lynch + technical analysis.
"""

import os
import sys
import json
import base64
import time
import requests

# Add src/ to path so we can import project modules
sys.path.insert(0, os.path.dirname(__file__))

from fetcher import fetch_fundamentals_lenient, fetch_history
from criteria import apply_lynch_filters_watchlist
from technical import compute_technical
from signals import evaluate_signal

TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])
GITHUB_TOKEN     = os.environ["GITHUB_TOKEN"]
GITHUB_REPO      = os.environ["GITHUB_REPO"]

_GH_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}
_WATCHLIST_PATH = "watchlist.json"
_OFFSET_PATH    = "data/last_update_id.txt"


# ── GitHub API helpers ────────────────────────────────────────────────────────

def _gh_get(path: str) -> tuple[str | None, str | None]:
    url  = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    resp = requests.get(url, headers=_GH_HEADERS, timeout=10)
    if resp.status_code == 404:
        return None, None
    data = resp.json()
    return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]


def _gh_put(path: str, content: str, sha: str | None, message: str) -> None:
    url     = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    body    = {"message": message, "content": encoded}
    if sha:
        body["sha"] = sha
    requests.put(url, headers=_GH_HEADERS, json=body, timeout=10)


# ── Watchlist helpers ─────────────────────────────────────────────────────────

def _load_watchlist() -> tuple[dict, str | None]:
    content, sha = _gh_get(_WATCHLIST_PATH)
    if content is None:
        return {"tickers": []}, None
    return json.loads(content), sha


def _save_watchlist(data: dict, sha: str | None, ticker: str, action: str) -> None:
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    _gh_put(_WATCHLIST_PATH, content, sha, f"watchlist: {action} {ticker} via Telegram")


# ── Offset tracking ───────────────────────────────────────────────────────────

def _load_offset() -> tuple[int, str | None]:
    content, sha = _gh_get(_OFFSET_PATH)
    return (int(content.strip()), sha) if content else (0, None)


def _save_offset(offset: int, sha: str | None) -> None:
    _gh_put(_OFFSET_PATH, str(offset) + "\n", sha, f"bot: offset {offset}")


# ── Telegram helpers ──────────────────────────────────────────────────────────

def _send(text: str) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )


def _get_updates(offset: int) -> list[dict]:
    resp = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
        params={"offset": offset, "limit": 100, "timeout": 0},
        timeout=15,
    )
    return resp.json().get("result", [])


# ── /check command ────────────────────────────────────────────────────────────

def _v(val, decimals: int = 2, suffix: str = "") -> str:
    return "—" if val is None else f"{val:.{decimals}f}{suffix}"


def _fcf_icon(fcf) -> str:
    if fcf is None:
        return "—"
    return "✅" if fcf > 0 else "❌"


def _cmd_check(ticker: str) -> None:
    _send(f"🔍 Analizando <b>{ticker}</b>… (puede tomar hasta 30 seg)")

    data = fetch_fundamentals_lenient(ticker)
    if data is None:
        _send(f"❌ No se encontraron datos para <b>{ticker}</b>.\n\nVerifica que el ticker sea correcto (ej. AAPL, SQM-B.SN, MC.PA).")
        return

    result = apply_lynch_filters_watchlist(data)

    hist = fetch_history(ticker)
    if hist is not None:
        tech = compute_technical(hist)
        result = evaluate_signal(result, tech)

    # Lynch fundamentals
    lynch_ok = "✅ Cumple criterios Lynch" if result.passes_all else "❌ No cumple criterios Lynch"

    # Criteria detail
    peg_ok  = "✅" if result.peg and result.peg <= 1.0   else "❌"
    pe_ok   = "✅" if result.pe  and result.pe  > 0      else "❌"
    grw_ok  = "✅" if result.earnings_growth_pct > 0     else "❌"
    de_ok   = ("✅" if result.debt_to_equity is not None and result.debt_to_equity < 0.5
               else "⚠️" if result.debt_to_equity is None else "❌")
    fcf_ok  = ("✅" if result.free_cash_flow and result.free_cash_flow > 0
               else "❌" if result.free_cash_flow is not None else "⚠️")
    fvr_ok  = ("✅" if result.fair_value_ratio and result.fair_value_ratio >= 1.5
               else "❌" if result.fair_value_ratio is not None else "⚠️")

    # RSI label
    rsi = result.rsi
    if rsi is None:
        rsi_label = "—"
    elif rsi < 30:
        rsi_label = f"{rsi:.1f} 🟢 Sobreventa fuerte"
    elif rsi < 45:
        rsi_label = f"{rsi:.1f} 🟡 Zona favorable"
    elif rsi < 65:
        rsi_label = f"{rsi:.1f} ⚪ Neutral"
    elif rsi < 70:
        rsi_label = f"{rsi:.1f} 🟠 Zona alta"
    else:
        rsi_label = f"{rsi:.1f} 🔴 Sobrecomprada"

    # MACD label
    mh = result.macd_histogram
    if mh is None:
        macd_label = "—"
    elif mh > 0:
        macd_label = f"{mh:.4f} 📈 Alcista"
    else:
        macd_label = f"{mh:.4f} 📉 Bajista"

    # SMA distances
    sma50  = (f"{result.price_vs_sma50:+.1f}%" if result.price_vs_sma50  is not None else "—")
    sma200 = (f"{result.price_vs_sma200:+.1f}%" if result.price_vs_sma200 is not None else "—")

    signal_emoji = {
        "COMPRA_FUERTE": "🚀", "COMPRA": "🟢", "SEGUIMIENTO": "👀",
        "SOBRECOMPRADA": "⚠️", "VENTA": "🔴", "NEUTRAL": "⚪",
    }.get(result.signal, "")

    msg = (
        f"<b>{result.ticker} — {result.name}</b>\n"
        f"{signal_emoji} <b>{result.signal.replace('_', ' ')}</b> · {result.category}\n"
        f"{lynch_ok}\n"
        f"\n<b>📊 Criterios Peter Lynch</b>\n"
        f"{peg_ok} PEG:          {_v(result.peg, 3)}  <i>(≤ 1.0)</i>\n"
        f"{pe_ok} P/E:           {_v(result.pe, 1)}  <i>(> 0)</i>\n"
        f"{grw_ok} Crec. EPS:    {_v(result.earnings_growth_pct, 1, '%')}  <i>(> 0%)</i>\n"
        f"{de_ok} Deuda/Pat:     {_v(result.debt_to_equity, 2)}  <i>(< 0.5)</i>\n"
        f"{fcf_ok} FCF:          {_fcf_icon(result.free_cash_flow)}  <i>(> 0)</i>\n"
        f"{fvr_ok} FV ratio:     {_v(result.fair_value_ratio, 2)}  <i>(≥ 1.5)</i>\n"
        f"  Div. yield:    {_v(result.dividend_yield_pct, 2, '%')}\n"
        f"\n<b>📈 Análisis Técnico</b>\n"
        f"  RSI (14):      {rsi_label}\n"
        f"  MACD hist:     {macd_label}\n"
        f"  vs SMA 50:     {sma50}\n"
        f"  vs SMA 200:    {sma200}\n"
        f"\n<i>↳ {result.signal_reason}</i>"
    )
    _send(msg)


# ── Other command handlers ────────────────────────────────────────────────────

def _cmd_add(ticker: str, tickers: list[str], wl_data: dict, wl_sha: str | None) -> list[str]:
    if ticker in tickers:
        _send(f"⚠️ <b>{ticker}</b> ya está en tu watchlist.")
        return tickers
    tickers.append(ticker)
    wl_data["tickers"] = tickers
    _save_watchlist(wl_data, wl_sha, ticker, "add")
    _send(f"✅ <b>{ticker}</b> agregado a la watchlist.\n\nSe analizará en el próximo reporte (11:00 AM Santiago).")
    return tickers


def _cmd_remove(ticker: str, tickers: list[str], wl_data: dict, wl_sha: str | None) -> list[str]:
    if ticker not in tickers:
        _send(f"⚠️ <b>{ticker}</b> no está en tu watchlist.")
        return tickers
    tickers.remove(ticker)
    wl_data["tickers"] = tickers
    _save_watchlist(wl_data, wl_sha, ticker, "remove")
    _send(f"🗑 <b>{ticker}</b> eliminado de la watchlist.")
    return tickers


def _cmd_list(tickers: list[str]) -> None:
    if not tickers:
        _send("Tu watchlist está vacía.\n\nUsa /add TICKER para agregar (ej. /add AAPL).")
        return
    lines = [f"📋 <b>Watchlist ({len(tickers)} acciones):</b>"]
    for t in tickers:
        lines.append(f"  • {t}")
    _send("\n".join(lines))


def _cmd_help() -> None:
    _send(
        "🤖 <b>LynchFinder Bot — Comandos</b>\n\n"
        "/check TICKER — análisis completo de una acción\n"
        "  ej: /check AAPL\n"
        "  ej: /check SQM-B.SN\n\n"
        "/add TICKER — agregar a watchlist\n"
        "  ej: /add AAPL\n\n"
        "/remove TICKER — eliminar de watchlist\n"
        "  ej: /remove AAPL\n\n"
        "/list — ver watchlist actual\n\n"
        "/help — este mensaje\n\n"
        "<i>⚠️ El bot revisa mensajes cada ~5 min.</i>"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def process_commands() -> None:
    offset, offset_sha = _load_offset()
    updates = _get_updates(offset + 1)

    if not updates:
        print("[bot] Sin mensajes nuevos.")
        return

    wl_data, wl_sha = _load_watchlist()
    tickers = [t.upper() for t in wl_data.get("tickers", [])]
    new_offset = offset

    for update in updates:
        new_offset = max(new_offset, update["update_id"])

        msg     = update.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text    = msg.get("text", "").strip()

        if chat_id != TELEGRAM_CHAT_ID:
            continue

        parts = text.split()
        cmd   = parts[0].lower().split("@")[0] if parts else ""
        arg   = parts[1].upper() if len(parts) > 1 else ""

        if cmd == "/check":
            if not arg:
                _send("Uso: /check TICKER\nEjemplo: /check AAPL")
            else:
                _cmd_check(arg)

        elif cmd == "/add":
            if not arg:
                _send("Uso: /add TICKER\nEjemplo: /add AAPL")
            else:
                tickers = _cmd_add(arg, tickers, wl_data, wl_sha)
                wl_data["tickers"] = tickers
                _, wl_sha = _load_watchlist()

        elif cmd in ("/remove", "/del"):
            if not arg:
                _send("Uso: /remove TICKER\nEjemplo: /remove AAPL")
            else:
                tickers = _cmd_remove(arg, tickers, wl_data, wl_sha)
                wl_data["tickers"] = tickers
                _, wl_sha = _load_watchlist()

        elif cmd == "/list":
            _cmd_list(tickers)

        elif cmd in ("/help", "/start"):
            _cmd_help()

    if new_offset > offset:
        _save_offset(new_offset, offset_sha)
        print(f"[bot] Offset actualizado: {offset} → {new_offset}")


if __name__ == "__main__":
    process_commands()
