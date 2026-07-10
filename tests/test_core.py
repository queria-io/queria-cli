from __future__ import annotations

import pytest

import queria
from queria import core


def test_connect_lists_datasets(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql(core.list_datasets_sql()).fetchall()
    assert [r[0] for r in rows] == ["demo", "zipcode"]


def test_auto_attach_on_reference(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql("SELECT n, label FROM demo.main.numbers ORDER BY n").fetchall()
    assert rows == [(1, "one"), (2, "two"), (3, "three")]


def test_attach_is_idempotent(storage: str) -> None:
    with queria.connect(storage) as conn:
        conn.attach("demo")
        conn.attach("demo")
        assert conn.sql("SELECT count(*) FROM demo.main.numbers").fetchone()[0] == 3


def test_missing_dataset_raises(storage: str) -> None:
    with queria.connect(storage) as conn:
        with pytest.raises(Exception, match="nope"):
            conn.sql("SELECT * FROM nope.main.t")


def test_attach_rejects_bad_identifier(storage: str) -> None:
    with queria.connect(storage) as conn:
        with pytest.raises(ValueError):
            conn.attach("bad-name; DROP TABLE x")


def test_writes_rejected_by_engine(storage: str) -> None:
    with queria.connect(storage) as conn:
        with pytest.raises(Exception, match="(?i)read.only"):
            conn.sql("DELETE FROM demo.main.numbers")


def test_search_escapes_quotes(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql(core.search_datasets_sql("o'brien")).fetchall()
    assert rows == []


def test_schema_and_columns_sql(storage: str) -> None:
    with queria.connect(storage) as conn:
        tables = conn.sql(core.schema_sql("demo")).fetchall()
        assert [t[1] for t in tables] == ["numbers", "stg_numbers"]
        cols = conn.sql(core.columns_sql("demo", "numbers")).fetchall()
        assert [c[1] for c in cols] == ["label", "n"]


def test_columns_sql_rejects_bad_table() -> None:
    with pytest.raises(ValueError):
        core.columns_sql("demo", "numbers; --")


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT 1", True),
        ("  WITH t AS (SELECT 1) SELECT * FROM t", True),
        ("EXPLAIN SELECT 1", True),
        ("SUMMARIZE demo.main.numbers", True),
        ("DROP TABLE x", False),
        ("INSERT INTO t VALUES (1)", False),
        ("ATTACH 'x' AS y", False),
        ("UPDATE t SET x = 1", False),
    ],
)
def test_is_read_only(sql: str, expected: bool) -> None:
    assert core.is_read_only(sql) is expected
