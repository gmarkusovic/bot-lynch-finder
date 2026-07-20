"""
News enrichment for COMPRA_FUERTE/COMPRA signals using yfinance (no API key required).

Fetches recent headlines per ticker in parallel and formats them for Telegram.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone


def _fetch_news(ticker: str, company_name: str) -> tuple[str, str]:
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).news or []
    except Exception:
        return ticker, ""

    headlines: list[str] = []
    for item in info[:5]:
        # yfinance >= 0.2.x wraps content under 'content' key; older versions are flat
        content = item.get("content") or item
        title = content.get("title") or item.get("title") or ""
        if not title:
            continue

        source = (
            (content.get("provider") or {}).get("displayName")
            or item.get("publisher")
            or ""
        )
        pub_raw = content.get("pubDate") or ""
        try:
            if pub_raw:
                dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                date_str = dt.astimezone(timezone.utc).strftime("%d/%m")
            else:
                ts = item.get("providerPublishTime")
                date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d/%m") if ts else ""
        except Exception:
            date_str = ""

        meta = " · ".join(filter(None, [source, date_str]))
        headlines.append(f"• {title}" + (f" ({meta})" if meta else ""))

    text = "\n".join(headlines)
    return ticker, text


def enrich_signals(candidates: list[tuple[str, str]]) -> dict[str, str]:
    """
    Fetch recent news headlines for each (ticker, company_name) pair in parallel.
    Returns {ticker: formatted_headlines}. Always free — uses yfinance, no API key.
    """
    if not candidates:
        return {}

    research: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_fetch_news, t, n): t for t, n in candidates}
        for future in as_completed(futures):
            try:
                ticker, text = future.result()
                if text:
                    research[ticker] = text
            except Exception as e:
                print(f"[enricher] Error obteniendo noticias: {e}")

    found = len(research)
    print(f"[enricher] Noticias obtenidas para {found}/{len(candidates)} ticker(s).")
    return research
