# src/ops_rest.py
import os, base64, time
from dataclasses import dataclass
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv
from src.config import OPS_BASE, OPS_TOKEN_URL

# OPS_BASE = OPS_BASE
# OPS_TOKEN_URL = OPS_TOKEN_URL

@dataclass
class OPSAuth:
    key: str
    secret: str
    token: Optional[str] = None
    token_expiry: float = 0.0

def get_auth() -> OPSAuth:
    load_dotenv()
    key = os.getenv("OPS_KEY")
    secret = os.getenv("OPS_SECRET")
    if not key or not secret:
        raise RuntimeError("Faltan OPS_KEY / OPS_SECRET en .env")
    return OPSAuth(key=key, secret=secret)

def _refresh_token(auth: OPSAuth, timeout=30):
    b64 = base64.b64encode(f"{auth.key}:{auth.secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {b64}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {"grant_type": "client_credentials"}
    r = requests.post(OPS_TOKEN_URL, headers=headers, data=data, timeout=timeout)
    if not r.ok:
        raise RuntimeError(f"Token error {r.status_code}: {r.text[:300]}")
    j = r.json()
    auth.token = j["access_token"]
    expires_in = float(j.get("expires_in", 600))
    auth.token_expiry = time.time() + expires_in * 0.9

def ops_get(path,
            auth,
            accept="application/xml",
            timeout=30,
            params=None,
            headers_extra=None):
    """
    Llamada GET robusta a OPS.

    - path: ruta relativa (ej. /published-data/search) o URL completa
    - auth: OPSAuth (con token)
    - params: dict de query params (opcional)
    - headers_extra: dict de headers extra (ej. {"Range": "1-25"})
    """

    # Refresca token si hace falta
    if auth.token is None or time.time() > auth.token_expiry:
        _refresh_token(auth, timeout=timeout)

    # Construye URL final
    url = path if path.startswith("http") else (OPS_BASE + path)

    # Headers base
    headers = {
        "Authorization": f"Bearer {auth.token}",
        "Accept": accept,
    }

    # Headers extra (Range, etc.)
    if headers_extra:
        headers.update(headers_extra)

    # Primera llamada
    r = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=timeout,
    )

    # Reintentos suaves por cuota / picos
    if r.status_code in (429, 503):
        import time as _t
        for wait in (1.0, 2.0, 4.0):
            _t.sleep(wait)
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code not in (429, 503):
                break

    # Si el token ha expirado entre medias, refresca y reintenta una vez
    if r.status_code == 401:
        _refresh_token(auth, timeout=timeout)
        headers["Authorization"] = f"Bearer {auth.token}"

        r = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=timeout,
        )

    return r

