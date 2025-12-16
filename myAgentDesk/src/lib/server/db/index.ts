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
