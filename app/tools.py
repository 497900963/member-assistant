"""Preset read-only member tools.

Hard guarantees:
1. The tool registry is closed: only the three tools below exist, no dynamic
   registration, no raw SQL passthrough.
2. The sqlite database is opened in read-only mode (URI mode=ro). Any write
   attempt raises sqlite3.OperationalError.
3. member_id is injected by the server from the auth header, never taken from
   the LLM or the request body.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Callable

from .config import settings
from .log import get_logger, log_with

logger = get_logger(__name__)

_READONLY_URI = f"file:{settings.db_path}?mode=ro"


def _ro_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_READONLY_URI, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_points(member_id: str) -> dict[str, Any]:
    """Return the member's points balance."""
    with _ro_connect() as conn:
        row = conn.execute(
            "SELECT member_id, name, level, points FROM members WHERE member_id = ?",
            (member_id,),
        ).fetchone()
    if row is None:
        return {"member_id": member_id, "found": False}
    return {
        "member_id": row["member_id"],
        "name": row["name"],
        "level": row["level"],
        "points": row["points"],
        "found": True,
    }


def get_coupons(member_id: str) -> dict[str, Any]:
    """Return the member's coupons."""
    with _ro_connect() as conn:
        rows = conn.execute(
            "SELECT id, title, threshold, amount, status, expire_date FROM coupons "
            "WHERE member_id = ? ORDER BY expire_date",
            (member_id,),
        ).fetchall()
    return {
        "member_id": member_id,
        "coupons": [dict(r) for r in rows],
    }


def get_orders(member_id: str) -> dict[str, Any]:
    """Return the member's recent orders."""
    with _ro_connect() as conn:
        rows = conn.execute(
            "SELECT id, amount, status, created_date FROM orders "
            "WHERE member_id = ? ORDER BY created_date DESC LIMIT 10",
            (member_id,),
        ).fetchall()
    return {
        "member_id": member_id,
        "orders": [dict(r) for r in rows],
    }


# ---- closed registry: the ONLY tools the assistant may call ----
TOOLS: dict[str, Callable[[str], dict[str, Any]]] = {
    "get_points": get_points,
    "get_coupons": get_coupons,
    "get_orders": get_orders,
}

TOOL_DESCRIPTIONS = """Available tools (call at most one per round, JSON format):
{"tool": "get_points"} - member points balance
{"tool": "get_coupons"} - member coupons
{"tool": "get_orders"} - member recent orders
If no tool is needed, answer directly. member_id is injected by the system; do not invent it."""


def call_tool(name: str, member_id: str) -> dict[str, Any]:
    if name not in TOOLS:
        raise ValueError(f"tool not allowed: {name}")
    log_with(logger, 20, "tool call", tool=name, member_id=member_id)
    return TOOLS[name](member_id)
