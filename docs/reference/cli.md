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

データセット・テーブル・カラムを横断するキーワード検索です（大文字小文字を区別しない部分一致）。データセットはタイトルと説明、テーブルとカラムは名前・タイトル・説明・タグに対してマッチします。

```bash
queria search <keyword> [--type {dataset,table,column}] [--limit N] [--format FMT] [--out PATH]
```

| オプション | 説明 |
|---|---|
| `--type` | エントリ種別で絞り込み（デフォルト: すべて） |
| `--limit` | 最大件数（デフォルト: 50） |

## queria info

データセットのメタデータ（ライセンス・出典 URL・リポジトリ・スキーマ一覧・更新日時など）を `field` / `value` の 2 列で表示します。値が NULL のフィールドは省略されます。

```bash
queria info <dataset> [--readme] [--format FMT] [--out PATH]
```

| オプション | 説明 |
|---|---|
| `--readme` | データセットの README 本文も含める |

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

## queria summarize

テーブルのカラム統計（件数・min/max・NULL 率・近似ユニーク数など、DuckDB の `SUMMARIZE`）を表示します。テーブル全体をスキャンするため、大きなテーブルでは時間と通信量がかかります。

```bash
queria summarize <dataset>.<schema>.<table> [--format FMT] [--out PATH]
```

スキーマを省略した `<dataset>.<table>` は `main` スキーマとして解釈されます。

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
