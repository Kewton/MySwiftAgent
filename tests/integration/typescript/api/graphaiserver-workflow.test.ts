/**
 * GraphAI Server Workflow Registration Integration Tests
 *
 * Migrated from: graphAiServer/tests/integration/workflow.test.ts
 * Framework: Jest -> Vitest
 *
 * Note: These tests run from tests/integration/typescript/ directory,
 * so workflow files are created relative to that directory.
 * We verify the file path returned by the API response.
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import request from 'supertest';
import fs from 'fs';
import path from 'path';
import app from '../../../../graphAiServer/src/app.js';
import { createFileCleanup, YAML_TEMPLATES } from '../helpers/test-utils.js';

// The workflow directory that will be created during tests (relative to cwd)
// Since app uses process.cwd(), and tests run from tests/integration/typescript/,
// workflows are created in tests/integration/typescript/config/graphai/
const WORKFLOW_DIR = path.resolve(process.cwd(), 'config/graphai');

// Create file cleanup manager with tracked workflow names
const fileCleanup = createFileCleanup({ baseDir: WORKFLOW_DIR, extension: '.yml' });

// Track all test workflow names for cleanup
const TEST_WORKFLOW_NAMES = [
  'test_workflow',
  'test_overwrite',
  'test_special_chars',
  'test-workflow_123',
  'complex_workflow',
  'test_workflow_conflict',
];
TEST_WORKFLOW_NAMES.forEach((name) => fileCleanup.track(name));

describe('POST /api/v1/workflows/register', () => {
  // Clean up before all tests to ensure a clean state
  beforeAll(() => {
    fileCleanup.cleanup();
  });

  // Clean up after each test to prevent conflicts between tests
  afterEach(() => {
    fileCleanup.cleanup();
  });

  // Final cleanup after all tests
  afterAll(() => {
    fileCleanup.cleanup();
    fileCleanup.cleanupDirectory();
  });

  describe('Success cases', () => {
    it('should register a valid workflow', async () => {
      const yamlContent = YAML_TEMPLATES.simple('Hello World');
      const requestBody = {
        workflow_name: 'test_workflow',
        yaml_content: yamlContent,
      };

      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send(requestBody);

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('success');
      expect(response.body.workflow_name).toBe('test_workflow');
      expect(response.body.file_path).toContain('test_workflow.yml');

      // Get the actual file path from the response
      const filePath = response.body.file_path;

      // Verify file was created
      expect(fs.existsSync(filePath)).toBe(true);

      // Verify file content
      const fileContent = fs.readFileSync(filePath, 'utf8');
      expect(fileContent).toBe(yamlContent);
    });

    it('should allow alphanumeric, underscores, and hyphens in workflow_name', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test-workflow_123',
          yaml_content: YAML_TEMPLATES.simple(),
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('success');
    });

    it('should overwrite existing workflow when overwrite=true', async () => {
      const initialContent = YAML_TEMPLATES.simple('Initial');
      const updatedContent = YAML_TEMPLATES.simple('Updated');

      // First request: create workflow
      const firstResponse = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_overwrite',
          yaml_content: initialContent,
        });

      expect(firstResponse.status).toBe(200);
      const filePath = firstResponse.body.file_path;

      // Second request: overwrite workflow
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_overwrite',
          yaml_content: updatedContent,
          overwrite: true,
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('success');

      // Verify file content was updated using the path from response
      const fileContent = fs.readFileSync(filePath, 'utf8');
      expect(fileContent).toBe(updatedContent);
    });
  });

  describe('Validation error cases', () => {
    it('should return 400 if workflow_name is missing', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          yaml_content: 'version: 0.5',
        });

      expect(response.status).toBe(400);
      expect(response.body.status).toBe('error');
      expect(response.body.error_message).toContain('required');
    });

    it('should return 400 if yaml_content is missing', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_workflow',
        });

      expect(response.status).toBe(400);
      expect(response.body.status).toBe('error');
      expect(response.body.error_message).toContain('required');
    });

    it('should return 400 if workflow_name contains special characters', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test@workflow!',
          yaml_content: 'version: 0.5',
        });

      expect(response.status).toBe(400);
      expect(response.body.status).toBe('error');
      expect(response.body.error_message).toContain('alphanumeric');
    });

    it('should return 400 for path traversal in workflow_name (..)', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: '../malicious',
          yaml_content: 'version: 0.5',
        });

      expect(response.status).toBe(400);
      expect(response.body.status).toBe('error');
      expect(response.body.error_message).toContain('alphanumeric');
    });

    it('should return 400 for path traversal in workflow_name (forward slash)', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test/malicious',
          yaml_content: 'version: 0.5',
        });

      expect(response.status).toBe(400);
      expect(response.body.status).toBe('error');
      expect(response.body.error_message).toContain('alphanumeric');
    });

    it('should return 400 for path traversal in workflow_name (backslash)', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test\\malicious',
          yaml_content: 'version: 0.5',
        });

      expect(response.status).toBe(400);
      expect(response.body.status).toBe('error');
      expect(response.body.error_message).toContain('alphanumeric');
    });

    it('should return 400 for invalid YAML syntax', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_workflow',
          yaml_content: `version: 0.5
nodes:
  invalid_node:
    - not valid
    - yaml: syntax
  - this is wrong
`,
        });

      expect(response.status).toBe(400);
      expect(response.body.status).toBe('error');
      expect(response.body.error_message).toContain('YAML syntax validation failed');
      expect(response.body.validation_errors).toBeDefined();
      expect(response.body.validation_errors.length).toBeGreaterThan(0);
      expect(response.body.validation_errors[0].type).toBe('yaml_syntax');
    });

    it('should return 409 if workflow already exists and overwrite=false', async () => {
      const yamlContent = YAML_TEMPLATES.simple();

      // First request: create workflow
      const firstResponse = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_workflow_conflict',
          yaml_content: yamlContent,
        });

      expect(firstResponse.status).toBe(200);

      // Second request: attempt to overwrite without permission
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_workflow_conflict',
          yaml_content: yamlContent,
          overwrite: false,
        });

      expect(response.status).toBe(409);
      expect(response.body.status).toBe('error');
      expect(response.body.error_message).toContain('already exists');
    });
  });

  describe('Complex YAML validation', () => {
    it('should accept complex GraphAI workflow', async () => {
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'complex_workflow',
          yaml_content: YAML_TEMPLATES.complex,
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('success');
    });
  });
});
