"""Unit tests for the created_at migration script."""

import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from contextlib import closing
import pytest
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from migrate_add_created_at import (
    check_column_exists,
    migrate_database,
    verify_migration
)


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create test database with old schema (without created_at)
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()

        # Create projects table first (foreign key dependency)
        cursor.execute("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                is_default BOOLEAN DEFAULT FALSE
            )
        """)

        # Create secrets table with OLD schema (no created_at)
        cursor.execute("""
            CREATE TABLE secrets (
                id INTEGER NOT NULL PRIMARY KEY,
                project VARCHAR(100) NOT NULL,
                path VARCHAR(500) NOT NULL,
                encrypted_value TEXT NOT NULL,
                encryption_iv VARCHAR(32) NOT NULL,
                encryption_tag VARCHAR(32) NOT NULL,
                version INTEGER NOT NULL,
                updated_at DATETIME NOT NULL,
                updated_by VARCHAR(100) NOT NULL,
                project_id INTEGER,
                FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL
            )
        """)

        # Insert test data
        cursor.execute("""
            INSERT INTO projects (name, is_default) VALUES ('test_project', TRUE)
        """)

        test_data = [
            ("test_project", "API_KEY_1", b"encrypted1", b"iv1", b"tag1", 1,
             "2024-01-01 10:00:00", "user1"),
            ("test_project", "API_KEY_2", b"encrypted2", b"iv2", b"tag2", 1,
             "2024-02-01 11:00:00", "user2"),
            ("test_project", "API_KEY_3", b"encrypted3", b"iv3", b"tag3", 2,
             "2024-03-01 12:00:00", "user3"),
        ]

        cursor.executemany("""
            INSERT INTO secrets (project, path, encrypted_value, encryption_iv,
                               encryption_tag, version, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, test_data)

        conn.commit()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_check_column_exists(test_db):
    """Test the check_column_exists function."""
    with closing(sqlite3.connect(test_db)) as conn:
        cursor = conn.cursor()

        # Should find existing columns
        assert check_column_exists(cursor, "secrets", "updated_at") is True
        assert check_column_exists(cursor, "secrets", "project") is True

        # Should not find non-existent columns
        assert check_column_exists(cursor, "secrets", "created_at") is False
        assert check_column_exists(cursor, "secrets", "nonexistent") is False


def test_migrate_database_success(test_db):
    """Test successful migration."""
    # Run migration
    migrate_database(test_db)

    with closing(sqlite3.connect(test_db)) as conn:
        cursor = conn.cursor()

        # Check column was added
        assert check_column_exists(cursor, "secrets", "created_at") is True

        # Check all records have created_at set
        cursor.execute("SELECT COUNT(*) FROM secrets WHERE created_at IS NULL")
        assert cursor.fetchone()[0] == 0

        # Check created_at equals updated_at (since we copied the values)
        cursor.execute("""
            SELECT COUNT(*) FROM secrets
            WHERE created_at != updated_at
        """)
        assert cursor.fetchone()[0] == 0

        # Check we still have all records
        cursor.execute("SELECT COUNT(*) FROM secrets")
        assert cursor.fetchone()[0] == 3


def test_migrate_database_idempotent(test_db):
    """Test that migration is idempotent (safe to run multiple times)."""
    # Run migration twice
    migrate_database(test_db)
    migrate_database(test_db)  # Should not fail

    with closing(sqlite3.connect(test_db)) as conn:
        cursor = conn.cursor()

        # Should still have the column
        assert check_column_exists(cursor, "secrets", "created_at") is True

        # Should still have all records
        cursor.execute("SELECT COUNT(*) FROM secrets")
        assert cursor.fetchone()[0] == 3


def test_verify_migration_before_migration(test_db):
    """Test verify_migration returns False before migration."""
    assert verify_migration(test_db) is False


def test_verify_migration_after_migration(test_db):
    """Test verify_migration returns True after successful migration."""
    migrate_database(test_db)
    assert verify_migration(test_db) is True


def test_migration_with_empty_table(test_db):
    """Test migration works with empty secrets table."""
    # Clear the secrets table
    with closing(sqlite3.connect(test_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM secrets")
        conn.commit()

    # Run migration
    migrate_database(test_db)

    with closing(sqlite3.connect(test_db)) as conn:
        cursor = conn.cursor()

        # Column should be added even with empty table
        assert check_column_exists(cursor, "secrets", "created_at") is True

        # No records to check
        cursor.execute("SELECT COUNT(*) FROM secrets")
        assert cursor.fetchone()[0] == 0


def test_migration_preserves_data_integrity(test_db):
    """Test that migration preserves all existing data."""
    # Get data before migration
    with closing(sqlite3.connect(test_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT project, path, version, updated_at, updated_by
            FROM secrets ORDER BY path
        """)
        before_data = cursor.fetchall()

    # Run migration
    migrate_database(test_db)

    # Get data after migration
    with closing(sqlite3.connect(test_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT project, path, version, updated_at, updated_by
            FROM secrets ORDER BY path
        """)
        after_data = cursor.fetchall()

    # Data should be unchanged
    assert before_data == after_data