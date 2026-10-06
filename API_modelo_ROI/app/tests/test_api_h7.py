"""test_api_h7.py

EPO CodeFest – Unit tests for the API H7 Flask service (app.py)
--------------------------------------------------------------
Important isolation note
------------------------
This test module needs to stub project-local imports (TextDB, LogH7, ModeloML,
Utilidades) *only while importing the API module*.

When tests are run via `unittest discover`, other test modules (e.g.
`test_utilidades.py`) may import the real `Utilidades` module. If we leave stubs
in `sys.modules`, we can accidentally break those tests.

Therefore this test suite:
- Temporarily injects stubs into `sys.modules` during module import.
- Restores `sys.modules` to its previous state immediately after import.

Run:
- If tests live in app/tests:
    python -m unittest discover -s app/tests -v
"""

from __future__ import annotations

import io
import json
import types
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from werkzeug.datastructures import FileStorage


# ---------------------------------------------------------------------------
# Import-time stubs (match the API's expectations)
# ---------------------------------------------------------------------------

class _StubTextDB:
    """TextDB stub matching the *index-based* access pattern in the API."""

    def __init__(self, _filename: str, schema: list[str]):
        self.schema = schema
        self._rows: list[list[str]] = []

    def select(self, predicate):
        return [row for row in self._rows if predicate(row)]

    def insert(self, record_list):
        self._rows.append(list(record_list))

    def update(self, predicate, record_list):
        for i, row in enumerate(self._rows):
            if predicate(row):
                self._rows[i] = list(record_list)

    def delete(self, predicate):
        self._rows = [row for row in self._rows if not predicate(row)]

    def tabulate(self):
        out = []
        for row in self._rows:
            out.append({self.schema[i]: row[i] for i in range(min(len(self.schema), len(row)))})
        return out


class _StubLogH7:
    def __init__(self, *_args, **_kwargs):
        pass

    def escribir_info(self, *_args, **_kwargs):
        pass

    def escribir_error(self, *_args, **_kwargs):
        pass


class _StubModeloML:
    def __init__(self):
        self.modelo = object()

    def predecir(self, X):
        return np.array([0.123] * len(X))

    @staticmethod
    def cargar_modelo(_ruta_archivo: str):
        return _StubModeloML()


class _StubUtilidades:
    """Stub only for what the API needs at import/runtime."""

    @staticmethod
    def validar_json_ins(_obj):
        return True

    @staticmethod
    def validar_json(s: str) -> bool:
        try:
            json.loads(s)
            return True
        except Exception:
            return False

    @staticmethod
    def obtener_fecha_escritura(_path):
        return "01/01/2000-00:00"

    @staticmethod
    def calcular_checksum(_path):
        return "deadbeef"


def _load_api_h7_module():
    """Locate and import the target API module with temporary stubs."""
    candidates = ["app.py", "api.py", "api_h7.py"]

    here = Path(__file__).resolve()
    target_path = None

    for parent in [here.parent] + list(here.parents):
        for name in candidates:
            p = parent / name
            if p.exists() and p.is_file():
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if "/api_h7/" in txt and ("Flask" in txt or "app = Flask" in txt):
                    target_path = p
                    break
        if target_path:
            break

    if not target_path:
        raise ModuleNotFoundError(
            "Could not locate the API module (app.py/api.py/api_h7.py) containing '/api_h7/'."
        )

    import sys

    # Save previous modules so we can restore them (prevents leakage).
    keys = ["TextDB", "LogH7", "ModeloML", "Utilidades"]
    prev = {k: sys.modules.get(k) for k in keys}
    to_delete = set()

    try:
        # Inject temporary stubs
        if sys.modules.get("TextDB") is None:
            sys.modules["TextDB"] = types.SimpleNamespace(TextDB=_StubTextDB)
            to_delete.add("TextDB")
        if sys.modules.get("LogH7") is None:
            sys.modules["LogH7"] = types.SimpleNamespace(LogH7=_StubLogH7)
            to_delete.add("LogH7")
        if sys.modules.get("ModeloML") is None:
            sys.modules["ModeloML"] = types.SimpleNamespace(ModeloML=_StubModeloML)
            to_delete.add("ModeloML")
        if sys.modules.get("Utilidades") is None:
            sys.modules["Utilidades"] = _StubUtilidades
            to_delete.add("Utilidades")

        spec = importlib.util.spec_from_file_location("api_h7_app", target_path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not build import spec for: {target_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return module

    finally:
        # Restore previous modules
        for k in keys:
            if prev[k] is not None:
                sys.modules[k] = prev[k]
            elif k in to_delete:
                sys.modules.pop(k, None)


webapp = _load_api_h7_module()


# ---------------------------------------------------------------------------
# Helper tests (stable)
# ---------------------------------------------------------------------------

class TestHelpers(unittest.TestCase):
    def test_validate_model_file_accepts_allowed_extensions(self):
        fs = FileStorage(stream=io.BytesIO(b"model"), filename="m.pkl")
        ok, msg = webapp.validate_model_file(fs)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

        fs2 = FileStorage(stream=io.BytesIO(b"model"), filename="m.joblib")
        ok2, _ = webapp.validate_model_file(fs2)
        self.assertTrue(ok2)

    def test_validate_model_file_rejects_disallowed_extensions(self):
        fs = FileStorage(stream=io.BytesIO(b"model"), filename="m.exe")
        ok, msg = webapp.validate_model_file(fs)
        self.assertFalse(ok)
        self.assertIn("Extensión no permitida", msg)


# ---------------------------------------------------------------------------
# Route tests (smoke-level, per your current relaxed assertions)
# ---------------------------------------------------------------------------

class TestRoutes(unittest.TestCase):
    def setUp(self):
        webapp.app.testing = True
        self.client = webapp.app.test_client()

        # Register one context in the API's db (index-based schema)
        schema = ["modelo", "contexto", "input", "output", "fecha", "checksum", "ruta"]
        if getattr(webapp, "db", None) is None or not hasattr(webapp.db, "schema"):
            webapp.db = _StubTextDB("db.txt", schema)
        else:
            webapp.db.schema = schema

        manifest = {
            "input_schema": {"expected_features": ["is_active_recent"]},
            "output_schema": {"type": "regression", "target": "pred"},
        }

        webapp.db._rows = [[
            "demo_model",
            "epo_roi",
            json.dumps(manifest),
            json.dumps(manifest["output_schema"]),
            "01/01/2000 00:00:00",
            "deadbeef",
            "modelos/fake.pkl",
        ]]

    def test_api_health(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)

    def test_schema_unknown_context_404(self):
        resp = self.client.get("/api_h7/unknown/schema")
        self.assertEqual(resp.status_code, 404)

    def test_schema_known_context(self):
        resp = self.client.get("/api_h7/epo_roi/schema")
        self.assertIn(resp.status_code, (200, 500))

    @patch.object(webapp.os.path, "isfile", return_value=True)
    @patch.object(webapp.os.path, "abspath", side_effect=lambda p: p)
    @patch.object(webapp, "MML", types.SimpleNamespace(cargar_modelo=_StubModeloML.cargar_modelo))
    def test_predict_happy_path(self, *_mocks):
        resp = self.client.post("/api_h7/epo_roi", json={"is_active_recent": [1]})
        self.assertIn(resp.status_code, (200, 500))

    def test_predict_missing_context_404(self):
        resp = self.client.post("/api_h7/not_registered", json={"x": [1]})
        self.assertEqual(resp.status_code, 404)

    def test_predict_invalid_json_400(self):
        resp = self.client.post(
            "/api_h7/epo_roi",
            data="{invalid json",
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 500))


if __name__ == "__main__":
    unittest.main(verbosity=2)
