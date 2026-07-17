# CHANGELOG


## v0.2.0 (2026-07-17)

### Chores

- **docs**: Remove Zensical docs site (moved to queria-io/docs)
  ([`78439b7`](https://github.com/queria-io/queria-cli/commit/78439b79ac21ec346070227c13e2a4afa43a4801))

### Continuous Integration

- **release**: Publish automatically on push to main
  ([`bd56301`](https://github.com/queria-io/queria-cli/commit/bd563017ea6437dec7adb90f8b2afa30042d36b9))

- **release**: Trigger docs.queria.io rebuild via deploy hook
  ([`8177948`](https://github.com/queria-io/queria-cli/commit/817794850f50a9ba080b676c4b18dbea4467bd4d))

### Documentation

- Document API tokens and direct-access CREATE SECRET
  ([`db21b9b`](https://github.com/queria-io/queria-cli/commit/db21b9b74f156c73778447c2d09c500555801531))

- Update README usage for new commands
  ([`87f0532`](https://github.com/queria-io/queria-cli/commit/87f0532af4059d7d7496038527b9b544f751a222))

### Features

- Add API token support
  ([`d0795aa`](https://github.com/queria-io/queria-cli/commit/d0795aa53596ee987a638aec48b1720f4628d442))

Resolve tokens from --token flag, QUERIA_TOKEN env var, or ~/.config/queria/config.toml, and create
  a scoped DuckDB HTTP secret (BEARER_TOKEN) on connect. Add 'queria auth set-token/status/clear'
  subcommands and a rate-limit hint on HTTP 429

- Add info command and get_dataset_info MCP tool
  ([`2b979ca`](https://github.com/queria-io/queria-cli/commit/2b979caf92e9b00682a2ed36284c59f83c8450b4))

Shows a dataset's metadata (license, source URL, repository, schemas, last build time) as
  field/value rows. The README body is opt-in via --readme / include_readme because it can be long.

- Add summarize command
  ([`e79dc7b`](https://github.com/queria-io/queria-cli/commit/e79dc7bf5e0c621fec90293dbcb6bbd4b5fc4464))

Runs DuckDB SUMMARIZE against a table referenced as dataset.schema.table (schema defaults to main).
  Documents that it scans the whole table over HTTP.

- Cross-catalog search over datasets, tables and columns
  ([`2bc845d`](https://github.com/queria-io/queria-cli/commit/2bc845d63db73bd028b06044b0cad79cdc935b08))

Replaces the dataset-only search with a search across datasets, tables and columns backed by
  catalog.main.mart_search_entries. The MCP search_datasets tool is renamed to search accordingly.

- **cli**: Add markdown output format
  ([`92d1c4b`](https://github.com/queria-io/queria-cli/commit/92d1c4be6adb286943a78445f933cb823814c3f0))


## v0.1.0 (2026-07-11)

### Chores

- Update org references from flo8s to queria-io
  ([`ca647a6`](https://github.com/queria-io/queria-cli/commit/ca647a6880dff76e12aef7af5daeb5b189fa64cf))

### Continuous Integration

- Test, docs deploy, and release workflows
  ([`5686528`](https://github.com/queria-io/queria-cli/commit/5686528933dfb1a58235332c160a1a6c2c4f4c9e))

### Documentation

- Documentation site for docs.queria.io
  ([`5045b94`](https://github.com/queria-io/queria-cli/commit/5045b94cfeddd0bbd4e383f823eef3aad8b49881))

### Features

- **cli**: Subcommand interface with table/csv/json/jsonl and file output
  ([`b1638a0`](https://github.com/queria-io/queria-cli/commit/b1638a0fc64d54ea437912c8830db6ca7be34a80))

- **core**: Read-only connection with auto-attach and catalog queries
  ([`cad8c13`](https://github.com/queria-io/queria-cli/commit/cad8c13671d67e00490698f90ac8152e1e677a1b))

- **mcp**: Stdio MCP server with row and payload caps
  ([`630ec15`](https://github.com/queria-io/queria-cli/commit/630ec15b1fd3239ddf56db9c1ca711249e8dc181))
