---
title: 直接アクセス
---

# 直接アクセス（素の DuckDB で読む）

queria は利便性レイヤーであり、Queria のデータは標準の DuckLake 形式で公開されているため、duckdb >= 1.5.4 があればどの言語・環境からでも直接読めます。

## ATTACH の書き方

各データセットは `https://data.queria.io/<dataset>/` 配下に公開されています:

```sql
INSTALL ducklake; LOAD ducklake;
INSTALL httpfs; LOAD httpfs;

ATTACH 'ducklake:https://data.queria.io/zipcode/ducklake.duckdb' AS zipcode (
    READ_ONLY,
    DATA_PATH 'https://data.queria.io/zipcode/ducklake.duckdb.files/',
    OVERRIDE_DATA_PATH true
);

SELECT * FROM zipcode.main.zipcodes LIMIT 10;
```

メタデータカタログ（データセット・テーブル・カラムの一覧）は `catalog` データセットにあります:

```sql
ATTACH 'ducklake:https://data.queria.io/catalog/ducklake.duckdb' AS catalog (
    READ_ONLY,
    DATA_PATH 'https://data.queria.io/catalog/ducklake.duckdb.files/',
    OVERRIDE_DATA_PATH true
);

SELECT datasource, title FROM catalog.main.mart_datasets;
```

## 注意点

- DuckDB CLI（対話シェル）の同梱 ducklake 拡張はバージョンによって古い場合があります。`uvx duckdb` などで 1.5.4 以上を使ってください。
- GEOMETRY カラムを含むデータセット（nlftp、e_stat の境界データなど）には `INSTALL spatial; LOAD spatial;` が必要です。
- Python では `queria.connect()` がこの一連の処理（拡張ロード・ATTACH・自動 ATTACH）を代行します。[Python API リファレンス](../reference/python-api.md)を参照してください。
