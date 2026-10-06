"""textdb.py

EPO CodeFest style example
-------------------------
Ultra-lightweight text-based persistence layer.

This module implements a minimalistic "database" backed by a plain text file,
using a pipe ('|') as field separator.

Why this exists in a CodeFest / demo context:
- Zero external dependencies.
- Fully transparent storage format (easy to inspect, diff, version, back up).
- Suitable for prototypes, PoCs, offline demos, or constrained environments.

Important:
This is NOT intended to replace a real database in production systems.
It trades robustness and performance for simplicity and clarity.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class TextDB:
    """A minimal text-file–based data store.

    Parameters
    ----------
    filename:
        Path to the backing text file.
    schema:
        Ordered list of field names defining the record structure.
    """

    def __init__(self, filename: str, schema: List[str]):
        self.filename = filename
        self.schema = schema

    def read_data(self) -> List[List[str]]:
        """Read all records from the backing file.

        Returns
        -------
        List of records, where each record is a list of string values.
        """
        try:
            with open(self.filename, "r") as file:
                data = file.readlines()
            return [line.strip().split("|") for line in data]
        except FileNotFoundError:
            # File does not exist yet: treat as empty database.
            return []

    def write_data(self, data: List[List[str]]) -> None:
        """Overwrite the backing file with the provided records."""
        with open(self.filename, "w") as file:
            for item in data:
                file.write("|".join(item) + "\n")

    def upsert(self, key_field: str, key_value: Any, new_values: List[Any]) -> None:
        """Insert or update a record based on a key field.

        If a record with `key_field == key_value` exists, it is updated.
        Otherwise, a new record is appended.
        """
        if len(new_values) != len(self.schema):
            raise ValueError("new_values length does not match schema")

        data = self.read_data()
        idx = self.schema.index(key_field)

        updated = False
        for i, record in enumerate(data):
            if record[idx] == str(key_value):
                data[i] = [str(x) for x in new_values]
                updated = True
                break

        if not updated:
            data.append([str(x) for x in new_values])

        self.write_data(data)

    def get_one(self, condition: Callable[[List[str]], bool]) -> Optional[Dict[str, str]]:
        """Return the first record matching a condition, or None."""
        rows = self.select(condition)
        return rows[0] if rows else None

    def insert(self, record: List[Any]) -> None:
        """Insert a new record with a simple uniqueness constraint."""
        if len(record) != len(self.schema):
            raise ValueError("Record length does not match schema.")

        data = self.read_data()
        new_field_value_1 = record[1]

        for existing_record in data:
            if existing_record[1] == new_field_value_1:
                raise Exception("Uniqueness constraint violated.")

        data.append([str(x) for x in record])
        self.write_data(data)

    def delete_row(self, record: List[str]) -> None:
        """Delete an exact record match."""
        data = self.read_data()
        if record in data:
            data.remove(record)
            self.write_data(data)

    def delete(self, condition: Callable[[List[str]], bool]) -> None:
        """Delete all records matching a condition."""
        data = self.read_data()
        data = [record for record in data if not condition(record)]
        self.write_data(data)

    def update(self, condition: Callable[[List[str]], bool], new_values: List[Any]) -> None:
        """Update all records matching a condition."""
        if len(new_values) != len(self.schema):
            raise ValueError("new_values length does not match schema")

        data = self.read_data()
        for i, record in enumerate(data):
            if condition(record):
                data[i] = [str(x) for x in new_values]

        self.write_data(data)

    def drop(self) -> None:
        """Remove all records from the database."""
        with open(self.filename, "w") as file:
            file.write("")

    def select(self, condition: Callable[[List[str]], bool]) -> List[Dict[str, str]]:
        """Select records matching a condition and return them as dicts."""
        data = self.read_data()
        selected_records: List[Dict[str, str]] = []

        for record in data:
            if condition(record):
                record_dict = {
                    self.schema[i]: field for i, field in enumerate(record)
                }
                selected_records.append(record_dict)

        return selected_records

    def show(self) -> List[List[str]]:
        """Return all raw records."""
        return self.read_data()

    def tabulate(self) -> List[Dict[str, str]]:
        """Return all records as a list of dictionaries."""
        data = self.read_data()
        return [
            {self.schema[i]: field for i, field in enumerate(record)}
            for record in data
        ]
