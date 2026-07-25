# Security Policy

## Supported versions

Only the latest release on PyPI receives security fixes. Upgrade with `pip install --upgrade queria`, or use `uvx queria@latest`.

## Reporting a vulnerability

Please do not open a public issue.

Use GitHub's private vulnerability reporting: [Report a vulnerability](https://github.com/queria-io/queria-cli/security/advisories/new). English and Japanese are both fine.

Include the version (`queria --version`), your operating system, and the steps to reproduce. We aim to acknowledge a report within three business days.

## Scope

This policy covers the `queria` package on PyPI — the CLI, the Python API and the MCP server.

The MCP `query` tool is a deliberate security boundary: it only runs SELECT statements against the Queria catalog, and rejects functions that read local files or arbitrary URLs as well as dynamic SQL. Any way around that boundary is in scope and worth reporting.

Issues in the Queria service itself (queria.io, data.queria.io) are also in scope; report them the same way.
