/**
 * Unit tests for app.ts - job_params parsing (Issue #331)
 *
 * Tests that API endpoints correctly extract job_params from request body
 * and pass it to runGraphAI. Uses real test workflow to validate.
 *
 * Issue #331 改善: user_inputにjob_paramsがマージされることを検証
 * - job_paramsをベースにuser_inputでマージ（user_inputが優先）
 * - これにより、ワークフローYAMLは常に :source.user_input.* を使用可能
 */

import request from 'supertest';
import { describe, it, expect } from '@jest/globals';
import app from '../../src/app.js';

describe('API Endpoints - job_params support', () => {
  describe('POST /api/v1/myagent/:category/:model', () => {
    it('should pass job_params to runGraphAI and inject into source node', async () => {
      const requestBody = {
        user_input: { query: 'test query' },
        job_params: { template_id: 'template-001', debug: true },
      };

      const response = await request(app)
        .post('/api/v1/myagent/test/model')
        .send(requestBody);

      expect(response.status).toBe(200);

      // Verify source node structure in response
      // Issue #331 改善: user_inputにjob_paramsがマージされている
      const outputResult = response.body.results.output as {
        result: { user_input: unknown; job_params: unknown };
      };
      expect(outputResult.result).toEqual({
        user_input: { ...requestBody.job_params, ...requestBody.user_input },
        job_params: requestBody.job_params,
      });
    });

    it('should inject empty job_params when not provided', async () => {
      const requestBody = {
        user_input: { query: 'test query' },
      };

      const response = await request(app)
        .post('/api/v1/myagent/test/model')
        .send(requestBody);

      expect(response.status).toBe(200);

      const outputResult = response.body.results.output as {
        result: { user_input: unknown; job_params: unknown };
      };
      // job_paramsがない場合、user_inputはそのまま
      expect(outputResult.result).toEqual({
        user_input: requestBody.user_input,
        job_params: {},
      });
    });

    it('should handle project and job_params together', async () => {
      const requestBody = {
        user_input: { query: 'test query' },
        project: 'test-project',
        job_params: { setting: 'value' },
      };

      const response = await request(app)
        .post('/api/v1/myagent/test/model')
        .send(requestBody);

      expect(response.status).toBe(200);

      const outputResult = response.body.results.output as {
        result: { user_input: unknown; job_params: unknown };
      };
      // Issue #331 改善: user_inputにjob_paramsがマージされている
      expect(outputResult.result).toEqual({
        user_input: { ...requestBody.job_params, ...requestBody.user_input },
        job_params: requestBody.job_params,
      });
    });

    it('should handle complex nested job_params', async () => {
      const requestBody = {
        user_input: { data: 'test' },
        job_params: {
          config: { nested: { value: 123 } },
          array_param: [1, 2, 3],
        },
      };

      const response = await request(app)
        .post('/api/v1/myagent/test/model')
        .send(requestBody);

      expect(response.status).toBe(200);

      const outputResult = response.body.results.output as {
        result: { user_input: unknown; job_params: unknown };
      };
      // Issue #331 改善: user_inputにjob_paramsがマージされている
      expect(outputResult.result).toEqual({
        user_input: { ...requestBody.job_params, ...requestBody.user_input },
        job_params: requestBody.job_params,
      });
    });

    it('should prioritize user_input over job_params when keys conflict', async () => {
      const requestBody = {
        user_input: { query: 'user value', unique_to_user: 'user only' },
        job_params: { query: 'job value', unique_to_job: 'job only' },
      };

      const response = await request(app)
        .post('/api/v1/myagent/test/model')
        .send(requestBody);

      expect(response.status).toBe(200);

      const outputResult = response.body.results.output as {
        result: { user_input: unknown; job_params: unknown };
      };
      // user_inputのqueryが優先される（マージ順序: job_params -> user_input）
      expect(outputResult.result).toEqual({
        user_input: {
          query: 'user value',  // user_inputが優先
          unique_to_user: 'user only',
          unique_to_job: 'job only',  // job_paramsから追加
        },
        job_params: requestBody.job_params,
      });
    });
  });

  describe('POST /api/v1/myagent (legacy format)', () => {
    it('should pass job_params to runGraphAI and inject into source node', async () => {
      const requestBody = {
        user_input: { query: 'test query' },
        model_name: 'test/model',
        job_params: { template_id: 'template-001' },
      };

      const response = await request(app)
        .post('/api/v1/myagent')
        .send(requestBody);

      expect(response.status).toBe(200);

      const outputResult = response.body.results.output as {
        result: { user_input: unknown; job_params: unknown };
      };
      // Issue #331 改善: user_inputにjob_paramsがマージされている
      expect(outputResult.result).toEqual({
        user_input: { ...requestBody.job_params, ...requestBody.user_input },
        job_params: requestBody.job_params,
      });
    });

    it('should inject empty job_params when not provided', async () => {
      const requestBody = {
        user_input: { query: 'test query' },
        model_name: 'test/model',
      };

      const response = await request(app)
        .post('/api/v1/myagent')
        .send(requestBody);

      expect(response.status).toBe(200);

      const outputResult = response.body.results.output as {
        result: { user_input: unknown; job_params: unknown };
      };
      // job_paramsがない場合、user_inputはそのまま
      expect(outputResult.result).toEqual({
        user_input: requestBody.user_input,
        job_params: {},
      });
    });

    it('should handle project and job_params together', async () => {
      const requestBody = {
        user_input: { query: 'test query' },
        model_name: 'test/model',
        project: 'test-project',
        job_params: { config: { key: 'value' } },
      };

      const response = await request(app)
        .post('/api/v1/myagent')
        .send(requestBody);

      expect(response.status).toBe(200);

      const outputResult = response.body.results.output as {
        result: { user_input: unknown; job_params: unknown };
      };
      // Issue #331 改善: user_inputにjob_paramsがマージされている
      expect(outputResult.result).toEqual({
        user_input: { ...requestBody.job_params, ...requestBody.user_input },
        job_params: requestBody.job_params,
      });
    });
  });
});
