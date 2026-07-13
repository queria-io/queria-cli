---
title: MCP サーバー
---

# MCP サーバー

`queria mcp` は stdio の MCP サーバーです。Claude Code、Claude Desktop、Cursor などの MCP クライアントから Queria のデータを探索・クエリできます。

## セットアップ

### Claude Code

```bash
claude mcp add queria -- uvx --from 'queria[mcp]' queria mcp
```

### Claude Desktop / Cursor など（JSON 設定）

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

## 提供ツール

| ツール | 役割 |
|---|---|
| `list_datasets` | データセット一覧 |
| `search_datasets` | キーワード検索 |
| `get_schema` | テーブル一覧 |
| `get_columns` | カラム一覧 |
| `query` | read-only SQL の実行 |

詳細な引数と挙動は [MCP ツールリファレンス](../reference/mcp-tools.md)を参照してください。

## API トークン

MCP サーバーも CLI と同じトークン解決（環境変数 `QUERIA_TOKEN` → 設定ファイル）を使います。`queria auth set-token <token>` で保存しておくか、MCP クライアントの設定で環境変数を渡してください（[CLI ガイド](cli.md#api)参照）。

## 結果の上限について

`query` の結果は行数（デフォルト 100、最大 1000）とペイロードサイズ（約 1MB）で打ち切られます。これはエージェントのコンテキストを守るための仕様です。打ち切られた場合は `truncated: true` とヒントが返るので、集計や LIMIT で絞るか、バルク抽出には CLI の `--out` を使ってください。

## スキルとの関係

Claude Code では配布用スキル（queria-io/queria-skill）も利用できます。スキルはカタログの構造や活用パターンの知識を含むため、Claude Code では スキル + CLI の組み合わせを推奨します。MCP サーバーは Claude Code 以外のクライアントで使う場合の選択肢です。
