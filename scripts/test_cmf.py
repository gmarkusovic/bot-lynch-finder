"""CMF API connectivity test - inspect raw response to determine correct format."""
import os
import requests

api_key = os.environ.get("CMF_API_KEY", "")
print(f"CMF_API_KEY present: {'YES' if api_key else 'NO'}")
if not api_key:
    raise SystemExit(0)

BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

# Test SQM-B only, with multiple format/endpoint combinations
RUT = "93007000-9"

cases = [
    (f"{BASE}/empresas/{RUT}/estados_financieros", {"apikey": api_key, "formato": "json"}),
    (f"{BASE}/empresas/{RUT}/estados_financieros", {"apikey": api_key, "formato": "xml"}),
    (f"{BASE}/empresas/{RUT}/estados_financieros", {"apikey": api_key}),
    (f"{BASE}/empresas/{RUT}",                    {"apikey": api_key, "formato": "json"}),
    (f"{BASE}/empresas",                          {"apikey": api_key, "formato": "json", "rut": RUT}),
    (f"https://api.cmfchile.cl/api-sbifv3/recursos_api/empresas/{RUT}/balances",
                                                   {"apikey": api_key, "formato": "json"}),
]

for url, params in cases:
    path = url.replace("https://api.cmfchile.cl/api-sbifv3/recursos_api", "")
    try:
        resp = requests.get(url, params=params, timeout=15)
        content_type = resp.headers.get("Content-Type", "unknown")
        body = resp.text
        print(f"\nPATH: {path}  params={list(params.keys())}")
        print(f"  HTTP {resp.status_code}  Content-Type: {content_type}")
        print(f"  Body ({len(body)} chars): {body[:500]}")
    except Exception as e:
        print(f"  Exception: {e}")

print("\nDone.")
