from __future__ import annotations

import json

import pytest

import queria
from queria import mcp


def test_relation_payload_caps_rows(storage: str) -> None:
    with queria.connect(storage) as conn:
        rel = conn.sql("SELECT n FROM demo.main.numbers ORDER BY n")
        payload = mcp._relation_payload(rel, max_rows=2)
    assert payload["rows"] == [[1], [2]]
    assert payload["truncated"] is True
    assert payload["row_count"] == 2
    assert "hint" in payload


def test_relation_payload_no_truncation(storage: str) -> None:
    with queria.connect(storage) as conn:
        rel = conn.sql("SELECT n FROM demo.main.numbers ORDER BY n")
        payload = mcp._relation_payload(rel, max_rows=10)
    assert payload["truncated"] is False
    assert payload["row_count"] == 3
    assert "hint" not in payload


def test_relation_payload_caps_bytes(storage: str) -> None:
    with queria.connect(storage) as conn:
        rel = conn.sql(
            "SELECT repeat('x', 100000) AS blob FROM range(100)"
        )
        payload = mcp._relation_payload(rel, max_rows=100)
    assert payload["truncated"] is True
    size = len(json.dumps(payload, ensure_ascii=False))
    # Halving stops at one row, so a single oversized row may still exceed
    # the cap; with 100KB rows we must end well below 10 rows.
    assert payload["row_count"] < 10
    assert size < mcp.MAX_PAYLOAD_BYTES + 200_000


def test_relation_payload_jsonable_values(storage: str) -> None:
    with queria.connect(storage) as conn:
        rel = conn.sql("SELECT DATE '2026-01-01' AS d, 1.5::DECIMAL(4,2) AS x")
        payload = mcp._relation_payload(rel)
    json.dumps(payload)  # must not raise
    assert payload["rows"][0][0] == "2026-01-01"


def test_build_server_registers_tools(storage: str) -> None:
    server = mcp.build_server(storage)
    import anyio

    tools = anyio.run(server.list_tools)
    names = {t.name for t in tools}
    assert names == {
        "list_datasets",
        "search",
        "get_schema",
        "get_columns",
        "query",
    }


def test_search_tool_spans_entry_types(storage: str) -> None:
    server = mcp.build_server(storage)
    import anyio

    result = anyio.run(server.call_tool, "search", {"keyword": "postal"})
    payload = json.loads(result[0].text)
    assert [row[0] for row in payload["rows"]] == ["dataset", "column"]


def test_query_tool_rejects_writes(storage: str) -> None:
    server = mcp.build_server(storage)
    import anyio

    with pytest.raises(Exception, match="read-only"):
        anyio.run(server.call_tool, "query", {"sql": "DROP TABLE x"})


def test_query_tool_returns_rows(storage: str) -> None:
    server = mcp.build_server(storage)
    import anyio

    result = anyio.run(
        server.call_tool,
        "query",
        {"sql": "SELECT n FROM demo.main.numbers ORDER BY n", "max_rows": 2},
    )
    # FastMCP returns a list of content blocks; ours is one JSON text block.
    payload = json.loads(result[0].text)
    assert payload["rows"] == [[1], [2]]
    assert payload["truncated"] is True
