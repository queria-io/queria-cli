---
title: インストール
---

# インストール

queria は PyPI で配布される Python パッケージです。Python 3.10+ が必要です。

## uvx（推奨）

[uv](https://docs.astral.sh/uv/) があればインストール不要で実行できます:

```bash
uvx queria list
```

MCP サーバーを使う場合は `mcp` extra を付けます:

```bash
uvx --from 'queria[mcp]' queria mcp
```

## pip / pipx

```bash
pip install queria
# MCP サーバーも使う場合
pip install 'queria[mcp]'
```

```bash
pipx install queria
```

## 依存関係

依存は `duckdb>=1.5.4` のみです。このピンは Queria が公開する DuckLake format 1.0 を読むために必要なバージョンで、詳細は[互換性ポリシー](../guide/compatibility.md)を参照してください。
