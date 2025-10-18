#!/bin/bash
# Migration script to fix uppercase status values in tasks table
# Issue: TaskStatus enum expects lowercase values, but database has uppercase values

set -e

DB_PATH="/Users/maenokota/share/work/github_kewton/MySwiftAgent/jobqueue/data/jobqueue.db"
BACKUP_PATH="${DB_PATH}.backup.$(date +%Y%m%d_%H%M%S)"

echo "========================================="
echo "Task Status Migration Script"
echo "========================================="
echo ""

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    exit 1
fi

# Backup database
echo "1. Creating backup..."
cp "$DB_PATH" "$BACKUP_PATH"
echo "   ✓ Backup created: $BACKUP_PATH"
echo ""

# Show current status values
echo "2. Current status values:"
sqlite3 "$DB_PATH" "SELECT status, COUNT(*) as count FROM tasks GROUP BY status ORDER BY status;"
echo ""

# Perform migration
echo "3. Migrating uppercase status values to lowercase..."
sqlite3 "$DB_PATH" <<EOF
BEGIN TRANSACTION;

-- Update all uppercase status values to lowercase
UPDATE tasks SET status = 'queued' WHERE status = 'QUEUED';
UPDATE tasks SET status = 'running' WHERE status = 'RUNNING';
UPDATE tasks SET status = 'succeeded' WHERE status = 'SUCCEEDED';
UPDATE tasks SET status = 'failed' WHERE status = 'FAILED';
UPDATE tasks SET status = 'skipped' WHERE status = 'SKIPPED';

COMMIT;
EOF
echo "   ✓ Migration completed"
echo ""

# Show updated status values
echo "4. Updated status values:"
sqlite3 "$DB_PATH" "SELECT status, COUNT(*) as count FROM tasks GROUP BY status ORDER BY status;"
echo ""

# Verify no uppercase values remain
UPPERCASE_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM tasks WHERE status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'SKIPPED');")

if [ "$UPPERCASE_COUNT" -eq 0 ]; then
    echo "========================================="
    echo "✓ Migration successful!"
    echo "========================================="
    echo "All status values are now lowercase."
    echo "Backup saved at: $BACKUP_PATH"
else
    echo "========================================="
    echo "⚠️  Warning: Some uppercase values remain"
    echo "========================================="
    echo "Found $UPPERCASE_COUNT uppercase status values"
    exit 1
fi
