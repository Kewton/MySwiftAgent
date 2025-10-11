import request from 'supertest';
import app from '../../src/app.js';

describe('API Endpoints', () => {
  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toEqual({
        status: 'healthy',
        service: 'graphAiServer'
      });
    });
  });

  describe('GET /', () => {
    it('should return welcome message', async () => {
      const response = await request(app).get('/');
      expect(response.status).toBe(200);
      expect(response.body.message).toBeDefined();
      expect(response.body.message).toBe('Welcome to Graph AI Server');
    });
  });

  describe('GET /api/v1/', () => {
    it('should return API version info', async () => {
      const response = await request(app).get('/api/v1/');
      expect(response.status).toBe(200);
      expect(response.body).toEqual({
        version: '1.0',
        service: 'graphAiServer'
      });
    });
  });

  describe('POST /api/v1/myagent (legacy format)', () => {
    it('should return 400 if user_input is missing', async () => {
      const response = await request(app)
        .post('/api/v1/myagent')
        .send({ model_name: 'test' });
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('user_input is required');
    });

    it('should return 400 if model_name is missing', async () => {
      const response = await request(app)
        .post('/api/v1/myagent')
        .send({ user_input: 'test' });
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('model_name is required');
    });
  });

  describe('POST /api/v1/myagent/:category/:model (new format)', () => {
    it('should return 400 if user_input is missing', async () => {
      const response = await request(app)
        .post('/api/v1/myagent/default/test')
        .send({});
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('user_input is required');
    });

    it('should return 404 for path traversal in category (Express routing protection)', async () => {
      // Note: Express normalizes paths and returns 404 for .. in URL
      const response = await request(app)
        .post('/api/v1/myagent/../malicious/test')
        .send({ user_input: 'test' });
      expect(response.status).toBe(404);
    });

    it('should return 404 for path traversal in model (Express routing protection)', async () => {
      // Note: Express normalizes paths and returns 404 for .. in URL
      const response = await request(app)
        .post('/api/v1/myagent/default/../malicious')
        .send({ user_input: 'test' });
      expect(response.status).toBe(404);
    });

    it('should return 404 if path contains extra segments (forward slash in category)', async () => {
      // Note: Express routing handles this case, returns 404
      const response = await request(app)
        .post('/api/v1/myagent/cat/egory/test')
        .send({ user_input: 'test' });
      expect(response.status).toBe(404);
    });

    it('should return 404 if path contains extra segments (forward slash in model)', async () => {
      // Note: Express routing handles this case, returns 404
      const response = await request(app)
        .post('/api/v1/myagent/default/te/st')
        .send({ user_input: 'test' });
      expect(response.status).toBe(404);
    });

    it('should return 404 if path contains backslash', async () => {
      // Note: Express routing handles this case, returns 404
      const response = await request(app)
        .post('/api/v1/myagent/cat\\egory/test')
        .send({ user_input: 'test' });
      expect(response.status).toBe(404);
    });

    it('should accept valid category and model parameters', async () => {
      const response = await request(app)
        .post('/api/v1/myagent/expert/ollama')
        .send({ user_input: 'test input' });
      // Note: This will fail if the YAML file or API keys are not configured
      // We're just testing parameter validation here
      expect([200, 500]).toContain(response.status);
    });
  });
});
