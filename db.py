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
    key_people TEXT DEFAULT '[]',
    wiki_url TEXT,
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


def init_db(db_path: str | sqlite3.Connection = DB_PATH) -> None:
    """Create all tables if they don't exist."""
    if isinstance(db_path, sqlite3.Connection):
        conn = db_path
        conn.executescript(_SCHEMA)
        _init_talent_tables(conn)
        return
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA)
    _init_talent_tables(conn)
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
    if cur.rowcount > 0:
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


# --- Talent Flow tables (Iteration 2) ---

def _init_talent_tables(conn: sqlite3.Connection) -> None:
    """Create talent_moves and company_discovery tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS talent_moves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT NOT NULL,
            linkedin_url TEXT UNIQUE NOT NULL,
            previous_lab TEXT NOT NULL,
            previous_title TEXT DEFAULT '',
            current_company TEXT NOT NULL,
            current_title TEXT DEFAULT '',
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_query TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS company_discovery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            talent_count INTEGER DEFAULT 0,
            talent_sources TEXT DEFAULT '{}',
            category TEXT DEFAULT 'unknown',
            funding TEXT DEFAULT '',
            founded TEXT DEFAULT '',
            hq_location TEXT DEFAULT '',
            careers_url TEXT DEFAULT '',
            website TEXT DEFAULT '',
            description TEXT DEFAULT '',
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enriched BOOLEAN DEFAULT 0,
            added_to_pipeline BOOLEAN DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_talent_lab ON talent_moves(previous_lab);
        CREATE INDEX IF NOT EXISTS idx_talent_company ON talent_moves(current_company);
        CREATE INDEX IF NOT EXISTS idx_discovery_talent ON company_discovery(talent_count DESC);
    """)


def insert_talent_move(conn: sqlite3.Connection, move: dict) -> None:
    """Insert a talent move, ignoring duplicates by linkedin_url."""
    conn.execute(
        """INSERT OR IGNORE INTO talent_moves
           (person_name, linkedin_url, previous_lab, previous_title, current_company, current_title, source_query)
           VALUES (:person_name, :linkedin_url, :previous_lab, :previous_title, :current_company, :current_title, :source_query)""",
        move,
    )
    conn.commit()


def insert_discovered_company(conn: sqlite3.Connection, company: dict) -> None:
    """Insert or update a discovered company."""
    conn.execute(
        """INSERT OR REPLACE INTO company_discovery
           (company_name, talent_count, talent_sources, category)
           VALUES (:company_name, :talent_count, :talent_sources, :category)""",
        company,
    )
    conn.commit()


def get_talent_moves_by_lab(conn: sqlite3.Connection, lab: str) -> list[dict]:
    """Get all talent moves from a specific source lab."""
    rows = conn.execute("SELECT * FROM talent_moves WHERE previous_lab = ?", (lab,)).fetchall()
    return [dict(r) for r in rows]


def get_top_companies_by_talent(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    """Get companies ranked by talent inflow count."""
    rows = conn.execute("SELECT * FROM company_discovery ORDER BY talent_count DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
