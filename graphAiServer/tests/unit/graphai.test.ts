/**
 * Unit tests for graphai.ts - job_params support (Issue #331)
 *
 * Tests the source node structure change:
 * - Before: graph.injectValue("source", user_input)
 * - After: graph.injectValue("source", { user_input, job_params })
 *
 * Issue #331 改善: user_inputにjob_paramsがマージされることを検証
 * - job_paramsをベースにuser_inputでマージ（user_inputが優先）
 * - これにより、ワークフローYAMLは常に :source.user_input.* を使用可能
 *
 * Uses a real test workflow to verify the source node structure.
 */

import { describe, it, expect } from '@jest/globals';
import { runGraphAI } from '../../src/services/graphai.js';

describe('runGraphAI - job_params support', () => {
  describe('source node injection', () => {
    it('should inject job_params into source node structure with merged user_input', async () => {
      const user_input = { query: 'test query' };
      const job_params = { template_id: 'template-001', debug: true };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      // The output node copies :source, so we can verify the source structure
      // Issue #331 改善: user_inputにjob_paramsがマージされている
      expect(result.results).toHaveProperty('output');
      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      expect(outputResult.result).toEqual({
        user_input: { ...job_params, ...user_input },
        job_params: job_params,
      });
    });

    it('should inject empty object for job_params when not provided', async () => {
      const user_input = { query: 'test query' };

      const result = await runGraphAI(user_input, 'test/model', undefined, undefined);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      // job_paramsがない場合、user_inputはそのまま
      expect(outputResult.result).toEqual({
        user_input: user_input,
        job_params: {},
      });
    });

    it('should inject empty object for job_params when null is provided', async () => {
      const user_input = 'simple string input';

      // @ts-expect-error Testing null case
      const result = await runGraphAI(user_input, 'test/model', undefined, null);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      // user_inputが文字列の場合、マージは行われない
      expect(outputResult.result).toEqual({
        user_input: user_input,
        job_params: {},
      });
    });

    it('should merge job_params into user_input (object type)', async () => {
      const user_input = {
        email_address: 'test@example.com',
        subject: 'Test Subject',
        body: 'Test Body',
      };
      const job_params = { notification_type: 'email' };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      // Issue #331 改善: user_inputにjob_paramsがマージされている
      expect(outputResult.result).toEqual({
        user_input: { ...job_params, ...user_input },
        job_params: job_params,
      });
    });

    it('should preserve user_input as-is when it is string type (no merge)', async () => {
      const user_input = 'simple string input';
      const job_params = { format: 'text' };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      // user_inputが文字列の場合、マージは行われない
      expect(outputResult.result).toEqual({
        user_input: user_input,
        job_params: job_params,
      });
    });

    it('should handle complex nested job_params with merge', async () => {
      const user_input = { data: 'test' };
      const job_params = {
        config: {
          nested: {
            value: 123,
          },
        },
        array_param: [1, 2, 3],
      };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      // Issue #331 改善: user_inputにjob_paramsがマージされている
      expect(outputResult.result).toEqual({
        user_input: { ...job_params, ...user_input },
        job_params: job_params,
      });
    });

    it('should allow workflow access to :source.user_input.* properties (including merged)', async () => {
      const user_input = { query: 'test query', email: 'test@example.com' };
      const job_params = { setting: 'value' };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: Record<string, unknown>; job_params: unknown } };
      // user_inputの元の値にアクセス可能
      expect(outputResult.result.user_input.query).toBe('test query');
      expect(outputResult.result.user_input.email).toBe('test@example.com');
      // マージされたjob_paramsの値にもアクセス可能
      expect(outputResult.result.user_input.setting).toBe('value');
    });

    it('should allow workflow access to :source.job_params.* properties', async () => {
      const user_input = { data: 'test' };
      const job_params = { template_id: 'template-001', debug: true };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: { template_id: string; debug: boolean } } };
      expect(outputResult.result.job_params.template_id).toBe('template-001');
      expect(outputResult.result.job_params.debug).toBe(true);
    });

    it('should prioritize user_input values when keys conflict with job_params', async () => {
      const user_input = { query: 'user value', unique_user: 'from user' };
      const job_params = { query: 'job value', unique_job: 'from job' };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: Record<string, unknown>; job_params: unknown } };
      // user_inputのqueryが優先される
      expect(outputResult.result.user_input.query).toBe('user value');
      // 両方のuniqueキーがマージされる
      expect(outputResult.result.user_input.unique_user).toBe('from user');
      expect(outputResult.result.user_input.unique_job).toBe('from job');
    });
  });
});
