"""Stdio MCP server exposing Queria's public open data to agents.

Run with ``queria mcp`` (requires the ``mcp`` extra: ``pip install
'queria[mcp]'`` or ``uvx --from 'queria[mcp]' queria mcp``).

The ``query`` tool enforces a row and payload-size cap so a single tool call
cannot flood an agent's context. Bulk extraction should go through the CLI's
``--out`` option instead.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from queria import auth, core

DEFAULT_MAX_ROWS = 100
MAX_ROWS_LIMIT = 1000
MAX_PAYLOAD_BYTES = 1_000_000

_BULK_HINT = (
    "Result truncated. Narrow the query (LIMIT / WHERE / aggregate), or use "
    "the CLI for bulk export: queria sql '<query>' --out result.parquet"
)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _relation_payload(
    rel: Any, max_rows: int | None = None
) -> dict[str, Any]:
    """Convert a duckdb relation into a JSON-safe payload with caps applied.

    Rows are capped at ``max_rows`` first, then dropped from the tail until
    the serialized payload fits within ``MAX_PAYLOAD_BYTES``.
    """
    columns = rel.columns
    if max_rows is None:
        raw = rel.fetchall()
        truncated = False
    else:
        raw = rel.fetchmany(max_rows + 1)
        truncated = len(raw) > max_rows
        raw = raw[:max_rows]
    rows = [[_jsonable(v) for v in row] for row in raw]

    payload = {"columns": columns, "rows": rows, "truncated": truncated}
    while (
        len(json.dumps(payload, ensure_ascii=False)) > MAX_PAYLOAD_BYTES
        and payload["rows"]
    ):
        payload["rows"] = payload["rows"][: max(1, len(payload["rows"]) // 2)]
        payload["truncated"] = True
        if len(payload["rows"]) == 1:
            break
    payload["row_count"] = len(payload["rows"])
    if payload["truncated"]:
        payload["hint"] = _BULK_HINT
    return payload


def build_server(
    storage: str = core.DEFAULT_STORAGE, token: str | None = None
) -> Any:
    """Build the FastMCP server with all Queria tools registered.

    ``token`` defaults to the usual resolution (QUERIA_TOKEN, then the
    config file).
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        sys.exit(
            "The MCP server requires the 'mcp' extra:\n"
            "  pip install 'queria[mcp]'\n"
            "  # or: uvx --from 'queria[mcp]' queria mcp"
        )

    server = FastMCP(
        "queria",
        instructions=(
            "Read-only access to Queria (data.queria.io), a catalog of "
            "Japanese open data published as DuckLake. Start with "
            "list_datasets or search, inspect tables with "
            "get_schema / get_columns, then run DuckDB SQL with query. "
            "Reference tables as <dataset>.<schema>.<table>."
        ),
    )
    if token is None:
        token, _ = auth.resolve_token()
    conn = core.connect(
        storage, user_agent=f"queria-mcp/{core.version()}", token=token
    )

    @server.tool()
    def list_datasets() -> dict:
        """List all datasets published on Queria."""
        return _relation_payload(conn.sql(core.list_datasets_sql()))

    @server.tool()
    def search(
        keyword: str, entry_type: str | None = None, limit: int = 50
    ) -> dict:
        """Search datasets, tables and columns by keyword.

        entry_type filters to 'dataset', 'table' or 'column' (default: all).
        """
        return _relation_payload(
            conn.sql(
                core.search_sql(keyword, entry_type=entry_type, limit=limit)
            )
        )

    @server.tool()
    def get_dataset_info(dataset: str, include_readme: bool = False) -> dict:
        """Show a dataset's metadata (license, source, schemas) as field/value rows."""
        return _relation_payload(
            conn.sql(core.info_sql(dataset, include_readme=include_readme))
        )

    @server.tool()
    def get_schema(dataset: str) -> dict:
        """List a dataset's tables and views with descriptions."""
        return _relation_payload(conn.sql(core.schema_sql(dataset)))

    @server.tool()
    def get_columns(dataset: str, table: str | None = None) -> dict:
        """List a dataset's columns (optionally for a single table)."""
        return _relation_payload(conn.sql(core.columns_sql(dataset, table)))

    @server.tool()
    def query(sql: str, max_rows: int = DEFAULT_MAX_ROWS) -> dict:
        """Run a read-only DuckDB SQL query against Queria datasets.

        Reference tables as <dataset>.<schema>.<table>; datasets attach
        automatically. Results are capped at max_rows (up to 1000) and ~1MB;
        use the queria CLI with --out for bulk extraction.
        """
        if not core.is_read_only(sql):
            raise ValueError(core.READONLY_ERROR)
        capped = max(1, min(max_rows, MAX_ROWS_LIMIT))
        return _relation_payload(conn.sql(sql), max_rows=capped)

    return server


def serve(storage: str = core.DEFAULT_STORAGE, token: str | None = None) -> None:
    """Run the stdio MCP server (blocks until the client disconnects)."""
    build_server(storage, token=token).run()
