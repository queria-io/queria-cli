from __future__ import annotations

import duckdb
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


def test_connect_with_token_creates_secret(storage: str) -> None:
    with queria.connect(storage, token="tok_abc-123") as conn:
        rows = conn.sql(
            "SELECT name, scope FROM duckdb_secrets() WHERE name = 'queria_auth'"
        ).fetchall()
    assert len(rows) == 1
    assert storage in rows[0][1]


def test_connect_without_token_creates_no_secret(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql(
            "SELECT name FROM duckdb_secrets() WHERE name = 'queria_auth'"
        ).fetchall()
    assert rows == []


def test_connect_rejects_invalid_token(storage: str) -> None:
    with pytest.raises(ValueError, match="invalid token"):
        queria.connect(storage, token="tok', SCOPE ''); DROP SECRET x; --")


def test_rate_limit_detected_from_http_429() -> None:
    exc = duckdb.IOException(
        "HTTP GET error on 'https://data.queria.io/x' (HTTP 429)"
    )
    with pytest.raises(core.RateLimitError, match="queria auth set-token"):
        core._raise_if_rate_limited(exc)


def test_other_errors_are_not_rate_limits() -> None:
    core._raise_if_rate_limited(duckdb.IOException("HTTP 404"))  # no raise
    core._raise_if_rate_limited(duckdb.BinderException("429"))  # not an IO error


def test_search_escapes_quotes(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql(core.search_sql("o'brien")).fetchall()
    assert rows == []


def test_search_spans_datasets_tables_and_columns(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql(core.search_sql("postal")).fetchall()
    # (entry_type, datasource, schema_name, table_name, column_name, description)
    assert [(r[0], r[1], r[4]) for r in rows] == [
        ("dataset", "zipcode", None),
        ("column", "zipcode", "code"),
    ]


def test_search_filters_by_entry_type(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql(core.search_sql("numbers", entry_type="table")).fetchall()
    assert [(r[0], r[3]) for r in rows] == [("table", "numbers")]


def test_search_applies_limit(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql(core.search_sql("e", limit=1)).fetchall()
    assert len(rows) == 1


def test_search_rejects_bad_arguments() -> None:
    with pytest.raises(ValueError):
        core.search_sql("x", entry_type="schema")
    with pytest.raises(ValueError):
        core.search_sql("x", limit=0)


def test_info_sql_returns_field_value_rows(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = dict(conn.sql(core.info_sql("demo")).fetchall())
    assert rows["license"] == "CC-BY-4.0"
    assert rows["source_url"] == "https://example.com/source"
    assert "readme" not in rows


def test_info_sql_omits_null_fields(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = dict(conn.sql(core.info_sql("zipcode")).fetchall())
    assert rows["license"] == "CC-BY-4.0"
    assert "source_url" not in rows


def test_info_sql_include_readme(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = dict(
            conn.sql(core.info_sql("demo", include_readme=True)).fetchall()
        )
    assert rows["readme"] == "# Demo readme"


def test_info_sql_rejects_bad_identifier() -> None:
    with pytest.raises(ValueError):
        core.info_sql("demo; --")


def test_schema_and_columns_sql(storage: str) -> None:
    with queria.connect(storage) as conn:
        tables = conn.sql(core.schema_sql("demo")).fetchall()
        assert [t[1] for t in tables] == ["numbers", "stg_numbers"]
        cols = conn.sql(core.columns_sql("demo", "numbers")).fetchall()
        assert [c[1] for c in cols] == ["label", "n"]


def test_summarize_sql_defaults_schema_to_main() -> None:
    assert core.summarize_sql("demo.numbers") == "SUMMARIZE demo.main.numbers"
    assert core.summarize_sql("demo.main.numbers") == "SUMMARIZE demo.main.numbers"


def test_summarize_sql_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        core.summarize_sql("numbers")
    with pytest.raises(ValueError):
        core.summarize_sql("a.b.c.d")
    with pytest.raises(ValueError):
        core.summarize_sql("demo.main.numbers; --")


def test_summarize_auto_attaches(storage: str) -> None:
    with queria.connect(storage) as conn:
        rows = conn.sql(core.summarize_sql("demo.numbers")).fetchall()
    assert {r[0] for r in rows} == {"n", "label"}


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


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT content FROM read_text('/etc/passwd')", "read_text"),
        ("SELECT * FROM read_csv('http://169.254.169.254/x')", "read_csv"),
        ("SELECT * FROM glob('/**')", "glob"),
        ("SELECT * FROM ST_Read('/x.shp')", "st_read"),
        ("SELECT * FROM sniff_csv('/x.csv')", "sniff_csv"),
        # nested inside a CTE / subquery / function argument
        ("WITH t AS (SELECT * FROM read_blob('/x')) SELECT * FROM t", "read_blob"),
        ("SELECT * FROM (SELECT content FROM read_text('/x')) u", "read_text"),
        ("SELECT upper(read_text('/x'))", "read_text"),
        # dynamic SQL would smuggle a reader past the AST scan inside a string
        (
            "SELECT * FROM query('SELECT content FROM read_text(''/x'')')",
            "query",
        ),
        ("SELECT * FROM query_table('demo.main.numbers')", "query_table"),
        # safe queries against the catalog
        ("SELECT n FROM demo.main.numbers ORDER BY n", None),
        ("SELECT count(*) FROM catalog.main.mart_datasets", None),
        ("SUMMARIZE demo.main.numbers", None),
        # a string literal that merely looks like a call must not trip it
        ("SELECT 'read_text(' AS x", None),
    ],
)
def test_unsafe_function(sql: str, expected: str | None) -> None:
    assert core.unsafe_function(sql) == expected


def test_unsafe_function_lexical_fallback() -> None:
    # DESCRIBE of a table function cannot be serialized to JSON, so the check
    # falls back to a lexical scan rather than failing open.
    assert core.unsafe_function("DESCRIBE read_csv('/x')") == "read_csv"
