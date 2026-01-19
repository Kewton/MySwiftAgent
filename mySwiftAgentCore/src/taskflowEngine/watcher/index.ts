/**
 * Watcher module exports
 *
 * Issue #375: File system watcher for workflow hot reload
 */

export {
  FileSystemWatcher,
  createFileSystemWatcher,
  type FileChangeEvent,
  type FileChangeType,
  type WatcherOptions,
} from './FileSystemWatcher.js';
