import dotenv from 'dotenv';
import app from './app.js';

// Load environment variables
dotenv.config();

// Override console.log to include timestamp
const originalLog = console.log;
const originalError = console.error;

console.log = (...args: any[]) => {
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
  originalLog(`[${timestamp}]`, ...args);
};

console.error = (...args: any[]) => {
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
  originalError(`[${timestamp}]`, ...args);
};

const PORT = process.env.PORT || 8000;

app.listen(PORT, () => {
  console.log(`🚀 Graph AI Server is running on port ${PORT}`);
});
