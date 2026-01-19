/**
 * FileSystemWatcher Unit Tests
 *
 * Issue #375: File system watching for workflow hot reload
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { FileSystemWatcher } from '../../../../src/taskflowEngine/watcher/FileSystemWatcher.js';

describe('FileSystemWatcher', () => {
  let watcher: FileSystemWatcher;
  const testPath = '/tmp/test-workflows';

  beforeEach(() => {
    watcher = new FileSystemWatcher();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    watcher.stop();
  });

  describe('constructor', () => {
    it('should create watcher instance', () => {
      expect(watcher).toBeInstanceOf(FileSystemWatcher);
    });

    it('should not be watching initially', () => {
      expect(watcher.isWatching()).toBe(false);
    });
  });

  describe('watch', () => {
    it('should start watching specified path', async () => {
      const callback = vi.fn();
      await watcher.watch(testPath, callback);

      expect(watcher.isWatching()).toBe(true);
    });

    it('should accept options', async () => {
      const callback = vi.fn();
      await watcher.watch(testPath, callback, {
        debounceMs: 500,
        recursive: true,
        extensions: ['.json', '.yaml'],
      });

      expect(watcher.isWatching()).toBe(true);
    });
  });

  describe('stop', () => {
    it('should stop watching', async () => {
      const callback = vi.fn();
      await watcher.watch(testPath, callback);

      expect(watcher.isWatching()).toBe(true);

      await watcher.stop();

      expect(watcher.isWatching()).toBe(false);
    });

    it('should handle stop when not watching', async () => {
      await expect(watcher.stop()).resolves.not.toThrow();
    });
  });

  describe('callback invocation', () => {
    it('should call callback with file path on change', async () => {
      const callback = vi.fn();
      await watcher.watch(testPath, callback);

      // Simulate file change
      watcher.simulateFileChange('add', '/tmp/test-workflows/workflow.json');

      // Fast-forward past debounce
      vi.advanceTimersByTime(300);

      expect(callback).toHaveBeenCalledWith({
        type: 'add',
        path: '/tmp/test-workflows/workflow.json',
      });
    });

    it('should debounce rapid changes', async () => {
      const callback = vi.fn();
      await watcher.watch(testPath, callback, { debounceMs: 200 });

      // Simulate multiple rapid changes
      watcher.simulateFileChange('change', '/tmp/test-workflows/workflow.json');
      vi.advanceTimersByTime(50);
      watcher.simulateFileChange('change', '/tmp/test-workflows/workflow.json');
      vi.advanceTimersByTime(50);
      watcher.simulateFileChange('change', '/tmp/test-workflows/workflow.json');

      // Should not have called yet
      expect(callback).not.toHaveBeenCalled();

      // Fast-forward past debounce
      vi.advanceTimersByTime(250);

      // Should have been called only once
      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should filter by extension', async () => {
      const callback = vi.fn();
      await watcher.watch(testPath, callback, {
        extensions: ['.json'],
      });

      // Simulate change to non-json file
      watcher.simulateFileChange('add', '/tmp/test-workflows/workflow.txt');
      vi.advanceTimersByTime(300);

      expect(callback).not.toHaveBeenCalled();

      // Simulate change to json file
      watcher.simulateFileChange('add', '/tmp/test-workflows/workflow.json');
      vi.advanceTimersByTime(300);

      expect(callback).toHaveBeenCalled();
    });
  });

  describe('getWatchedPath', () => {
    it('should return the watched path', async () => {
      const callback = vi.fn();
      await watcher.watch(testPath, callback);

      expect(watcher.getWatchedPath()).toBe(testPath);
    });

    it('should return undefined when not watching', () => {
      expect(watcher.getWatchedPath()).toBeUndefined();
    });
  });
});
