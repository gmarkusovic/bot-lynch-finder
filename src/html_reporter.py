"""Generate a mobile-friendly HTML report published to GitHub Pages."""

import os
from datetime import date, datetime, timezone

from criteria import LynchResult
from utils import fmt, fcf_icon, SIGNAL_EMOJI, SIGNAL_ORDER, SHOW_SIGNALS

_DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


def _rsi_class(rsi: float | None) -> str:
    if rsi is None:
        return ""
    if rsi < 35:
        return "rsi-low"
    if rsi > 65:
        return "rsi-high"
    return ""


def _card(r: LynchResult) -> str:
    emoji = SIGNAL_EMOJI.get(r.signal, "")
    price = f"${r.price:,.2f}" if r.price else "—"

    return f"""
    <div class="card sig-{r.signal}" data-signal="{r.signal}">
      <div class="card-top">
        <div>
          <span class="ticker">{r.ticker}</span>
          <span class="badge badge-{r.signal}">{emoji} {r.signal.replace('_', ' ')}</span>
        </div>
        <span class="category">{r.category}</span>
      </div>
      <div class="company">{r.name}</div>
      <div class="sector">{r.sector} · {r.industry}</div>
      <div class="metrics">
        <div class="metric"><span class="ml">Precio</span><span class="mv">{price}</span></div>
        <div class="metric"><span class="ml">PEG</span><span class="mv">{fmt(r.peg, 3)}</span></div>
        <div class="metric"><span class="ml">P/E</span><span class="mv">{fmt(r.pe, 1)}</span></div>
        <div class="metric"><span class="ml">Crec.</span><span class="mv">{fmt(r.earnings_growth_pct, 1, '%')}</span></div>
        <div class="metric"><span class="ml">RSI</span><span class="mv {_rsi_class(r.rsi)}">{fmt(r.rsi, 1)}</span></div>
        <div class="metric"><span class="ml">MACD</span><span class="mv">{fmt(r.macd_histogram, 4)}</span></div>
        <div class="metric"><span class="ml">D/E</span><span class="mv">{fmt(r.debt_to_equity, 2)}</span></div>
        <div class="metric"><span class="ml">FV ratio</span><span class="mv">{fmt(r.fair_value_ratio, 2)}</span></div>
        <div class="metric"><span class="ml">FCF</span><span class="mv">{fcf_icon(r.free_cash_flow)}</span></div>
        <div class="metric"><span class="ml">Div.</span><span class="mv">{fmt(r.dividend_yield_pct, 2, '%')}</span></div>
      </div>
      <div class="reason">{r.signal_reason}</div>
    </div>"""


def _market_section(market: str, results: list[LynchResult]) -> str:
    visible = [r for r in results if r.signal in SHOW_SIGNALS]
    ordered = sorted(
        visible,
        key=lambda r: (SIGNAL_ORDER.index(r.signal) if r.signal in SIGNAL_ORDER else 99, r.peg or 99)
    )
    if not ordered:
        return f'<div class="market" id="m-{market}"><div class="no-data">Sin señales destacadas hoy.</div></div>'
    cards = "".join(_card(r) for r in ordered)
    return f'<div class="market" id="m-{market}">{cards}</div>'


def generate_html(all_results: dict[str, list[LynchResult]]) -> str:
    now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    markets = list(all_results.keys())

    if not markets:
        return "<html><body>Sin resultados.</body></html>"

    tabs = "".join(
        f'<button class="tab" id="t-{m}" onclick="showMarket(\'{m}\')">{m.upper()}</button>'
        for m in markets
    )
    sections = "".join(_market_section(m, all_results[m]) for m in markets)
    first    = markets[0]

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LynchFinder — {date.today()}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0d1117; color: #c9d1d9; padding: 16px; font-size: 14px; }}
    h1   {{ font-size: 1.15rem; color: #58a6ff; margin-bottom: 2px; }}
    .sub {{ font-size: 0.78rem; color: #8b949e; margin-bottom: 14px; }}
    .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
    .tab  {{ padding: 6px 16px; border-radius: 20px; border: 1px solid #30363d;
             background: #161b22; color: #c9d1d9; font-size: 0.82rem; cursor: pointer; }}
    .tab.active {{ background: #58a6ff; color: #0d1117; border-color: #58a6ff; font-weight: bold; }}
    .market {{ display: none; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-left: 4px solid #30363d;
             border-radius: 8px; padding: 12px; margin-bottom: 10px; }}
    .sig-COMPRA_FUERTE {{ border-left-color: #2ea043; background: #0d2818; }}
    .sig-COMPRA        {{ border-left-color: #3fb950; }}
    .sig-SEGUIMIENTO   {{ border-left-color: #58a6ff; }}
    .sig-SOBRECOMPRADA {{ border-left-color: #d29922; background: #1f1a0e; }}
    .sig-VENTA         {{ border-left-color: #f85149; background: #2d1015; }}
    .card-top  {{ display: flex; justify-content: space-between; align-items: flex-start;
                  margin-bottom: 4px; gap: 8px; }}
    .ticker    {{ font-weight: 700; font-size: 1rem; margin-right: 6px; }}
    .badge     {{ font-size: 0.68rem; padding: 2px 8px; border-radius: 12px;
                  font-weight: bold; white-space: nowrap; }}
    .badge-COMPRA_FUERTE {{ background: #2ea043; color: #fff; }}
    .badge-COMPRA        {{ background: #3fb950; color: #fff; }}
    .badge-SEGUIMIENTO   {{ background: #1f6feb; color: #fff; }}
    .badge-SOBRECOMPRADA {{ background: #d29922; color: #000; }}
    .badge-VENTA         {{ background: #f85149; color: #fff; }}
    .category {{ font-size: 0.72rem; color: #8b949e; white-space: nowrap; }}
    .company  {{ font-size: 0.82rem; color: #e6edf3; margin-bottom: 2px; }}
    .sector   {{ font-size: 0.72rem; color: #6e7681; margin-bottom: 8px; }}
    .metrics  {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 6px; }}
    .metric   {{ display: flex; flex-direction: column; }}
    .ml       {{ font-size: 0.68rem; color: #8b949e; }}
    .mv       {{ font-size: 0.88rem; font-weight: 600; color: #e6edf3; }}
    .rsi-low  {{ color: #3fb950; }}
    .rsi-high {{ color: #f85149; }}
    .reason   {{ font-size: 0.72rem; color: #8b949e; margin-top: 4px; font-style: italic; }}
    .no-data  {{ color: #6e7681; font-style: italic; padding: 20px 0; }}
  </style>
</head>
<body>
  <h1>📊 LynchFinder</h1>
  <div class="sub">Actualizado: {now}</div>
  <div class="tabs">{tabs}</div>
  {sections}
  <script>
    function showMarket(id) {{
      document.querySelectorAll('.market').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
      document.getElementById('m-' + id).style.display = 'block';
      document.getElementById('t-' + id).classList.add('active');
    }}
    document.addEventListener('DOMContentLoaded', () => showMarket('{first}'));
  </script>
</body>
</html>"""


def save_html_report(all_results: dict[str, list[LynchResult]]) -> str:
    """Generate and save docs/index.html. Returns the file path."""
    os.makedirs(_DOCS_DIR, exist_ok=True)
    path = os.path.join(_DOCS_DIR, "index.html")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(generate_html(all_results))
    except OSError as e:
        print(f"[html_reporter] No se pudo guardar el reporte: {e}")
    return path
