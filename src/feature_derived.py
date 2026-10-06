# src/feature_derived.py
from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, date

def _parse_yyyymmdd(s: str) -> pd.Timestamp | pd.NaT:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return pd.NaT
    s = str(s).strip()
    if not s:
        return pd.NaT
    # Acepta "YYYYMMDD" o "YYYY-MM-DD"
    if len(s) == 8 and s.isdigit():
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return pd.to_datetime(s, errors="coerce")
    # fallback: quitar no dígitos
    s2 = "".join(ch for ch in s if ch.isdigit())
    if len(s2) == 8:
        return pd.to_datetime(s2, format="%Y%m%d", errors="coerce")
    return pd.NaT

def add_derived_features(
    df: pd.DataFrame,
    today: date | None = None,
    alpha_alive: float = 0.6,
    beta_recent: float = 0.4,
) -> pd.DataFrame:
    """
    Añade:
      - years_since_first_legal
      - years_since_last_legal
      - alive_span_days
      - alive_years (span en años)
      - events_per_year
      - is_active_recent (último evento en últimos 365 días)
      - cost_proxy_v2 = log_family_size + alive_years
      - roi_proxy_v3 = roi_proxy_v2 + alpha*alive_years + beta*is_active_recent

    Requiere (si existen):
      - legal_first_date, legal_last_date, legal_events_count
      - family_size_simple (para log_family_size)
      - roi_proxy y/o roi_proxy_v2 (si no existe v2, se crea)
    """
    out = df.copy()

    if today is None:
        today = date.today()
    today_ts = pd.Timestamp(today)

    # ---- family derived ----
    if "family_size_simple" in out.columns:
        out["log_family_size"] = np.log1p(pd.to_numeric(out["family_size_simple"], errors="coerce").fillna(0))
    else:
        out["log_family_size"] = 0.0

    # ---- legal date parsing (con fallback y flags) ----
    first_raw = out.get("legal_first_date", pd.Series([None]*len(out)))
    last_raw  = out.get("legal_last_date",  pd.Series([None]*len(out)))

    out["_first_ts"] = first_raw.map(_parse_yyyymmdd)
    out["_last_ts"]  = last_raw.map(_parse_yyyymmdd)

    # Flag: faltan fechas legales
    out["legal_missing_dates"] = (out["_first_ts"].isna() | out["_last_ts"].isna()).astype(int)

    # Fallback: si faltan, usa ops_pub_date (si existe)
    if "ops_pub_date" in out.columns:
        pub_ts = out["ops_pub_date"].map(_parse_yyyymmdd)
        out["_first_ts"] = out["_first_ts"].fillna(pub_ts)
        out["_last_ts"]  = out["_last_ts"].fillna(pub_ts)

    # Si aún falta (ni legal ni pub_date), ponemos un valor neutro: today
    out["_first_ts"] = out["_first_ts"].fillna(today_ts)
    out["_last_ts"]  = out["_last_ts"].fillna(today_ts)

    # ---- ages (ya nunca NaN) ----
    out["years_since_first_legal"] = ((today_ts - out["_first_ts"]).dt.days / 365.25).clip(lower=0)
    out["years_since_last_legal"]  = ((today_ts - out["_last_ts"]).dt.days / 365.25).clip(lower=0)

    # span en días (si first==last => 0)
    out["alive_span_days"] = (out["_last_ts"] - out["_first_ts"]).dt.days.clip(lower=0)

    out["alive_years"] = (out["alive_span_days"] / 365.25).fillna(0.0)


    # ---- derived strong ----
    events = pd.to_numeric(out.get("legal_events_count", 0), errors="coerce").fillna(0.0)
    out["events_per_year"] = events / (out["alive_years"] + 0.1)  # +0.1 para estabilizar


    out["is_active_recent"] = ((today_ts - out["_last_ts"]).dt.days <= 365).astype("Int64")
    out["is_active_recent"] = out["is_active_recent"].fillna(0).astype(int)

    # ---- roi proxy v2/v3 ----
    if "roi_proxy_v2" not in out.columns:
        # v2 mínimo: roi_proxy + 0.6*log_family_size (si roi_proxy existe)
        if "roi_proxy" in out.columns:
            out["roi_proxy_v2"] = pd.to_numeric(out["roi_proxy"], errors="coerce").fillna(0.0) + 0.6*out["log_family_size"]
        else:
            out["roi_proxy_v2"] = 0.6*out["log_family_size"]

    out["roi_proxy_v3"] = (
        pd.to_numeric(out["roi_proxy_v2"], errors="coerce").fillna(0.0)
        + alpha_alive * out["alive_years"]
        + beta_recent * out["is_active_recent"]
    )

    # ---- coste lagrangiano (v2) ----
    out["cost_proxy_v2"] = out["log_family_size"] + out["alive_years"]

    # limpieza
    out.drop(columns=["_first_ts", "_last_ts"], inplace=True, errors="ignore")

    return out
