# src/table_builder.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple

import pandas as pd


@dataclass
class JoinSpec:
    """Especifica un join de un parquet (right) sobre una tabla base (left)."""
    name: str                   # nombre lógico (ej. "family", "legal", "cits")
    parquet_path: str           # ruta parquet right
    on: str = "pub"             # clave join
    how: str = "left"           # left join por defecto
    cols: Optional[List[str]] = None  # columnas a traer del right (None = todas menos key)
    suffix: str = ""            # sufijo para conflictos de nombres (si quieres)
    dedup_right_on_key: bool = True   # deduplica right por key quedándose con la primera


def _read_parquet(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe parquet: {path}")
    return pd.read_parquet(path)


def _dedup_on_key(df: pd.DataFrame, key: str) -> pd.DataFrame:
    if key not in df.columns:
        raise KeyError(f"Clave '{key}' no está en columnas: {df.columns.tolist()}")
    # Mantiene el primer registro por key
    return df.drop_duplicates(subset=[key], keep="first")


def _ensure_key(df: pd.DataFrame, key: str, df_name: str) -> None:
    if key not in df.columns:
        raise KeyError(f"'{df_name}' no contiene la clave '{key}'. Columnas: {df.columns.tolist()}")


def _select_cols(df: pd.DataFrame, key: str, cols: Optional[List[str]]) -> pd.DataFrame:
    if cols is None:
        # todas menos key
        cols2 = [c for c in df.columns if c != key]
    else:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise KeyError(f"Columnas solicitadas no existen en right: {missing}")
        cols2 = cols
    return df[[key] + cols2]


def build_final_table(
    base_parquet: str,
    joins: List[JoinSpec],
    out_parquet: str,
    key: str = "pub",
    sort_by: Optional[List[str]] = None,
    keep_only_base_rows: bool = True,
) -> pd.DataFrame:
    """
    Construye un 'tablón final' (feature table) desde un parquet base + una lista de joins.

    - base_parquet: el parquet principal (p.ej. train.parquet o test.parquet)
    - joins: lista de JoinSpec (familia, legal, citas, texto, etc.)
    - out_parquet: ruta donde guardar el resultado
    - key: clave join (por defecto 'pub')
    - sort_by: orden final de columnas (si quieres poner primero key, fechas, etc.)
    - keep_only_base_rows: si True, fuerza left join siempre aunque un JoinSpec diga otro how (seguridad)
    """
    base = _read_parquet(base_parquet)
    _ensure_key(base, key, "base")

    # Asegura que la clave es string (evita mismatches)
    base[key] = base[key].astype(str)

    cur = base.copy()

    for spec in joins:
        right = _read_parquet(spec.parquet_path)
        _ensure_key(right, spec.on, spec.name)

        # normaliza tipo key
        right[spec.on] = right[spec.on].astype(str)

        if spec.dedup_right_on_key:
            right = _dedup_on_key(right, spec.on)

        right = _select_cols(right, spec.on, spec.cols)

        # si la key del right se llama distinto, renómbrala
        if spec.on != key:
            right = right.rename(columns={spec.on: key})

        # Manejo de conflictos de nombres
        overlap = set(cur.columns) & set(right.columns) - {key}
        if overlap:
            # si no hay suffix, forzamos uno automático
            suffix = spec.suffix if spec.suffix else f"_{spec.name}"
            right = right.rename(columns={c: f"{c}{suffix}" for c in overlap})

        how = "left" if keep_only_base_rows else spec.how
        cur = cur.merge(right, on=key, how=how)

    # Orden de columnas (opcional)
    if sort_by:
        # sort_by aquí se interpreta como "columnas primero"
        first = [c for c in sort_by if c in cur.columns]
        rest = [c for c in cur.columns if c not in first]
        cur = cur[first + rest]

    Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
    cur.to_parquet(out_parquet, index=False)
    return cur


def build_train_test_tables(
    processed_dir: str = "data/processed",
    out_dir: str = "data/processed/final",
    key: str = "pub",
) -> Tuple[pd.DataFrame]:
    """
    Conveniencia: construye tablon finales asumiendo nombres estándar:
      - tablon.parquet
      - tablon_family.parquet
    Luego irás añadiendo legal/citations/etc.
    """
    processed = Path(processed_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    tablon_base = str(processed / "tablon.parquet")
    
    # Joins
    joins_tablon = [
        # 1️⃣ Familia (estructura)
        JoinSpec(
            name="family",
            parquet_path=str(processed / "tablon_family.parquet"),
            on="pub",
            how="left",
            cols=[
                "family_size_simple",
                "family_country_count_simple",
                "family_kinds_count_simple",
            ],
        ),
    
        # 2️⃣ Legal (dinámica histórica resumida)
        JoinSpec(
            name="legal",
            parquet_path=str(processed / "tablon_legal.parquet"),
            on="pub",
            how="left",
            cols=[
                "legal_events_count",
                "legal_codes_unique",
                "legal_first_date",
                "legal_last_date",
                "legal_has_grant_like",
                "legal_has_opposition_like",
            ],
        ),
    
        # 3️⃣ Bibliographic / OPS light
        # (aunque title/abstract estén a None, este join ES CLAVE)
        JoinSpec(
            name="biblio",
            parquet_path=str(processed / "tablon_text.parquet"),
            on="pub",
            how="left",
            cols=[
                "ops_pub_date",
                "ops_n_applicants",
                "ops_n_inventors",
                "ops_n_cpc",
                "ops_n_ipc",
                "ops_ipc_main",
                "ops_title",      # opcional hoy
                "ops_abstract",   # opcional hoy
            ],
        ),

        # 4 Bibliographic / OPS light
        # (aunque title/abstract estén a None, este join ES CLAVE)
        JoinSpec(
            name="biblio",
            parquet_path=str(processed / "tablon_biblio_light_ext.parquet"),
            on="pub",
            how="left",
            cols=[
                "biblio_priority_count",
                "biblio_priority_date_min",
                "biblio_priority_year",
                "biblio_application_date",
                "biblio_application_year",
                "biblio_publication_date",
                "biblio_publication_year",  
                "biblio_kind",  
                "biblio_title",
                "biblio_abstract",
            ],
        ),

        # 5 Bibliographic / Party
        # (aunque title/abstract estén a None, este join ES CLAVE)
        JoinSpec(
            name="party",
            parquet_path=str(processed / "tablon_biblio_light_ext1.parquet"),
            on="pub",
            how="left",
            cols=[
                "party_applicant_count",
                "party_inventor_count",
                "party_applicant_country_list",
                "party_applicant_country_count",
                "party_applicant_country_main",
                "party_applicant_type_main",
                "party_applicant_type_conf",  
            ],
        ),

        # 6 Bibliographic / Party
        # (aunque title/abstract estén a None, este join ES CLAVE)
        JoinSpec(
            name="text",
            parquet_path=str(processed / "tablon_biblio_light.parquet"),
            on="pub",
            how="left",
            cols=[
                "text_title",
                "text_abstract",
                "text_claims",
                "text_description",
                "text_has_claims",
                "text_has_description",
                "text_available",
                "text_len_title",
                "text_len_abstract",
                "text_len_claims",
                "text_len_description",
                "text_for_embedding",
                "text_len_embedding",
            ],
        ),
    ]


    tablon_final = build_final_table(
        base_parquet=tablon_base,
        joins=joins_tablon,
        out_parquet=str(out / "tablon_final.parquet"),
        key=key,
        sort_by=[key, "ops_pub_date", "roi_proxy", "roi_class"],
    )


    return tablon_final
