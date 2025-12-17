/**
 * Database configuration and connection module for myAgentDesk.
 *
 * This module provides the main database instance using Drizzle ORM with better-sqlite3.
 * It handles database initialization, foreign key enforcement, and exports the
 * database instance for use throughout the application.
 *
 * @module db
 */
import Database from 'better-sqlite3';
import { drizzle, type BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import * as schema from './schema';

/** Default path for the SQLite database file */
const DEFAULT_DATABASE_PATH = './data/local.db';

/**
 * Database file path.
 * Uses DATABASE_URL environment variable if set, otherwise defaults to local.db
 */
const DATABASE_PATH = process.env.DATABASE_URL || DEFAULT_DATABASE_PATH;

/**
 * Raw SQLite database instance created with better-sqlite3.
 * This is the underlying database connection used by Drizzle ORM.
 */
const sqlite = new Database(DATABASE_PATH);

// Enable foreign keys for referential integrity
sqlite.pragma('foreign_keys = ON');

/**
 * Initialize database schema if tables don't exist.
 * This allows the application to work without requiring manual db:push.
 */
function initializeSchema() {
	// Check if project table exists
	const tableExists = sqlite
		.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='project'")
		.get();

	if (!tableExists) {
		console.log('[DB] Tables not found. Initializing schema...');

		// Create tables in order (respecting foreign key dependencies)
		sqlite.exec(`
			CREATE TABLE IF NOT EXISTS project (
				id TEXT PRIMARY KEY NOT NULL,
				external_project_id TEXT NOT NULL UNIQUE,
				name TEXT NOT NULL,
				description TEXT,
				last_synced_at INTEGER,
				created_at INTEGER NOT NULL,
				updated_at INTEGER NOT NULL
			);

			CREATE TABLE IF NOT EXISTS workbench (
				id TEXT PRIMARY KEY NOT NULL,
				project_id TEXT NOT NULL REFERENCES project(id),
				name TEXT NOT NULL,
				description TEXT,
				status TEXT NOT NULL DEFAULT 'draft',
				active_requirement_version_id TEXT,
				external_job_master_id TEXT,
				created_at INTEGER NOT NULL,
				updated_at INTEGER NOT NULL
			);

			CREATE TABLE IF NOT EXISTS requirement_version (
				id TEXT PRIMARY KEY NOT NULL,
				workbench_id TEXT NOT NULL REFERENCES workbench(id),
				version INTEGER NOT NULL,
				content TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'draft',
				change_summary TEXT,
				created_at INTEGER NOT NULL,
				updated_at INTEGER NOT NULL,
				UNIQUE(workbench_id, version)
			);

			CREATE TABLE IF NOT EXISTS job_version (
				id TEXT PRIMARY KEY NOT NULL,
				workbench_id TEXT NOT NULL REFERENCES workbench(id),
				source_requirement_version_id TEXT NOT NULL REFERENCES requirement_version(id),
				major_version INTEGER NOT NULL,
				minor_version INTEGER NOT NULL,
				version_label TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'generating',
				task_breakdown TEXT,
				interface_definitions TEXT,
				workflows TEXT,
				external_job_master_id TEXT,
				external_trace_id TEXT,
				error_message TEXT,
				generated_at INTEGER,
				created_at INTEGER NOT NULL,
				updated_at INTEGER NOT NULL,
				UNIQUE(workbench_id, major_version, minor_version)
			);

			CREATE TABLE IF NOT EXISTS run (
				id TEXT PRIMARY KEY NOT NULL,
				workbench_id TEXT NOT NULL REFERENCES workbench(id),
				job_version_id TEXT NOT NULL REFERENCES job_version(id),
				status TEXT NOT NULL DEFAULT 'queued',
				external_job_id TEXT,
				external_trace_id TEXT,
				execution_params TEXT,
				result_summary TEXT,
				started_at INTEGER,
				completed_at INTEGER,
				created_at INTEGER NOT NULL,
				updated_at INTEGER NOT NULL
			);

			CREATE TABLE IF NOT EXISTS schedule (
				id TEXT PRIMARY KEY NOT NULL,
				workbench_id TEXT NOT NULL REFERENCES workbench(id),
				target_job_version_id TEXT NOT NULL REFERENCES job_version(id),
				name TEXT NOT NULL,
				cron_expression TEXT NOT NULL,
				is_enabled INTEGER NOT NULL DEFAULT 1,
				external_scheduler_id TEXT,
				execution_params TEXT,
				next_run_at INTEGER,
				last_run_at INTEGER,
				created_at INTEGER NOT NULL,
				updated_at INTEGER NOT NULL
			);
		`);

		console.log('[DB] Schema initialized successfully.');
	}
}

// Initialize schema on module load
initializeSchema();

/**
 * Drizzle ORM database instance with full schema type information.
 * Use this for all database operations in the application.
 *
 * @example
 * ```typescript
 * import { db, project } from '$lib/server/db';
 *
 * // Query all projects
 * const projects = await db.select().from(project);
 *
 * // Insert a new project
 * await db.insert(project).values({
 *   id: 'proj_001',
 *   externalProjectId: 'ext_001',
 *   name: 'My Project',
 *   createdAt: new Date(),
 *   updatedAt: new Date()
 * });
 * ```
 */
export const db: BetterSQLite3Database<typeof schema> = drizzle(sqlite, { schema });

/**
 * Raw SQLite database instance for direct access when needed.
 * Use sparingly - prefer the Drizzle `db` instance for type-safe operations.
 */
export { sqlite };

// Export all schema definitions and types
export * from './schema';
