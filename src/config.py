# src/config.py
from pathlib import Path

# OPS configuration
OPS_BASE = "https://ops.epo.org/3.2/rest-services"
OPS_TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"

# Cache configuration
CACHE_DIR = Path("data/interim/ops_cache")

# Congfiguracion descarga
OPS_QUERY = "pn=EP"
OPS_N_PATENTS = 2000
OPS_BATCH_LEN = 25
OPS_PUB_YEAR = 2023
OPS_START = 1
OPS_MAX_TRIES = 8




