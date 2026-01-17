/**
 * Logger Unit Tests
 *
 * Issue #370: Structured logging utility
 * TDD Phase: Red - Write failing tests first
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  Logger,
  createLogger,
  type LogLevel,
  type LogEntry,
  type LoggerConfig,
} from '../../../../src/utils/logger/Logger.js';

describe('Logger', () => {
  let logger: Logger;
  let consoleOutput: string[];

  beforeEach(() => {
    consoleOutput = [];
    // Mock console methods to capture output
    vi.spyOn(console, 'log').mockImplementation((msg: string) => {
      consoleOutput.push(msg);
    });
    vi.spyOn(console, 'error').mockImplementation((msg: string) => {
      consoleOutput.push(msg);
    });

    logger = createLogger({ name: 'test-logger' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('log levels', () => {
    it('should log debug messages', () => {
      logger.debug('debug message');

      expect(consoleOutput.length).toBe(1);
      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.level).toBe('debug');
      expect(entry.message).toBe('debug message');
    });

    it('should log info messages', () => {
      logger.info('info message');

      expect(consoleOutput.length).toBe(1);
      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.level).toBe('info');
      expect(entry.message).toBe('info message');
    });

    it('should log warn messages', () => {
      logger.warn('warn message');

      expect(consoleOutput.length).toBe(1);
      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.level).toBe('warn');
      expect(entry.message).toBe('warn message');
    });

    it('should log error messages', () => {
      logger.error('error message');

      expect(consoleOutput.length).toBe(1);
      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.level).toBe('error');
      expect(entry.message).toBe('error message');
    });
  });

  describe('structured output', () => {
    it('should include timestamp in ISO format', () => {
      const before = new Date().toISOString();
      logger.info('test');
      const after = new Date().toISOString();

      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.timestamp).toBeDefined();
      expect(entry.timestamp >= before).toBe(true);
      expect(entry.timestamp <= after).toBe(true);
    });

    it('should include logger name', () => {
      logger.info('test');

      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.name).toBe('test-logger');
    });

    it('should include context when provided', () => {
      logger.info('test', { userId: '123', action: 'create' });

      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.context).toEqual({ userId: '123', action: 'create' });
    });

    it('should output valid JSON', () => {
      logger.info('test message', { key: 'value' });

      expect(() => JSON.parse(consoleOutput[0] as string)).not.toThrow();
    });
  });

  describe('log level filtering', () => {
    it('should filter debug messages when level is info', () => {
      const infoLogger = createLogger({ name: 'info-logger', level: 'info' });
      infoLogger.debug('should not appear');
      infoLogger.info('should appear');

      expect(consoleOutput.length).toBe(1);
      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.level).toBe('info');
    });

    it('should filter debug and info messages when level is warn', () => {
      const warnLogger = createLogger({ name: 'warn-logger', level: 'warn' });
      warnLogger.debug('should not appear');
      warnLogger.info('should not appear');
      warnLogger.warn('should appear');

      expect(consoleOutput.length).toBe(1);
      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.level).toBe('warn');
    });

    it('should only log error messages when level is error', () => {
      const errorLogger = createLogger({ name: 'error-logger', level: 'error' });
      errorLogger.debug('should not appear');
      errorLogger.info('should not appear');
      errorLogger.warn('should not appear');
      errorLogger.error('should appear');

      expect(consoleOutput.length).toBe(1);
      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.level).toBe('error');
    });
  });

  describe('child logger', () => {
    it('should create child logger with additional context', () => {
      const childLogger = logger.child({ requestId: 'req-123' });
      childLogger.info('child message');

      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.context?.requestId).toBe('req-123');
    });

    it('should merge parent and child context', () => {
      const parentLogger = createLogger({ name: 'parent', defaultContext: { service: 'api' } });
      const childLogger = parentLogger.child({ requestId: 'req-123' });
      childLogger.info('test');

      const entry = JSON.parse(consoleOutput[0] as string) as LogEntry;
      expect(entry.context?.service).toBe('api');
      expect(entry.context?.requestId).toBe('req-123');
    });
  });
});

describe('createLogger factory', () => {
  beforeEach(() => {
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should create a Logger instance', () => {
    const logger = createLogger({ name: 'test' });
    expect(logger).toBeInstanceOf(Logger);
  });

  it('should use default level of debug', () => {
    const logger = createLogger({ name: 'test' });
    expect(logger.getLevel()).toBe('debug');
  });

  it('should accept custom level', () => {
    const logger = createLogger({ name: 'test', level: 'warn' });
    expect(logger.getLevel()).toBe('warn');
  });
});
