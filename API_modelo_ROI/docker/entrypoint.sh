#!/bin/sh
set -e

echo "[entrypoint] installing hotfix module LogH7 into /tmp/hotfix"

mkdir -p /tmp/hotfix

cat > /tmp/hotfix/LogH7.py <<'PY'
import logging
from pathlib import Path

class LogH7:
    """
    Hotfix runtime logger to avoid boot-time crashes due to missing/invalid 'log_general' config.
    It mimics the interface expected by the app, but degrades gracefully.
    """
    def __init__(self, db_conf=None):
        # Fichero por defecto (si el original esperaba una ruta)
        self.filename = "/tmp/log_h7.log"
        try:
            Path("/tmp").mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self._logger = logging.getLogger("LogH7Hotfix")
        if not self._logger.handlers:
            self._logger.setLevel(logging.INFO)
            h = logging.StreamHandler()
            fmt = logging.Formatter("[LogH7Hotfix] %(levelname)s %(message)s")
            h.setFormatter(fmt)
            self._logger.addHandler(h)

        self._logger.info("LogH7Hotfix activo (db_conf ignorado para evitar crash en arranque).")

    # Métodos típicos: si tu app llama a alguno, no fallará
    def info(self, msg, *args, **kwargs): self._logger.info(str(msg))
    def debug(self, msg, *args, **kwargs): self._logger.debug(str(msg))
    def warning(self, msg, *args, **kwargs): self._logger.warning(str(msg))
    def warn(self, msg, *args, **kwargs): self._logger.warning(str(msg))
    def error(self, msg, *args, **kwargs): self._logger.error(str(msg))
    def exception(self, msg, *args, **kwargs): self._logger.exception(str(msg))

    # Si el código llama a cualquier otro método, no rompas
    def __getattr__(self, name):
        def _noop(*args, **kwargs):
            # No-op silencioso
            return None
        return _noop
PY

# Asegura que Python encuentra primero /tmp/hotfix, y también tu paquete real /app/app
export PYTHONPATH="/tmp/hotfix:/app/app:/app:${PYTHONPATH}"

echo "[entrypoint] PYTHONPATH=$PYTHONPATH"
echo "[entrypoint] starting gunicorn..."
exec gunicorn wsgi:app --bind 0.0.0.0:8000