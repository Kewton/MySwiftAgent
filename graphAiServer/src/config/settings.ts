// src/config/settings.ts
import dotenv from 'dotenv';

dotenv.config();

export interface Settings {
  // Server Configuration
  PORT: number;
  NODE_ENV: string;
  MODEL_BASE_PATH: string;

  // MyVault Configuration
  MYVAULT_ENABLED: boolean;
  MYVAULT_BASE_URL: string;
  MYVAULT_SERVICE_NAME: string;
  MYVAULT_SERVICE_TOKEN: string;
  MYVAULT_DEFAULT_PROJECT: string;

  // Secrets Cache Configuration
  SECRETS_CACHE_TTL: number;

  // Admin API Configuration
  ADMIN_TOKEN: string;

  // Fallback Secret Values (for development)
  OPENAI_API_KEY?: string;
  ANTHROPIC_API_KEY?: string;
  GOOGLE_API_KEY?: string;
  GROQ_API_KEY?: string;

  // Index signature for dynamic property access
  [key: string]: string | number | boolean | undefined;
}

export const settings: Settings = {
  PORT: parseInt(process.env.PORT || '8000', 10),
  NODE_ENV: process.env.NODE_ENV || 'development',
  MODEL_BASE_PATH: process.env.MODEL_BASE_PATH || './config/graphai/',

  MYVAULT_ENABLED: process.env.MYVAULT_ENABLED === 'true',
  MYVAULT_BASE_URL: process.env.MYVAULT_BASE_URL || 'http://localhost:8000',
  MYVAULT_SERVICE_NAME: process.env.MYVAULT_SERVICE_NAME || 'graphaiserver-service',
  MYVAULT_SERVICE_TOKEN: process.env.MYVAULT_SERVICE_TOKEN || '',
  MYVAULT_DEFAULT_PROJECT: process.env.MYVAULT_DEFAULT_PROJECT || 'default_project',

  SECRETS_CACHE_TTL: parseInt(process.env.SECRETS_CACHE_TTL || '300', 10),

  ADMIN_TOKEN: process.env.ADMIN_TOKEN || '',

  OPENAI_API_KEY: process.env.OPENAI_API_KEY,
  ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY,
  GOOGLE_API_KEY: process.env.GOOGLE_API_KEY,
  GROQ_API_KEY: process.env.GROQ_API_KEY,
};
