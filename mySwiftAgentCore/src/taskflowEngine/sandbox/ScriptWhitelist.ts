/**
 * ScriptWhitelist - Manage allowed scripts for code_js execution
 *
 * Issue #363: Security whitelist for JavaScript execution
 */

import * as path from 'path';

/**
 * Whitelist entry for a script
 */
export interface ScriptWhitelistEntry {
  path: string;
  hash: string;
  description?: string;
}

/**
 * ScriptWhitelist - Manages allowed scripts for sandbox execution
 *
 * Features:
 * - Add/remove scripts from whitelist
 * - Path traversal detection
 * - Hash verification support
 */
export class ScriptWhitelist {
  private readonly entries: Map<string, ScriptWhitelistEntry>;

  constructor() {
    this.entries = new Map();
  }

  /**
   * Add a script to the whitelist
   *
   * @param entry - The whitelist entry
   */
  add(entry: ScriptWhitelistEntry): void {
    const normalized = this.normalizePath(entry.path);
    this.entries.set(normalized, {
      ...entry,
      path: normalized,
    });
  }

  /**
   * Remove a script from the whitelist
   *
   * @param scriptPath - Path to the script
   * @returns true if removed, false if not found
   */
  remove(scriptPath: string): boolean {
    const normalized = this.normalizePath(scriptPath);
    return this.entries.delete(normalized);
  }

  /**
   * Check if a script is whitelisted
   *
   * Also performs path traversal detection.
   *
   * @param scriptPath - Path to the script
   * @returns true if whitelisted and safe
   */
  isWhitelisted(scriptPath: string): boolean {
    if (this.hasPathTraversal(scriptPath)) {
      return false;
    }

    const normalized = this.normalizePath(scriptPath);
    return this.entries.has(normalized);
  }

  /**
   * Get the hash for a whitelisted script
   *
   * @param scriptPath - Path to the script
   * @returns The hash if found, undefined otherwise
   */
  getHash(scriptPath: string): string | undefined {
    const normalized = this.normalizePath(scriptPath);
    return this.entries.get(normalized)?.hash;
  }

  /**
   * Get the full entry for a whitelisted script
   *
   * @param scriptPath - Path to the script
   * @returns The entry if found, undefined otherwise
   */
  getEntry(scriptPath: string): ScriptWhitelistEntry | undefined {
    const normalized = this.normalizePath(scriptPath);
    return this.entries.get(normalized);
  }

  /**
   * List all whitelist entries
   *
   * @returns Array of all entries
   */
  listAll(): ScriptWhitelistEntry[] {
    return Array.from(this.entries.values());
  }

  /**
   * Clear all entries
   */
  clear(): void {
    this.entries.clear();
  }

  /**
   * Get the number of entries
   */
  size(): number {
    return this.entries.size;
  }

  /**
   * Normalize a path for consistent comparison
   */
  private normalizePath(scriptPath: string): string {
    // Remove leading ./ if present
    let normalized = scriptPath.replace(/^\.\//, '');
    // Normalize path separators
    normalized = path.normalize(normalized);
    return normalized;
  }

  /**
   * Detect path traversal attempts
   */
  private hasPathTraversal(scriptPath: string): boolean {
    return scriptPath.includes('..');
  }
}

/**
 * Factory function to create ScriptWhitelist
 */
export function createScriptWhitelist(
  initialEntries?: ScriptWhitelistEntry[]
): ScriptWhitelist {
  const whitelist = new ScriptWhitelist();

  if (initialEntries) {
    for (const entry of initialEntries) {
      whitelist.add(entry);
    }
  }

  return whitelist;
}
