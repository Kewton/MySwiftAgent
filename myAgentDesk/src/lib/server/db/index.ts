import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from './schema';

// Database file path - uses environment variable or default to local.db
const DATABASE_PATH = process.env.DATABASE_URL || './data/local.db';

// Create SQLite database instance
const sqlite = new Database(DATABASE_PATH);

// Enable foreign keys for referential integrity
sqlite.pragma('foreign_keys = ON');

// Create drizzle instance with schema
export const db = drizzle(sqlite, { schema });

// Export the raw sqlite instance for direct access if needed
export { sqlite };

// Export all schema definitions and types
export * from './schema';
