"""SQLite schema and helpers for AIJobCrawler."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from config import DB_PATH, DATA_DIR

_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    careers_url TEXT,
    category TEXT,
    founded TEXT,
    hq TEXT,
    funding TEXT,
    products TEXT,
    description TEXT,
    employee_count TEXT,
    tech_stack TEXT DEFAULT '[]',
    recent_news TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    title TEXT NOT NULL,
    team TEXT,
    location TEXT,
    url TEXT,
    seniority_level TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL UNIQUE REFERENCES roles(id),
    min_yoe INTEGER,
    max_yoe INTEGER,
    degree_level TEXT,
    skills TEXT DEFAULT '[]',
    languages TEXT DEFAULT '[]',
    publications_expected INTEGER DEFAULT 0,
    description_raw TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a connection to the SQLite database, creating it if needed."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create all tables if they don't exist."""
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA)
    conn.close()


def insert_company(conn: sqlite3.Connection, **kwargs: Any) -> int:
    """Insert a company and return its id. Skips if name already exists."""
    cols = ", ".join(kwargs.keys())
    placeholders = ", ".join(["?"] * len(kwargs))
    cur = conn.execute(
        f"INSERT OR IGNORE INTO companies ({cols}) VALUES ({placeholders})",
        list(kwargs.values()),
    )
    conn.commit()
    if cur.lastrowid:
        return cur.lastrowid
    # Already existed — fetch id
    row = conn.execute(
        "SELECT id FROM companies WHERE name = ?", (kwargs["name"],)
    ).fetchone()
    return row["id"]


def update_company(conn: sqlite3.Connection, company_id: int, **kwargs: Any) -> None:
    """Update fields on an existing company row."""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    conn.execute(
        f"UPDATE companies SET {set_clause} WHERE id = ?",
        [*kwargs.values(), company_id],
    )
    conn.commit()


def insert_role(conn: sqlite3.Connection, **kwargs: Any) -> int:
    """Insert a role and return its id."""
    cols = ", ".join(kwargs.keys())
    placeholders = ", ".join(["?"] * len(kwargs))
    cur = conn.execute(
        f"INSERT INTO roles ({cols}) VALUES ({placeholders})",
        list(kwargs.values()),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def insert_requirements(
    conn: sqlite3.Connection,
    role_id: int,
    min_yoe: Optional[int] = None,
    max_yoe: Optional[int] = None,
    degree_level: Optional[str] = None,
    skills: Optional[list[str]] = None,
    languages: Optional[list[str]] = None,
    publications_expected: bool = False,
    description_raw: Optional[str] = None,
) -> int:
    """Insert requirements for a role."""
    cur = conn.execute(
        """INSERT OR REPLACE INTO requirements
           (role_id, min_yoe, max_yoe, degree_level, skills, languages,
            publications_expected, description_raw)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            role_id,
            min_yoe,
            max_yoe,
            degree_level,
            json.dumps(skills or []),
            json.dumps(languages or []),
            int(publications_expected),
            description_raw,
        ),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
