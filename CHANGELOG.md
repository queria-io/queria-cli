# CHANGELOG


## v0.3.1 (2026-07-18)

### Bug Fixes

- **mcp**: Block filesystem, SSRF and dynamic-SQL access from the query tool

The query tool gated SQL only with is_read_only(), an advisory check on the leading keyword. A
  SELECT could still read local files via read_text() / read_csv() / glob() / ST_Read(), reach
  internal endpoints (read_csv('http://169.254.169.254/...')), or smuggle any of these past
  inspection with query('...'). An MCP client driven by untrusted data could be made to exfiltrate
  secrets (e.g. ~/.ssh/id_rsa) through the tool result.

Reject these functions in the query tool. core.unsafe_function() parses the SQL with DuckDB's own
  parser (json_serialize_sql) and walks the AST, so a call is found regardless of nesting, with a
  lexical scan as a fail-closed fallback for statements the parser refuses. The CLI keeps
  unrestricted SQL: it is run by a trusted local user, not an untrusted agent.

Also correct the tool docstring and server instructions, which described the tool as plain
  "read-only" and implied it was safe.

### Continuous Integration

- **release**: Docs.queria.io デプロイフックのステップを削除

### Documentation

- Describe query tool sandboxing in the README

Note that the MCP query tool runs SELECT-only over the catalogs and blocks file/URL readers and
  dynamic SQL, and point users at the CLI when they need unrestricted SQL.


## v0.3.0 (2026-07-18)

### Continuous Integration

- Add Dependabot config for weekly dependency updates

### Documentation

- Add CLAUDE.md with release and docs-update guidance

### Features

- Cli コマンドと MCP ツール呼び出しにテレメトリを配線

- 匿名・オプトアウト可能なテレメトリ基盤を追加


## v0.2.1 (2026-07-17)

### Bug Fixes

- **cli**: Align read-only error message with accepted statements

The read-only guard accepts VALUES, TABLE, and FROM statements in addition to the seven listed in
  the rejection message. Centralize the message as core.READONLY_ERROR next to _READONLY_RE and list
  all ten accepted statement types.


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

Resolve tokens from --token flag, QUERIA_TOKEN env var, or ~/.config/queria/config.toml, and create
  a scoped DuckDB HTTP secret (BEARER_TOKEN) on connect. Add 'queria auth set-token/status/clear'
  subcommands and a rate-limit hint on HTTP 429

- Add info command and get_dataset_info MCP tool

Shows a dataset's metadata (license, source URL, repository, schemas, last build time) as
  field/value rows. The README body is opt-in via --readme / include_readme because it can be long.

- Add summarize command

Runs DuckDB SUMMARIZE against a table referenced as dataset.schema.table (schema defaults to main).
  Documents that it scans the whole table over HTTP.

- Cross-catalog search over datasets, tables and columns

Replaces the dataset-only search with a search across datasets, tables and columns backed by
  catalog.main.mart_search_entries. The MCP search_datasets tool is renamed to search accordingly.

- **cli**: Add markdown output format


## v0.1.0 (2026-07-11)

### Chores

- Update org references from flo8s to queria-io

### Continuous Integration

- Test, docs deploy, and release workflows

### Documentation

- Documentation site for docs.queria.io

### Features

- **cli**: Subcommand interface with table/csv/json/jsonl and file output

- **core**: Read-only connection with auto-attach and catalog queries

- **mcp**: Stdio MCP server with row and payload caps
