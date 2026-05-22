"""CMF API connectivity test — run via GitHub Actions to validate the API key and endpoint."""
import os
import json
import requests

api_key = os.environ.get("CMF_API_KEY", "")
print(f"CMF_API_KEY present: {'YES' if api_key else 'NO (secret not configured)'}")

if not api_key:
    print("Skipping — set CMF_API_KEY secret in GitHub repo settings.")
    raise SystemExit(0)

BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

# Test three well-known IPSA RUTs
TICKERS = {
    "SQM-B":     "93007000-9",
    "CHILE":     "97004000-5",
    "FALABELLA": "81463600-0",
}

# Try two possible endpoint patterns
ENDPOINTS = [
    "{base}/empresas/{rut}/estados_financieros",
    "{base}/emisores/{rut}/estados_financieros",
    "{base}/empresas/{rut}",
]

for ticker, rut in TICKERS.items():
    print(f"\n{'='*50}")
    print(f"Ticker: {ticker}  RUT: {rut}")
    for tmpl in ENDPOINTS:
        url = tmpl.format(base=BASE, rut=rut)
        try:
            resp = requests.get(
                url,
                params={"apikey": api_key, "formato": "json"},
                timeout=15,
            )
            print(f"  {url.split('recursos_api')[1]}  →  HTTP {resp.status_code}")
            if resp.ok:
                data = resp.json()
                if isinstance(data, dict):
                    print(f"  Claves: {list(data.keys())}")
                    print(f"  Preview: {str(data)[:400]}")
                elif isinstance(data, list):
                    print(f"  Lista de {len(data)} items")
                    if data:
                        print(f"  Primer item keys: {list(data[0].keys()) if isinstance(data[0], dict) else data[0]}")
                break  # found working endpoint
            else:
                print(f"  Error body: {resp.text[:200]}")
        except Exception as e:
            print(f"  Exception: {e}")

print("\nTest completado.")
