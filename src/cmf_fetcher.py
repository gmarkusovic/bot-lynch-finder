"""
Fundamental data for Chilean stocks from CMF (Comisión para el Mercado Financiero).

Requires CMF_API_KEY environment variable.
Free registration at: https://api.cmfchile.cl/

Returns earnings_growth, debt_to_equity, free_cash_flow to augment yfinance data.
Only covers tickers with a known RUT mapping (IPSA stocks).
"""

import os
import time
import requests

_API_BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

# Nemotécnico (sin .SN) → RUT chileno
_TICKER_TO_RUT: dict[str, str] = {
    "SQM-B":      "93007000-9",
    "SQM-A":      "93007000-9",
    "CHILE":      "97004000-5",
    "FALABELLA":  "81463600-0",
    "COPEC":      "99520000-7",
    "ENELAM":     "91081000-6",
    "CENCOSUD":   "93834000-1",
    "BSANTANDER": "97036000-K",
    "ENELCHILE":  "99527000-5",
    "CMPC":       "93272000-9",
    "BCI":        "97006000-6",
    "LTM":        "89862200-2",
    "COLBUN":     "96505760-9",
    "RIPLEY":     "76518760-1",
    "SECURITY":   "90590000-9",
    "AGUAS-A":    "90290000-6",
    "IAM":        "76075488-0",
    "PARAUCO":    "89836400-9",
    "ITAUCL":     "76645030-K",
    "SONDA":      "96507290-9",
    "CCU":        "91705000-6",
    "ENTEL":      "92580000-7",
    "SMU":        "76045760-K",
    "FORUS":      "79613480-2",
    "HITES":      "79575680-K",
}


def _rut(ticker: str) -> str | None:
    return _TICKER_TO_RUT.get(ticker.removesuffix(".SN").upper())


def _get(rut: str, api_key: str) -> dict | None:
    try:
        resp = requests.get(
            f"{_API_BASE}/empresas/{rut}/estados_financieros",
            params={"apikey": api_key, "formato": "json"},
            timeout=15,
        )
        time.sleep(0.3)
        return resp.json() if resp.ok else None
    except Exception:
        time.sleep(0.3)
        return None


def _num(d: dict | None, *keys: str) -> float | None:
    """Return first valid float found among the given keys, or None."""
    if not d:
        return None
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _parse(data: dict) -> dict | None:
    # Unwrap common envelope keys
    root = data
    for wrapper in ("Emision", "BloqueFinanciero", "Estados_Financieros"):
        if wrapper in root and isinstance(root[wrapper], (dict, list)):
            root = root[wrapper]
            break

    # If the API returns a list of periods, take the first (most recent)
    if isinstance(root, list):
        root = root[0] if root else {}

    income   = root.get("EstadoResultados") or root.get("Estado_de_Resultados") or root
    balance  = root.get("Balance") or root.get("Estado_de_Situacion_Financiera") or root
    cashflow = root.get("FlujosEfectivo") or root.get("Estado_de_Flujos_de_Efectivo") or root

    # Net income: current period and prior period for YoY growth
    net_now = _num(income,
        "GananciaNeta", "GananciaPerdida",
        "GananciaAtribuibleControladora",
        "GananciaPerdidaAtribuibleAccionistasMayoritarios",
        "Ganancia",
    )
    net_prev = _num(income,
        "GananciaNeta_PeriodoAnterior", "GananciaPerdida_PA",
        "GananciaAtribuibleControladora_PA",
        "GananciaPerdidaAtribuibleAccionistasMayoritarios_PA",
        "Ganancia_PA",
    )

    # Debt and equity for D/E ratio
    debt = _num(balance,
        "PasivosFinancieros", "DeudaFinanciera",
        "PasivosFinancierosCorrientesNoCorrientes",
        "PasivosTotales",
    )
    equity = _num(balance,
        "PatrimonioTotal", "TotalPatrimonio",
        "Patrimonio", "PatrimonioNeto",
    )

    # Cash flows for FCF = operating CF − capex
    op_cf = _num(cashflow,
        "ActividadesOperacion", "FlujosOperacion",
        "FlujosEfectivoActividadesOperacion",
        "EfectivoGeneradoPorActividadesOperacion",
    )
    capex = _num(cashflow,
        "AdquisicionActivosTangibles", "AdquisicionPropiedadPlantaEquipo",
        "PagosActivosFijos", "InversionActivos",
    )

    result: dict = {}

    if net_now is not None and net_prev and net_prev != 0:
        result["earnings_growth"] = (net_now - net_prev) / abs(net_prev)

    if debt is not None and equity and equity > 0:
        result["debt_to_equity"] = debt / equity

    if op_cf is not None:
        result["free_cash_flow"] = op_cf - (abs(capex) if capex else 0.0)

    return result if result else None


def fetch_cmf_fundamentals(ticker: str) -> dict | None:
    """
    Return {earnings_growth, debt_to_equity, free_cash_flow} from CMF for a .SN ticker.
    Returns None if CMF_API_KEY not set, ticker not mapped, or API unavailable.
    """
    api_key = os.environ.get("CMF_API_KEY")
    if not api_key:
        return None

    rut = _rut(ticker)
    if not rut:
        return None

    data = _get(rut, api_key)
    if not data:
        return None

    return _parse(data)
