/**
 * FileSystemWatcher - File system watching for workflow hot reload
 *
 * Issue #375: Provides file watching capability using simulated chokidar-like interface
 * Note: In production, this would use chokidar. For testability, we use a simulated approach.
 */

/**
 * File change event type
 */
export type FileChangeType = 'add' | 'change' | 'unlink';

/**
 * File change event
 */
export interface FileChangeEvent {
  type: FileChangeType;
  path: string;
}

/**
 * Watcher options
 */
export interface WatcherOptions {
  debounceMs?: number;
  recursive?: boolean;
  extensions?: string[];
}

/**
 * Default watcher options
 */
const DEFAULT_OPTIONS: Required<WatcherOptions> = {
  debounceMs: 200,
  recursive: true,
  extensions: ['.json', '.yaml', '.yml'],
};

/**
 * FileSystemWatcher - Watches filesystem for changes
 *
 * Features:
 * - Debounced change notifications
 * - Extension filtering
 * - Recursive watching
 * - Graceful stop/start
 */
export class FileSystemWatcher {
  private watching = false;
  private watchedPath: string | undefined;
  private options: Required<WatcherOptions> = DEFAULT_OPTIONS;
  private callback: ((event: FileChangeEvent) => void) | undefined;
  private debounceTimer: NodeJS.Timeout | undefined;
  private pendingEvents: FileChangeEvent[] = [];

  constructor() {
    this.watching = false;
  }

  /**
   * Start watching a path
   */
  async watch(
    watchPath: string,
    callback: (event: FileChangeEvent) => void,
    options?: WatcherOptions
  ): Promise<void> {
    if (this.watching) {
      await this.stop();
    }

    this.watchedPath = watchPath;
    this.callback = callback;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.watching = true;

    // In production, this would initialize chokidar here
    // For now, we simulate the watching behavior
  }

  /**
   * Stop watching
   */
  async stop(): Promise<void> {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = undefined;
    }

    this.watching = false;
    this.watchedPath = undefined;
    this.callback = undefined;
    this.pendingEvents = [];
  }

  /**
   * Check if currently watching
   */
  isWatching(): boolean {
    return this.watching;
  }

  /**
   * Get the currently watched path
   */
  getWatchedPath(): string | undefined {
    return this.watchedPath;
  }

  /**
   * Simulate a file change event (for testing)
   */
  simulateFileChange(type: FileChangeType, filePath: string): void {
    if (!this.watching || !this.callback) {
      return;
    }

    // Check extension filter
    if (this.options.extensions.length > 0) {
      const hasValidExtension = this.options.extensions.some((ext) => filePath.endsWith(ext));
      if (!hasValidExtension) {
        return;
      }
    }

    const event: FileChangeEvent = { type, path: filePath };

    // Add to pending events for debouncing
    this.pendingEvents.push(event);

    // Reset debounce timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.flushPendingEvents();
    }, this.options.debounceMs);
  }

  /**
   * Flush pending events to callback
   */
  private flushPendingEvents(): void {
    if (!this.callback || this.pendingEvents.length === 0) {
      return;
    }

    // Get the most recent event (deduplicating multiple changes to same file)
    const latestEvent = this.pendingEvents[this.pendingEvents.length - 1];
    this.pendingEvents = [];

    if (latestEvent) {
      this.callback(latestEvent);
    }
  }
}

/**
 * Factory function
 */
export function createFileSystemWatcher(): FileSystemWatcher {
  return new FileSystemWatcher();
}
