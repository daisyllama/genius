"""Structural checks for the SQL schema in lyrics_analysis.db.models."""

from __future__ import annotations

import re

from lyrics_analysis.db.models import SCHEMA_SQL

CREATE_TABLE_RE = re.compile(r"CREATE TABLE IF NOT EXISTS (\w+)")
REFERENCES_RE = re.compile(r"REFERENCES (\w+)\(")
CREATE_INDEX_RE = re.compile(r"CREATE INDEX IF NOT EXISTS \w+\s+ON (\w+)")


def test_every_reference_target_defined_earlier():
    defined_tables: list[str] = []
    pos = 0
    while True:
        table_match = CREATE_TABLE_RE.search(SCHEMA_SQL, pos)
        ref_match = REFERENCES_RE.search(SCHEMA_SQL, pos)

        if table_match and (not ref_match or table_match.start() < ref_match.start()):
            defined_tables.append(table_match.group(1))
            pos = table_match.end()
        elif ref_match:
            target = ref_match.group(1)
            assert target in defined_tables, (
                f"REFERENCES {target} appears before its table is defined"
            )
            pos = ref_match.end()
        else:
            break


def test_every_index_targets_a_defined_table():
    defined_tables = set(CREATE_TABLE_RE.findall(SCHEMA_SQL))
    for match in CREATE_INDEX_RE.finditer(SCHEMA_SQL):
        table = match.group(1)
        assert table in defined_tables, f"CREATE INDEX targets undefined table {table}"


def test_schema_is_nonempty():
    assert len(CREATE_TABLE_RE.findall(SCHEMA_SQL)) > 0
