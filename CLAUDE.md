# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Queria の公開オープンデータ (data.queria.io) にアクセスする CLI / Python パッケージ / MCP サーバー。PyPI に `queria` として公開している。

## コマンド

```bash
uv sync            # 依存インストール
uv run pytest      # テスト（network マーカーは既定で除外）
uv run queria --help
```

本番カタログに対するテストは `-m network` で明示的に実行する。

## リリース

- リリースは `.github/workflows/release.yml`（python-semantic-release）が行う。`pyproject.toml` の version を手で書き換えない
- conventional commits がバージョン判定に直結する（feat → minor、fix → patch。docs / chore / ci はリリースなし）

## ドキュメント更新（必須）

ユーザー向けドキュメントは queria-io/docs (docs.queria.io) にある。この README はクイックスタートのみ。

- CLI のコマンド・オプション、Python API（`queria.connect()` / `Connection`）、MCP ツール、認証・レートリミットの挙動を変えたら、同じ作業の中で queria-io/docs の該当ページも更新して PR を作る
- 主な対応先: `docs/reference/cli.mdx`、`docs/reference/python-api.mdx`、`docs/reference/mcp-tools.mdx`、`docs/cli/`、`docs/(ai)/`、`docs/connection/authentication.mdx`
- ドキュメント更新が不要な変更（内部リファクタ・CI など）の場合は、PR 説明に「docs 更新不要」とひとこと書く
- `/changelog` は GitHub Releases から自動生成されるため対応不要
