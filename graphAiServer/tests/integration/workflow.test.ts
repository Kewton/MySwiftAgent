import request from 'supertest';
import fs from 'fs';
import path from 'path';
import app from '../../src/app.js';

const TEST_WORKFLOW_DIR = path.resolve(process.cwd(), 'config/graphai');

describe('POST /api/v1/workflows/register', () => {
  // Clean up test files after each test
  afterEach(() => {
    const testFiles = ['test_workflow', 'test_overwrite', 'test_special_chars'];
    testFiles.forEach((name) => {
      const filePath = path.join(TEST_WORKFLOW_DIR, `${name}.yml`);
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    });
  });

  describe('Success cases', () => {
    it('should register a valid workflow', async () => {
      const requestBody = {
        workflow_name: 'test_workflow',
        yaml_content: `version: 0.5
nodes:
  test_node:
    value: "Hello World"
`,
      };

      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send(requestBody);

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('success');
      expect(response.body.workflow_name).toBe('test_workflow');
      expect(response.body.file_path).toContain('test_workflow.yml');

      // Verify file was created
      const filePath = path.join(TEST_WORKFLOW_DIR, 'test_workflow.yml');
      expect(fs.existsSync(filePath)).toBe(true);

      // Verify file content
      const fileContent = fs.readFileSync(filePath, 'utf8');
      expect(fileContent).toBe(requestBody.yaml_content);
    });

    it('should allow alphanumeric, underscores, and hyphens in workflow_name', async () => {
      const requestBody = {
        workflow_name: 'test-workflow_123',
        yaml_content: `version: 0.5
nodes:
  test_node:
    value: "Test"
`,
      };

      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send(requestBody);

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('success');

      // Clean up
      const filePath = path.join(TEST_WORKFLOW_DIR, 'test-workflow_123.yml');
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    });

    it('should overwrite existing workflow when overwrite=true', async () => {
      const initialContent = `version: 0.5
nodes:
  initial_node:
    value: "Initial"
`;
      const updatedContent = `version: 0.5
nodes:
  updated_node:
    value: "Updated"
`;

      // First request: create workflow
      await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_overwrite',
          yaml_content: initialContent,
        });

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

      // Verify file content was updated
      const filePath = path.join(TEST_WORKFLOW_DIR, 'test_overwrite.yml');
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
      const yamlContent = `version: 0.5
nodes:
  test_node:
    value: "Test"
`;

      // First request: create workflow
      await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_workflow',
          yaml_content: yamlContent,
        });

      // Second request: attempt to overwrite without permission
      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'test_workflow',
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
      const complexYaml = `version: 0.5
nodes:
  source:
    value: {}
  llm_node:
    agent: openAIAgent
    params:
      model: gpt-4
    inputs:
      - :source
  output_node:
    agent: copyAgent
    inputs:
      - :llm_node
`;

      const response = await request(app)
        .post('/api/v1/workflows/register')
        .send({
          workflow_name: 'complex_workflow',
          yaml_content: complexYaml,
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('success');

      // Clean up
      const filePath = path.join(TEST_WORKFLOW_DIR, 'complex_workflow.yml');
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    });
  });
});
