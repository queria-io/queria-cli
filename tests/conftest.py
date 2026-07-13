"""Shared fixtures: a local DuckLake storage layout mimicking data.queria.io.

The fixture builds real DuckLake catalogs on disk (a ``catalog`` metadata
dataset plus a ``demo`` data dataset) so tests exercise the actual attach /
auto-attach / query paths without network access.
"""

from __future__ import annotations

import duckdb
import pytest


@pytest.fixture(autouse=True)
def isolate_auth(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests independent of the developer's real token configuration."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.delenv("QUERIA_TOKEN", raising=False)


def _attach_writable(con: duckdb.DuckDBPyConnection, root: str, alias: str) -> None:
    con.execute(
        f"ATTACH 'ducklake:{root}/{alias}/ducklake.duckdb' AS {alias} "
        f"(DATA_PATH '{root}/{alias}/ducklake.duckdb.files/')"
    )


@pytest.fixture(scope="session")
def storage(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = tmp_path_factory.mktemp("storage")
    (root / "catalog").mkdir()
    (root / "demo").mkdir()

    con = duckdb.connect()
    con.execute("INSTALL ducklake; LOAD ducklake;")

    _attach_writable(con, str(root), "catalog")
    con.execute("""
        CREATE TABLE catalog.main.mart_datasets AS
        SELECT * FROM (VALUES
            ('demo', 'Demo dataset', 'Numbers for testing', 'cover.png',
             'https://example.com/demo/ducklake.duckdb',
             'https://github.com/example/demo', 'daily', '["test"]',
             'CC-BY-4.0', 'https://example.com/license',
             'https://example.com/source', '["main"]', '1.8.0',
             TIMESTAMP '2026-01-01 00:00:00', 'inv-1', '# Demo readme'),
            ('zipcode', 'Zipcode', 'Japanese postal codes', NULL,
             NULL, NULL, NULL, NULL,
             'CC-BY-4.0', NULL,
             NULL, '["main"]', NULL,
             NULL, NULL, NULL)
        ) t(datasource, title, description, cover, ducklake_url,
            repository_url, schedule, tags_json, license, license_url,
            source_url, schemas_json, dbt_version, dbt_generated_at,
            dbt_invocation_id, readme)
    """)
    con.execute("""
        CREATE TABLE catalog.main.mart_nodes AS
        SELECT * FROM (VALUES
            ('demo', 'main', 'numbers', 'A tiny numbers table', 'model'),
            ('demo', 'main', 'stg_numbers', 'Staging numbers', 'model'),
            ('zipcode', 'main', 'zipcodes', 'Postal codes', 'model')
        ) t(datasource, schema_name, name, description, resource_type)
    """)
    con.execute("""
        CREATE TABLE catalog.main.mart_columns AS
        SELECT * FROM (VALUES
            ('demo', 'numbers', 'n', 'INTEGER', 'The number'),
            ('demo', 'numbers', 'label', 'VARCHAR', 'Its label'),
            ('demo', 'stg_numbers', 'n', 'INTEGER', 'The number'),
            ('zipcode', 'zipcodes', 'code', 'VARCHAR', 'Postal code')
        ) t(datasource, table_name, column_name, data_type, description)
    """)
    con.execute("""
        CREATE TABLE catalog.main.mart_search_entries AS
        SELECT * FROM (VALUES
            ('table', 'demo', 'main', 'numbers', 'Numbers', NULL,
             'A tiny numbers table', 'numbers Numbers A tiny numbers table',
             '/datasets/demo/main/numbers'),
            ('column', 'demo', 'main', 'numbers', 'Numbers', 'label',
             'Its label', 'label Its label numbers',
             '/datasets/demo/main/numbers'),
            ('column', 'zipcode', 'main', 'zipcodes', 'Zipcodes', 'code',
             'Postal code', 'code Postal code zipcodes',
             '/datasets/zipcode/main/zipcodes')
        ) t(entry_type, datasource, schema_name, table_name, table_title,
            column_name, description, search_text, href)
    """)
    con.execute("DETACH catalog")

    _attach_writable(con, str(root), "demo")
    con.execute("""
        CREATE TABLE demo.main.numbers AS
        SELECT * FROM (VALUES
            (1, 'one'), (2, 'two'), (3, 'three')
        ) t(n, label)
    """)
    con.execute("DETACH demo")
    con.close()

    return str(root)
