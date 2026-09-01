# queria

English | [日本語](https://github.com/queria-io/queria-cli/blob/main/README.ja.md)

Query Japanese open data on [Queria](https://data.queria.io) from the terminal, Python, and MCP.

A client for the Japanese open data published on [Queria](https://data.queria.io) — e-Stat, National Land Numerical Information, EDINET, the Japan Meteorological Agency, and more. Explore it from the terminal, Python and MCP, and declare your own datasets for the catalog. The data is published in DuckLake format, and all computation runs locally in DuckDB.

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

## Publishing a dataset

`queria validate` and `queria compile` work on the metadata you declare for a dataset, turning it into `dataset.json`, the file Queria reads to list your data in the catalog. It works whether or not you build the dataset with dbt, and it never talks to the network — it only reads your declarations and your local data.

You declare two kinds of file. Directory names are up to you.

| File | Content |
| --- | --- |
| `dataset.yml` (repository root, required) | the dataset itself |
| `**/*.table.yml` (anywhere) | one table, or several |

```yaml
# dataset.yml
spec_version: "0.1"
name: calendar
title: Japanese calendar
description: A date spine from 1955 to 2027 with holidays, weekdays and Japanese eras.
language: ja
licenses: [CC-BY-4.0]          # optional; the ID is enough, and title, URL and rights come from the registry
contributors:
  - title: Cabinet Office
    roles: [rightsHolder]
```

```yaml
# models/main/mart/mart_calendar.table.yml
schema: main
name: mart_calendar
title: Japanese calendar
description: A date spine with holidays, weekdays, Japanese eras and fiscal years.
published: true
fields:
  - name: date
    title: Date
    semantic: { role: entity, name: date }
```

Tables that share a column layout can go in one file, so YAML anchors can carry the shared part:

```yaml
_fields: &fields
  - { name: area, title: Area code }
  - { name: value, title: Value, semantic: { role: measure, agg: sum } }
tables:
  - { schema: ssds, name: a_population, title: Population, fields: *fields }
  - { schema: ssds, name: b_land,       title: Land,       fields: *fields }
```

**Do not write column types.** They are read from your data, so they cannot drift from it.

```bash
queria validate                    # check the declarations against the data
queria validate --strict           # and fail on warnings too
queria compile -o dist/dataset.json
```

Licenses are optional. Leaving them out is like a repository with no `LICENSE` file: you keep every right, and what others may do with the data is left to Queria's terms of use. `validate` says so as a warning. `--strict` fails on warnings as well as errors, which is what Queria's own dataset repositories run in CI.

Point it at your data with `--ducklake` / `--data-path`, or `--parquet` for plain Parquet files. Inside `fdl run`, the catalog location is picked up from the environment. Pass `--manifest target/manifest.json` to also pull lineage and compiled SQL out of dbt (`target/manifest.json` is used automatically when it exists).

Where each piece of information comes from:

| Information | Source |
| --- | --- |
| title, description, license, published, semantic roles | your declarations |
| tables, columns, types, column order, nullability | your data |
| lineage, compiled SQL, source file paths | dbt's `manifest.json`, when present |

Without dbt you can still declare lineage with `depends_on`, and a `.sql` file next to a `*.table.yml` of the same name is picked up as the table's SQL.

If you keep `*.table.yml` under dbt's `model-paths`, add `*.table.yml` to `.dbtignore` — dbt reads every `.yml` there as a properties file and would fail on these. `validate` tells you when this is missing.

## API token

The client works without a token, but rate limits apply. Logging in via the browser issues a token (valid for 90 days) and raises the limit:

```bash
queria login                    # opens the browser for approval
queria login --no-browser       # for SSH etc.: paste the code shown on the page
queria logout                   # remove the saved token
```

Tokens can also be issued manually at [https://queria.io/profile/api-keys](https://queria.io/profile/api-keys) (for CI and other tools) and registered with:

```bash
queria auth set-token <token>   # saved to ~/.config/queria/config.toml
queria auth status              # check
```

You can also pass a token via the `--token` option or the `QUERIA_TOKEN` environment variable (in that order of precedence).

Setting `QUERIA_TOKEN` to an **empty value** ignores any saved token and accesses the data anonymously. Use it in CI, containers and on shared machines to state that a run uses no token.

## Python API

```python
import queria

# what is published, and what is in it
queria.list_datasets()
queria.search("population")
queria.tables("calendar")
queria.columns("calendar", "mart_calendar")

# the data itself
with queria.connect() as conn:
    conn.sql("SELECT * FROM calendar.main.mart_calendar LIMIT 10").show()
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

### Keeping your own traffic out of the usage figures

If you work on Queria itself, or on a dataset published to it, set the machine's
affiliation once and every request it makes says so:

```bash
export QUERIA_AFFILIATION=internal   # or `affiliation = "internal"` in the config file
```

It travels in the user agent (`queria-cli/0.21.0 (aff=internal)`), so builds,
CI and a contributor's laptop can be told apart from people using the data.
Dataset builds are named `queria-build` without anyone setting anything.

This is used for measurement and nothing else. It does not change what a
request may do, or how it is rate limited.

## Documentation

The documentation is readable from the terminal, so an agent needs no browser:

```bash
queria docs list                     # every page, with the name `docs show` takes
queria docs show reference/cli       # one page as Markdown
queria docs show reference/cli --lang ja
```

Pages are read from docs.queria.io and cached, so a run that has lost its
connection still gets the copy it read last. The MCP server exposes the same
two as the `list_docs` and `show_doc` tools.

The same pages in a browser: https://docs.queria.io/

They are also served in agent-readable form:

- [llms.txt](https://docs.queria.io/llms.txt) — page index / [llms-full.txt](https://docs.queria.io/llms-full.txt) — all pages concatenated
- Append `.md` to any page path for raw Markdown (e.g. [/reference/cli.md](https://docs.queria.io/reference/cli.md))

## Source and issues

Every release on PyPI ships the source, so you can read and audit what runs on your machine. Development itself happens in a private repository: this repository holds the README, the changelog and the issue tracker, and does not accept pull requests.

Bug reports and feature requests are welcome as [issues](https://github.com/queria-io/queria-cli/issues).

## License

MIT
