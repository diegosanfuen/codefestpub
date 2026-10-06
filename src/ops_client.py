import os
from dotenv import load_dotenv
import epo_ops

def get_ops_client():
    # Carga variables desde .env
    load_dotenv()

    key = os.getenv("OPS_KEY")
    secret = os.getenv("OPS_SECRET")

    if not key or not secret:
        raise RuntimeError(
            "Faltan OPS_KEY / OPS_SECRET en el fichero .env"
        )

    # El cliente gestiona OAuth2 automáticamente
    client = epo_ops.Client(
        key=key,
        secret=secret
    )
    return client
