"""Send Telegram notifications with screening results."""

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


def _format_results(all_results: dict[str, list[LynchResult]], date_str: str) -> str:
    lines = [f"<b>📊 LynchFinder — {date_str}</b>\n"]

    for market, results in all_results.items():
        if not results:
            continue

        compra_fuerte = [r for r in results if r.signal == "COMPRA_FUERTE"]
        compra        = [r for r in results if r.signal == "COMPRA"]
        venta         = [r for r in results if r.signal == "VENTA"]
        sobrecomprada = [r for r in results if r.signal == "SOBRECOMPRADA"]

        if not any([compra_fuerte, compra, venta, sobrecomprada]):
            lines.append(f"<b>{market.upper()}</b>: sin alertas destacadas.")
            continue

        lines.append(f"\n<b>── {market.upper()} ──</b>")

        if compra_fuerte:
            lines.append(f"\n🚀 <b>COMPRA FUERTE ({len(compra_fuerte)})</b>")
            for r in sorted(compra_fuerte, key=lambda x: x.peg):
                rsi = f"RSI={r.rsi:.0f}" if r.rsi else ""
                lines.append(f"  • <b>{r.ticker} - {r.name}</b> — PEG={r.peg:.2f} {rsi}")

        if compra:
            lines.append(f"\n🟢 <b>COMPRA ({len(compra)})</b>")
            for r in sorted(compra, key=lambda x: x.peg):
                rsi = f"RSI={r.rsi:.0f}" if r.rsi else ""
                lines.append(f"  • <b>{r.ticker} - {r.name}</b> — PEG={r.peg:.2f} {rsi}")

        if venta:
            lines.append(f"\n🔴 <b>VENTA/CAUTELA ({len(venta)})</b>")
            for r in sorted(venta, key=lambda x: x.rsi or 0, reverse=True):
                rsi = f"RSI={r.rsi:.0f}" if r.rsi else ""
                lines.append(f"  • <b>{r.ticker} - {r.name}</b> — {rsi}")

        if sobrecomprada:
            lines.append(f"\n⚠️ <b>SOBRECOMPRADA ({len(sobrecomprada)})</b>")
            for r in sorted(sobrecomprada, key=lambda x: x.rsi or 0, reverse=True):
                rsi = f"RSI={r.rsi:.0f}" if r.rsi else ""
                lines.append(f"  • <b>{r.ticker} - {r.name}</b> — {rsi}")

    lines.append("\n<i>Ver CSV completo en GitHub Actions → Artifacts</i>")
    return "\n".join(lines)


_MAX_CHARS = 4096


def _split_message(text: str) -> list[str]:
    """Split a message into chunks of max 4096 chars, breaking only on newlines."""
    if len(text) <= _MAX_CHARS:
        return [text]

    chunks = []
    current = ""
    for line in text.split("\n"):
        # +1 for the newline we'll re-add
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


def send_telegram(
    all_results: dict[str, list[LynchResult]],
    date_str: str,
) -> None:
    """
    Send Telegram message(s) with the screening summary.
    Splits automatically into multiple messages if content exceeds 4096 chars.
    Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment variables.
    """
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[notifier] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados — omitiendo.")
        return

    message = _format_results(all_results, date_str)
    chunks  = _split_message(message)

    try:
        for i, chunk in enumerate(chunks, 1):
            ok = _post(token, chat_id, chunk)
            if ok:
                print(f"[notifier] Mensaje {i}/{len(chunks)} enviado a Telegram.")
            else:
                print(f"[notifier] Error enviando mensaje {i}/{len(chunks)}.")
    except Exception as e:
        print(f"[notifier] No se pudo enviar a Telegram: {e}")
