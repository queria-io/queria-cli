# queria

Query Japanese open data on [Queria](https://data.queria.io) from the terminal, Python, and MCP.

[Queria](https://data.queria.io) が公開する日本のオープンデータ（e-Stat、国土数値情報、EDINET、気象庁ほか）を、ターミナル・Python・MCP から read-only で探索するクライアントです。データは DuckLake 形式で公開されており、計算はすべて手元の DuckDB で行われます。

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

## API トークン

トークンなしでも使えますが、レートリミットがあります。[https://queria.io/profile/api-keys](https://queria.io/profile/api-keys) で発行したトークンを登録すると上限が上がります:

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

## License

MIT
