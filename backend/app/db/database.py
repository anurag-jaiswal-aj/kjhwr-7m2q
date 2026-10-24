import sqlite3
from typing import Generator
from pathlib import Path
from contextlib import contextmanager

from backend.app.config import DEFAULT_DB_PATH


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db(db_path: str = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actual_generation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                publish_time TEXT NOT NULL,
                settlement_date TEXT NOT NULL,
                settlement_period INTEGER NOT NULL,
                fuel_type TEXT NOT NULL,
                generation INTEGER NOT NULL,
                CONSTRAINT uq_actual_start_fuel UNIQUE (start_time, fuel_type)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_actual_start_time ON actual_generation(start_time);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_actual_settlement_date ON actual_generation(settlement_date);
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecast_generation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publish_time TEXT NOT NULL,
                start_time TEXT NOT NULL,
                generation INTEGER NOT NULL,
                CONSTRAINT uq_forecast_pub_start UNIQUE (publish_time, start_time)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_forecast_start_pub ON forecast_generation(start_time, publish_time);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_forecast_pub_time ON forecast_generation(publish_time);
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset TEXT NOT NULL,
                date_range_start TEXT NOT NULL,
                date_range_end TEXT NOT NULL,
                retrieved_count INTEGER NOT NULL,
                valid_count INTEGER NOT NULL,
                unique_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
