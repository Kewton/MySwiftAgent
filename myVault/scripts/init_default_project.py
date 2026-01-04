#!/usr/bin/env python3
"""Initialize default project in MyVault.

This script creates the 'default_project' if it doesn't exist
and sets it as the default project (is_default=true).

Usage:
    python scripts/init_default_project.py

Environment variables:
    DATABASE_URL: SQLite database URL (default: sqlite:///./data/myvault.db)
"""

import os
import sqlite3
import sys
from pathlib import Path


def get_db_path() -> Path:
    """Get database path from DATABASE_URL or default."""
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./data/myvault.db")
    # Extract path from sqlite URL
    if db_url.startswith("sqlite:///"):
        db_path_str = db_url.replace("sqlite:///", "")
        # Handle relative paths
        if db_path_str.startswith("./"):
            db_path_str = db_path_str[2:]
        return Path(__file__).parent.parent / db_path_str
    return Path(__file__).parent.parent / "data" / "myvault.db"


def main():
    """Initialize default project."""
    db_path = get_db_path()

    print(f"📂 Database: {db_path}")

    if not db_path.exists():
        print(f"⚠️  Database not found at {db_path}")
        print("   This is normal for first-time setup.")
        print("   The database will be created when MyVault starts.")
        print("   Run this script again after starting MyVault.")
        sys.exit(0)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if projects table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='projects'
        """)
        if not cursor.fetchone():
            print("⚠️  Projects table not found.")
            print("   The database schema will be created when MyVault starts.")
            print("   Run this script again after starting MyVault.")
            conn.close()
            sys.exit(0)

        # Check if default_project exists
        cursor.execute("""
            SELECT id, name, is_default FROM projects WHERE name = 'default_project'
        """)
        project = cursor.fetchone()

        if project:
            project_id, name, is_default = project
            if is_default:
                print(f"✅ Project '{name}' already exists and is set as default.")
            else:
                print(f"🔄 Setting project '{name}' as default...")
                # First, unset any existing default
                cursor.execute(
                    "UPDATE projects SET is_default = 0 WHERE is_default = 1"
                )
                # Set default_project as default
                cursor.execute(
                    "UPDATE projects SET is_default = 1 WHERE name = 'default_project'"
                )
                conn.commit()
                print(f"✅ Project '{name}' is now set as default.")
        else:
            print("🔄 Creating 'default_project'...")
            # First, unset any existing default
            cursor.execute("UPDATE projects SET is_default = 0 WHERE is_default = 1")
            # Create default_project
            cursor.execute("""
                INSERT INTO projects (name, description, is_default)
                VALUES ('default_project', 'Default project for storing secrets', 1)
            """)
            conn.commit()
            print("✅ Created 'default_project' and set as default.")

        # Show current projects
        cursor.execute("SELECT id, name, is_default FROM projects ORDER BY name")
        projects = cursor.fetchall()

        print("\n📦 Current projects:")
        for _project_id, name, is_default in projects:
            default_marker = "⭐ (default)" if is_default else ""
            print(f"  - {name} {default_marker}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
