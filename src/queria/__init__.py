"""Queria — query Japanese open data (data.queria.io) from Python and the CLI."""

from queria.core import DEFAULT_STORAGE, Connection, connect, version

__version__ = version()

__all__ = ["DEFAULT_STORAGE", "Connection", "connect", "__version__"]
