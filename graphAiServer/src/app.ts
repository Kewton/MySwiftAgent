import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { runGraphAI, testGraphAI } from './services/graphai.js';

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
    const result = await testGraphAI();
    console.log("GraphAI sample finished.");
    res.json(result);
  } catch (error) {
    console.error("Error executing GraphAI sample:", error);
    res.status(500).json({ error: 'An error occurred while executing the GraphAI sample.' });
  }
});

// GraphAI agent endpoint
app.post('/api/v1/myagent', async (req: Request, res: Response) => {
  const { user_input, model_name } = req.body;

  if (!user_input) {
    return res.status(400).json({ error: 'user_input is required' });
  }

  if (!model_name) {
    return res.status(400).json({ error: 'model_name is required' });
  }

  try {
    const result = await runGraphAI(user_input, model_name);
    res.json(result);
  } catch (error) {
    console.error("Error executing GraphAI sample:", error);
    res.status(500).json({ error: 'An error occurred while executing the GraphAI sample.' });
  }
});

export default app;
