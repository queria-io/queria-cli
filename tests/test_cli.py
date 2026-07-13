from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from queria import cli


def run_cli(*argv: str) -> None:
    cli.main(list(argv))


def test_list_json(storage: str, capsys: pytest.CaptureFixture) -> None:
    run_cli("--storage-url", storage, "list", "--format", "json")
    records = json.loads(capsys.readouterr().out)
    assert [r["datasource"] for r in records] == ["demo", "zipcode"]


def test_search(storage: str, capsys: pytest.CaptureFixture) -> None:
    run_cli("--storage-url", storage, "search", "postal", "--format", "json")
    records = json.loads(capsys.readouterr().out)
    assert [(r["entry_type"], r["datasource"]) for r in records] == [
        ("dataset", "zipcode"),
        ("column", "zipcode"),
    ]


def test_search_type_and_limit(storage: str, capsys: pytest.CaptureFixture) -> None:
    run_cli(
        "--storage-url", storage,
        "search", "numbers", "--type", "column", "--limit", "1",
        "--format", "json",
    )
    records = json.loads(capsys.readouterr().out)
    assert [r["column_name"] for r in records] == ["label"]


def test_schema_table_format(storage: str, capsys: pytest.CaptureFixture) -> None:
    run_cli("--storage-url", storage, "schema", "demo")
    out = capsys.readouterr().out
    assert "numbers" in out and "stg_numbers" in out


def test_columns_filtered(storage: str, capsys: pytest.CaptureFixture) -> None:
    run_cli(
        "--storage-url", storage, "columns", "demo", "numbers", "--format", "jsonl"
    )
    lines = capsys.readouterr().out.strip().splitlines()
    records = [json.loads(line) for line in lines]
    assert {r["column_name"] for r in records} == {"n", "label"}


def test_list_markdown(storage: str, capsys: pytest.CaptureFixture) -> None:
    run_cli("--storage-url", storage, "list", "--format", "markdown")
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0] == "| datasource | title | description |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| demo | Demo dataset | Numbers for testing |"


def test_markdown_escapes_pipes_and_newlines(
    storage: str, capsys: pytest.CaptureFixture
) -> None:
    run_cli(
        "--storage-url", storage,
        "sql", "SELECT 'a|b' AS x, 'c\nd' AS y",
        "--format", "markdown",
    )
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[2] == "| a\\|b | c d |"


def test_sql_auto_attach_csv(storage: str, capsys: pytest.CaptureFixture) -> None:
    run_cli(
        "--storage-url", storage,
        "sql", "SELECT n, label FROM demo.main.numbers ORDER BY n",
        "--format", "csv",
    )
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0] == "n,label"
    assert lines[1] == "1,one"


def test_sql_rejects_writes(storage: str) -> None:
    with pytest.raises(SystemExit, match="read-only"):
        run_cli("--storage-url", storage, "sql", "DROP TABLE demo.main.numbers")


def test_sql_out_parquet(
    storage: str, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    out = tmp_path / "result.parquet"
    run_cli(
        "--storage-url", storage,
        "sql", "SELECT * FROM demo.main.numbers",
        "--out", str(out),
    )
    assert out.exists()
    count = duckdb.sql(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    assert count == 3


def test_out_rejects_unknown_extension(storage: str, tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match=r"\.csv or \.parquet"):
        run_cli(
            "--storage-url", storage,
            "sql", "SELECT 1",
            "--out", str(tmp_path / "result.xlsx"),
        )


def test_version(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit):
        run_cli("--version")
    assert capsys.readouterr().out.startswith("queria ")
