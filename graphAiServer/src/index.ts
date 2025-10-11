import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import app from './app.js';

// Load environment variables from graphAiServer/.env (new policy)
// Note: override=false respects existing environment variables set by quick-start.sh or docker-compose
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const envPath = path.join(projectRoot, '.env');

dotenv.config({ path: envPath, override: false });

// Setup file logging
const LOG_DIR = process.env.LOG_DIR || './';
const logDir = path.resolve(LOG_DIR);
const logFile = path.join(logDir, 'app.log');

// Create log directory if it doesn't exist
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

// Function to write to log file
const writeToLogFile = (message: string) => {
  try {
    fs.appendFileSync(logFile, message + '\n', 'utf8');
  } catch (error) {
    // Silently fail to avoid infinite loops
  }
};

// Override console.log to include timestamp and write to file
const originalLog = console.log;
const originalError = console.error;

console.log = (...args: any[]) => {
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
  const message = `[${timestamp}] ${args.join(' ')}`;
  originalLog(message);
  writeToLogFile(message);
};

console.error = (...args: any[]) => {
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
  const message = `[${timestamp}] ERROR: ${args.join(' ')}`;
  originalError(message);
  writeToLogFile(message);
};

const PORT = process.env.PORT || 8000;

console.log(`Logging configured: log_dir=${logDir}, log_file=${logFile}`);

app.listen(PORT, () => {
  console.log(`🚀 Graph AI Server is running on port ${PORT}`);
});
