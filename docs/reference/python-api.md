---
title: Python API リファレンス
---

# Python API リファレンス

queria は CLI と同じ操作を Python パッケージとしても公開しています。ノートブックやスクリプトから、サブプロセスなしで Queria のデータを読めます。

## 概要

```python
import queria

with queria.connect() as conn:
    # データセット一覧（メタデータカタログ）
    conn.sql("SELECT datasource, title FROM catalog.main.mart_datasets").show()

    # 参照したデータセットは自動 ATTACH される
    df = conn.sql("""
        SELECT date, holiday_name
        FROM calendar.main.mart_calendar
        WHERE is_holiday AND date >= DATE '2026-01-01'
    """).df()
```

`Connection.sql()` は DuckDB の `DuckDBPyRelation` を返すので、`.df()`（pandas）、`.pl()`（Polars)、`.arrow()`、`.fetchall()` など DuckDB の標準 API がそのまま使えます。

## 安定性

`queria.connect()` と `Connection` の公開メソッド（`sql` / `execute` / `attach` / `close`）は公式 API です。それ以外のモジュール内部は予告なく変わることがあります。

## API

::: queria

::: queria.core.Connection
