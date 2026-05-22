"""CMF API test - diagnose correct endpoints for banks vs non-bank listed companies."""
import os
import requests

api_key = os.environ.get("CMF_API_KEY", "")
print(f"CMF_API_KEY: {'SET' if api_key else 'MISSING'}")
if not api_key:
    raise SystemExit(0)

SBIF_BASE  = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

# --- Test 1: Banks via SBIF (should have data) ---
print("\n=== TEST 1: SBIF API - BANKS ===")
for name, rut in [("Banco Chile", "97004000-5"), ("BCI", "97006000-6"), ("Santander", "97036000-K")]:
    for path in [
        f"/empresas/{rut}/estados_financieros",
        f"/bancos/{rut}/estados_financieros",
        f"/bancos/{rut}",
    ]:
        resp = requests.get(f"{SBIF_BASE}{path}",
                            params={"apikey": api_key, "formato": "json"}, timeout=15)
        body = resp.text
        print(f"  {name} {path}: HTTP {resp.status_code}, {len(body)} chars, CT: {resp.headers.get('Content-Type','?')[:40]}")
        if body.strip():
            print(f"    Preview: {body[:300]}")
        if resp.ok and body.strip():
            break  # found working path

# --- Test 2: Non-bank listed company via SBIF (likely empty) ---
print("\n=== TEST 2: SBIF API - NON-BANK (SQM-B) ===")
for path in [
    "/empresas/93007000-9/estados_financieros",
    "/empresas/93007000-9",
    "/emisores/93007000-9/estados_financieros",
]:
    resp = requests.get(f"{SBIF_BASE}{path}",
                        params={"apikey": api_key, "formato": "json"}, timeout=15)
    body = resp.text
    print(f"  {path}: HTTP {resp.status_code}, {len(body)} chars")
    if body.strip():
        print(f"    Preview: {body[:300]}")

# --- Test 3: Alternate CMF API base (valores/SVS side) ---
print("\n=== TEST 3: Alternate CMF endpoints ===")
for base in [
    "https://api.cmfchile.cl/api-svs/v1.0",
    "https://api.cmfchile.cl/api-svs",
    "https://api.cmfchile.cl/v1",
]:
    resp = requests.get(f"{base}/empresas/93007000-9/estados_financieros",
                        params={"apikey": api_key, "formato": "json"}, timeout=15)
    body = resp.text
    print(f"  {base}: HTTP {resp.status_code}, {len(body)} chars")
    if body.strip():
        print(f"    Preview: {body[:400]}")

print("\nDone.")
