"""SQLite schema for the local spectral line database."""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = "1"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gas_catalog (
    gas_id INTEGER PRIMARY KEY AUTOINCREMENT,
    gas_name TEXT NOT NULL UNIQUE,
    hitran_molecule_id INTEGER NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS line_coverage (
    coverage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    gas_id INTEGER NOT NULL,
    nu_min REAL NOT NULL,
    nu_max REAL NOT NULL,
    line_count INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'local',
    downloaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gas_id) REFERENCES gas_catalog(gas_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS spectral_lines (
    line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    gas_id INTEGER NOT NULL,
    wavenumber REAL NOT NULL,
    line_intensity REAL NOT NULL,
    air_width REAL NOT NULL,
    self_width REAL NOT NULL,
    lower_state_energy REAL NOT NULL,
    temperature_dependence REAL NOT NULL,
    pressure_shift REAL NOT NULL,
    source TEXT NOT NULL DEFAULT 'local',
    downloaded_at TEXT,
    FOREIGN KEY (gas_id) REFERENCES gas_catalog(gas_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS download_tasks (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL DEFAULT '',
    gas_id INTEGER NOT NULL,
    nu_min REAL NOT NULL,
    nu_max REAL NOT NULL,
    mode TEXT NOT NULL DEFAULT 'skip_covered',
    status TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    started_at TEXT,
    finished_at TEXT,
    FOREIGN KEY (gas_id) REFERENCES gas_catalog(gas_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_line_coverage_gas_range
    ON line_coverage(gas_id, nu_min, nu_max);

CREATE INDEX IF NOT EXISTS idx_spectral_lines_gas_wavenumber
    ON spectral_lines(gas_id, wavenumber);
"""


def connect_database(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with project defaults."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection and always close its file handle."""
    connection = connect_database(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        # sqlite3.Connection 的上下文协议不会关闭文件句柄，Windows 下必须显式 close。
        connection.close()


def initialize_database(db_path: str | Path) -> None:
    """Create local line database tables and schema metadata."""
    with database_connection(db_path) as connection:
        # Schema 初始化集中在一个事务内，避免应用启动中断后留下半初始化数据库。
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            """
            INSERT INTO schema_metadata(key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (SCHEMA_VERSION,),
        )
