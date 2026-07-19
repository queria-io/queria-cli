"""Core connection and catalog helpers for Queria's public DuckLake catalogs.

Queria (https://data.queria.io) publishes Japanese open data as read-only
DuckLake catalogs. This module owns the connection lifecycle: attaching the
``catalog`` metadata dataset, auto-attaching other datasets referenced in
queries, and building the catalog queries shared by the CLI and MCP server.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.request

import duckdb

from queria import auth

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

# Keep the statement list in sync with _READONLY_RE above.
READONLY_ERROR = (
    "Only read-only queries are allowed (SELECT/WITH/DESCRIBE/SHOW/"
    "PRAGMA/EXPLAIN/SUMMARIZE/VALUES/TABLE/FROM)."
)

# Functions that reach outside the attached catalogs. A "read-only" SELECT is
# still dangerous if it can read the local filesystem
# (read_text('/home/user/.ssh/id_rsa')), reach internal network endpoints
# (read_csv('http://169.254.169.254/latest/meta-data/...')), or run SQL smuggled
# in a string literal (query('SELECT read_text(...)'), which the AST cannot see
# inside the constant). Queria's catalogs are reached through ducklake/httpfs and
# never need any of these, so the MCP query tool rejects them. The ST_* / GDAL
# readers are here too: the spatial extension is loaded for GEOMETRY support and
# its readers hit the filesystem as well.
_UNSAFE_FUNCTIONS = frozenset(
    {
        # local file / URL readers
        "read_text",
        "read_blob",
        "read_csv",
        "read_csv_auto",
        "read_json",
        "read_json_auto",
        "read_json_objects",
        "read_json_objects_auto",
        "read_ndjson",
        "read_ndjson_auto",
        "read_ndjson_objects",
        "read_parquet",
        "parquet_scan",
        "parquet_metadata",
        "parquet_schema",
        "parquet_file_metadata",
        "parquet_full_metadata",
        "parquet_kv_metadata",
        "parquet_bloom_probe",
        "sniff_csv",
        "read_duckdb",
        "ducklake_scan",
        "glob",
        # spatial (GDAL) readers
        "st_read",
        "st_readosm",
        "st_readshp",
        "st_read_meta",
        "shapefile_meta",
        # dynamic SQL: would smuggle any of the above past the AST scan
        "query",
        "query_table",
        "json_execute_serialized_sql",
    }
)

_UNSAFE_FUNC_RE = re.compile(
    r"\b(" + "|".join(sorted(_UNSAFE_FUNCTIONS)) + r")\s*\(",
    re.IGNORECASE,
)

UNSAFE_QUERY_ERROR = (
    "This query calls {name}(), which can read local files, fetch arbitrary "
    "URLs, or run dynamic SQL. The query tool only reads Queria's published "
    "catalogs; filesystem, network and dynamic-SQL access is not allowed."
)

_parser_lock = threading.Lock()
_parser: duckdb.DuckDBPyConnection | None = None


def _referenced_functions(sql: str) -> set[str] | None:
    """Return the function names referenced anywhere in ``sql``.

    Uses DuckDB's own parser (``json_serialize_sql``) and walks the AST, so a
    call is found regardless of nesting (CTE, subquery, function argument).
    Returns ``None`` when the statement cannot be parsed/serialized (e.g. a
    non-SELECT), leaving the caller to fall back to a lexical scan.
    """
    global _parser
    try:
        with _parser_lock:
            if _parser is None:
                _parser = duckdb.connect()
            row = _parser.execute(
                "SELECT json_serialize_sql(?)", [sql]
            ).fetchone()
        ast = json.loads(row[0])
    except Exception:
        return None
    if not isinstance(ast, dict) or ast.get("error"):
        return None
    found: set[str] = set()
    stack: list[object] = [ast]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            name = node.get("function_name")
            if isinstance(name, str):
                found.add(name.lower())
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def unsafe_function(sql: str) -> str | None:
    """Return a filesystem/URL/dynamic-SQL function ``sql`` uses, or ``None``.

    Prefers DuckDB's parser; if the statement cannot be serialized, falls back
    to a lexical scan so the check never fails open.
    """
    names = _referenced_functions(sql)
    if names is not None:
        hits = names & _UNSAFE_FUNCTIONS
        return sorted(hits)[0] if hits else None
    m = _UNSAFE_FUNC_RE.search(sql)
    return m.group(1).lower() if m else None


class RateLimitError(RuntimeError):
    """Raised when the storage responds with HTTP 429 (rate limited)."""


RATE_LIMIT_MESSAGE = (
    "Rate limit reached. Run `queria login` to get an API token and raise "
    "the limit (or create one at https://queria.io/profile/api-keys and run "
    "`queria auth set-token <token>`). Expired tokens are renewed by "
    "`queria login` as well."
)

_HTTP_429_RE = re.compile(r"\b429\b")


def _raise_if_rate_limited(exc: duckdb.Error) -> None:
    """Convert an HTTP 429 from the storage into a RateLimitError."""
    if getattr(exc, "status_code", None) == 429 or (
        isinstance(exc, duckdb.IOException) and _HTTP_429_RE.search(str(exc))
    ):
        raise RateLimitError(RATE_LIMIT_MESSAGE) from exc


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
        self,
        storage: str = DEFAULT_STORAGE,
        *,
        user_agent: str | None = None,
        token: str | None = None,
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
        if token is not None:
            # Send the token as an Authorization header on every request to
            # the storage (catalog files and parquet alike). CREATE SECRET is
            # DDL and cannot be parameterized, hence the strict validation.
            auth.validate_token(token)
            self._con.execute(
                "CREATE SECRET queria_auth (TYPE http, "
                f"BEARER_TOKEN '{token}', SCOPE '{_quote(self.storage)}')"
            )
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
        try:
            self._con.execute(
                f"ATTACH 'ducklake:{url}' AS {dataset} "
                f"(READ_ONLY, DATA_PATH '{data_path}', OVERRIDE_DATA_PATH true)"
            )
        except duckdb.Error as exc:
            _raise_if_rate_limited(exc)
            raise
        self._attached.add(dataset)

    def sql(self, query: str) -> duckdb.DuckDBPyRelation:
        """Run a query, auto-attaching datasets it references."""
        try:
            for _ in range(MAX_AUTO_ATTACH):
                try:
                    return self._con.sql(query)
                except duckdb.Error as exc:
                    self._attach_missing(exc)
            return self._con.sql(query)
        except duckdb.Error as exc:
            _raise_if_rate_limited(exc)
            raise

    def execute(self, query: str) -> None:
        """Execute a statement (e.g. COPY), auto-attaching referenced datasets."""
        try:
            for _ in range(MAX_AUTO_ATTACH):
                try:
                    self._con.execute(query)
                    return
                except duckdb.Error as exc:
                    self._attach_missing(exc)
            self._con.execute(query)
        except duckdb.Error as exc:
            _raise_if_rate_limited(exc)
            raise

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
    storage: str = DEFAULT_STORAGE,
    *,
    user_agent: str | None = None,
    token: str | None = None,
) -> Connection:
    """Open a read-only connection to Queria's public catalogs.

    Args:
        storage: Base URL (or local path) of the catalog storage.
        user_agent: HTTP user agent reported to the storage. Defaults to
            ``queria-python/<version>``.
        token: API token sent as a Bearer Authorization header to the
            storage. Raises the rate limit on data.queria.io.
    """
    return Connection(storage, user_agent=user_agent, token=token)


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


SEARCH_ENTRY_TYPES = ("dataset", "table", "column")


def search_sql(
    keyword: str, *, entry_type: str | None = None, limit: int = 50
) -> str:
    """SQL searching datasets, tables and columns by keyword.

    Dataset hits match on title and description; table and column hits match
    on the catalog's precomputed search text (name, title, description, tags).
    """
    if entry_type is not None and entry_type not in SEARCH_ENTRY_TYPES:
        raise ValueError(
            f"entry_type must be one of {', '.join(SEARCH_ENTRY_TYPES)} "
            f"(got {entry_type!r})"
        )
    if limit < 1:
        raise ValueError(f"limit must be a positive integer (got {limit!r})")
    kw = _quote(keyword)
    type_filter = f"WHERE entry_type = '{entry_type}'" if entry_type else ""
    return f"""
        WITH hits AS (
            SELECT
                'dataset' AS entry_type,
                datasource,
                NULL::VARCHAR AS schema_name,
                NULL::VARCHAR AS table_name,
                NULL::VARCHAR AS column_name,
                description
            FROM {CATALOG_ALIAS}.main.mart_datasets
            WHERE lower(title || ' ' || COALESCE(description, ''))
                LIKE lower('%{kw}%')
            UNION ALL
            SELECT
                entry_type, datasource, schema_name, table_name, column_name,
                description
            FROM {CATALOG_ALIAS}.main.mart_search_entries
            WHERE lower(search_text) LIKE lower('%{kw}%')
        )
        SELECT * FROM hits
        {type_filter}
        ORDER BY
            CASE entry_type
                WHEN 'dataset' THEN 0 WHEN 'table' THEN 1 ELSE 2
            END,
            datasource, schema_name, table_name, column_name
        LIMIT {int(limit)}
    """


# Metadata fields exposed by info_sql, in display order. ``readme`` is opt-in
# because it can be long.
_INFO_FIELDS = (
    "datasource",
    "title",
    "description",
    "license",
    "license_url",
    "source_url",
    "repository_url",
    "schedule",
    "tags_json",
    "schemas_json",
    "dbt_generated_at",
)


def info_sql(dataset: str, *, include_readme: bool = False) -> str:
    """SQL returning one dataset's metadata as (field, value) rows.

    Values are cast to VARCHAR so UNPIVOT can stack heterogeneous columns;
    fields whose value is NULL are omitted from the result.
    """
    _validate_ident(dataset)
    fields = _INFO_FIELDS + (("readme",) if include_readme else ())
    casts = ", ".join(f"CAST({f} AS VARCHAR) AS {f}" for f in fields)
    return f"""
        UNPIVOT (
            SELECT {casts}
            FROM {CATALOG_ALIAS}.main.mart_datasets
            WHERE datasource = '{dataset}'
        )
        ON {", ".join(fields)}
        INTO NAME field VALUE value
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


def summarize_sql(table: str) -> str:
    """SQL summarizing a table (row count, min/max, null ratio per column).

    Accepts ``dataset.schema.table`` or ``dataset.table`` (the schema
    defaults to ``main``). Note that SUMMARIZE scans the whole table, which
    can be slow over HTTP for large tables.
    """
    parts = table.split(".")
    if len(parts) == 2:
        parts = [parts[0], "main", parts[1]]
    if len(parts) != 3:
        raise ValueError(
            f"expected <dataset>.<schema>.<table> or <dataset>.<table> "
            f"(got {table!r})"
        )
    for part in parts:
        _validate_ident(part)
    return f"SUMMARIZE {'.'.join(parts)}"


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
