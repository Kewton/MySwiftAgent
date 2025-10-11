import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { runGraphAI, testGraphAI, GraphAIResponse } from './services/graphai.js';
import { secretsManager } from './services/secretsManager.js';
import { settings } from './config/settings.js';

const app = express();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Health check endpoint (required for CI/CD)
app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'graphAiServer' });
});

// Root endpoint
app.get('/', (_req: Request, res: Response) => {
  res.json({ message: 'Welcome to Graph AI Server' });
});

// API v1 root
app.get('/api/v1/', (_req: Request, res: Response) => {
  res.json({ version: '1.0', service: 'graphAiServer' });
});

// GraphAI test endpoint
app.get('/api/v1/test', async (_req: Request, res: Response) => {
  try {
    console.log("Executing GraphAI sample...");
    const result: GraphAIResponse = await testGraphAI();
    console.log("GraphAI sample finished.");

    // Check if there are any errors in the execution
    const hasErrors = Object.keys(result.errors).length > 0;
    const hasTimedOutNodes = result.logs.some(log => log.state === 'timed-out');

    if (hasErrors || hasTimedOutNodes) {
      // Return 500 if there are errors or timeouts, but include full details
      res.status(500).json(result);
    } else {
      // Return 200 for successful execution
      res.json(result);
    }
  } catch (error) {
    console.error("Error executing GraphAI sample:", error);

    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;

    res.status(500).json({
      error: 'An error occurred while executing the GraphAI sample.',
      details: {
        message: errorMessage,
        type: errorMessage.includes('Timeout') ? 'timeout' : 'initialization_error',
        timestamp: new Date().toISOString(),
      },
      ...(process.env.NODE_ENV !== 'production' && { stack: errorStack })
    });
  }
});

// GraphAI agent endpoint with path parameters (new format)
app.post('/api/v1/myagent/:category/:model', async (req: Request, res: Response) => {
  const { user_input, project } = req.body;
  const { category, model } = req.params;

  if (!user_input) {
    return res.status(400).json({ error: 'user_input is required' });
  }

  // Path traversal security validation
  if (category.includes('..') || category.includes('/') || category.includes('\\')) {
    return res.status(400).json({ error: 'Invalid category parameter' });
  }

  if (model.includes('..') || model.includes('/') || model.includes('\\')) {
    return res.status(400).json({ error: 'Invalid model parameter' });
  }

  try {
    // Construct model_name from category and model
    const model_name = `${category}/${model}`;

    const result: GraphAIResponse = await runGraphAI(user_input, model_name, project);

    // Check if there are any errors in the execution
    const hasErrors = Object.keys(result.errors).length > 0;
    const hasTimedOutNodes = result.logs.some(log => log.state === 'timed-out');

    if (hasErrors || hasTimedOutNodes) {
      // Return 500 if there are errors or timeouts, but include full details
      res.status(500).json(result);
    } else {
      // Return 200 for successful execution
      res.json(result);
    }
  } catch (error) {
    console.error("Error executing GraphAI sample:", error);

    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;

    res.status(500).json({
      error: 'An error occurred while executing the GraphAI sample.',
      details: {
        message: errorMessage,
        type: errorMessage.includes('Timeout') ? 'timeout' : 'initialization_error',
        timestamp: new Date().toISOString(),
      },
      ...(process.env.NODE_ENV !== 'production' && { stack: errorStack })
    });
  }
});

// GraphAI agent endpoint (legacy format for backward compatibility)
app.post('/api/v1/myagent', async (req: Request, res: Response) => {
  const { user_input, model_name, project } = req.body;

  if (!user_input) {
    return res.status(400).json({ error: 'user_input is required' });
  }

  if (!model_name) {
    return res.status(400).json({ error: 'model_name is required' });
  }

  try {
    const result: GraphAIResponse = await runGraphAI(user_input, model_name, project);

    // Check if there are any errors in the execution
    const hasErrors = Object.keys(result.errors).length > 0;
    const hasTimedOutNodes = result.logs.some(log => log.state === 'timed-out');

    if (hasErrors || hasTimedOutNodes) {
      // Return 500 if there are errors or timeouts, but include full details
      res.status(500).json(result);
    } else {
      // Return 200 for successful execution
      res.json(result);
    }
  } catch (error) {
    console.error("Error executing GraphAI sample:", error);

    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;

    res.status(500).json({
      error: 'An error occurred while executing the GraphAI sample.',
      details: {
        message: errorMessage,
        type: errorMessage.includes('Timeout') ? 'timeout' : 'initialization_error',
        timestamp: new Date().toISOString(),
      },
      ...(process.env.NODE_ENV !== 'production' && { stack: errorStack })
    });
  }
});

// Admin token middleware
const requireAdminToken = (req: Request, res: Response, next: Function) => {
  const token = req.headers['x-admin-token'];
  if (!settings.ADMIN_TOKEN || token !== settings.ADMIN_TOKEN) {
    return res.status(403).json({ error: 'Invalid admin token' });
  }
  next();
};

// Admin health check
app.get('/api/v1/admin/health', (_req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'graphaiserver-admin' });
});

// Cache reload endpoint
app.post('/api/v1/admin/reload-secrets', requireAdminToken, (req: Request, res: Response) => {
  try {
    const { project } = req.body;
    secretsManager.clearCache(project);
    res.json({
      success: true,
      message: project ? `Cache cleared for project: ${project}` : 'All cache cleared',
    });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

export default app;
