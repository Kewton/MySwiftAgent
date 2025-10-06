#!/usr/bin/env python3
"""Migration script to add is_default column to projects table.

This script adds the is_default boolean column to the projects table
and ensures only one project can be marked as default.
"""

import sqlite3
import sys
from pathlib import Path


def main():
    """Run migration."""
    # Database path
    db_path = Path(__file__).parent.parent / "myvault.db"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        sys.exit(1)

    print(f"📂 Database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in cursor.fetchall()]

        if "is_default" in columns:
            print("✅ Column 'is_default' already exists. Skipping migration.")
            return

        print("🔄 Adding 'is_default' column to projects table...")

        # Add is_default column with default value False
        cursor.execute("""
            ALTER TABLE projects
            ADD COLUMN is_default BOOLEAN NOT NULL DEFAULT 0
        """)

        conn.commit()
        print("✅ Migration completed successfully!")

        # Show current projects
        cursor.execute("SELECT id, name, is_default FROM projects")
        projects = cursor.fetchall()

        if projects:
            print("\n📦 Current projects:")
            for project_id, name, is_default in projects:
                default_marker = "⭐" if is_default else "□"
                print(f"  {default_marker} {name} (id={project_id})")
        else:
            print("\n📦 No projects found.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
