---
title: CLI ガイド
---

# CLI ガイド

## コマンド体系

| コマンド | 役割 |
|---|---|
| `queria list` | データセット一覧 |
| `queria search <keyword>` | データセット・テーブル・カラムの横断キーワード検索 |
| `queria info <dataset>` | データセットのメタデータ（ライセンス・出典など） |
| `queria schema <dataset>` | データセットのテーブル一覧 |
| `queria columns <dataset> [table]` | カラム一覧（table 指定で絞り込み） |
| `queria summarize <table>` | テーブルのカラム統計（全件スキャン） |
| `queria sql "<query>"` | read-only SQL の実行 |
| `queria auth set-token / status / clear` | API トークンの管理 |
| `queria mcp` | stdio MCP サーバーの起動 |

## 出力形式

`--format` で stdout の形式を選べます:

- `table`（デフォルト）— 人間向けの整形テーブル
- `csv` — ヘッダー付き CSV
- `json` — レコードの JSON 配列
- `jsonl` — 1行1レコードの JSON（ストリーム処理向け）
- `markdown` — Markdown テーブル（ドキュメントや記事への貼り付け向け）

```bash
queria list --format json | jq '.[].datasource'
```

## ファイル出力

`--out` で結果をファイルに書き出します。拡張子で形式が決まります（`.parquet` / `.csv`）。大きな結果は stdout ではなく `--out` を使ってください。

```bash
queria sql "SELECT * FROM e_stat.main.mart_population_prefecture" --out pop.parquet
```

## データセットの自動 ATTACH

`sql` の中で `<dataset>.<schema>.<table>` を参照すると、未接続のデータセットは自動的に ATTACH されます。`information_schema` を引く場合など自動検出が効かないケースでは `--datasets` で明示できます:

```bash
queria sql "SELECT * FROM information_schema.tables WHERE table_catalog = 'jma'" --datasets jma
```

## API トークン（レートリミット緩和）

data.queria.io はトークンなしでも使えますが、レートリミットがあります。上限に達すると「Rate limit reached」というエラーになります。[https://queria.io/profile/api-keys](https://queria.io/profile/api-keys) でトークンを発行して登録すると上限が上がります:

```bash
queria auth set-token <token>   # ~/.config/queria/config.toml に保存（パーミッション 600）
queria auth status              # トークンの有無と取得元を確認
queria auth clear               # 保存したトークンを削除
```

トークンは次の優先順で解決されます:

1. `--token` オプション
2. 環境変数 `QUERIA_TOKEN`
3. 設定ファイル `~/.config/queria/config.toml`（`XDG_CONFIG_HOME` を尊重）の `token` キー

登録したトークンは data.queria.io へのリクエストに Authorization ヘッダとして自動的に付与されます。

## read-only ガードについて

`sql` は SELECT / WITH / DESCRIBE / SHOW / PRAGMA / EXPLAIN / SUMMARIZE で始まる文のみ受け付けます。これは事故防止のための簡易ガードであり、本質的な保護はカタログの READ_ONLY ATTACH です。公開カタログへの書き込みはエンジンレベルで失敗します。queria はサンドボックスではありません — 実行環境のローカルリソースへのアクセスは DuckDB の通常の権限に従います。
