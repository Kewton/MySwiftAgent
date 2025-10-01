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

  describe('POST /api/v1/myagent', () => {
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
});
