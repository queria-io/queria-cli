"""Core connection and catalog helpers for Queria's public DuckLake catalogs.

Queria (https://data.queria.io) publishes Japanese open data as read-only
DuckLake catalogs. This module owns the connection lifecycle: attaching the
``catalog`` metadata dataset, auto-attaching other datasets referenced in
queries, and building the catalog queries shared by the CLI and MCP server.
"""

from __future__ import annotations

import json
import re
import urllib.request

import duckdb

DEFAULT_STORAGE = "https://data.queria.io"
CATALOG_ALIAS = "catalog"
MAX_AUTO_ATTACH = 8

# duckdb version requirement, coupled to Queria's published DuckLake v1 format.
# The catalog is DuckLake format 1.0; only duckdb >= 1.5.4 ships a ducklake
# extension new enough to read it. Bump together with the pin in pyproject.toml
# if Queria's catalog format changes.
MIN_DUCKDB = (1, 5, 4)

_IDENT_RE = re.compile(r"^[A-Za-z0-9_]+$")
_MISSING_CATALOG_RE = re.compile(r'Catalog "?([A-Za-z0-9_]+)"? does not exist')

# Advisory guard for user-supplied SQL. The real protection is the READ_ONLY
# attach: writes to the catalogs fail at the engine level regardless. This
# regex only catches obvious accidents early with a clearer message.
_READONLY_RE = re.compile(
    r"^\s*(with|select|describe|show|pragma|explain|summarize|values|table|from)\b",
    re.IGNORECASE,
)


def version() -> str:
    """Return the installed queria package version."""
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("queria")
    except Exception:
        return "0.0.0"


def is_read_only(sql: str) -> bool:
    """Advisory check that ``sql`` looks like a read-only statement."""
    return bool(_READONLY_RE.match(sql))


def _check_duckdb_version() -> None:
    parts = []
    for chunk in duckdb.__version__.split(".")[:3]:
        m = re.match(r"\d+", chunk)
        parts.append(int(m.group()) if m else 0)
    if tuple(parts) < MIN_DUCKDB:
        want = ".".join(str(n) for n in MIN_DUCKDB)
        raise RuntimeError(
            f"duckdb >= {want} is required to read Queria's DuckLake catalogs "
            f"(found {duckdb.__version__}). Upgrade with: "
            f"pip install 'duckdb>={want}'"
        )


def _compat_hint(storage: str, exc: Exception) -> str | None:
    """Build an actionable message from the storage compatibility manifest.

    Queria publishes ``{storage}/meta.json`` describing the catalog format and
    the minimum client versions able to read it. The manifest is consulted
    only after an ATTACH failure, purely to improve the error message; its
    absence (or any fetch error) is never itself an error.
    """
    if not storage.startswith(("http://", "https://")):
        return None
    try:
        with urllib.request.urlopen(f"{storage}/meta.json", timeout=3) as res:
            meta = json.load(res)
    except Exception:
        return None
    if not isinstance(meta, dict):
        return None
    lines = [f"Failed to attach the Queria catalog at {storage}: {exc}"]
    if "ducklake_format" in meta:
        lines.append(f"The catalog uses DuckLake format {meta['ducklake_format']}.")
    if "min_duckdb" in meta:
        lines.append(
            f"It requires duckdb >= {meta['min_duckdb']} "
            f"(you have {duckdb.__version__})."
        )
    if "min_cli" in meta:
        lines.append(
            f"It requires queria >= {meta['min_cli']} (you have {version()}). "
            "Upgrade with: pip install -U queria (or clear the uvx cache)."
        )
    return "\n".join(lines)


class Connection:
    """Read-only connection to Queria's public DuckLake catalogs.

    On construction the ``catalog`` metadata dataset is attached. Other
    datasets are attached lazily: when a query references a dataset that is
    not attached yet, :meth:`sql` catches the missing-catalog error, attaches
    the dataset, and retries.

    Use as a context manager to make sure the underlying duckdb connection is
    closed::

        with queria.connect() as conn:
            conn.sql("SELECT * FROM catalog.main.mart_datasets").show()
    """

    def __init__(
        self, storage: str = DEFAULT_STORAGE, *, user_agent: str | None = None
    ) -> None:
        _check_duckdb_version()
        self.storage = storage.rstrip("/")
        config = {"custom_user_agent": user_agent or f"queria-python/{version()}"}
        self._con = duckdb.connect(config=config)
        self._con.execute("INSTALL ducklake; LOAD ducklake;")
        self._con.execute("INSTALL httpfs; LOAD httpfs;")
        # spatial: several datasets (nlftp, address_br, e_stat boundaries)
        # expose GEOMETRY columns and ST_* functions.
        self._con.execute("INSTALL spatial; LOAD spatial;")
        self._attached: set[str] = set()
        try:
            self.attach(CATALOG_ALIAS)
        except duckdb.Error as exc:
            hint = _compat_hint(self.storage, exc)
            if hint:
                raise RuntimeError(hint) from exc
            raise

    def attach(self, dataset: str) -> None:
        """Attach a dataset by name (idempotent)."""
        if dataset in self._attached:
            return
        _validate_ident(dataset)
        url = f"{self.storage}/{dataset}/ducklake.duckdb"
        data_path = f"{self.storage}/{dataset}/ducklake.duckdb.files/"
        self._con.execute(
            f"ATTACH 'ducklake:{url}' AS {dataset} "
            f"(READ_ONLY, DATA_PATH '{data_path}', OVERRIDE_DATA_PATH true)"
        )
        self._attached.add(dataset)

    def sql(self, query: str) -> duckdb.DuckDBPyRelation:
        """Run a query, auto-attaching datasets it references."""
        for _ in range(MAX_AUTO_ATTACH):
            try:
                return self._con.sql(query)
            except duckdb.Error as exc:
                self._attach_missing(exc)
        return self._con.sql(query)

    def execute(self, query: str) -> None:
        """Execute a statement (e.g. COPY), auto-attaching referenced datasets."""
        for _ in range(MAX_AUTO_ATTACH):
            try:
                self._con.execute(query)
                return
            except duckdb.Error as exc:
                self._attach_missing(exc)
        self._con.execute(query)

    def _attach_missing(self, exc: duckdb.Error) -> None:
        """Attach the dataset named in a missing-catalog error, or re-raise."""
        m = _MISSING_CATALOG_RE.search(str(exc))
        if not m or m.group(1) in self._attached:
            raise exc
        self.attach(m.group(1))

    def close(self) -> None:
        """Close the underlying duckdb connection."""
        self._con.close()

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def connect(
    storage: str = DEFAULT_STORAGE, *, user_agent: str | None = None
) -> Connection:
    """Open a read-only connection to Queria's public catalogs.

    Args:
        storage: Base URL (or local path) of the catalog storage.
        user_agent: HTTP user agent reported to the storage. Defaults to
            ``queria-python/<version>``.
    """
    return Connection(storage, user_agent=user_agent)


# ---- catalog queries shared by the CLI and the MCP server -------------------


def _validate_ident(name: str) -> None:
    if not _IDENT_RE.match(name):
        raise ValueError(f"invalid dataset/table name: {name!r}")


def _quote(value: str) -> str:
    return value.replace("'", "''")


def list_datasets_sql() -> str:
    """SQL listing all published datasets."""
    return (
        "SELECT datasource, title, description "
        f"FROM {CATALOG_ALIAS}.main.mart_datasets ORDER BY datasource"
    )


def search_datasets_sql(keyword: str) -> str:
    """SQL searching datasets by keyword over title and description."""
    kw = _quote(keyword)
    return f"""
        SELECT datasource, title, description
        FROM {CATALOG_ALIAS}.main.mart_datasets
        WHERE lower(title || ' ' || COALESCE(description, '')) LIKE lower('%{kw}%')
        ORDER BY datasource
    """


def schema_sql(dataset: str) -> str:
    """SQL listing a dataset's tables and views."""
    _validate_ident(dataset)
    return f"""
        SELECT schema_name, name AS table_name, description
        FROM {CATALOG_ALIAS}.main.mart_nodes
        WHERE datasource = '{dataset}' AND resource_type = 'model'
        ORDER BY schema_name, name
    """


def columns_sql(dataset: str, table: str | None = None) -> str:
    """SQL listing a dataset's columns, optionally filtered to one table."""
    _validate_ident(dataset)
    table_filter = ""
    if table:
        _validate_ident(table)
        table_filter = f"AND table_name = '{table}'"
    return f"""
        SELECT table_name, column_name, data_type, description
        FROM {CATALOG_ALIAS}.main.mart_columns
        WHERE datasource = '{dataset}' {table_filter}
        ORDER BY table_name, column_name
    """
