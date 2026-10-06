"""app.py

EPO CodeFest – Demo Web UI
-------------------------
Lightweight Flask web interface to manually call an ML inference API
(`/api_h7/<context>`) and inspect inputs / outputs.

Why this file exists (CodeFest context):
- Provide a human-friendly UI to test the ROI / valuation model.
- Make feature ranges and validation explicit and transparent.
- Allow evaluators to experiment without writing code.
- Keep everything dependency-light and easy to deploy.

This UI is intentionally simple:
- No authentication
- No database
- Short in-memory history (deque)

It is designed for demos, PoCs and hackathons, not for production.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from collections import deque
from typing import Any, Dict, Tuple

import requests
from flask import Flask, render_template, request


# ---------------------------------------------------------------------------
# Flask application setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Secret key is not strictly required here, but included as a best practice.
# In production, this must be provided via environment variables.
app.config["SECRET_KEY"] = "ChageIt"


# ---------------------------------------------------------------------------
# Feature configuration
# ---------------------------------------------------------------------------

# Expected (min, max) ranges for each feature.
# These ranges act as a first-line validation before calling the ML API.
RANGES: Dict[str, Tuple[float, float]] = {
    "is_active_recent": (0, 1),
    "log_legal_events_count": (0.0, 6.5),       # log1p(0..~665)
    "log_family_size": (0.0, 7.0),              # log1p(0..~1096)
    "novelty_x_breadth": (0.0, 1.0),            # novelty ∈ [0,1] × breadth ∈ [0,1]
    "novelty_x_family": (0.0, 7.0),             # novelty × log_family_size
    "log_priority_count": (0.0, 4.0),           # log1p(0..~54)
    "log_party_applicant_count": (0.0, 5.0),    # log1p(0..~147)
}

# Field definition used to build the form dynamically.
# (name, cast_type, label)
FIELDS = [
    ("is_active_recent", int, "Is the patent recently active? (0/1)"),
    ("log_legal_events_count", float, "Log legal events count"),
    ("log_family_size", float, "Log family size"),
    ("novelty_x_breadth", float, "Novelty × breadth"),
    ("novelty_x_family", float, "Novelty × family size"),
    ("log_priority_count", float, "Log priority count"),
    ("log_party_applicant_count", float, "Log applicant count"),
]

FEATURE_DESCRIPTIONS = {
    "is_active_recent":
        "<div class='info-row'><span class='info-label'>Meaning:</span> Indicates whether the patent has recent legal activity.</div>"
        "<div class='info-row'><span class='info-label'>Derived:</span> OPS <code>/legal</code> endpoint (event dates).</div>"
        "<div class='info-row'><span class='info-label'>Formula:</span> <code>is_active_recent = 1</code> if there is at least one legal event in the last T years, else <code>0</code>.</div>",

    "log_legal_events_count":
        "<div class='info-row'><span class='info-label'>Meaning:</span> Log-transformed number of legal events associated with the patent.</div>"
        "<div class='info-row'><span class='info-label'>Derived:</span> OPS <code>/legal</code> endpoint.</div>"
        "<div class='info-row'><span class='info-label'>Formula:</span> <code>log_legal_events_count = log(1 + number_of_legal_events)</code>.</div>",

    "log_family_size":
        "<div class='info-row'><span class='info-label'>Meaning:</span> Log-transformed size of the patent family.</div>"
        "<div class='info-row'><span class='info-label'>Derived:</span> OPS <code>/family</code> endpoint.</div>"
        "<div class='info-row'><span class='info-label'>Formula:</span> <code>log_family_size = log(1 + family_size)</code>.</div>",

    "novelty_x_breadth":
        "<div class='info-row'><span class='info-label'>Meaning:</span> Combined effect of novelty and technological breadth.</div>"
        "<div class='info-row'><span class='info-label'>Derived:</span> Novelty from text similarity; breadth from OPS <code>/biblio</code> IPC classes.</div>"
        "<div class='info-row'><span class='info-label'>Formula:</span> <code>novelty_x_breadth = novelty_score * number_of_IPC_classes</code>.</div>",

    "novelty_x_family":
        "<div class='info-row'><span class='info-label'>Meaning:</span> Combined effect of novelty and family size.</div>"
        "<div class='info-row'><span class='info-label'>Derived:</span> Novelty from text similarity; family size from OPS <code>/family</code>.</div>"
        "<div class='info-row'><span class='info-label'>Formula:</span> <code>novelty_x_family = novelty_score * log_family_size</code>.</div>",

    "log_priority_count":
        "<div class='info-row'><span class='info-label'>Meaning:</span> Log-transformed number of priority claims.</div>"
        "<div class='info-row'><span class='info-label'>Derived:</span> OPS <code>/biblio</code> endpoint.</div>"
        "<div class='info-row'><span class='info-label'>Formula:</span> <code>log_priority_count = log(1 + number_of_priorities)</code>.</div>",

    "log_party_applicant_count":
        "<div class='info-row'><span class='info-label'>Meaning:</span> Log-transformed number of applicants involved.</div>"
        "<div class='info-row'><span class='info-label'>Derived:</span> OPS <code>/biblio</code> endpoint.</div>"
        "<div class='info-row'><span class='info-label'>Formula:</span> <code>log_party_applicant_count = log(1 + number_of_applicants)</code>.</div>"
}


# ---------------------------------------------------------------------------
# Runtime data structures
# ---------------------------------------------------------------------------

@dataclass
class RunItem:
    """Represents a single API call executed from the UI."""
    ts: str
    url: str
    payload: Dict[str, Any]
    ok: bool
    status_code: int | None
    result: Dict[str, Any] | None
    error: str | None


# Keep a short rolling history in memory (demo-friendly).
HISTORY = deque(maxlen=10)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current timestamp formatted for display."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_url(scheme: str, host: str, port: str, context: str) -> str:
    """Build the target ML API URL from UI parameters."""
    scheme = scheme if scheme in ("http", "https") else "http"
    host = host.strip() or "localhost"
    port = port.strip() or "8000"
    context = (context or "epo_roi").strip()
    return f"{scheme}://{host}:{port}/api_h7/{context}"


def parse_value(name: str, raw: str, cast) -> Tuple[Any | None, str | None]:
    """Parse and validate a single form value.

    Returns:
        (value, error)
        - value is None if the field is empty
        - error contains a user-friendly message if validation fails
    """
    raw = (raw or "").strip()
    if raw == "":
        return None, None

    try:
        value = cast(raw)
    except ValueError:
        return None, f"Invalid value for '{name}'."

    if name in RANGES:
        minv, maxv = RANGES[name]
        if value < minv:
            return None, f"Out of range for '{name}': must be ≥ {minv}"
        if value > maxv:
            return None, f"Out of range for '{name}': must be ≤ {maxv}"

    return value, None


def build_payload_from_form(form: Dict[str, str]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Build the JSON payload expected by the ML API.

    Payload format:
        {"feature_name": [value], ...}

    Only non-empty fields are included.
    """
    payload: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    for name, cast, _label in FIELDS:
        v, err = parse_value(name, form.get(name, ""), cast)
        if err:
            errors[name] = err
            continue
        if v is not None:
            payload[name] = [v]

    return payload, errors


def pref_from_query_or_form(key: str, default: str) -> str:
    """Resolve UI preference with priority: querystring > form > default."""
    return (
        (request.args.get(key) or "").strip()
        or (request.form.get(key) or "").strip()
        or default
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    """Main UI endpoint.

    Renders the form, validates input and optionally calls the ML API.
    """
    # Default connection parameters
    scheme_default = "http"
    host_default = "localhost"
    port_default = "8000"
    context_default = "epo_roi"
    timeout_default = "10"

    # Resolve UI preferences
    scheme = pref_from_query_or_form("scheme", scheme_default)
    host = pref_from_query_or_form("host", host_default)
    port = pref_from_query_or_form("port", port_default)
    context = pref_from_query_or_form("context", context_default)
    timeout_s = pref_from_query_or_form("timeout", timeout_default)

    # Pre-fill feature values
    field_values: Dict[str, str] = {}
    for name, _cast, _label in FIELDS:
        field_values[name] = (
            request.args.get(name) or request.form.get(name) or ""
        ).strip()

    effective_url = build_url(scheme, host, port, context)

    result_json = None
    error_global = None
    payload_used = None
    status_code = None

    if request.method == "POST":
        # 1) Build payload + validate input
        payload, errors = build_payload_from_form(request.form)

        if not errors and not payload:
            errors["_global"] = "Please provide at least one feature value."

        # 2) Validation errors → render form again
        if errors:
            return render_template(
                "index.html",
                scheme=scheme,
                host=host,
                port=port,
                context=context,
                timeout=timeout_s,
                effective_url=effective_url,
                fields=FIELDS,
                ranges=RANGES,
                field_values=field_values,
                errors=errors,
                result_json=None,
                payload_used=None,
                status_code=None,
                history=list(HISTORY),
                feature_descriptions=FEATURE_DESCRIPTIONS,
            )

        # 3) Call ML API
        payload_used = payload
        try:
            timeout = float(timeout_s) if timeout_s else 10.0
            r = requests.post(effective_url, json=payload_used, timeout=timeout)
            status_code = r.status_code

            if not r.ok:
                error_global = f"HTTP {r.status_code}. Response: {(r.text or '')[:2000]}"
                HISTORY.appendleft(
                    RunItem(
                        ts=_now_iso(),
                        url=effective_url,
                        payload=payload_used,
                        ok=False,
                        status_code=r.status_code,
                        result=None,
                        error=error_global,
                    )
                )
            else:
                try:
                    result_json = r.json()
                except Exception:
                    result_json = {"raw_text": (r.text or "")[:4000]}

                HISTORY.appendleft(
                    RunItem(
                        ts=_now_iso(),
                        url=effective_url,
                        payload=payload_used,
                        ok=True,
                        status_code=r.status_code,
                        result=result_json if isinstance(result_json, dict) else {"result": result_json},
                        error=None,
                    )
                )

        except requests.RequestException as e:
            error_global = f"API error: {str(e)}"
            HISTORY.appendleft(
                RunItem(
                    ts=_now_iso(),
                    url=effective_url,
                    payload=payload_used or {},
                    ok=False,
                    status_code=None,
                    result=None,
                    error=error_global,
                )
            )

    return render_template(
        "index.html",
        scheme=scheme,
        host=host,
        port=port,
        context=context,
        timeout=timeout_s,
        effective_url=effective_url,
        fields=FIELDS,
        ranges=RANGES,
        field_values=field_values,
        errors={},
        result_json=result_json,
        payload_used=payload_used,
        status_code=status_code,
        history=list(HISTORY),
        error_global=error_global,
        feature_descriptions=FEATURE_DESCRIPTIONS,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Development server only.
    # For production: use gunicorn or another WSGI server.
    app.run(host="0.0.0.0", port=5000, debug=True)
