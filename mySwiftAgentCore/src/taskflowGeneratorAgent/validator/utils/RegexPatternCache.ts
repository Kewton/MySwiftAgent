/**
 * RegexPatternCache - Pre-compiled regex pattern cache for validation
 *
 * Issue #381: Implements Singleton/Flyweight Pattern for regex caching
 *
 * Features:
 * - Singleton pattern for global cache instance
 * - Flyweight pattern for sharing compiled regex patterns
 * - Returns new RegExp instances to prevent lastIndex conflicts
 */

/**
 * RegexPatternCache - Singleton cache for pre-compiled regex patterns
 */
export class RegexPatternCache {
  private static instance: RegexPatternCache;
  private readonly patterns: Map<string, RegExp>;

  /**
   * Private constructor - use getInstance() to get the singleton
   */
  private constructor() {
    this.patterns = new Map<string, RegExp>();
    this.initializePatterns();
  }

  /**
   * Get the singleton instance
   */
  static getInstance(): RegexPatternCache {
    if (!RegexPatternCache.instance) {
      RegexPatternCache.instance = new RegexPatternCache();
    }
    return RegexPatternCache.instance;
  }

  /**
   * Initialize pre-compiled patterns
   */
  private initializePatterns(): void {
    // Step reference pattern: $steps.<step_id>.<field_name>
    // step_id: starts with letter or underscore, followed by alphanumeric, underscore, or hyphen
    // field_name: starts with letter or underscore, followed by alphanumeric or underscore
    this.patterns.set(
      'stepReference',
      /\$steps\.([a-zA-Z_][a-zA-Z0-9_-]*)\.([a-zA-Z_][a-zA-Z0-9_]*)/g
    );

    // Mustache template pattern: {{expression}}
    this.patterns.set('mustache', /\{\{([^}]+)\}\}/g);

    // JSON path pattern: $.steps, $.input, $.env
    this.patterns.set('jsonPath', /\$\.(steps|input|env)/g);

    // Mixed pattern: mustache with JSON path inside {{$.expression}}
    this.patterns.set('mixed', /\{\{\$\.([^}]+)\}\}/g);

    // Unclosed mustache detection: {{ without matching }}
    this.patterns.set('unclosedMustache', /\{\{(?![^{]*\}\})/g);

    // Unmatched closing braces: }} without preceding {{
    this.patterns.set('unmatchedClosing', /(?<!\{\{[^}]*)\}\}/g);

    // Empty mustache: {{}}
    this.patterns.set('emptyMustache', /\{\{\s*\}\}/g);

    // Nested mustache: {{{{ or }}}}
    this.patterns.set('nestedMustache', /\{\{\{\{|\}\}\}\}/g);

    // Invalid JSON path prefix: $ followed by something other than steps, input, env
    this.patterns.set(
      'invalidJsonPath',
      /\$\.(?!steps|input|env)[a-zA-Z_][a-zA-Z0-9_]*/g
    );

    // Incomplete step reference: $steps. followed by nothing or incomplete
    this.patterns.set('incompleteStepRef', /\$steps\.(?![a-zA-Z_][a-zA-Z0-9_-]*\.)/g);
  }

  /**
   * Get a pattern by name
   *
   * Returns a NEW RegExp instance to prevent lastIndex conflicts
   * when using the same pattern in concurrent operations.
   *
   * @param name - Pattern name
   * @returns New RegExp instance or undefined if not found
   */
  getPattern(name: string): RegExp | undefined {
    const pattern = this.patterns.get(name);
    if (!pattern) {
      return undefined;
    }
    // Return a new RegExp instance with the same source and flags
    // This prevents lastIndex conflicts in concurrent usage
    return new RegExp(pattern.source, pattern.flags);
  }

  /**
   * Get all available pattern names
   *
   * @returns Array of pattern names
   */
  getAllPatternNames(): string[] {
    return Array.from(this.patterns.keys());
  }

  /**
   * Check if a pattern exists
   *
   * @param name - Pattern name to check
   * @returns true if pattern exists
   */
  hasPattern(name: string): boolean {
    return this.patterns.has(name);
  }
}
