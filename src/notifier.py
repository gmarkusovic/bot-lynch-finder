"""Send Telegram notifications with full Lynch + technical detail per stock."""

import os
import requests

from criteria import LynchResult

_SIGNAL_EMOJI = {
    "COMPRA_FUERTE": "🚀",
    "COMPRA":        "🟢",
    "SEGUIMIENTO":   "👀",
    "SOBRECOMPRADA": "⚠️",
    "VENTA":         "🔴",
    "NEUTRAL":       "⚪",
    "PENDIENTE":     "⏳",
}

_SIGNAL_ORDER = ["COMPRA_FUERTE", "COMPRA", "SEGUIMIENTO", "SOBRECOMPRADA", "VENTA"]

_SHOW_SIGNALS = {"COMPRA_FUERTE", "COMPRA", "SEGUIMIENTO", "SOBRECOMPRADA", "VENTA"}


def _v(val, decimals: int = 2, suffix: str = "") -> str:
    """Format a numeric value or return '—' if None."""
    if val is None:
        return "—"
    return f"{val:.{decimals}f}{suffix}"


def _fcf_icon(fcf) -> str:
    if fcf is None:
        return "—"
    return "✅" if fcf > 0 else "❌"


def _stock_block(r: LynchResult) -> str:
    """Full detail block for one stock."""
    emoji  = _SIGNAL_EMOJI.get(r.signal, "")
    lynch  = "✅ Lynch OK" if r.passes_all else "❌ Lynch NO"

    # Lynch fundamentals
    peg    = _v(r.peg, 3)
    pe     = _v(r.pe, 1)
    growth = _v(r.earnings_growth_pct, 1, "%")
    de     = _v(r.debt_to_equity, 2)
    fvr    = _v(r.fair_value_ratio, 2)
    div    = _v(r.dividend_yield_pct, 2, "%")
    fcf    = _fcf_icon(r.free_cash_flow)

    # Technical
    rsi    = _v(r.rsi, 1)
    macd   = _v(r.macd_histogram, 4)
    sma50  = (_v(r.price_vs_sma50, 1, "%") if r.price_vs_sma50 is not None
              else "—")
    sma200 = (_v(r.price_vs_sma200, 1, "%") if r.price_vs_sma200 is not None
              else "—")

    price  = f"${r.price:,.2f}" if r.price else "—"

    return (
        f"\n<b>{r.ticker} - {r.name}</b>\n"
        f"💲 Precio: <b>{price}</b>\n"
        f"{emoji} <b>{r.signal.replace('_', ' ')}</b> · {r.category} · {lynch}\n"
        f"<b>— Criterios Lynch —</b>\n"
        f"  PEG: {peg}   P/E: {pe}   Crec. EPS: {growth}\n"
        f"  Deuda/Pat: {de}   FV ratio: {fvr}\n"
        f"  Div. yield: {div}   FCF: {fcf}\n"
        f"<b>— Técnico —</b>\n"
        f"  RSI(14): {rsi}   MACD hist: {macd}\n"
        f"  vs SMA50: {sma50}   vs SMA200: {sma200}\n"
        f"<i>↳ {r.signal_reason}</i>"
    )


def _format_results(all_results: dict[str, list[LynchResult]], date_str: str) -> str:
    lines = [f"<b>📊 LynchFinder — {date_str}</b>"]

    for market, results in all_results.items():
        if not results:
            continue

        # Filter and group by signal
        visible = [r for r in results if r.signal in _SHOW_SIGNALS]
        if not visible:
            lines.append(f"\n<b>── {market.upper()} ──</b>")
            lines.append("Sin alertas destacadas hoy.")
            continue

        by_signal: dict[str, list[LynchResult]] = {s: [] for s in _SIGNAL_ORDER}
        for r in visible:
            if r.signal in by_signal:
                by_signal[r.signal].append(r)

        lines.append(f"\n<b>{'═'*20} {market.upper()} {'═'*20}</b>")

        for signal in _SIGNAL_ORDER:
            group = sorted(by_signal[signal], key=lambda r: r.peg if r.peg else 99)
            if not group:
                continue
            emoji = _SIGNAL_EMOJI.get(signal, "")
            lines.append(f"\n{emoji} <b>{signal.replace('_', ' ')} ({len(group)})</b>")
            for r in group:
                lines.append(_stock_block(r))
                lines.append("─" * 30)

    # GitHub Pages link
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        owner, repo_name = repo.split("/", 1)
        pages_url = f"https://{owner}.github.io/{repo_name}/"
        lines.append(f"\n🔗 <a href=\"{pages_url}\">Ver reporte visual completo</a>")

    return "\n".join(lines)


_MAX_CHARS = 4096


def _split_message(text: str) -> list[str]:
    """Split into ≤4096-char chunks, breaking only on newlines."""
    if len(text) <= _MAX_CHARS:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = current + line + "\n"
        if len(candidate) > _MAX_CHARS:
            if current:
                chunks.append(current.rstrip("\n"))
            current = line + "\n"
        else:
            current = candidate

    if current.strip():
        chunks.append(current.rstrip("\n"))

    return chunks


def _post(token: str, chat_id: str, text: str) -> bool:
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    return resp.ok


def send_telegram(all_results: dict[str, list[LynchResult]], date_str: str) -> None:
    """
    Send Telegram message(s) with full Lynch + technical detail per stock.
    Splits automatically into multiple messages if content exceeds 4096 chars.
    """
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[notifier] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados — omitiendo.")
        return

    chunks = _split_message(_format_results(all_results, date_str))

    try:
        for i, chunk in enumerate(chunks, 1):
            ok = _post(token, chat_id, chunk)
            status = "enviado" if ok else "ERROR"
            print(f"[notifier] Mensaje {i}/{len(chunks)} {status}.")
    except Exception as e:
        print(f"[notifier] No se pudo enviar a Telegram: {e}")
