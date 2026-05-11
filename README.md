# Bot LynchFinder

Screener automático de acciones basado en los criterios de **Peter Lynch** combinados con **análisis técnico** (RSI y MACD). Cubre **USA** (S&P 500), **Europa** (~110 acciones STOXX 600) y **Chile** (IPSA ~30 acciones). Usa `yfinance` — sin API key ni costo. Se ejecuta en la nube vía **GitHub Actions**.

---

## Señales generadas

| Señal | Condición |
|---|---|
| `*** COMPRA FUERTE ***` | Lynch OK + RSI < 30 (sobreventa) + MACD alcista |
| `**  COMPRA          **` | Lynch OK + RSI < 45 O MACD alcista |
| `    SEGUIMIENTO      ` | Lynch OK, pero técnico neutro o mixto |
| `!!! SOBRECOMPRADA !!!` | RSI > 70 (independiente de fundamentales) |
| `!!! VENTA/CAUTELA !!!` | RSI > 70 + MACD bajista |
| `    NEUTRAL          ` | No cumple Lynch + sin extremos técnicos |

---

## Criterios de Peter Lynch

| Criterio | Umbral | Descripción |
|---|---|---|
| **PEG ratio** | ≤ 1.0 | P/E ÷ crecimiento EPS % |
| **P/E** | > 0 | Empresa rentable |
| **EPS growth** | > 0% | Crecimiento positivo |
| **Debt/Equity** | < 0.5 | Bajo endeudamiento |
| **Free Cash Flow** | > 0 | Genera caja |
| **Fair Value ratio** | ≥ 1.5 | (EPS growth % + div yield %) / P/E |

---

## Uso local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Screener — busca oportunidades en el mercado completo
python src/main.py --mode screener --market chile      # Solo Chile (~2 min)
python src/main.py --mode screener --market europe     # Solo Europa (~5 min)
python src/main.py --mode screener --market usa        # S&P 500 (~15 min)
python src/main.py --mode screener --market all        # Todos los mercados

# 3. Watchlist — analiza tickers que tienes en seguimiento
python src/main.py --mode watchlist

# 4. Ambos a la vez
python src/main.py --mode all --market chile
```

Los resultados se guardan en `results/YYYY-MM-DD_{market}.csv`.

---

## Configurar tu watchlist

Edita `watchlist.json` en la raíz del proyecto:

```json
{
  "description": "Mis tickers en seguimiento",
  "tickers": [
    "SQM-B.SN",
    "AAPL",
    "MC.PA",
    "NVDA"
  ]
}
```

En modo watchlist, los tickers son analizados aunque **no pasen los criterios Lynch** — el objetivo es ver su señal técnica y estado fundamental en todo momento.

---

## Ejecución automática en la nube (GitHub Actions)

El bot corre **automáticamente** lunes a viernes a las **14:00 UTC** (11:00 Santiago, 10:00 NY, 16:00 Madrid) sin necesitar tu computador.

### Activar en GitHub

1. Sube el proyecto a un repositorio GitHub
2. Ve a **Actions** → habilitar workflows si es necesario
3. Trigger manual: **Actions → "Lynch Screener" → "Run workflow"**
4. Los resultados aparecen como **Artifacts** en cada run (retención 30 días)

---

## Estructura del proyecto

```
├── CLAUDE.md                        # Contexto para Claude Code
├── README.md
├── requirements.txt
├── watchlist.json                   # Tickers en seguimiento personal
├── .github/workflows/screener.yml   # Cron automático
├── src/
│   ├── main.py         # Orquestador CLI
│   ├── universe.py     # Universo de tickers por mercado
│   ├── fetcher.py      # Descarga de fundamentales e historial (yfinance)
│   ├── criteria.py     # Filtros y dataclass LynchResult
│   ├── technical.py    # RSI(14), MACD(12,26,9), SMA50/200
│   ├── signals.py      # Señales COMPRA/VENTA/SEGUIMIENTO
│   └── reporter.py     # Output a consola y CSV
└── results/            # CSVs generados
```

---

## Notas

- `yfinance` usa Yahoo Finance. Fundamentales no siempre disponibles para todas las acciones → se omiten automáticamente en modo screener.
- El PEG usa crecimiento TTM (Trailing Twelve Months). Lynch prefería proyecciones, pero no están disponibles gratis.
- Este screener es un **primer filtro** — no reemplaza el análisis manual que Lynch recomienda antes de invertir.
- RSI y MACD usan datos de cierre diario del último año.
