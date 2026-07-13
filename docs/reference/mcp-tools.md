---
title: MCP ツールリファレンス
---

# MCP ツールリファレンス

`queria mcp` が公開するツールの仕様です。すべてのツールは共通の形式で結果を返します:

```json
{
  "columns": ["datasource", "title"],
  "rows": [["zipcode", "Zipcode"]],
  "truncated": false,
  "row_count": 1
}
```

`truncated: true` の場合は `hint` フィールドに対処方法（クエリを絞る / CLI の `--out` を使う）が含まれます。

## list_datasets

公開されている全データセットを返します。引数はありません。

## search

| 引数 | 型 | 説明 |
|---|---|---|
| `keyword` | string | 部分一致キーワード |
| `entry_type` | string (省略可) | `dataset` / `table` / `column` で絞り込み |
| `limit` | int (デフォルト 50) | 最大件数 |

データセット・テーブル・カラムを横断して検索します。データセットはタイトルと説明、テーブルとカラムは名前・タイトル・説明・タグに対してマッチします。

## get_dataset_info

| 引数 | 型 | 説明 |
|---|---|---|
| `dataset` | string | データセット名 |
| `include_readme` | bool (デフォルト false) | README 本文も含める |

データセットのメタデータ（ライセンス・出典 URL・スキーマ一覧など）を `field` / `value` の行で返します。値が NULL のフィールドは省略されます。

## get_schema

| 引数 | 型 | 説明 |
|---|---|---|
| `dataset` | string | データセット名 |

データセットのテーブル・ビュー一覧（スキーマ名・テーブル名・説明）を返します。

## get_columns

| 引数 | 型 | 説明 |
|---|---|---|
| `dataset` | string | データセット名 |
| `table` | string (省略可) | テーブル名で絞り込み |

## query

| 引数 | 型 | 説明 |
|---|---|---|
| `sql` | string | read-only の DuckDB SQL |
| `max_rows` | int (デフォルト 100、最大 1000) | 返す行数の上限 |

テーブルは `<dataset>.<schema>.<table>` で参照します。データセットは自動 ATTACH されます。

結果は `max_rows` とペイロードサイズ約 1MB で打ち切られます。バルク抽出には CLI を使ってください:

```bash
queria sql "<query>" --out result.parquet
```
