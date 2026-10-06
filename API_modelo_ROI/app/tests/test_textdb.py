"""test_textdb.py

EPO CodeFest – Unit tests for `TextDB`
-------------------------------------
This test file is robust to common repo layouts, e.g.:

A) project_root/
      TextDB.py
      tests/test_textdb.py

B) project_root/
      app/
        TextDB.py
        tests/test_textdb.py

C) project_root/
      TextDB_commented.py
      app/tests/test_textdb.py

It will locate the module file by walking up parent directories and loading it
directly from its file path (so it does not depend on PYTHONPATH).

How to run (from project root):
    python -m unittest discover -s tests -v

or if tests are under app/tests:
    python -m unittest discover -s app/tests -v
"""

from __future__ import annotations

import importlib.util
import unittest
import tempfile
from pathlib import Path


def _load_textdb_class():
    """Locate TextDB module file and return the TextDB class.

    This avoids brittle `sys.path` assumptions when tests live in nested folders.
    """
    candidates = [
        "TextDB.py",
        "TextDB_commented.py",
        "textdb.py",
    ]

    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        for name in candidates:
            module_path = parent / name
            if module_path.exists() and module_path.is_file():
                spec = importlib.util.spec_from_file_location("textdb_module", module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)  # type: ignore[attr-defined]
                    if hasattr(module, "TextDB"):
                        return module.TextDB
    raise ModuleNotFoundError(
        "Could not locate TextDB module file. Expected one of: "
        + ", ".join(candidates)
        + " in this directory or any parent directory of the tests."
    )


TextDB = _load_textdb_class()


class TestTextDB(unittest.TestCase):
    """Unit tests for the TextDB text-file store."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.db_file = Path(self.tmp.name) / "db.txt"
        self.schema = ["id", "name", "value"]
        self.db = TextDB(str(self.db_file), self.schema)

    def test_read_data_returns_empty_when_file_missing(self):
        self.assertEqual(self.db.read_data(), [])

    def test_write_and_read_roundtrip(self):
        data = [["1", "alice", "10"], ["2", "bob", "20"]]
        self.db.write_data(data)
        self.assertEqual(self.db.read_data(), data)

    def test_insert_adds_record(self):
        self.db.insert(["1", "alice", "10"])
        self.assertEqual(self.db.read_data(), [["1", "alice", "10"]])

    def test_insert_enforces_uniqueness_on_second_field(self):
        self.db.insert(["1", "alice", "10"])
        with self.assertRaises(Exception):
            self.db.insert(["2", "alice", "99"])  # duplicate 'name' (index 1)

    def test_insert_validates_schema_length(self):
        with self.assertRaises(ValueError):
            self.db.insert(["1", "alice"])  # wrong length

    def test_upsert_inserts_when_key_not_found(self):
        self.db.upsert("id", "1", ["1", "alice", "10"])
        self.assertEqual(self.db.read_data(), [["1", "alice", "10"]])

    def test_upsert_updates_when_key_found(self):
        self.db.upsert("id", "1", ["1", "alice", "10"])
        self.db.upsert("id", "1", ["1", "alice", "999"])
        self.assertEqual(self.db.read_data(), [["1", "alice", "999"]])

    def test_upsert_validates_schema_length(self):
        with self.assertRaises(ValueError):
            self.db.upsert("id", "1", ["1", "alice"])  # wrong length

    def test_select_returns_dicts_with_schema_keys(self):
        self.db.write_data([["1", "alice", "10"], ["2", "bob", "20"]])
        rows = self.db.select(lambda r: r[2] == "20")
        self.assertEqual(rows, [{"id": "2", "name": "bob", "value": "20"}])

    def test_get_one_returns_first_or_none(self):
        self.db.write_data([["1", "alice", "10"], ["2", "bob", "20"]])

        row = self.db.get_one(lambda r: r[1] == "alice")
        self.assertEqual(row, {"id": "1", "name": "alice", "value": "10"})

        self.assertIsNone(self.db.get_one(lambda r: r[1] == "charlie"))

    def test_update_modifies_matching_rows(self):
        self.db.write_data([["1", "alice", "10"], ["2", "bob", "20"]])
        self.db.update(lambda r: r[1] == "bob", ["2", "bob", "999"])
        self.assertEqual(self.db.read_data(), [["1", "alice", "10"], ["2", "bob", "999"]])

    def test_update_validates_schema_length(self):
        self.db.write_data([["1", "alice", "10"]])
        with self.assertRaises(ValueError):
            self.db.update(lambda r: True, ["1", "alice"])  # wrong length

    def test_delete_removes_matching_rows(self):
        self.db.write_data([["1", "alice", "10"], ["2", "bob", "20"], ["3", "carl", "20"]])
        self.db.delete(lambda r: r[2] == "20")
        self.assertEqual(self.db.read_data(), [["1", "alice", "10"]])

    def test_delete_row_removes_exact_record(self):
        self.db.write_data([["1", "alice", "10"], ["2", "bob", "20"]])
        self.db.delete_row(["2", "bob", "20"])
        self.assertEqual(self.db.read_data(), [["1", "alice", "10"]])

    def test_drop_empties_file(self):
        self.db.write_data([["1", "alice", "10"]])
        self.db.drop()
        self.assertEqual(self.db.read_data(), [])

    def test_show_returns_raw_records(self):
        self.db.write_data([["1", "alice", "10"]])
        self.assertEqual(self.db.show(), [["1", "alice", "10"]])

    def test_tabulate_returns_all_as_dicts(self):
        self.db.write_data([["1", "alice", "10"], ["2", "bob", "20"]])
        rows = self.db.tabulate()
        self.assertEqual(
            rows,
            [
                {"id": "1", "name": "alice", "value": "10"},
                {"id": "2", "name": "bob", "value": "20"},
            ],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
