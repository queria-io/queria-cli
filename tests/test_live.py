"""Smoke tests against the production catalog (deselected by default).

Run with: uv run pytest -m network
"""

from __future__ import annotations

import pytest

import queria
from queria import core

pytestmark = pytest.mark.network


def test_production_catalog_lists_datasets() -> None:
    with queria.connect() as conn:
        rows = conn.sql(core.list_datasets_sql()).fetchall()
    datasources = [r[0] for r in rows]
    assert "e_stat" in datasources
    assert "zipcode" in datasources


def test_production_auto_attach_query() -> None:
    with queria.connect() as conn:
        count = conn.sql(
            "SELECT count(*) FROM calendar.main.mart_calendar "
            "WHERE date BETWEEN DATE '2026-01-01' AND DATE '2026-01-31'"
        ).fetchone()[0]
    assert count == 31
