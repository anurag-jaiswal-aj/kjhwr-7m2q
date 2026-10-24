import pytest
import sqlite3
from typing import Generator
from fastapi.testclient import TestClient

from backend.app.db.database import init_db, get_connection
from backend.app.main import app
from backend.app.api.endpoints import get_db_conn


@pytest.fixture
def temp_db(tmp_path) -> Generator[sqlite3.Connection, None, None]:
    """
    Creates an isolated, temporary SQLite database for unit and integration tests.
    """
    db_file = tmp_path / "test_analytics.db"
    init_db(str(db_file))
    conn = get_connection(str(db_file))
    yield conn
    conn.close()


@pytest.fixture
def api_client(temp_db: sqlite3.Connection) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient wired to the isolated temporary test database.
    Ensures zero interaction with production data or external network APIs.
    """
    def override_get_db():
        yield temp_db

    app.dependency_overrides[get_db_conn] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
