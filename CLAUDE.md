# LynchFinder — CLAUDE.md
> **Documento vivo.** Actualiza este archivo automáticamente cuando cambies arquitectura, comandos o convenciones. Es la referencia fija tras un `/clear`.

---

## 1. Contexto del Proyecto

Screener de acciones basado en **Peter Lynch** (PEG ≤ 1, EPS growth, D/E < 0.5, FCF > 0) combinado con **análisis técnico** (RSI 14, MACD 12-26-9, SMA50/200). Cubre **USA** (S&P 500), **Europa** (STOXX 600) y **Chile** (IPSA). Sin API key — usa `yfinance`. Scheduling automático vía **GitHub Actions** (cron lunes–viernes 14:00 UTC).

**Señales posibles:** `COMPRA_FUERTE` · `COMPRA` · `SEGUIMIENTO` · `SOBRECOMPRADA` · `VENTA` · `NEUTRAL`

---

## 2. Arquitectura

> Para planificación compleja usa `ultrathink` y referencia `@docs/architecture.md`.

**Pipeline de datos (izquierda → derecha):**
```
universe.py ──► fetcher.py ──► criteria.py ──► technical.py ──► signals.py ──► reporter.py
```

| Modo | Entrada | Salida |
|---|---|---|
| `screener` | universo de mercado completo | CSV + `print_summary` + `print_alerts` |
| `watchlist` | `watchlist.json` (lenient) | CSV + `print_watchlist_summary` |
| `all` | ambos simultáneamente | ambas salidas |

Regla de responsabilidad única: `signals.py` = única fuente de verdad para señales. `reporter.py` = único lugar que imprime.

---

## 3. Comandos de Terminal

```bash
# Setup
pip install -r requirements.txt

# Watchlist — rápido, ideal para verificar cambios
python src/main.py --mode watchlist

# Screener por mercado
python src/main.py --mode screener --market chile      # ~2 min
python src/main.py --mode screener --market europe     # ~5 min
python src/main.py --mode screener --market usa        # ~15 min
python src/main.py --mode screener --market all

# Todo junto
python src/main.py --mode all --market chile

# GitHub Actions (sin computador encendido)
# → Actions tab → "Lynch Screener" → "Run workflow"
```

---

## 4. Convenciones de Código

- **Python 3.11+** · type hints obligatorios en toda función pública
- **Sin comentarios** salvo que el WHY sea no obvio para un lector futuro
- **snake_case** variables/funciones · **PascalCase** clases y dataclasses
- Mutación de dataclasses: `dataclasses.replace()` — nunca asignación directa
- Manejo de errores en `fetcher.py`: silencioso — excepción → `return None` → ticker omitido
- `time.sleep(0.3)` entre llamadas fundamentales · `0.2` para historial → **nunca eliminar**
- `ThreadPoolExecutor(max_workers=5)` — no aumentar; Yahoo Finance bloquea IPs agresivas
- Sufijos de tickers: Chile `.SN` · Francia `.PA` · Alemania `.DE` · España `.MC` · UK `.L` · Italia `.MI`

---

## 5. Reglas de Comportamiento (IA)

1. **Leer antes de editar** — `Read` en cualquier archivo antes de modificarlo
2. **No refactorizar sin permiso explícito** del usuario
3. **Verificar con watchlist** tras cada cambio funcional: `python src/main.py --mode watchlist`
4. **Nunca eliminar** los `time.sleep()` de `fetcher.py`
5. **Actualizar este archivo** si cambian comandos, arquitectura o convenciones
6. **Para tareas arquitectónicas** → activar `ultrathink` + leer `@docs/architecture.md`
7. Al agregar un mercado: actualizar `universe.py` + sección 2 de este archivo + `docs/architecture.md`
8. Al agregar un criterio Lynch: actualizar `criteria.py` + sección 1 de este archivo
9. Al agregar una señal: actualizar `signals.py` + `reporter.py` + tabla de sección 1

---

## 6. Gestión de Contexto y Memoria

**Regla del 60%:** el total de este archivo + archivos abiertos no debe superar ~120 000 tokens (60% de la ventana de 200 000). Si el contexto se satura:

```
1. Guardar progreso → docs/session_YYYY-MM-DD.md  (qué cambió, por qué, qué queda)
2. Ejecutar /clear  → reinicia el contexto de trabajo
3. Reanudar con este CLAUDE.md como referencia fija
```

**Jerarquía de CLAUDE.md:**
- `CLAUDE.md` (raíz) — reglas globales del proyecto ← este archivo
- `src/CLAUDE.md` — reglas de dominio específicas del pipeline de datos
- `docs/CLAUDE.md` — si se agrega documentación extensa
