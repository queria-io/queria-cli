---
title: クイックスタート
---

# クイックスタート

探索 → クエリ → 出力までの基本フローです。以下は `uvx queria` でも `queria`（インストール済み）でも同じです。

## 1. データセットを探す

```bash
queria list
queria search 人口
```

## 2. テーブルとカラムを調べる

```bash
queria schema e_stat
queria columns e_stat mart_population_prefecture
```

## 3. SQL を実行する

テーブルは `<dataset>.<schema>.<table>` で参照します。参照したデータセットは自動的に ATTACH されるので、事前準備は不要です。

```bash
queria sql "
  SELECT date, holiday_name
  FROM calendar.main.mart_calendar
  WHERE is_holiday AND date BETWEEN DATE '2026-01-01' AND DATE '2026-12-31'
  ORDER BY date
"
```

DuckDB の SQL がそのまま使えます。データセットをまたぐ JOIN も可能です。

## 4. 結果をファイルに出力する

```bash
queria sql "SELECT * FROM zipcode.main.zipcodes" --out zipcodes.parquet
queria sql "SELECT * FROM zipcode.main.zipcodes" --out zipcodes.csv
```

stdout の形式は `--format table|csv|json|jsonl` で切り替えられます（デフォルトは `table`）。

## 次のステップ

- [CLI ガイド](../guide/cli.md) — オプションの詳細
- [MCP サーバー](../guide/mcp.md) — エージェントからの利用
- [Python API](../reference/python-api.md) — ノートブックやスクリプトからの利用
