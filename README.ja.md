# queria

[English](https://github.com/queria-io/queria-cli/blob/main/README.md) | 日本語

Query Japanese open data on [Queria](https://data.queria.io) from the terminal, Python, and MCP.

[Queria](https://data.queria.io) が公開する日本のオープンデータ（e-Stat、国土数値情報、EDINET、気象庁ほか）のクライアントです。ターミナル・Python・MCP から探索でき、自分のデータセットをカタログ向けに宣言することもできます。データは DuckLake 形式で公開されており、計算はすべて手元の DuckDB で行われます。

## インストール

```bash
uvx queria list          # インストール不要で実行
pip install queria       # または通常インストール
```

Python 3.10+ が必要です。

## 使い方

```bash
queria list                              # データセット一覧
queria search 人口                        # データセット・テーブル・カラムの横断検索
queria info e_stat                       # メタデータ（ライセンス・出典など）
queria schema e_stat                     # テーブル一覧
queria columns e_stat mart_population    # カラム一覧
queria summarize zipcode.main.zipcodes   # カラム統計（全件スキャン）
queria sql "SELECT * FROM zipcode.main.zipcodes LIMIT 10"
queria sql "SELECT * FROM zipcode.main.zipcodes" --out zipcodes.parquet
```

テーブルは `<dataset>.<schema>.<table>` で参照します。参照したデータセットは自動的に ATTACH されます。

## データセットを公開する

`queria validate` と `queria compile` は、データセットに付けたメタデータを検証し、Queria がカタログに載せるために読む `dataset.json` へまとめます。dbt を使うかどうかに関わらず使えて、ネットワークにはアクセスしません（宣言と手元のデータしか読みません）。

書くファイルは 2 種類です。ディレクトリ名は自由です。

| ファイル | 内容 |
| --- | --- |
| `dataset.yml`（リポジトリルート・必須） | データセット自体 |
| `**/*.table.yml`（どこでも） | テーブル 1 つ、または複数 |

```yaml
# dataset.yml
spec_version: "0.1"
name: calendar
title: 日本の暦データ
description: 1955年〜2027年の日付スパインに祝日・曜日・和暦を付与
language: ja
licenses: [CC-BY-4.0]          # 任意。ID だけでよく、名称・URL・権利はレジストリから入る
contributors:
  - title: 内閣府
    roles: [rightsHolder]
```

```yaml
# models/main/mart/mart_calendar.table.yml
schema: main
name: mart_calendar
title: 日本の暦データ
description: 祝日・曜日・和暦・会計年度を付与した日付スパイン
published: true
fields:
  - name: date
    title: 日付
    semantic: { role: entity, name: date }
```

列構成が同じテーブルが並ぶときは 1 ファイルにまとめられます。YAML アンカーで共通部分を持てます:

```yaml
_fields: &fields
  - { name: area, title: 地域コード }
  - { name: value, title: 統計値, semantic: { role: measure, agg: sum } }
tables:
  - { schema: ssds, name: a_population, title: 人口, fields: *fields }
  - { schema: ssds, name: b_land,       title: 自然環境, fields: *fields }
```

**列の型は書きません。** 実データから読むので、宣言と実体がずれません。

```bash
queria validate                    # 宣言と実データを突き合わせる
queria validate --strict           # 警告も失敗として扱う
queria compile -o dist/dataset.json
```

ライセンスは任意です。書かない場合は `LICENSE` ファイルのないリポジトリと同じで、権利は全て留保され、データを他人がどう扱えるかは Queria の利用規約に委ねられます（`validate` は警告で知らせます）。`--strict` を付けるとエラーだけでなく警告でも失敗します。Queria 自身のデータセットは CI でこちらを使います。

データの場所は `--ducklake` / `--data-path`、素の Parquet なら `--parquet` で指定します。`fdl run` の中で走らせれば環境変数から拾います。`--manifest target/manifest.json` を渡すと dbt から lineage と展開済み SQL も取ります（`target/manifest.json` があれば自動で使います）。

どの情報がどこから来るか:

| 情報 | 供給元 |
| --- | --- |
| title・description・ライセンス・公開可否・semantic | 宣言 |
| テーブル・列・型・列順・NULL 許容 | 実データ |
| lineage・展開済み SQL・ソースファイルのパス | dbt の `manifest.json`（あれば） |

dbt がなくても、lineage は `depends_on` で書け、`*.table.yml` と同名の `.sql` があればそのテーブルの SQL として拾われます。

`*.table.yml` を dbt の `model-paths` 配下に置く場合は `.dbtignore` に `*.table.yml` を足してください。dbt はそこにある `.yml` を全部自分の properties ファイルとして読むため、そのままだと失敗します。`validate` が知らせます。

## API トークン

トークンなしでも使えますが、レートリミットがあります。ブラウザでログインするとトークン（有効期限 90 日）が発行され、上限が上がります:

```bash
queria login                    # ブラウザが開いて承認するだけ
queria login --no-browser       # SSH などでは表示されたコードを貼り付け
queria logout                   # 保存済みトークンを削除
```

CI など向けには [https://queria.io/profile/api-keys](https://queria.io/profile/api-keys) で手動発行したトークンも登録できます:

```bash
queria auth set-token <token>   # ~/.config/queria/config.toml に保存
queria auth status              # 確認
```

`--token` オプションや環境変数 `QUERIA_TOKEN` でも指定できます（この順で優先）。

## Python API

```python
import queria

with queria.connect() as conn:
    conn.sql("SELECT * FROM catalog.main.mart_datasets").show()
```

## MCP サーバー

Claude Code / Claude Desktop / Cursor などの MCP クライアントから使えます:

```json
{
  "mcpServers": {
    "queria": {
      "command": "uvx",
      "args": ["--from", "queria[mcp]", "queria", "mcp"]
    }
  }
}
```

`query` ツールは Queria のカタログに対する SELECT のみを実行します。書き込みに加えて、ローカルファイルや任意 URL を読む関数（`read_text` / `read_csv` / `glob` / `ST_Read` など）と動的 SQL（`query()`）を拒否するため、未信頼データを処理するエージェントから手元のファイル読取や内部エンドポイントへの SSRF には使えません。ローカルデータとの結合など制約のない SQL が必要な場合は CLI（`queria sql`）を使ってください。

## テレメトリ

改善のため、匿名の利用データ(コマンド名・成否・バージョン・対象データセット名)を収集します。SQL の内容・ファイルパス・個人情報は送信しません。次のいずれかでオプトアウトできます:

```bash
queria telemetry disable        # 設定ファイルに保存
export DO_NOT_TRACK=1           # 標準の環境変数
export QUERIA_NO_TELEMETRY=1
```

詳細: https://docs.queria.io/telemetry

## ドキュメント

https://docs.queria.io/

エージェント向けに機械可読な形式でも配信しています:

- [llms.txt](https://docs.queria.io/llms.txt) — ページ索引 / [llms-full.txt](https://docs.queria.io/llms-full.txt) — 全ページ連結
- 任意のページパスに `.md` を付けると生 Markdown を取得できます（例: [/reference/cli.md](https://docs.queria.io/reference/cli.md)）

## ソースと issue

PyPI で配布する各リリースにはソースがそのまま含まれているので、手元で動くものを読んで監査できます。開発自体は非公開リポジトリで行っており、このリポジトリは README・変更履歴・issue トラッカーを置く場所で、プルリクエストは受け付けていません。

バグ報告・機能要望は [issue](https://github.com/queria-io/queria-cli/issues) でお寄せください。

## License

[Queria CLI License](https://github.com/queria-io/queria-cli/blob/main/LICENSE)。商用を含めて利用は自由ですが、再配布はできません。0.10.0 以前のバージョンは MIT License で公開されており、その条件のまま利用できます。
