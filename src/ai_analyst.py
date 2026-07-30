"""Análisis IA de candidatos COMPRA_FUERTE usando Groq (gratis)."""

import os
from criteria import LynchResult

_MAX_STOCKS = 3  # analizar solo los mejores para no gastar tokens


def _build_prompt(stocks: list[LynchResult]) -> str:
    lines = [
        "Eres un analista de renta variable estilo Peter Lynch. "
        "Para cada acción, da una conclusión en 2 frases: qué hace atractiva la acción "
        "y cuál es el mayor riesgo a vigilar. Responde en español, sin adornos.\n"
    ]
    for r in stocks:
        lines.append(
            f"\n{r.ticker} — {r.name} ({r.sector})\n"
            f"  PEG={r.peg:.2f}  P/E={r.pe:.1f}  Crec.EPS={r.earnings_growth_pct:.1f}%\n"
            f"  D/E={r.debt_to_equity}  FCF={'pos' if r.free_cash_flow and r.free_cash_flow > 0 else 'neg/nd'}\n"
            f"  FV ratio={r.fair_value_ratio}  RSI={r.rsi}  vs SMA50={r.price_vs_sma50}%"
        )
    return "\n".join(lines)


def analyze(stocks: list[LynchResult]) -> dict[str, str]:
    """
    Returns {ticker: "análisis breve"} for top COMPRA_FUERTE stocks.
    Silently skips if GROQ_API_KEY / openai package not available.
    """
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {}

    try:
        from openai import OpenAI
    except ImportError:
        return {}

    candidates = stocks[:_MAX_STOCKS]
    if not candidates:
        return {}

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.environ.get("LANGCHAIN_MODEL_NAME", "llama-3.3-70b-versatile")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _build_prompt(candidates)}],
            max_tokens=600,
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        print(f"[ai_analyst] Error llamando API: {e}")
        return {}

    # Parse: each ticker's analysis follows its header line
    results: dict[str, str] = {}
    current_ticker = None
    current_lines: list[str] = []

    for line in raw.splitlines():
        for r in candidates:
            if line.startswith(r.ticker):
                if current_ticker and current_lines:
                    results[current_ticker] = " ".join(current_lines).strip()
                current_ticker = r.ticker
                current_lines = []
                break
        else:
            if current_ticker and line.strip():
                current_lines.append(line.strip())

    if current_ticker and current_lines:
        results[current_ticker] = " ".join(current_lines).strip()

    return results
