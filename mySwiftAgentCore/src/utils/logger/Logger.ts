/**
 * Logger - Structured JSON logging utility
 *
 * Issue #370: Structured logging for workflow generation and registration
 *
 * Features:
 * - JSON structured output
 * - Timestamp in ISO format
 * - Log level filtering
 * - Context support
 * - Child logger creation
 */

/**
 * Log levels in order of severity
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

/**
 * Log level priority for filtering
 */
const LOG_LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/**
 * Log entry structure
 */
export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  name: string;
  message: string;
  context?: Record<string, unknown>;
}

/**
 * Logger configuration
 */
export interface LoggerConfig {
  name: string;
  level?: LogLevel;
  defaultContext?: Record<string, unknown>;
}

/**
 * Logger - Structured JSON logging utility
 */
export class Logger {
  private readonly name: string;
  private readonly level: LogLevel;
  private readonly defaultContext: Record<string, unknown>;

  constructor(config: LoggerConfig) {
    this.name = config.name;
    this.level = config.level ?? 'debug';
    this.defaultContext = config.defaultContext ?? {};
  }

  /**
   * Get current log level
   */
  getLevel(): LogLevel {
    return this.level;
  }

  /**
   * Log debug message
   */
  debug(message: string, context?: Record<string, unknown>): void {
    this.log('debug', message, context);
  }

  /**
   * Log info message
   */
  info(message: string, context?: Record<string, unknown>): void {
    this.log('info', message, context);
  }

  /**
   * Log warn message
   */
  warn(message: string, context?: Record<string, unknown>): void {
    this.log('warn', message, context);
  }

  /**
   * Log error message
   */
  error(message: string, context?: Record<string, unknown>): void {
    this.log('error', message, context);
  }

  /**
   * Create child logger with additional context
   */
  child(additionalContext: Record<string, unknown>): Logger {
    return new Logger({
      name: this.name,
      level: this.level,
      defaultContext: { ...this.defaultContext, ...additionalContext },
    });
  }

  /**
   * Internal log method
   */
  private log(level: LogLevel, message: string, context?: Record<string, unknown>): void {
    // Check log level filter
    if (LOG_LEVEL_PRIORITY[level] < LOG_LEVEL_PRIORITY[this.level]) {
      return;
    }

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      name: this.name,
      message,
    };

    // Merge default context with provided context
    const mergedContext = { ...this.defaultContext, ...context };
    if (Object.keys(mergedContext).length > 0) {
      entry.context = mergedContext;
    }

    // Output JSON
    const output = JSON.stringify(entry);

    if (level === 'error') {
      console.error(output);
    } else {
      console.log(output);
    }
  }
}

/**
 * Factory function to create Logger
 */
export function createLogger(config: LoggerConfig): Logger {
  return new Logger(config);
}
