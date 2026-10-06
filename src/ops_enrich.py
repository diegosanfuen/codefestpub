import re
from pathlib import Path
import pandas as pd
from lxml import etree
import epo_ops

from src.ops_client import get_ops_client
from src.config import CACHE_DIR


CACHE_DIR.mkdir(parents=True, exist_ok=True)

PUB_RE = re.compile(r"^([A-Z]{2})(\d+)([A-Z]\d)?$")  # EP1000000A1

def pub_to_docdb(pub: str):
    pub = str(pub).replace(" ", "").replace(".", "").upper()
    m = PUB_RE.match(pub)
    if not m:
        return None
    country, number, kind = m.group(1), m.group(2), m.group(3) or "A1"
    # OJO: orden correcto del Docdb: (number, country, kind)
    return epo_ops.models.Docdb(number, country, kind)

def cache_path(docdb, endpoint: str):
    return CACHE_DIR / f"{docdb.country}.{docdb.number}.{docdb.kind}.{endpoint}.xml"

def fetch_endpoint_xml(docdb, endpoint: str) -> bytes:
    cpath = cache_path(docdb, endpoint)
    if cpath.exists():
        return cpath.read_bytes()

    client = get_ops_client()
    r = client.published_data(reference_type="publication", input=docdb, endpoint=endpoint)
    if r.status_code != 200:
        raise RuntimeError(f"OPS {endpoint} error {r.status_code}: {r.content[:200]}")
    cpath.write_bytes(r.content)
    return r.content

def parse_biblio_features(xml_bytes: bytes) -> dict:
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
    }

    # IPC principal (simple)
    try:
        ipc_texts = root.xpath("//*[local-name()='classification-ipc']//*[local-name()='text']/text()", namespaces=ns)
        feats["ops_ipc_main"] = ipc_texts[0].strip() if ipc_texts else None
    except Exception:
        feats["ops_ipc_main"] = None

    return feats

def enrich_ops_biblio(df: pd.DataFrame, pub_col: str, limit: int | None = None) -> pd.DataFrame:
    n = len(df) if limit is None else min(len(df), int(limit))
    rows = []

    for i in range(n):
        idx = df.index[i]
        pub = df.iloc[i][pub_col]
        docdb = pub_to_docdb(pub)
        if docdb is None:
            rows.append({"_idx": idx, "ops_error": "bad_pub_format"})
            continue
        try:
            xmlb = fetch_endpoint_xml(docdb, "biblio")
            feats = parse_biblio_features(xmlb)
            feats["_idx"] = idx
            rows.append(feats)
        except Exception as e:
            rows.append({"_idx": idx, "ops_error": str(e)})

    feats_df = pd.DataFrame(rows).set_index("_idx")
    return df.join(feats_df, how="left")
