# src/ — CLAUDE.md (dominio: pipeline de datos)
> Reglas específicas del directorio `src/`. Complementa el CLAUDE.md raíz — no reemplaza.

---

## Responsabilidades por módulo

| Archivo | Hace | No hace |
|---|---|---|
| `universe.py` | Define/obtiene listas de tickers | Nunca toca datos de precios |
| `fetcher.py` | Descarga datos de Yahoo Finance | Nunca calcula nada, nunca imprime |
| `criteria.py` | Define `LynchResult` y aplica filtros Lynch | Nunca toca datos técnicos |
| `technical.py` | Calcula RSI, MACD, SMA desde closes | Nunca conoce a Lynch ni señales |
| `signals.py` | Combina Lynch + técnico en una señal | Nunca descarga datos, nunca imprime |
| `reporter.py` | Formatea e imprime resultados | Nunca calcula nada |
| `main.py` | Orquesta el pipeline completo | Nunca contiene lógica de negocio |

---

## Contratos de tipos críticos

```python
# fetcher.fetch_fundamentals → dict con estas claves o None
{
  "ticker": str, "name": str, "sector": str, "industry": str,
  "price": float|None, "market_cap": float|None,
  "pe": float, "earnings_growth": float,       # ambos > 0 garantizados
  "debt_to_equity": float|None, "free_cash_flow": float|None,
  "dividend_yield": float, "total_cash": float|None,
  "total_debt": float|None, "trailing_eps": float|None,
}

# fetcher.fetch_history → pd.Series de closes diarios, len >= 35, o None
# technical.compute_technical → TechnicalData dataclass (campos pueden ser None)
# signals.evaluate_signal → LynchResult (mutado via dataclasses.replace)
```

---

## Invariantes que no romper

1. `fetcher.py` nunca eleva excepciones al caller — toda excepción → `return None`
2. `signals.py` nunca devuelve `None` — siempre retorna un `LynchResult` con alguna señal
3. `criteria.apply_lynch_filters` devuelve `None` solo cuando PE o growth es `None`/≤0
4. `criteria.apply_lynch_filters_watchlist` **nunca** devuelve `None` (modo lenient)
5. `time.sleep()` en `fetcher.py` se ejecuta incluso en el bloque `except` — sin omitir

---

## Agregar un nuevo mercado (checklist)

- [ ] Agregar lista `NUEVO_TICKERS` en `universe.py`
- [ ] Agregar entrada en `_MARKETS` dict de `main.py`
- [ ] Agregar al argparse `--market choices` en `main.py`
- [ ] Actualizar tabla de cobertura en `docs/architecture.md`
- [ ] Actualizar sección 2 del CLAUDE.md raíz

## Agregar un nuevo criterio Lynch (checklist)

- [ ] Agregar constante umbral en `criteria.py`
- [ ] Agregar campo en `LynchResult` dataclass (con default si es opcional)
- [ ] Agregar a la condición `passes` en `apply_lynch_filters`
- [ ] Agregar manejo en `apply_lynch_filters_watchlist` (puede quedar None)
- [ ] Actualizar tabla de señales en CLAUDE.md raíz sección 1
- [ ] Verificar con `python src/main.py --mode watchlist`
