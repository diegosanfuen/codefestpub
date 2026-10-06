"""Unit tests for Utilidades.py (stdlib `unittest`).

Why `unittest` (instead of pytest):
- Zero extra dependencies for reviewers/runners.
- Works out-of-the-box in most Python environments.

How to run:
- From the project root (where Utilidades.py lives):
    python -m unittest -v

If your file is named `Utilidades_commented.py`, either:
- rename it to `Utilidades.py`, or
- adjust the import below.
"""

import os
import io
import time
import zipfile
import hashlib
import tempfile
import unittest
from pathlib import Path

# Load the real Utilidades module from the project tree.
# This avoids accidental interference from other tests that may stub modules.
import importlib.util

def _load_utilidades_module():
    here = Path(__file__).resolve()
    candidates = ["Utilidades.py", "Utilidades_commented.py", "utilidades.py"]
    for parent in [here.parent] + list(here.parents):
        for name in candidates:
            p = parent / name
            if p.exists() and p.is_file():
                spec = importlib.util.spec_from_file_location("utilidades_module", p)
                if spec and spec.loader:
                    m = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(m)  # type: ignore[attr-defined]
                    return m
    raise ModuleNotFoundError("Could not locate Utilidades.py (or Utilidades_commented.py) in parents.")

util = _load_utilidades_module()


class TestUtilidadesJSON(unittest.TestCase):
    def test_validar_json_true_for_valid_json_string(self):
        self.assertTrue(util.validar_json('{"a": 1, "b": [1, 2, 3]}'))

    def test_validar_json_false_for_invalid_json_string(self):
        self.assertFalse(util.validar_json('{"a": 1,'))  # trailing comma / incomplete

    def test_validar_json_ins_true_for_serializable_object(self):
        self.assertTrue(util.validar_json_ins({"a": 1, "b": [1, 2, 3]}))

    def test_validar_json_ins_false_for_non_serializable_object(self):
        # Sets are not JSON-serializable by default
        self.assertFalse(util.validar_json_ins({1, 2, 3}))


class TestUtilidadesFS(unittest.TestCase):
    def test_crear_ruta_temporal_creates_tmp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                util.crear_ruta_temporal()
                self.assertTrue((Path(tmp) / "_tmp").exists())
                self.assertTrue((Path(tmp) / "_tmp").is_dir())
            finally:
                os.chdir(old_cwd)

    def test_eliminar_ficheros_ruta_temporal_removes_files_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                # Prepare _tmp with a file and a subdir
                tmp_dir = Path(tmp) / "_tmp"
                tmp_dir.mkdir()
                (tmp_dir / "a.txt").write_text("hello", encoding="utf-8")
                (tmp_dir / "subdir").mkdir()

                util.eliminar_ficheros_ruta_temporal()

                self.assertFalse((tmp_dir / "a.txt").exists())
                self.assertTrue((tmp_dir / "subdir").exists())  # directories are kept
            finally:
                os.chdir(old_cwd)

    def test_eliminar_ruta_temporal_removes_tmp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                tmp_dir = Path(tmp) / "_tmp"
                tmp_dir.mkdir()
                (tmp_dir / "x.txt").write_text("x", encoding="utf-8")

                util.eliminar_ruta_temporal()
                self.assertFalse(tmp_dir.exists())
            finally:
                os.chdir(old_cwd)

    def test_obtener_fecha_escritura_returns_formatted_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "file.txt"
            p.write_text("content", encoding="utf-8")

            s = util.obtener_fecha_escritura(str(p))

            # Expected format: DD/MM/YYYY-HH:MM -> length 16, contains '/' and '-'
            self.assertEqual(len(s), 16)
            self.assertIn("/", s)
            self.assertIn("-", s)

    def test_comprimir_backup_file_creates_zip_with_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "model.pkl"
            src.write_bytes(b"abc123")

            out_zip = Path(tmp) / "backup.zip"
            util.comprimir_backup(src, out_zip)

            self.assertTrue(out_zip.exists())
            with zipfile.ZipFile(out_zip, "r") as zf:
                names = zf.namelist()
                self.assertIn("model.pkl", names)
                self.assertEqual(zf.read("model.pkl"), b"abc123")

    def test_calcular_checksum_matches_hashlib_md5(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.bin"
            data = b"hello world\n"
            p.write_bytes(data)

            expected = hashlib.md5(data).hexdigest()
            got = util.calcular_checksum(p)

            self.assertEqual(got, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
