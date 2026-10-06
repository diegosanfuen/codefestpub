# src/ops_build.py
import re
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import quote
import datetime as _dt
import pandas as pd
from lxml import etree

from src.ops_rest import get_auth, ops_get
from src.config import CACHE_DIR

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# EP4670682A2 -> CC=EP, NUM=4670682, KIND=A2
PUB_RE = re.compile(r"^([A-Z]{2})(\d+)([A-Z]\d)?$")

def normalize_pub(pub: str) -> Optional[str]:
    s = str(pub).replace(" ", "").replace(".", "").replace("-", "").upper()
    m = PUB_RE.match(s)
    if not m:
        return None
    cc, num, kind = m.group(1), m.group(2), m.group(3) or "A1"
    return f"{cc}{num}{kind}"

def pub_to_docdb_path(pub_norm: str) -> str:
    m = PUB_RE.match(pub_norm)
    if not m:
        raise ValueError(f"Bad pub format: {pub_norm}")
    cc, num, kind = m.group(1), m.group(2), m.group(3)
    return f"/published-data/publication/docdb/{cc}.{num}.{kind}"

def cache_file(pub_norm: str, endpoint: str) -> Path:
    return CACHE_DIR / f"{pub_norm}.{endpoint}.xml"

def fetch_biblio_xml(pub_norm: str) -> bytes:
    cpath = cache_file(pub_norm, "biblio")
    if cpath.exists():
        return cpath.read_bytes()

    auth = get_auth()
    docdb = pub_to_docdb_path(pub_norm)
    r = ops_get(docdb + "/biblio", auth=auth, accept="application/xml")
    if r.status_code != 200:
        raise RuntimeError(f"OPS biblio {r.status_code}: {r.text[:200]}")
    cpath.write_bytes(r.content)
    return r.content

def fetch_claims_xml(pub_norm: str) -> bytes:
    """
    Descarga/lee de cache el XML de claims (DOCDB).
    Endpoint OPS:
      /published-data/publication/docdb/CC.NUM.KIND/claims
    """
    cpath = cache_file(pub_norm, "claims")
    if cpath.exists():
        return cpath.read_bytes()

    auth = get_auth()
    docdb = pub_to_docdb_path(pub_norm)
    r = ops_get(docdb + "/claims", auth=auth, accept="application/xml")

    if r.status_code != 200:
        raise RuntimeError(f"OPS claims {r.status_code}: {r.text[:200]}")

    cpath.write_bytes(r.content)
    return r.content


def fetch_description_xml(pub_norm: str) -> bytes:
    """
    Descarga/lee de cache el XML de description (DOCDB).
    Endpoint OPS:
      /published-data/publication/docdb/CC.NUM.KIND/description
    """
    cpath = cache_file(pub_norm, "description")
    if cpath.exists():
        return cpath.read_bytes()

    auth = get_auth()
    docdb = pub_to_docdb_path(pub_norm)
    r = ops_get(docdb + "/description", auth=auth, accept="application/xml")

    if r.status_code != 200:
        raise RuntimeError(f"OPS description {r.status_code}: {r.text[:200]}")

    cpath.write_bytes(r.content)
    return r.content


def parse_biblio_features(xml_bytes: bytes) -> Dict:
    root = etree.fromstring(xml_bytes)
    ns = root.nsmap.copy()
    ns.pop(None, None)

    def xcount(xpath: str):
        try:
            return len(root.xpath(xpath, namespaces=ns))
        except Exception:
            return None

    feats = {
        "ops_n_applicants": xcount("//*[local-name()='applicants']//*[local-name()='applicant']"),
        "ops_n_inventors":  xcount("//*[local-name()='inventors']//*[local-name()='inventor']"),
        "ops_n_ipc":        xcount("//*[local-name()='classification-ipc']//*[local-name()='text']"),
        "ops_n_cpc":        xcount("//*[local-name()='patent-classifications']//*[local-name()='patent-classification']"),
    }

    # IPC principal
    try:
        ipc = root.xpath("//*[local-name()='classification-ipc']//*[local-name()='text']/text()", namespaces=ns)
        feats["ops_ipc_main"] = ipc[0].strip() if ipc else None
    except Exception:
        feats["ops_ipc_main"] = None

    # fecha publicación (si aparece)
    try:
        dates = root.xpath("//*[local-name()='publication-reference']//*[local-name()='date']/text()", namespaces=ns)
        feats["ops_pub_date"] = dates[0].strip() if dates else None
    except Exception:
        feats["ops_pub_date"] = None

    return feats

def parse_biblio_extra_features(xml_bytes: bytes) -> Dict:
    """
    Extrae features adicionales de biblio (sin tocar parse_biblio_features):
      - biblio_priority_date_min / biblio_priority_year / biblio_priority_count
      - biblio_application_date / biblio_application_year
      - biblio_publication_date / biblio_publication_year (si no existe ya)
      - biblio_kind (A1/A2/B1...)
      - biblio_title (primer título)
      - biblio_abstract (texto concatenado)
    """
    root = etree.fromstring(xml_bytes)
    ns = root.nsmap.copy()
    ns.pop(None, None)

    def _first_text(xpath: str):
        try:
            xs = root.xpath(xpath, namespaces=ns)
            if not xs:
                return None
            # xs puede ser lista de strings o nodos
            x0 = xs[0]
            return x0.strip() if isinstance(x0, str) else (x0.text or "").strip()
        except Exception:
            return None

    def _all_text(xpath: str, max_n: int = 2000):
        try:
            xs = root.xpath(xpath, namespaces=ns)
            out = []
            for x in xs[:max_n]:
                s = x.strip() if isinstance(x, str) else (x.text or "").strip()
                if s:
                    out.append(s)
            return " ".join(out).strip() if out else None
        except Exception:
            return None

    def _to_yyyymmdd_local(s: str) -> Optional[str]:
        return _to_yyyymmdd(s)

    # prioridades
    try:
        pr_dates = root.xpath("//*[local-name()='priority-claim']//*[local-name()='date']/text()", namespaces=ns)
        pr_dates = [_to_yyyymmdd_local(d) for d in pr_dates if d]
        pr_dates = [d for d in pr_dates if d]
        pr_dates = sorted(set(pr_dates))
    except Exception:
        pr_dates = []

    pr_min = pr_dates[0] if pr_dates else None

    # application/publication
    app_date = _to_yyyymmdd_local(_first_text("//*[local-name()='application-reference']//*[local-name()='date']/text()") or "")
    pub_date = _to_yyyymmdd_local(_first_text("//*[local-name()='publication-reference']//*[local-name()='date']/text()") or "")

    # kind
    kind = _first_text("//*[local-name()='publication-reference']//*[local-name()='document-id']//*[local-name()='kind']/text()")

    # title & abstract (tolerantes)
    title = _first_text("//*[local-name()='invention-title']/text()")
    if not title:
        title = _all_text("//*[local-name()='invention-title']//text()", max_n=200)

    abstract = _all_text("//*[local-name()='abstract']//text()", max_n=4000)

    feats = {
        "biblio_priority_count": len(pr_dates),
        "biblio_priority_date_min": pr_min,
        "biblio_priority_year": int(pr_min[:4]) if pr_min else None,

        "biblio_application_date": app_date,
        "biblio_application_year": int(app_date[:4]) if app_date else None,

        "biblio_publication_date": pub_date,
        "biblio_publication_year": int(pub_date[:4]) if pub_date else None,

        "biblio_kind": kind,
        "biblio_title": title,
        "biblio_abstract": abstract,
    }
    return feats
def parse_biblio_extra_features(xml_bytes: bytes) -> Dict:
    """
    Extrae features adicionales de biblio (sin tocar parse_biblio_features):
      - biblio_priority_date_min / biblio_priority_year / biblio_priority_count
      - biblio_application_date / biblio_application_year
      - biblio_publication_date / biblio_publication_year (si no existe ya)
      - biblio_kind (A1/A2/B1...)
      - biblio_title (primer título)
      - biblio_abstract (texto concatenado)
    """
    root = etree.fromstring(xml_bytes)
    ns = root.nsmap.copy()
    ns.pop(None, None)

    def _first_text(xpath: str):
        try:
            xs = root.xpath(xpath, namespaces=ns)
            if not xs:
                return None
            # xs puede ser lista de strings o nodos
            x0 = xs[0]
            return x0.strip() if isinstance(x0, str) else (x0.text or "").strip()
        except Exception:
            return None

    def _all_text(xpath: str, max_n: int = 2000):
        try:
            xs = root.xpath(xpath, namespaces=ns)
            out = []
            for x in xs[:max_n]:
                s = x.strip() if isinstance(x, str) else (x.text or "").strip()
                if s:
                    out.append(s)
            return " ".join(out).strip() if out else None
        except Exception:
            return None

    def _to_yyyymmdd_local(s: str) -> Optional[str]:
        return _to_yyyymmdd(s)

    # prioridades
    try:
        pr_dates = root.xpath("//*[local-name()='priority-claim']//*[local-name()='date']/text()", namespaces=ns)
        pr_dates = [_to_yyyymmdd_local(d) for d in pr_dates if d]
        pr_dates = [d for d in pr_dates if d]
        pr_dates = sorted(set(pr_dates))
    except Exception:
        pr_dates = []

    pr_min = pr_dates[0] if pr_dates else None

    # application/publication
    app_date = _to_yyyymmdd_local(_first_text("//*[local-name()='application-reference']//*[local-name()='date']/text()") or "")
    pub_date = _to_yyyymmdd_local(_first_text("//*[local-name()='publication-reference']//*[local-name()='date']/text()") or "")

    # kind
    kind = _first_text("//*[local-name()='publication-reference']//*[local-name()='document-id']//*[local-name()='kind']/text()")

    # title & abstract (tolerantes)
    title = _first_text("//*[local-name()='invention-title']/text()")
    if not title:
        title = _all_text("//*[local-name()='invention-title']//text()", max_n=200)

    abstract = _all_text("//*[local-name()='abstract']//text()", max_n=4000)

    feats = {
        "biblio_priority_count": len(pr_dates),
        "biblio_priority_date_min": pr_min,
        "biblio_priority_year": int(pr_min[:4]) if pr_min else None,

        "biblio_application_date": app_date,
        "biblio_application_year": int(app_date[:4]) if app_date else None,

        "biblio_publication_date": pub_date,
        "biblio_publication_year": int(pub_date[:4]) if pub_date else None,

        "biblio_kind": kind,
        "biblio_title": title,
        "biblio_abstract": abstract,
    }
    return feats

_CORP_MARKERS = [
    "S.A.", "SA", "S.L.", "SL", "LTD", "LIMITED", "INC", "CORP", "CORPORATION",
    "GMBH", "AG", "BV", "B.V.", "SARL", "S.R.L.", "SRL", "SAS", "SPA", "S.P.A", "KK"
]
_UNI_MARKERS = ["UNIVERSITY", "UNIV", "INSTITUTE", "INSTITUT", "POLYTECH", "HOSPITAL"]
_GOV_MARKERS = ["MINISTRY", "GOVERNMENT", "STATE", "MINISTERIO", "AYUNTAMIENTO", "GENERALITAT", "COMUNIDAD", "CONSEJERIA"]

def _classify_applicant_name(name: str) -> (str, float):
    if not name:
        return ("unknown", 0.0)
    up = re.sub(r"\s+", " ", name.strip()).upper()

    if any(m in up for m in _GOV_MARKERS):
        return ("government", 0.85)
    if any(m in up for m in _UNI_MARKERS):
        return ("university", 0.80)
    if any(m in up for m in _CORP_MARKERS):
        return ("company", 0.75)

    if "," in up:
        return ("individual", 0.60)

    toks = up.split()
    if 1 <= len(toks) <= 4:
        return ("individual", 0.45)

    return ("unknown", 0.20)


def parse_parties_features(xml_bytes: bytes) -> Dict:
    """
    Extrae:
      - party_applicant_count / party_inventor_count
      - party_applicant_country_list / party_applicant_country_main / party_applicant_country_count
      - party_applicant_type_main / party_applicant_type_conf (heurística por nombres)

    Versión robusta: prueba varios XPaths porque el XML de OPS (docdb/biblio) puede variar.
    """
    root = etree.fromstring(xml_bytes)
    ns = root.nsmap.copy()
    ns.pop(None, None)

    def _texts_multi(xpaths: List[str], max_n: int = 2000) -> List[str]:
        out: List[str] = []
        for xp in xpaths:
            try:
                xs = root.xpath(xp, namespaces=ns)
                for x in xs[:max_n]:
                    s = x.strip() if isinstance(x, str) else (x.text or "").strip()
                    if s:
                        out.append(s)
            except Exception:
                continue
        # dedup preservando orden
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq

    # --- Applicants names (varias estructuras posibles)
    appl_names = _texts_multi([
        # estructura "bonita" (exchange)
        "//*[local-name()='applicants']//*[local-name()='applicant']//*[local-name()='addressbook']//*[local-name()='name']/text()",
        # a veces name no está bajo addressbook
        "//*[local-name()='applicants']//*[local-name()='applicant']//*[local-name()='name']/text()",
        # algunas variantes usan applicant-name
        "//*[local-name()='applicants']//*[local-name()='applicant']//*[local-name()='applicant-name']/text()",
        # fallback super-tolerante: cualquier name dentro de applicant
        "//*[local-name()='applicants']//*[local-name()='applicant']//*[local-name()='addressbook']//*[local-name()='*'][local-name()='name']/text()",
    ], max_n=300)

    # --- Applicants countries
    appl_countries = _texts_multi([
        "//*[local-name()='applicants']//*[local-name()='applicant']//*[local-name()='addressbook']//*[local-name()='country']/text()",
        "//*[local-name()='applicants']//*[local-name()='applicant']//*[local-name()='country']/text()",
        # fallback: cualquier country dentro de applicant
        "//*[local-name()='applicants']//*[local-name()='applicant']//*[local-name()='*'][local-name()='country']/text()",
    ], max_n=500)
    appl_countries = [c.strip().upper() for c in appl_countries if c and c.strip()]

    # --- Inventors names/countries (similar)
    inv_names = _texts_multi([
        "//*[local-name()='inventors']//*[local-name()='inventor']//*[local-name()='addressbook']//*[local-name()='name']/text()",
        "//*[local-name()='inventors']//*[local-name()='inventor']//*[local-name()='name']/text()",
        "//*[local-name()='inventors']//*[local-name()='inventor']//*[local-name()='inventor-name']/text()",
        "//*[local-name()='inventors']//*[local-name()='inventor']//*[local-name()='addressbook']//*[local-name()='*'][local-name()='name']/text()",
    ], max_n=500)

    inv_countries = _texts_multi([
        "//*[local-name()='inventors']//*[local-name()='inventor']//*[local-name()='addressbook']//*[local-name()='country']/text()",
        "//*[local-name()='inventors']//*[local-name()='inventor']//*[local-name()='country']/text()",
        "//*[local-name()='inventors']//*[local-name()='inventor']//*[local-name()='*'][local-name()='country']/text()",
    ], max_n=800)
    inv_countries = [c.strip().upper() for c in inv_countries if c and c.strip()]

    uniq_countries = sorted(set(appl_countries))
    main_country = appl_countries[0] if appl_countries else None

    # --- clasificación por voto (igual que antes)
    votes = {}
    confs = []
    for nm in appl_names[:10]:
        t, c = _classify_applicant_name(nm)
        votes[t] = votes.get(t, 0) + 1
        confs.append(c)

    if votes:
        t_main = sorted(votes.items(), key=lambda kv: kv[1], reverse=True)[0][0]
        t_conf = float(sum(confs) / max(len(confs), 1))
    else:
        t_main, t_conf = "unknown", 0.0

    return {
        "party_applicant_count": len(appl_names),
        "party_inventor_count": len(inv_names),

        "party_applicant_country_list": uniq_countries,
        "party_applicant_country_count": len(uniq_countries),
        "party_applicant_country_main": main_country,

        "party_applicant_type_main": t_main,
        "party_applicant_type_conf": t_conf,
    }



def ops_search_publications(query: str, start: int = 1, rows: int = 25):
    """
    Search robusto:
    - Por defecto rows=25 (estable)
    - Intenta Range en query string
    - Si falla, intenta Range como header HTTP
    """
    auth = get_auth()

    # CQL-friendly encoding (dejamos operadores)
    q = quote(query, safe="=:+*()\"'->")

    range_value = f"{start}-{start+rows-1}"
    path = f"/published-data/search?q={q}&Range={range_value}"

    r = ops_get(path, auth=auth, accept="application/xml")

    # Fallback: Range como header (si algunos proxies no aceptan Range como param)
    if r.status_code == 400:
        path2 = f"/published-data/search?q={q}"
        r = ops_get(path2, auth=auth, accept="application/xml", headers_extra={"Range": range_value})

    if r.status_code != 200:
        raise RuntimeError(f"OPS search {r.status_code}: url={r.url} body={r.text[:200]}")

    root = etree.fromstring(r.content)
    ns = root.nsmap.copy()
    ns.pop(None, None)

    pubs = []
    doc_numbers = root.xpath("//*[local-name()='document-id']//*[local-name()='doc-number']/text()", namespaces=ns)
    kinds       = root.xpath("//*[local-name()='document-id']//*[local-name()='kind']/text()", namespaces=ns)
    countries   = root.xpath("//*[local-name()='document-id']//*[local-name()='country']/text()", namespaces=ns)

    if not (doc_numbers and countries):
        return pubs

    n = min(len(doc_numbers), len(countries), len(kinds) if kinds else len(doc_numbers))
    for i in range(n):
        cc = countries[i].strip().upper()
        num = re.sub(r"\D", "", doc_numbers[i])
        kind = kinds[i].strip().upper() if kinds else "A1"
        pub = normalize_pub(f"{cc}{num}{kind}")
        if pub:
            pubs.append(pub)

    # dedup preservando orden
    seen = set()
    out = []
    for p in pubs:
        if p not in seen:
            seen.add(p)
            out.append(p)

    return out



def build_dataset_from_pubs(pubs: List[str], max_n: Optional[int] = None) -> pd.DataFrame:
    pubs = [normalize_pub(p) for p in pubs]
    pubs = [p for p in pubs if p]
    if max_n is not None:
        pubs = pubs[: int(max_n)]

    rows = []
    for p in pubs:
        try:
            xmlb = fetch_biblio_xml(p)
            feats = parse_biblio_features(xmlb)
            feats["pub"] = p
            rows.append(feats)
        except Exception as e:
            rows.append({"pub": p, "ops_error": str(e)})

    return pd.DataFrame(rows)


# --- FAMILY (DOCDB simple family via published-data equivalents) ---

def pub_to_epodoc_base(pub_norm: str) -> str:
    """
    EP4670650A2 -> EP4670650  (para endpoint epodoc)
    """
    m = PUB_RE.match(pub_norm)
    if not m:
        raise ValueError(f"Bad pub format: {pub_norm}")
    cc, num, _kind = m.group(1), m.group(2), m.group(3)
    return f"{cc}{num}"

def fetch_equivalents_xml(pub_norm: str) -> bytes:
    """
    Descarga/lee de cache el XML de equivalents (simple family).
    Endpoint (OPS v3.2 guide):
      /published-data/publication/epodoc/{EPxxxxxxx}/equivalents
    """
    cpath = cache_file(pub_norm, "equivalents")
    if cpath.exists():
        return cpath.read_bytes()

    auth = get_auth()
    epodoc = pub_to_epodoc_base(pub_norm)

    # published-data / publication / epodoc / {number} / equivalents
    path = f"/published-data/publication/epodoc/{epodoc}/equivalents"
    r = ops_get(path, auth=auth, accept="application/xml")

    if r.status_code != 200:
        raise RuntimeError(f"OPS equivalents {r.status_code}: {r.text[:200]}")

    cpath.write_bytes(r.content)
    return r.content

def parse_equivalents_features(xml_bytes: bytes) -> Dict:
    """
    Extrae features de familia simple:
      - family_size_simple: nº de miembros (aprox)
      - family_country_count_simple: nº de países distintos
      - family_kinds_count_simple: nº de kinds distintos
    """
    root = etree.fromstring(xml_bytes)
    ns = root.nsmap.copy()
    ns.pop(None, None)

    # Hay varias estructuras posibles; usamos una estrategia tolerante:
    # capturamos todos los document-id/country + doc-number + kind que aparezcan.
    countries = root.xpath("//*[local-name()='document-id']//*[local-name()='country']/text()", namespaces=ns)
    docnums   = root.xpath("//*[local-name()='document-id']//*[local-name()='doc-number']/text()", namespaces=ns)
    kinds     = root.xpath("//*[local-name()='document-id']//*[local-name()='kind']/text()", namespaces=ns)

    # Limpieza básica
    countries = [c.strip().upper() for c in countries if c and c.strip()]
    kinds = [k.strip().upper() for k in kinds if k and k.strip()]

    # family_size: mejor aproximación = nº de doc-number si existe, si no nº de countries
    family_size = len(docnums) if docnums else (len(countries) if countries else 0)

    feats = {
        "family_size_simple": family_size,
        "family_country_count_simple": len(set(countries)) if countries else 0,
        "family_kinds_count_simple": len(set(kinds)) if kinds else 0,
    }
    return feats

def enrich_family_simple(df: pd.DataFrame, pub_col: str = "pub", limit: Optional[int] = None) -> pd.DataFrame:
    """
    Join por pub -> añade family_*_simple con cache.
    """
    n = len(df) if limit is None else min(len(df), int(limit))
    rows = []

    for i in range(n):
        idx = df.index[i]
        pub = df.iloc[i][pub_col]
        pub_norm = normalize_pub(pub)
        if not pub_norm:
            rows.append({"_idx": idx, "family_error": "bad_pub_format"})
            continue
        try:
            xmle = fetch_equivalents_xml(pub_norm)
            feats = parse_equivalents_features(xmle)
            feats["_idx"] = idx
            rows.append(feats)
        except Exception as e:
            rows.append({"_idx": idx, "family_error": str(e)})

    feats_df = pd.DataFrame(rows).set_index("_idx")
    return df.join(feats_df, how="left")

def _to_yyyymmdd(s: str) -> str | None:
    if not s:
        return None
    s = s.strip()
    # puede venir 2000-05-17 o 20000517
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s.replace("-", "")
    if len(s) == 8 and s.isdigit():
        return s
    # último intento: quitar no dígitos
    dd = re.sub(r"\D", "", s)
    return dd if len(dd) == 8 else None

def fetch_legal_xml(pub_norm: str) -> bytes:
    """
    Descarga/lee de cache el XML legal del pub (DOCDB).
    Endpoint (OPS v3.2):
      /legal/publication/docdb/CC.NUM.KIND
    """
    cpath = cache_file(pub_norm, "legal")
    if cpath.exists():
        return cpath.read_bytes()

    auth = get_auth()
    m = PUB_RE.match(pub_norm)
    if not m:
        raise ValueError(f"Bad pub format: {pub_norm}")
    cc, num, kind = m.group(1), m.group(2), m.group(3)

    path = f"/legal/publication/docdb/{cc}.{num}.{kind}"
    r = ops_get(path, auth=auth, accept="application/xml")

    if r.status_code != 200:
        raise RuntimeError(f"OPS legal {r.status_code}: {r.text[:200]}")

    cpath.write_bytes(r.content)
    return r.content

def parse_legal_features(xml_bytes: bytes) -> Dict:
    """
    Features robustas sin “interpretar demasiado” códigos:
      - legal_events_count: nº de elementos <ops:legal>
      - legal_codes_unique: nº de códigos distintos (atributo code)
      - legal_first_date / legal_last_date: min/max de fechas encontradas
      - legal_has_grant_like: heurística (si aparece un evento con desc que contiene 'GRANT')
      - legal_has_opposition_like: heurística (si aparece 'OPPOSITION')
    """
    root = etree.fromstring(xml_bytes)
    ns = root.nsmap.copy()
    ns.pop(None, None)

    legals = root.xpath("//*[local-name()='legal']", namespaces=ns)
    codes = []
    descs = []

    dates = []

    for le in legals:
        code = le.get("code")
        desc = le.get("desc")
        if code:
            codes.append(code.strip())
        if desc:
            descs.append(desc.strip().upper())

        # 1) fecha tipo Gazette DATE: elementos tipo L007EP / L007XX con formato YYYY-MM-DD
        # 2) también permitimos <date>YYYYMMDD</date> dentro de document-id
        # buscamos cualquier sub-elemento cuyo local-name empiece por 'L007'
        for child in le.iter():
            ln = etree.QName(child).localname if isinstance(child.tag, str) else ""
            if ln.startswith("L007"):
                if child.text:
                    d = _to_yyyymmdd(child.text)
                    if d:
                        dates.append(d)

    # fallback: buscar <date> en el documento (a veces viene en referencias)
    if not dates:
        raw_dates = root.xpath("//*[local-name()='date']/text()", namespaces=ns)
        for rd in raw_dates[:200]:  # límite por seguridad
            d = _to_yyyymmdd(rd)
            if d:
                dates.append(d)

    dates = sorted(set(dates))

    def _min_date(ds): return ds[0] if ds else None
    def _max_date(ds): return ds[-1] if ds else None

    feats = {
        "legal_events_count": len(legals),
        "legal_codes_unique": len(set(codes)) if codes else 0,
        "legal_first_date": _min_date(dates),
        "legal_last_date": _max_date(dates),
        # heurísticas suaves basadas en descripciones (no dependemos de códigos exactos)
        "legal_has_grant_like": int(any("GRANT" in d for d in descs)),
        "legal_has_opposition_like": int(any("OPPOSITION" in d for d in descs)),
    }
    return feats

def enrich_legal(df: pd.DataFrame, pub_col: str = "pub", limit: Optional[int] = None) -> pd.DataFrame:
    """
    Join por pub -> añade columnas legal_* con cache.
    """
    n = len(df) if limit is None else min(len(df), int(limit))
    rows = []

    for i in range(n):
        idx = df.index[i]
        pub = df.iloc[i][pub_col]
        pub_norm = normalize_pub(pub)
        if not pub_norm:
            rows.append({"_idx": idx, "legal_error": "bad_pub_format"})
            continue
        try:
            xmlb = fetch_legal_xml(pub_norm)
            feats = parse_legal_features(xmlb)
            feats["_idx"] = idx
            rows.append(feats)
        except Exception as e:
            rows.append({"_idx": idx, "legal_error": str(e)})

    feats_df = pd.DataFrame(rows).set_index("_idx")
    return df.join(feats_df, how="left")

def parse_text_features(
    biblio_xml_bytes: bytes,
    claims_xml_bytes: Optional[bytes] = None,
    description_xml_bytes: Optional[bytes] = None,
    truncate_claims: int = 12000,
    truncate_description: int = 20000,
) -> Dict:
    """
    Construye campos text_* para embeddings:
      - text_title / text_abstract (desde biblio)
      - text_claims / text_description (si vienen)
      - text_for_embedding + longitudes + flags
    """
    # reutilizamos el extra biblio para title/abstract
    b = parse_biblio_extra_features(biblio_xml_bytes)
    title = b.get("biblio_title")
    abstract = b.get("biblio_abstract")

    def _extract_all_text(xml_bytes: bytes, node_name: str, max_n: int = 50000) -> Optional[str]:
        root = etree.fromstring(xml_bytes)
        ns = root.nsmap.copy()
        ns.pop(None, None)
        try:
            xs = root.xpath(f"//*[local-name()='{node_name}']//text()", namespaces=ns)
            out = []
            for x in xs[:max_n]:
                s = x.strip() if isinstance(x, str) else (x.text or "").strip()
                if s:
                    out.append(s)
            txt = " ".join(out).strip()
            txt = re.sub(r"\s+", " ", txt).strip()
            return txt if txt else None
        except Exception:
            return None

    claims = None
    if claims_xml_bytes:
        claims = _extract_all_text(claims_xml_bytes, "claims") or _extract_all_text(claims_xml_bytes, "claim")
        if claims:
            claims = claims[:truncate_claims]

    desc = None
    if description_xml_bytes:
        desc = _extract_all_text(description_xml_bytes, "description")
        if desc:
            desc = desc[:truncate_description]

    parts = []
    if title:
        parts.append(f"TITLE: {title}")
    if abstract:
        parts.append(f"ABSTRACT: {abstract}")
    if claims:
        parts.append(f"CLAIMS: {claims}")
    if desc:
        parts.append(f"DESCRIPTION: {desc}")

    text_for_embedding = "\n\n".join(parts).strip() if parts else None

    return {
        "text_title": title,
        "text_abstract": abstract,
        "text_claims": claims,
        "text_description": desc,

        "text_has_claims": int(bool(claims)),
        "text_has_description": int(bool(desc)),
        "text_available": int(bool(title or abstract or claims or desc)),

        "text_len_title": len(title) if isinstance(title, str) else 0,
        "text_len_abstract": len(abstract) if isinstance(abstract, str) else 0,
        "text_len_claims": len(claims) if isinstance(claims, str) else 0,
        "text_len_description": len(desc) if isinstance(desc, str) else 0,

        "text_for_embedding": text_for_embedding,
        "text_len_embedding": len(text_for_embedding) if isinstance(text_for_embedding, str) else 0,
    }
def enrich_biblio(df: pd.DataFrame, pub_col: str = "pub", limit: Optional[int] = None) -> pd.DataFrame:
    """
    Join por pub -> añade columnas biblio_* (prioridad, años, title, abstract, kind)
    Reutiliza cache de biblio.
    """
    n = len(df) if limit is None else min(len(df), int(limit))
    rows = []

    for i in range(n):
        idx = df.index[i]
        pub = df.iloc[i][pub_col]
        pub_norm = normalize_pub(pub)
        if not pub_norm:
            rows.append({"_idx": idx, "biblio_error": "bad_pub_format"})
            continue
        try:
            xmlb = fetch_biblio_xml(pub_norm)
            feats = parse_biblio_extra_features(xmlb)
            feats["_idx"] = idx
            rows.append(feats)
        except Exception as e:
            rows.append({"_idx": idx, "biblio_error": str(e)})

    feats_df = pd.DataFrame(rows).set_index("_idx")
    return df.join(feats_df, how="left")

def enrich_parties(df: pd.DataFrame, pub_col: str = "pub", limit: Optional[int] = None) -> pd.DataFrame:
    """
    Join por pub -> añade columnas party_* (solicitantes/inventores, países solicitantes, tipo solicitante)
    Reutiliza cache de biblio (porque parties salen de biblio).
    """
    n = len(df) if limit is None else min(len(df), int(limit))
    rows = []

    for i in range(n):
        idx = df.index[i]
        pub = df.iloc[i][pub_col]
        pub_norm = normalize_pub(pub)
        if not pub_norm:
            rows.append({"_idx": idx, "party_error": "bad_pub_format"})
            continue
        try:
            xmlb = fetch_biblio_xml(pub_norm)
            feats = parse_parties_features(xmlb)
            feats["_idx"] = idx
            rows.append(feats)
        except Exception as e:
            rows.append({"_idx": idx, "party_error": str(e)})

    feats_df = pd.DataFrame(rows).set_index("_idx")
    return df.join(feats_df, how="left")

def enrich_text(
    df: pd.DataFrame,
    pub_col: str = "pub",
    limit: Optional[int] = None,
    include_claims: bool = True,
    include_description: bool = True,
    truncate_claims: int = 12000,
    truncate_description: int = 20000,
) -> pd.DataFrame:
    """
    Join por pub -> añade columnas text_* (title/abstract/claims/description + text_for_embedding)
    - title/abstract: desde biblio (cache)
    - claims/description: endpoints propios (cache)
    """
    n = len(df) if limit is None else min(len(df), int(limit))
    rows = []

    for i in range(n):
        idx = df.index[i]
        pub = df.iloc[i][pub_col]
        pub_norm = normalize_pub(pub)
        if not pub_norm:
            rows.append({"_idx": idx, "text_error": "bad_pub_format"})
            continue

        try:
            biblio_xml = fetch_biblio_xml(pub_norm)

            claims_xml = None
            if include_claims:
                try:
                    claims_xml = fetch_claims_xml(pub_norm)
                except Exception:
                    claims_xml = None

            desc_xml = None
            if include_description:
                try:
                    desc_xml = fetch_description_xml(pub_norm)
                except Exception:
                    desc_xml = None

            feats = parse_text_features(
                biblio_xml_bytes=biblio_xml,
                claims_xml_bytes=claims_xml,
                description_xml_bytes=desc_xml,
                truncate_claims=truncate_claims,
                truncate_description=truncate_description,
            )
            feats["_idx"] = idx
            rows.append(feats)

        except Exception as e:
            rows.append({"_idx": idx, "text_error": str(e)})

    feats_df = pd.DataFrame(rows).set_index("_idx")
    return df.join(feats_df, how="left")


