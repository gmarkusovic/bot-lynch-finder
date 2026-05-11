# LynchFinder — Arquitectura Detallada
> Referenciado con `@docs/architecture.md`. Usar `ultrathink` para tareas que modifiquen este documento.

---

## Diagrama de módulos

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                 │
│   --mode screener|watchlist|all   --market usa|europe|chile     │
│                                                                 │
│   run_screener()                  run_watchlist()               │
│       │                               │                         │
│       ▼                               ▼                         │
│   universe.py                     watchlist.json                │
│   ├─ get_sp500_tickers()          (tickers manuales)            │
│   ├─ EUROPE_TICKERS (static)                                    │
│   └─ CHILE_TICKERS (static)                                     │
│       │                               │                         │
│       ▼                               ▼                         │
│   fetcher.py                      fetcher.py                    │
│   fetch_fundamentals()            fetch_fundamentals_lenient()  │
│       │                               │                         │
│       ▼                               ▼                         │
│   criteria.py                     criteria.py                   │
│   apply_lynch_filters()           apply_lynch_filters_watchlist()
│       │                               │                         │
│       ▼                               ▼                         │
│   fetcher.py ◄────────────────────────┘                        │
│   fetch_history(period="1y")                                    │
│       │                                                         │
│       ▼                                                         │
│   technical.py                                                  │
│   compute_technical(closes)                                     │
│   ├─ compute_rsi(period=14)                                     │
│   ├─ compute_macd(fast=12, slow=26, signal=9)                  │
│   └─ compute_sma_distance(50) + compute_sma_distance(200)      │
│       │                                                         │
│       ▼                                                         │
│   signals.py                                                    │
│   evaluate_signal(LynchResult, TechnicalData) → LynchResult    │
│       │                                                         │
│       ▼                                                         │
│   reporter.py                                                   │
│   ├─ save_results()       → results/YYYY-MM-DD_{market}.csv    │
│   ├─ print_summary()      → screener output                    │
│   ├─ print_alerts()       → buy/sell alerts                    │
│   └─ print_watchlist_summary() → watchlist output              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Modelo de datos principal: `LynchResult`

```python
@dataclass
class LynchResult:
    # Identificación
    ticker: str
    name: str
    sector: str
    industry: str

    # Precio
    price: float | None
    market_cap: float | None

    # Fundamentales (Lynch)
    pe: float
    earnings_growth_pct: float      # porcentaje (20.0 = 20%)
    peg: float                       # pe / earnings_growth_pct
    debt_to_equity: float | None
    free_cash_flow: float | None
    dividend_yield_pct: float
    fair_value_ratio: float | None   # (growth% + div%) / PE
    category: str                    # Fast Grower / Stalwart / Slow Grower
    passes_all: bool

    # Técnico (populate post fetch_history)
    rsi: float | None = None
    macd_histogram: float | None = None
    price_vs_sma50: float | None = None
    price_vs_sma200: float | None = None

    # Señal combinada
    signal: str = "PENDIENTE"
    signal_reason: str = ""
```

---

## Lógica de señales (`signals.py`)

```
RSI > 70 + MACD bearish   →  VENTA
RSI > 70                  →  SOBRECOMPRADA
Lynch OK + RSI < 30 + MACD bullish  →  COMPRA_FUERTE
Lynch OK + (RSI < 45 OR MACD bullish)  →  COMPRA
Lynch OK + technical neutral  →  SEGUIMIENTO
(default)  →  NEUTRAL
```

Invariante: `VENTA`/`SOBRECOMPRADA` toman prioridad sobre cualquier señal de compra.

---

## Cobertura de mercados

| Mercado | Universo | Fuente | Tickers aprox. |
|---|---|---|---|
| USA | S&P 500 | Wikipedia (scraping runtime) | ~503 |
| Europa | STOXX 600 representativo | Lista estática en `universe.py` | ~110 |
| Chile | IPSA | Lista estática en `universe.py` | 30 |
| Watchlist | Manual | `watchlist.json` | ilimitado |

**Tasa de datos disponibles estimada:** USA ~70% · Europa ~60% · Chile ~40% (Yahoo Finance tiene menor cobertura de fundamentales para mercados pequeños).

---

## Concurrencia y rate limiting

```
ThreadPoolExecutor(max_workers=5)
├─ fetch_fundamentals: sleep=0.3s por ticker
└─ fetch_history:      sleep=0.2s por ticker

Estimado por mercado:
  Chile (30):   ~30 × 0.5s ÷ 5 workers ≈ 3 min
  Europa (110): ~110 × 0.5s ÷ 5 workers ≈ 11 min
  USA (503):    ~503 × 0.5s ÷ 5 workers ≈ 50 min
```

Aumentar `max_workers` sin pruebas puede resultar en bloqueo de IP por Yahoo Finance.

---

## GitHub Actions scheduling

```yaml
cron: '0 14 * * 1-5'
# 14:00 UTC = 11:00 Santiago (CLT, UTC-3)
#           = 10:00 New York (EDT, UTC-4)
#           = 16:00 Madrid (CEST, UTC+2)
```

Los mercados europeos cierran ~17:30 CET; USA cierra ~21:00 UTC. El cron en 14:00 UTC captura datos intraday de USA y pre-cierre de Europa.

---

## Decisiones de diseño

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| yfinance (no oficial) | Alpha Vantage, FMP free | Sin API key, sin límites duros |
| Lista estática Europa | Scraping STOXX 600 | Estructura HTML inestable |
| ThreadPoolExecutor | asyncio | yfinance no es async-safe |
| CSV output | SQLite, JSON | Portabilidad y apertura en Excel |
| GitHub Actions | PythonAnywhere, Render | Gratis ilimitado en repos públicos |

---

## Extensiones planificadas (no implementadas)

- [ ] Notificaciones por email (SendGrid free tier) cuando haya COMPRA_FUERTE
- [ ] Gráfico RSI+MACD en HTML para cada ticker de watchlist (matplotlib)
- [ ] Soporte para `--ticker AAPL` one-shot sin correr todo el mercado
- [ ] Score compuesto 0-100 ponderando Lynch + técnico
