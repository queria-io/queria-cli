---
title: CLI リファレンス
---

# CLI リファレンス

## 共通オプション

| オプション | 説明 |
|---|---|
| `--storage-url URL` | カタログのベース URL（デフォルト: `https://data.queria.io`） |
| `--version` | バージョンを表示 |

## 出力オプション（list / search / schema / columns / sql 共通）

| オプション | 説明 |
|---|---|
| `--format {table,csv,json,jsonl,markdown}` | stdout の形式（デフォルト: `table`） |
| `--out PATH` | 結果を `.csv` / `.parquet` ファイルに書き出す（`--format` は無視される） |

## queria list

公開されている全データセットを一覧します。

```bash
queria list [--format FMT] [--out PATH]
```

## queria search

タイトルと説明に対するキーワード検索です（大文字小文字を区別しない部分一致）。

```bash
queria search <keyword> [--format FMT] [--out PATH]
```

## queria schema

データセットのテーブル・ビュー一覧を表示します。

```bash
queria schema <dataset> [--format FMT] [--out PATH]
```

## queria columns

データセットのカラム一覧を表示します。テーブル名を指定すると絞り込めます。

```bash
queria columns <dataset> [table] [--format FMT] [--out PATH]
```

## queria sql

read-only SQL を実行します。`<dataset>.<schema>.<table>` で参照されたデータセットは自動 ATTACH されます。

```bash
queria sql "<query>" [--datasets DS1,DS2] [--format FMT] [--out PATH]
```

| オプション | 説明 |
|---|---|
| `--datasets` | 事前に ATTACH するデータセット（通常は自動検出されるため不要） |

SELECT / WITH / DESCRIBE / SHOW / PRAGMA / EXPLAIN / SUMMARIZE で始まる文のみ受け付けます。

## queria mcp

stdio MCP サーバーを起動します。`mcp` extra が必要です（[MCP サーバー](../guide/mcp.md)参照）。

```bash
queria [--storage-url URL] mcp
```
