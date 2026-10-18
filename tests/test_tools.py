"""Tests for the preset read-only tool registry."""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import tools  # noqa: E402


def test_registry_is_closed():
    assert set(tools.TOOLS.keys()) == {"get_points", "get_coupons", "get_orders"}


def test_unknown_tool_rejected():
    with pytest.raises(ValueError):
        tools.call_tool("drop_table", "M10001")


def test_db_is_read_only():
    # any write attempt must fail: the connection is opened with mode=ro
    with pytest.raises(sqlite3.OperationalError):
        with tools._ro_connect() as conn:
            conn.execute("INSERT INTO members VALUES ('X', 'x', 'x', 0)")


def test_get_points():
    r = tools.get_points("M10001")
    assert r["found"] is True and r["points"] == 12580


def test_get_points_unknown_member():
    r = tools.get_points("NOPE")
    assert r["found"] is False


def test_get_coupons():
    r = tools.get_coupons("M10001")
    assert len(r["coupons"]) == 2


def test_get_orders():
    r = tools.get_orders("M10001")
    assert len(r["orders"]) == 2
    assert r["orders"][0]["id"] == "O9001"  # newest first
