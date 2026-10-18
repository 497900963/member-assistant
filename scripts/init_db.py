"""Initialize the sample member database (sqlite).

Usage: python scripts/init_db.py
Creates MEMBER_ASSISTANT_DB_PATH with sample members, coupons and orders.
Safe to re-run: drops and recreates the tables.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
from app.log import get_logger, log_with

logger = get_logger("init_db")

SCHEMA = """
DROP TABLE IF EXISTS members;
DROP TABLE IF EXISTS coupons;
DROP TABLE IF EXISTS orders;
CREATE TABLE members (
  member_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  level TEXT NOT NULL,
  points INTEGER NOT NULL
);
CREATE TABLE coupons (
  id TEXT PRIMARY KEY,
  member_id TEXT NOT NULL,
  title TEXT NOT NULL,
  threshold REAL NOT NULL,
  amount REAL NOT NULL,
  status TEXT NOT NULL,
  expire_date TEXT NOT NULL
);
CREATE TABLE orders (
  id TEXT PRIMARY KEY,
  member_id TEXT NOT NULL,
  amount REAL NOT NULL,
  status TEXT NOT NULL,
  created_date TEXT NOT NULL
);
"""


def main() -> None:
    os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)
    if os.path.exists(settings.db_path):
        os.remove(settings.db_path)
    conn = sqlite3.connect(settings.db_path)
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO members VALUES (?, ?, ?, ?)",
        [
            ("M10001", "张三", "金卡", 12580),
            ("M10002", "李四", "银卡", 3200),
            ("M10003", "王五", "普卡", 450),
        ],
    )
    conn.executemany(
        "INSERT INTO coupons VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("C001", "M10001", "满200减50券", 200, 50, "valid", "2026-10-31"),
            ("C002", "M10001", "生日专享50元券", 0, 50, "valid", "2026-10-31"),
            ("C003", "M10002", "满100减20券", 100, 20, "valid", "2026-10-31"),
            ("C004", "M10002", "满200减50券", 200, 50, "used", "2026-09-30"),
        ],
    )
    conn.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        [
            ("O9001", "M10001", 899.0, "已完成", "2026-10-10"),
            ("O9002", "M10001", 1299.0, "已完成", "2026-10-05"),
            ("O9003", "M10002", 259.0, "已完成", "2026-10-12"),
        ],
    )
    conn.commit()
    conn.close()
    log_with(logger, 20, "db initialized", path=settings.db_path)


if __name__ == "__main__":
    main()
