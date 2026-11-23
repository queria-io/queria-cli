# queria

English | [日本語](https://github.com/queria-io/queria-cli/blob/main/README.ja.md)

Query Japanese open data on [Queria](https://data.queria.io) from the terminal and Python.

A client for the Japanese open data published on [Queria](https://data.queria.io) — e-Stat, National Land Numerical Information, EDINET, the Japan Meteorological Agency, and more. Explore it from the terminal and Python, and declare your own datasets for the catalog. The data is published in DuckLake format, and all computation runs locally in DuckDB.

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
queria search --column 町丁目 --column 人口  # tables holding both columns
queria info e_stat                       # metadata (license, source, etc.)
queria schema e_stat                     # list tables
queria columns e_stat mart_population    # list columns
queria summarize zipcode.main.zipcodes   # per-column statistics (scans the whole table)
queria sql "SELECT * FROM zipcode.main.zipcodes LIMIT 10"
queria sql "SELECT * FROM zipcode.main.zipcodes" --out zipcodes.parquet
```

Tables are referenced as `<dataset>.<schema>.<table>`. Referenced datasets are attached automatically.

## Publishing a dataset

A dataset is a version made with [fdl](https://fdl.queria.io) (`fdl commit` and `fdl push`). Its description is written in YAML and Markdown and put into the version with [tabledoc](https://github.com/queria-io/tabledoc):

```bash
tabledoc validate                                  # check the description
tabledoc load --out .fdl/pack                      # write it into the working catalog's _meta schema
fdl commit … --dataset .fdl/pack/dataset.json --assets .fdl/pack/assets && fdl push …
```

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
queria.search(columns=["町丁目", "人口"], geo=True)
queria.tables("calendar")
queria.columns("calendar", "day")

# the data itself
with queria.connect() as conn:
    conn.sql("SELECT * FROM calendar.calendar.day LIMIT 10").show()
```

## Agent skills

Install the [Queria agent skills](https://github.com/queria-io/skills), which teach a coding agent how to find and query the data:

```bash
queria skills list                   # every published skill
queria skills install                # install them into this project
queria skills install --global       # or for every project on this machine
```

They go into `.agents/skills`, which Codex, Cursor, OpenCode and others read, and into `.claude/skills` wherever Claude Code is set up. A skill you have edited yourself is never replaced without `--force`.

## MCP server

Queria's MCP server runs at `https://mcp.queria.io`; add that URL to your MCP client, with nothing to install. The `queria mcp` command has been removed: replace `uvx --from 'queria[mcp]' queria mcp` in your client's settings with the URL. Setup: https://docs.queria.io/en/mcp

## Telemetry

To help improve the tool, we collect anonymous usage data (command name, success/failure, version, and target dataset name). File paths and personal information are never sent. The SQL you run is sent only if you say yes when the CLI asks, once, at a terminal (`queria telemetry enable --sql` / `disable --sql` change it later). Opt out of everything with any of the following:

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
connection still gets the copy it read last.

The same pages in a browser: https://docs.queria.io/

They are also served in agent-readable form:

- [llms.txt](https://docs.queria.io/llms.txt) — page index / [llms-full.txt](https://docs.queria.io/llms-full.txt) — all pages concatenated
- Append `.md` to any page path for raw Markdown (e.g. [/reference/cli.md](https://docs.queria.io/reference/cli.md))

## Source and issues

Every release on PyPI ships the source, so you can read and audit what runs on your machine. Development itself happens in a private repository: this repository holds the README, the changelog and the issue tracker, and does not accept pull requests.

Bug reports and feature requests are welcome as [issues](https://github.com/queria-io/queria-cli/issues).

## License

MIT
