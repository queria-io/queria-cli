# queria

English | [日本語](README.ja.md)

Query Japanese open data on [Queria](https://data.queria.io) from the terminal, Python, and MCP.

A read-only client for exploring Japanese open data published on [Queria](https://data.queria.io) — e-Stat, National Land Numerical Information, EDINET, the Japan Meteorological Agency, and more — from the terminal, Python, and MCP. The data is published in DuckLake format, and all computation runs locally in DuckDB.

## Installation

```bash
uvx queria list          # run without installing
pip install queria       # or install normally
```

Requires Python 3.10+.

## Usage

```bash
queria list                              # list datasets
queria search 人口                        # search datasets, tables and columns
queria info e_stat                       # metadata (license, source, etc.)
queria schema e_stat                     # list tables
queria columns e_stat mart_population    # list columns
queria summarize zipcode.main.zipcodes   # per-column statistics (scans the whole table)
queria sql "SELECT * FROM zipcode.main.zipcodes LIMIT 10"
queria sql "SELECT * FROM zipcode.main.zipcodes" --out zipcodes.parquet
```

Tables are referenced as `<dataset>.<schema>.<table>`. Referenced datasets are attached automatically.

## API token

The client works without a token, but rate limits apply. Registering a token issued at [https://queria.io/profile/api-keys](https://queria.io/profile/api-keys) raises the limit:

```bash
queria auth set-token <token>   # saved to ~/.config/queria/config.toml
queria auth status              # check
```

You can also pass a token via the `--token` option or the `QUERIA_TOKEN` environment variable (in that order of precedence).

## Python API

```python
import queria

with queria.connect() as conn:
    conn.sql("SELECT * FROM catalog.main.mart_datasets").show()
```

## MCP server

Works with MCP clients such as Claude Code, Claude Desktop, and Cursor:

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

The `query` tool only runs SELECT statements against the Queria catalog. Besides writes, it rejects functions that read local files or arbitrary URLs (`read_text` / `read_csv` / `glob` / `ST_Read`, etc.) and dynamic SQL (`query()`), so agents processing untrusted data cannot use it to read local files or perform SSRF against internal endpoints. If you need unrestricted SQL, such as joining with local data, use the CLI (`queria sql`).

## Telemetry

To help improve the tool, we collect anonymous usage data (command name, success/failure, version, and target dataset name). SQL contents, file paths, and personal information are never sent. Opt out with any of the following:

```bash
queria telemetry disable        # saved to the config file
export DO_NOT_TRACK=1           # standard environment variable
export QUERIA_NO_TELEMETRY=1
```

Details: https://docs.queria.io/telemetry

## Documentation

https://docs.queria.io/

The docs are also served in agent-readable form:

- [llms.txt](https://docs.queria.io/llms.txt) — page index / [llms-full.txt](https://docs.queria.io/llms-full.txt) — all pages concatenated
- Append `.md` to any page path for raw Markdown (e.g. [/reference/cli.md](https://docs.queria.io/reference/cli.md))

## License

MIT
