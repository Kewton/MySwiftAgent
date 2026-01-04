#!/usr/bin/env python3
"""Migration script to add created_at column to secrets table.

This script adds the missing created_at column to the secrets table
and populates it with the existing updated_at values for backward compatibility.
"""

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    return any(col[1] == column for col in columns)


def migrate_database(db_path: str) -> None:
    """Add created_at column to secrets table if it doesn't exist.

    Args:
        db_path: Path to the SQLite database file
    """
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()

        # Check if created_at column already exists
        if check_column_exists(cursor, "secrets", "created_at"):
            print("✅ created_at column already exists in secrets table")
            return

        print("📝 Adding created_at column to secrets table...")

        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            # Add created_at column with a temporary default
            cursor.execute("""
                ALTER TABLE secrets
                ADD COLUMN created_at DATETIME
            """)

            # Update created_at with values from updated_at for existing records
            cursor.execute("""
                UPDATE secrets
                SET created_at = updated_at
                WHERE created_at IS NULL
            """)

            # Verify the migration
            cursor.execute("SELECT COUNT(*) FROM secrets WHERE created_at IS NULL")
            null_count = cursor.fetchone()[0]

            if null_count > 0:
                raise Exception(
                    f"Migration failed: {null_count} records have NULL created_at"
                )

            # Commit transaction
            conn.commit()

            # Verify column was added
            if check_column_exists(cursor, "secrets", "created_at"):
                cursor.execute("SELECT COUNT(*) FROM secrets")
                total_count = cursor.fetchone()[0]
                print(
                    f"✅ Successfully added created_at column to {total_count} records"
                )
            else:
                raise Exception("Column was not added successfully")

        except Exception as e:
            conn.rollback()
            print(f"❌ Migration failed: {e}")
            raise


def verify_migration(db_path: str) -> bool:
    """Verify that the migration was successful.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        True if migration is verified, False otherwise
    """
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()

        # Check column exists
        if not check_column_exists(cursor, "secrets", "created_at"):
            print("❌ created_at column not found")
            return False

        # Check no NULL values
        cursor.execute("SELECT COUNT(*) FROM secrets WHERE created_at IS NULL")
        null_count = cursor.fetchone()[0]
        if null_count > 0:
            print(f"❌ Found {null_count} records with NULL created_at")
            return False

        # Check created_at <= updated_at for all records
        cursor.execute("""
            SELECT COUNT(*) FROM secrets
            WHERE created_at > updated_at
        """)
        invalid_count = cursor.fetchone()[0]
        if invalid_count > 0:
            print(f"❌ Found {invalid_count} records where created_at > updated_at")
            return False

        print("✅ Migration verified successfully")
        return True


def main():
    """Main entry point for the migration script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add created_at column to secrets table"
    )
    parser.add_argument(
        "--db-path",
        default="/app/data/myvault.db",
        help="Path to the SQLite database file (default: /app/data/myvault.db)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify the migration without making changes",
    )

    args = parser.parse_args()

    # Check if database file exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"❌ Database file not found: {db_path}")
        sys.exit(1)

    try:
        if args.verify_only:
            success = verify_migration(str(db_path))
            sys.exit(0 if success else 1)
        else:
            migrate_database(str(db_path))
            success = verify_migration(str(db_path))
            sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
