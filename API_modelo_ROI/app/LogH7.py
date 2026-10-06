"""LogH7 - lightweight file logger helper.

This class is intentionally small and dependency-free: it reads a tiny logging
configuration from the provided `db` object and writes daily log files.

EPO CodeFest-friendly goals:
- Keep it simple to reuse in small services / demos.
- Make behavior explicit via comments and docstrings.
- Avoid surprising logger duplication when instantiated multiple times.
"""

import datetime
import logging
from typing import Any, Dict, Iterable, Tuple


class LogH7:
    """Small helper to log to a daily rotating file (by date).

    Expected DB contract (minimal):
        db.select(callable) -> list[dict]
    where the first result for the key "log_general" contains:
        - 'parametro': 'key=value;key2=value2;...'
        - 'ruta': base path/prefix for the log file (e.g. '/var/log/app_')

    Notes
    -----
    - This is *not* a full-blown logging config system.
    - It is designed for small internal tools where a DB record acts as config.
    """

    def __init__(self, db: Any):
        # Fetch the "log_general" config once (the original version fetched twice).
        record = db.select(lambda r: (r[1] == "log_general"))[0]

        # Parse the parameter string: "key=value;key2=value2;..."
        listado_parametros = str(record.get("parametro", "")).split(";")
        dict_parametros = self._parse_params(listado_parametros)

        # Config defaults (sane and predictable).
        logging_mode = dict_parametros.get("logmode", "INFO").upper()
        formato = dict_parametros.get("format", "%(asctime)s - %(levelname)s - %(message)s")

        # Build the base logger for this module.
        # Using __name__ keeps logs grouped per module (good default).
        self.logger = logging.getLogger(__name__)

        # Base file prefix/path (e.g., '/tmp/h7_' -> '/tmp/h7_YYYYMMDD.log')
        self.filename = str(record.get("ruta", ""))

        # Today's date in the filename: one log per day.
        timestamp = datetime.datetime.now()
        log_path = f"{self.filename}{timestamp.strftime('%Y%m%d')}.log"

        # Map string level -> logging level, defaulting to INFO.
        self.logger.setLevel(self._level_from_string(logging_mode))

        # Create a file handler for the daily file. To avoid duplicated lines
        # when multiple LogH7 instances are created, do not add a duplicate
        # FileHandler pointing to the same file.
        handler = logging.FileHandler(log_path)
        handler.setFormatter(logging.Formatter(formato))

        if not self._has_equivalent_file_handler(self.logger, handler):
            self.logger.addHandler(handler)

        # Optional: prevent messages from being duplicated by parent loggers.
        # Uncomment if you see double logs due to root logger propagation.
        # self.logger.propagate = False

    @staticmethod
    def _parse_params(parts: Iterable[str]) -> Dict[str, str]:
        """Parse a list like ['a=b', 'c=d'] into a dict, ignoring bad entries."""
        parsed: Dict[str, str] = {}
        for raw in parts:
            raw = raw.strip()
            if not raw:
                continue
            if "=" not in raw:
                # Ignore malformed chunks; we keep the logger resilient.
                continue
            k, v = raw.split("=", 1)
            parsed[k.strip()] = v.strip()
        return parsed

    @staticmethod
    def _level_from_string(level: str) -> int:
        """Translate a string level into a `logging` level constant."""
        return {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }.get(level, logging.INFO)

    @staticmethod
    def _has_equivalent_file_handler(logger: logging.Logger, candidate: logging.FileHandler) -> bool:
        """Check whether `logger` already has a FileHandler for the same file."""
        try:
            cand_path = getattr(candidate, "baseFilename", None)
        except Exception:
            cand_path = None

        for h in logger.handlers:
            if isinstance(h, logging.FileHandler):
                try:
                    if getattr(h, "baseFilename", None) == cand_path:
                        return True
                except Exception:
                    continue
        return False

    # --- Public API (Spanish method names kept for backward compatibility) ---

    def escribir_info(self, mensaje: str) -> None:
        """Write an INFO message."""
        self.logger.info(mensaje)

    def escribir_error(self, mensaje: str, excepcion: Exception) -> None:
        """Write an ERROR message plus the exception details."""
        self.logger.error(mensaje)
        self.logger.error(str(excepcion))

    def escribir_warning(self, mensaje: str) -> None:
        """Write a WARNING message."""
        self.logger.warning(mensaje)

    def escribir_debug(self, mensaje: str, detalle: str = "") -> None:
        """Write a DEBUG message and (optionally) extra detail."""
        self.logger.debug(mensaje)
        if detalle:
            self.logger.debug(detalle)
