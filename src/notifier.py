"""Send Telegram notifications with full Lynch + technical detail per stock."""

import os
import requests

from criteria import LynchResult
from utils import fmt, fcf_icon, pages_url, SIGNAL_EMOJI, SIGNAL_ORDER, SHOW_SIGNALS


def _rsi_label(rsi: float | None) -> str:
    if rsi is None:
        return "—"
    if rsi < 30:
        return f"{rsi:.1f} 🟢 Sobreventa fuerte"
    if rsi < 45:
        return f"{rsi:.1f} 🟡 Zona favorable"
    if rsi < 65:
        return f"{rsi:.1f} ⚪ Neutral"
    if rsi < 70:
        return f"{rsi:.1f} 🟠 Zona alta"
    return f"{rsi:.1f} 🔴 Sobrecomprada"


def _macd_label(mh: float | None) -> str:
    if mh is None:
        return "—"
    return f"{mh:.4f} 📈 Alcista" if mh > 0 else f"{mh:.4f} 📉 Bajista"


def _stock_block(r: LynchResult) -> str:
    emoji  = SIGNAL_EMOJI.get(r.signal, "")
    lynch  = "✅ Lynch OK" if r.passes_all else "❌ Lynch NO"
    price  = f"${r.price:,.2f}" if r.price else "—"
    peg_ok = "✅" if r.peg and r.peg <= 1.0 else "❌"
    pe_ok  = "✅" if r.pe and r.pe > 0 else "❌"
    grw_ok = "✅" if r.earnings_growth_pct > 0 else "❌"
    de_ok  = ("✅" if r.debt_to_equity is not None and r.debt_to_equity < 0.5
              else "⚠️" if r.debt_to_equity is None else "❌")
    fcf_ok = ("✅" if r.free_cash_flow and r.free_cash_flow > 0
              else "❌" if r.free_cash_flow is not None else "⚠️")
    fvr_ok = ("✅" if r.fair_value_ratio and r.fair_value_ratio >= 1.5
              else "❌" if r.fair_value_ratio is not None else "⚠️")
    sma50  = f"{r.price_vs_sma50:+.1f}%"  if r.price_vs_sma50  is not None else "—"
    sma200 = f"{r.price_vs_sma200:+.1f}%" if r.price_vs_sma200 is not None else "—"

    return (
        f"\n{r.ticker} - {r.name}\n"
        f"💲 Precio: {price}\n"
        f"{emoji} {r.signal.replace('_', ' ')} · {r.category} · {lynch}\n"
        f"— Criterios Lynch —\n"
        f"{peg_ok} PEG:       {fmt(r.peg, 3)}  (<=1.0)\n"
        f"{pe_ok} P/E:        {fmt(r.pe, 1)}  (>0)\n"
        f"{grw_ok} Crec.EPS: {fmt(r.earnings_growth_pct, 1, '%')}  (>0%)\n"
        f"{de_ok} Deuda/Pat: {fmt(r.debt_to_equity, 2)}  (<0.5)\n"
        f"{fcf_ok} FCF:       {fcf_icon(r.free_cash_flow)}  (>0)\n"
        f"{fvr_ok} FV ratio:  {fmt(r.fair_value_ratio, 2)}  (>=1.5)\n"
        f"   Div. yield: {fmt(r.dividend_yield_pct, 2, '%')}\n"
        f"— Tecnico —\n"
        f"  RSI(14):   {_rsi_label(r.rsi)}\n"
        f"  MACD hist: {_macd_label(r.macd_histogram)}\n"
        f"  SMA50: {sma50}  SMA200: {sma200}\n"
        f">> {r.signal_reason}"
    )


def _format_results(all_results: dict[str, list[LynchResult]], date_str: str) -> str:
    lines = [f"📊 LynchFinder — {date_str}"]

    for market, results in all_results.items():
        if not results:
            continue

        visible = [r for r in results if r.signal in SHOW_SIGNALS]
        if not visible:
            lines.append(f"\n<b>── {market.upper()} ──</b>")
            lines.append("Sin alertas destacadas hoy.")
            continue

        by_signal: dict[str, list[LynchResult]] = {s: [] for s in SIGNAL_ORDER}
        for r in visible:
            by_signal[r.signal].append(r)

        lines.append(f"\n{'='*22} {market.upper()} {'='*22}")

        for signal in SIGNAL_ORDER:
            group = sorted(by_signal[signal], key=lambda r: r.peg if r.peg else 99)
            if not group:
                continue
            emoji = SIGNAL_EMOJI.get(signal, "")
            lines.append(f"\n{emoji} {signal.replace('_', ' ')} ({len(group)})")
            for r in group:
                lines.append(_stock_block(r))
                lines.append("-" * 32)

    url = pages_url()
    if url:
        lines.append(f"\n🔗 <a href=\"{url}\">Ver reporte visual completo</a>")

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
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        if not resp.ok:
            print(f"[notifier] Telegram error: {resp.status_code} — {resp.text[:300]}")
        return resp.ok
    except Exception as e:
        print(f"[notifier] Excepción al enviar: {e}")
        return False


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

    message = _format_results(all_results, date_str)
    chunks  = _split_message(message)
    print(f"[notifier] Enviando {len(chunks)} mensaje(s), total {len(message)} chars.")

    for i, chunk in enumerate(chunks, 1):
        ok = _post(token, chat_id, chunk)
        print(f"[notifier] Mensaje {i}/{len(chunks)} {'enviado' if ok else 'ERROR'}.")
