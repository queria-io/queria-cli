---
title: Home
---

# Queria Docs

[Queria](https://data.queria.io) は、日本のオープンデータ（e-Stat、国土数値情報、EDINET、気象庁ほか）を DuckLake 形式で公開するデータカタログです。データはすべて read-only で公開されており、クエリの計算は手元の DuckDB（ブラウザでは DuckDB WASM）で行われます。

このサイトは Queria をターミナル・Python・MCP から使うためのドキュメントです。データセット個別のスキーマやガイドは[カタログ UI](https://data.queria.io) を参照してください。

## はじめる

インストール不要で、まず1クエリ:

```bash
uvx queria list
uvx queria sql "SELECT * FROM zipcode.main.zipcodes LIMIT 10"
```

## 学ぶ

- [クイックスタート](getting-started/quickstart.md) — 探索から Parquet 出力まで5分で
- [CLI ガイド](guide/cli.md) — コマンド体系と使い分け
- [MCP サーバー](guide/mcp.md) — Claude Code / Cursor などからの利用
- [直接アクセス](guide/direct-access.md) — 素の DuckDB で ATTACH する方法
- [互換性ポリシー](guide/compatibility.md) — スキーマとバージョンの安定性について

## リファレンス

- [CLI リファレンス](reference/cli.md)
- [Python API リファレンス](reference/python-api.md)
- [MCP ツールリファレンス](reference/mcp-tools.md)
