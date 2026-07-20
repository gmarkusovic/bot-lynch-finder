"""
Async web research for actionable signals via GPT Researcher.

Requires TAVILY_API_KEY and OPENAI_API_KEY (or ANTHROPIC_API_KEY) set as env vars.
Only called for COMPRA_FUERTE and COMPRA signals — silently skipped otherwise.
"""

import asyncio
import os

_MAX_CHARS = 1000
_MAX_TICKERS = 8  # cap to avoid hitting rate limits / timeout in GitHub Actions
_ENRICH_SIGNALS = {"COMPRA_FUERTE", "COMPRA"}


async def _research_one(ticker: str, company_name: str) -> tuple[str, str]:
    from gpt_researcher import GPTResearcher

    query = (
        f"{company_name} ({ticker}) stock 2025: "
        f"recent earnings, revenue growth, key risks, catalysts, competitive position"
    )
    researcher = GPTResearcher(
        query=query,
        report_type="research_report",
        verbose=False,
    )
    await researcher.conduct_research()
    report = await researcher.write_report()
    text = report[:_MAX_CHARS] + ("…" if len(report) > _MAX_CHARS else "")
    return ticker, text


async def _research_all(candidates: list[tuple[str, str]]) -> dict[str, str]:
    tasks = [_research_one(ticker, name) for ticker, name in candidates]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    result: dict[str, str] = {}
    for item in outcomes:
        if isinstance(item, Exception):
            print(f"[enricher] Research error: {item}")
        else:
            ticker, text = item
            result[ticker] = text
    return result


def enrich_signals(candidates: list[tuple[str, str]]) -> dict[str, str]:
    """
    Run GPT Researcher for each (ticker, company_name) pair in parallel.

    Candidates are expected pre-filtered to COMPRA_FUERTE / COMPRA signals only,
    sorted by priority (best signal + lowest PEG first). Capped at _MAX_TICKERS.
    Returns {ticker: research_text}. Returns {} if env vars are missing.
    """
    if not candidates:
        return {}

    has_tavily = bool(os.environ.get("TAVILY_API_KEY"))
    has_llm = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
    if not has_tavily or not has_llm:
        print("[enricher] TAVILY_API_KEY o LLM API key no configurados — omitiendo research.")
        return {}

    batch = candidates[:_MAX_TICKERS]
    print(f"[enricher] Iniciando research para {len(batch)} ticker(s)…")
    try:
        return asyncio.run(_research_all(batch))
    except Exception as e:
        print(f"[enricher] Error general: {e}")
        return {}
