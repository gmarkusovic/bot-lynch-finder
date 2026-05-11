"""
Telegram bot command handler — runs via GitHub Actions cron every 5 minutes.
Reads new messages, processes /add /remove /list /help commands,
and updates watchlist.json in the repo via GitHub API.
"""

import os
import json
import base64
import requests

TELEGRAM_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])
GITHUB_TOKEN    = os.environ["GITHUB_TOKEN"]
GITHUB_REPO     = os.environ["GITHUB_REPO"]   # e.g. "gmarkusovic/bot-lynch-finder"

_GH_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}
_WATCHLIST_PATH    = "watchlist.json"
_OFFSET_PATH       = "data/last_update_id.txt"


# ── GitHub API helpers ────────────────────────────────────────────────────────

def _gh_get(path: str) -> tuple[str | None, str | None]:
    """Return (decoded_content, sha) or (None, None) if file doesn't exist."""
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


# ── Command handlers ──────────────────────────────────────────────────────────

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
        "/add TICKER — agregar acción a watchlist\n"
        "  ej: /add AAPL\n"
        "  ej: /add SQM-B.SN\n\n"
        "/remove TICKER — eliminar de watchlist\n"
        "  ej: /remove AAPL\n\n"
        "/list — ver todas las acciones en seguimiento\n\n"
        "/help — mostrar este mensaje\n\n"
        "<i>El screener corre automáticamente lunes–viernes 11:00 AM Santiago.</i>"
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

        # Ignore messages from unauthorized users
        if chat_id != TELEGRAM_CHAT_ID:
            continue

        parts  = text.split()
        cmd    = parts[0].lower().split("@")[0] if parts else ""
        arg    = parts[1].upper() if len(parts) > 1 else ""

        if cmd == "/add":
            if not arg:
                _send("Uso: /add TICKER\nEjemplo: /add AAPL")
            else:
                tickers = _cmd_add(arg, tickers, wl_data, wl_sha)
                wl_data["tickers"] = tickers
                _, wl_sha = _load_watchlist()   # refresh sha after write

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
