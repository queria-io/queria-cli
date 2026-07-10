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
queria search 人口                        # キーワード検索
queria schema e_stat                     # テーブル一覧
queria columns e_stat mart_population    # カラム一覧
queria sql "SELECT * FROM zipcode.main.zipcodes LIMIT 10"
queria sql "SELECT * FROM zipcode.main.zipcodes" --out zipcodes.parquet
```

テーブルは `<dataset>.<schema>.<table>` で参照します。参照したデータセットは自動的に ATTACH されます。

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

## ドキュメント

https://docs.queria.io/

## License

MIT
