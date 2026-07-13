"""Command-line interface for exploring Queria's public open data."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections.abc import Sequence
from typing import Any

from queria import core

FORMATS = ("table", "csv", "json", "jsonl", "markdown")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _print_table(columns: Sequence[str], rows: list[tuple]) -> None:
    text_rows = [["" if v is None else str(v) for v in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in text_rows:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(v))
    print(" | ".join(c.ljust(w) for c, w in zip(columns, widths)))
    print("-+-".join("-" * w for w in widths))
    for row in text_rows:
        print(" | ".join(v.ljust(w) for v, w in zip(row, widths)))
    print(f"\n({len(text_rows)} rows)", file=sys.stderr)


def _print_markdown(columns: Sequence[str], rows: list[tuple]) -> None:
    def cell(value: Any) -> str:
        if value is None:
            return ""
        return str(value).replace("|", "\\|").replace("\n", " ")

    print("| " + " | ".join(cell(c) for c in columns) + " |")
    print("|" + "|".join(" --- " for _ in columns) + "|")
    for row in rows:
        print("| " + " | ".join(cell(v) for v in row) + " |")


def _emit(conn: core.Connection, sql: str, fmt: str, out: str | None) -> None:
    if out:
        ext = os.path.splitext(out)[1].lower()
        if ext not in (".csv", ".parquet"):
            sys.exit(f"--out expects a .csv or .parquet path (got {out!r})")
        copy_fmt = "PARQUET" if ext == ".parquet" else "CSV, HEADER"
        # Run once first so referenced datasets get attached before COPY.
        conn.sql(sql)
        conn.execute(f"COPY ({sql}) TO '{out}' (FORMAT {copy_fmt})")
        print(f"Wrote {out}", file=sys.stderr)
        return

    rel = conn.sql(sql)
    columns = rel.columns
    rows = rel.fetchall()
    if fmt == "table":
        _print_table(columns, rows)
    elif fmt == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(columns)
        writer.writerows(rows)
    elif fmt == "json":
        records = [
            {c: _jsonable(v) for c, v in zip(columns, row)} for row in rows
        ]
        json.dump(records, sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif fmt == "jsonl":
        for row in rows:
            record = {c: _jsonable(v) for c, v in zip(columns, row)}
            print(json.dumps(record, ensure_ascii=False))
    elif fmt == "markdown":
        _print_markdown(columns, rows)


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=FORMATS,
        default="table",
        help="stdout format (default: table; ignored when --out is set)",
    )
    parser.add_argument("--out", help="write the result to a .csv or .parquet file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="queria",
        description="Explore Queria public open data (data.queria.io, read-only).",
    )
    parser.add_argument(
        "--version", action="version", version=f"queria {core.version()}"
    )
    parser.add_argument(
        "--storage-url",
        dest="storage",
        default=core.DEFAULT_STORAGE,
        help=f"catalog base URL (default: {core.DEFAULT_STORAGE})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list available datasets")
    _add_output_args(p_list)

    p_search = sub.add_parser(
        "search", help="search datasets, tables and columns by keyword"
    )
    p_search.add_argument("keyword")
    p_search.add_argument(
        "--type",
        choices=core.SEARCH_ENTRY_TYPES,
        help="filter by entry type (default: all)",
    )
    p_search.add_argument(
        "--limit", type=int, default=50, help="max results (default: 50)"
    )
    _add_output_args(p_search)

    p_schema = sub.add_parser("schema", help="list a dataset's tables")
    p_schema.add_argument("dataset")
    _add_output_args(p_schema)

    p_columns = sub.add_parser("columns", help="list a dataset's columns")
    p_columns.add_argument("dataset")
    p_columns.add_argument("table", nargs="?", help="filter to one table")
    _add_output_args(p_columns)

    p_sql = sub.add_parser("sql", help="run a read-only SQL query")
    p_sql.add_argument("query")
    p_sql.add_argument(
        "--datasets",
        help="comma-separated datasets to pre-attach (usually auto-detected)",
    )
    _add_output_args(p_sql)

    sub.add_parser("mcp", help="run the stdio MCP server")

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.command == "mcp":
        from queria import mcp

        mcp.serve(args.storage)
        return

    try:
        conn = core.connect(
            args.storage, user_agent=f"queria-cli/{core.version()}"
        )
    except RuntimeError as exc:
        sys.exit(str(exc))

    try:
        if args.command == "list":
            _emit(conn, core.list_datasets_sql(), args.format, args.out)
        elif args.command == "search":
            _emit(
                conn,
                core.search_sql(
                    args.keyword, entry_type=args.type, limit=args.limit
                ),
                args.format,
                args.out,
            )
        elif args.command == "schema":
            _emit(conn, core.schema_sql(args.dataset), args.format, args.out)
        elif args.command == "columns":
            _emit(
                conn,
                core.columns_sql(args.dataset, args.table),
                args.format,
                args.out,
            )
        elif args.command == "sql":
            if not core.is_read_only(args.query):
                sys.exit(
                    "Only read-only queries are allowed "
                    "(SELECT/WITH/DESCRIBE/SHOW/PRAGMA/EXPLAIN/SUMMARIZE)."
                )
            if args.datasets:
                for ds in args.datasets.split(","):
                    if ds.strip():
                        conn.attach(ds.strip())
            _emit(conn, args.query, args.format, args.out)
    except ValueError as exc:
        sys.exit(str(exc))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
