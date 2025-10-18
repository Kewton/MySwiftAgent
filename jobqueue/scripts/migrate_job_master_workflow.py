"""
Migration script to add workflow support to JobMaster.

Changes:
1. Create job_master_tasks table for workflow task associations
2. Add input_interface_id and output_interface_id columns to job_masters table

Run: uv run python -m scripts.migrate_job_master_workflow
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# Database paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "jobqueue.db"
BACKUP_DIR = BASE_DIR / "data" / "backups"


def create_backup() -> Path:
    """Create database backup."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"jobqueue.db.backup.{timestamp}"
    shutil.copy(DB_PATH, backup_path)
    return backup_path


def migrate() -> None:
    """Execute database migration."""
    print("=" * 80)
    print("🚀 JobMaster Workflow Migration")
    print("=" * 80)
    print(f"⏰ Timestamp: {datetime.now().isoformat()}\n")

    # Check if database exists
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Please ensure JobQueue is initialized first.")
        return

    # Create backup
    print("📦 Step 1: Creating database backup...")
    try:
        backup_path = create_backup()
        print(f"   ✅ Backup created: {backup_path}\n")
    except Exception as e:
        print(f"   ❌ Backup failed: {e}")
        return

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Step 2: Create job_master_tasks table
        print("📝 Step 2: Creating job_master_tasks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_master_tasks (
                id TEXT PRIMARY KEY,
                job_master_id TEXT NOT NULL,
                task_master_id TEXT NOT NULL,
                "order" INTEGER NOT NULL,
                input_data_template TEXT,
                is_required INTEGER DEFAULT 1,
                retry_on_failure INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_master_id) REFERENCES job_masters(id) ON DELETE CASCADE,
                FOREIGN KEY (task_master_id) REFERENCES task_masters(id),
                UNIQUE(job_master_id, "order"),
                UNIQUE(job_master_id, task_master_id)
            );
        """)
        print("   ✅ Table 'job_master_tasks' created")

        # Create indexes
        print("   Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_master_tasks_job_master_id
            ON job_master_tasks(job_master_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_master_tasks_order
            ON job_master_tasks(job_master_id, "order");
        """)
        print("   ✅ Indexes created\n")

        # Step 3: Add columns to job_masters
        print("📝 Step 3: Adding columns to job_masters table...")

        # Check existing columns
        cursor.execute("PRAGMA table_info(job_masters)")
        columns = {col[1] for col in cursor.fetchall()}

        added_columns = []

        if "input_interface_id" not in columns:
            cursor.execute("""
                ALTER TABLE job_masters ADD COLUMN input_interface_id TEXT;
            """)
            added_columns.append("input_interface_id")
            print("   ✅ Added column: input_interface_id")
        else:
            print("   ⏭️  Column already exists: input_interface_id")

        if "output_interface_id" not in columns:
            cursor.execute("""
                ALTER TABLE job_masters ADD COLUMN output_interface_id TEXT;
            """)
            added_columns.append("output_interface_id")
            print("   ✅ Added column: output_interface_id")
        else:
            print("   ⏭️  Column already exists: output_interface_id")

        if added_columns:
            print(f"   ✅ Added {len(added_columns)} new column(s)\n")
        else:
            print("   ℹ️  No new columns added (already exist)\n")

        # Commit changes
        conn.commit()

        # Step 4: Verify migration
        print("🔍 Step 4: Verifying migration...")

        # Check job_master_tasks table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='job_master_tasks';
        """)
        if cursor.fetchone():
            print("   ✅ Table 'job_master_tasks' exists")
        else:
            raise Exception("Table 'job_master_tasks' not found")

        # Check job_masters columns
        cursor.execute("PRAGMA table_info(job_masters)")
        columns = {col[1] for col in cursor.fetchall()}

        required_columns = {"input_interface_id", "output_interface_id"}
        if required_columns.issubset(columns):
            print("   ✅ All required columns exist in 'job_masters'")
        else:
            missing = required_columns - columns
            raise Exception(f"Missing columns: {missing}")

        # Check indexes
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name='job_master_tasks';
        """)
        indexes = {row[0] for row in cursor.fetchall()}
        expected_indexes = {
            "idx_job_master_tasks_job_master_id",
            "idx_job_master_tasks_order",
        }
        if expected_indexes.issubset(indexes):
            print("   ✅ All indexes created successfully\n")
        else:
            print("   ⚠️  Some indexes may be missing\n")

        # Summary
        print("=" * 80)
        print("✅ Migration completed successfully!")
        print("=" * 80)
        print("\n📊 Summary:")
        print("   - job_master_tasks table: Created")
        print("   - job_masters.input_interface_id: Added")
        print("   - job_masters.output_interface_id: Added")
        print("   - Indexes: Created (2)")
        print(f"\n📦 Backup: {backup_path}")
        print()

    except Exception as e:
        conn.rollback()
        print("\n" + "=" * 80)
        print("❌ Migration failed!")
        print("=" * 80)
        print(f"\nError: {e}")
        print("\n🔄 Database has been rolled back.")
        print(f"📦 You can restore from backup: {backup_path}")
        print()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
