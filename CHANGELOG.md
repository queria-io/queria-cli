# CHANGELOG

<!-- version list -->

## v0.19.1 (2026-08-02)

### Bug Fixes

- **preview**: 地図プレビューを .geo.json に、中身を FeatureCollection にする


## v0.19.0 (2026-08-02)

### Continuous Integration

- **release**: ミラーの認証を GitHub App のインストールトークンにする

- **release**: ミラーを別ジョブに分け、publish に skip-existing を付ける

- **release**: 内部リンクの除去が取りこぼす形を塞ぐ

### Features

- Add Secret, which keeps a long build's credentials alive


## v0.18.0 (2026-08-01)

### Bug Fixes

- **cli**: テーブルのセルを切り詰めずに折り返す

- **cli**: テーブル出力が非 TTY で黙って切られないようにする

### Chores

- **deps**: Bump uv from 0.11.32 to 0.12.0 in the minor-and-patch group

### Features

- **docs**: Queria docs list / show でドキュメントを端末から読めるようにする

- **push**: Publish preview rows and map geometry for published tables

### Refactoring

- **dataset**: Extract the read-only attach from schema reading


## v0.17.0 (2026-07-31)

### Features

- **cli**: メタデータのコマンドを queria.io から読む


## v0.16.0 (2026-07-31)

### Bug Fixes

- **cli**: Fail on an unknown dataset or table instead of printing nothing

- **cli**: Keep table columns aligned when values hold newlines

- **cli**: Refuse a --format that contradicts --out

- **cli**: Show a message instead of a traceback for a bad query

- **cli**: 複数文の SQL を黙って捨てず、1文だけ受け付ける

- **core**: Auto-attach a dataset referenced without its schema

- **lake**: Expire against the session's clock, not a UTC reading of it

- **release**: Give the changelog somewhere to write the next version

- **search**: データセットの検索結果が二重に出ないようにする

### Features

- **auth**: Treat an empty QUERIA_TOKEN as an explicit request for anonymous access

- **cli**: Read queria sql from a file or stdin

- **cli**: Write --out to .json and .jsonl

### Performance Improvements

- **core**: Attach the catalog on first reference, not at connect

- **core**: Load spatial when a query first calls an ST_ function

### Refactoring

- **cli**: Drop the bind-only pre-run before COPY

- **cli**: Render results to a stream, not straight to stdout


## v0.15.0 (2026-07-31)

### Bug Fixes

- **feedback**: 確認プロンプトを [Y/n] にして誤判定で送信を捨てない

### Continuous Integration

- **release**: Publish an existing tag on demand

### Features

- **feedback**: Queria feedback と submit_feedback を追加

### Testing

- **tools**: Probe the write paths that do not go through dbt

- **tools**: Stand in for the server side, and rotate a real dataset against it


## v0.14.0 (2026-07-26)

### Features

- **lake**: Hand a build the catalog as a URL as well as a path

- **lake**: Publish dbt's artifacts alongside the data


## v0.13.0 (2026-07-26)

### Features

- **lake**: Create, edit and delete the dataset itself

- **lake**: Expire snapshots and clear the files they held

- **lake**: Implement the credential process a build authenticates through

- **lake**: Publish what the build left in the dataset's storage

- **lake**: Sync — pull, build, publish

- **lake**: Tell a build whether its storage speaks TLS


## v0.12.0 (2026-07-26)

### Features

- **lake**: Run a build against the dataset's own storage

### Testing

- **lake**: Pin the two properties the two formats exist for


## v0.11.0 (2026-07-26)

### Chores

- **deps**: Bump duckdb from 1.5.4 to 1.5.5 in the patch-updates group

- **deps**: Bump uv from 0.8.24 to 0.11.32

### Continuous Integration

- Dependabot の patch/minor 更新を CI 通過後に自動マージする

- **release**: 公開リポジトリへ README・変更履歴・リリースノートをミラーする

### Documentation

- 開発が非公開リポジトリで行われることを README に書く

### Features

- **lake**: Add the working catalog, and pull onto it


## v0.10.0 (2026-07-25)

### Documentation

- README を licenses 任意化と --strict に合わせる

### Features

- **cli**: Validate/compile に --strict を追加

- **dataset**: Commercial_use による拒否をやめる

- **dataset**: Licenses を任意にする


## v0.9.1 (2026-07-25)

### Bug Fixes

- **dataset**: Spatial を読み込んでから実データを見る


## v0.9.0 (2026-07-25)

### Features

- **dataset**: CC BY 2.1 JP をライセンスレジストリに追加


## v0.8.0 (2026-07-25)

### Features

- **dataset**: 公共データ利用規約（第1.0版）をライセンスレジストリに追加


## v0.7.0 (2026-07-25)

### Documentation

- Queria dataset の使い方を README に追加

- Read-only という説明をやめる

### Features

- **cli**: Queria dataset サブコマンドを追加

- **cli**: Queria init を追加する

- **dataset**: データセット宣言の検証と dataset.json ビルドを追加

### Refactoring

- **cli**: Dataset グループをやめて validate / compile をトップレベルにする

- **dataset**: 英語に統一し spec を 0.1 にする


## v0.6.1 (2026-07-19)

### Bug Fixes

- Duckdb の必要バージョンを 1.5.2 に修正

### Refactoring

- **core**: 実在しない互換マニフェストの参照を削除


## v0.6.0 (2026-07-19)

### Documentation

- Mention queria login first in the README quickstart

- Use absolute URLs for README language switch links

### Features

- Add browser-based login and logout commands


## v0.5.1 (2026-07-19)

### Bug Fixes

- テレメトリ送信に User-Agent を設定 (Cloudflare のボット判定で 403 になるため)


## v0.5.0 (2026-07-19)

### Chores

- Sync queria version in uv.lock with released version

### Continuous Integration

- Update uv.lock during semantic-release version bump


## v0.4.0 (2026-07-19)

### Chores

- **deps**: Bump actions/checkout from 5 to 7

- **deps**: Bump python-semantic-release/python-semantic-release

### Documentation

- Describe agent-readable docs endpoints in the READMEs

- Translate README to English, keep Japanese as README.ja.md

### Features

- Link agent-readable docs from --help and MCP instructions

- テレメトリの送信先を第一者エンドポイント telemetry.queria.io に変更


## v0.3.1 (2026-07-18)

### Bug Fixes

- **mcp**: Block filesystem, SSRF and dynamic-SQL access from the query tool

### Continuous Integration

- **release**: Docs.queria.io デプロイフックのステップを削除

### Documentation

- Describe query tool sandboxing in the README


## v0.3.0 (2026-07-18)

### Continuous Integration

- Add Dependabot config for weekly dependency updates

### Documentation

- Add CLAUDE.md with release and docs-update guidance

### Features

- CLI コマンドと MCP ツール呼び出しにテレメトリを配線

- 匿名・オプトアウト可能なテレメトリ基盤を追加


## v0.2.1 (2026-07-17)

### Bug Fixes

- **cli**: Align read-only error message with accepted statements


## v0.2.0 (2026-07-17)

### Chores

- **docs**: Remove Zensical docs site (moved to queria-io/docs)

### Continuous Integration

- **release**: Publish automatically on push to main

- **release**: Trigger docs.queria.io rebuild via deploy hook

### Documentation

- Document API tokens and direct-access CREATE SECRET

- Update README usage for new commands

### Features

- Add API token support

- Add info command and get_dataset_info MCP tool

- Add summarize command

- Cross-catalog search over datasets, tables and columns

- **cli**: Add markdown output format


## v0.1.0 (2026-07-11)

- Initial Release
