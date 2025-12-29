/**
 * Unit tests for graphai.ts - job_params support (Issue #331)
 *
 * Tests the source node structure change:
 * - Before: graph.injectValue("source", user_input)
 * - After: graph.injectValue("source", { user_input, job_params })
 *
 * Uses a real test workflow to verify the source node structure.
 */

import { describe, it, expect } from '@jest/globals';
import { runGraphAI } from '../../src/services/graphai.js';

describe('runGraphAI - job_params support', () => {
  describe('source node injection', () => {
    it('should inject job_params into source node structure', async () => {
      const user_input = { query: 'test query' };
      const job_params = { template_id: 'template-001', debug: true };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      // The output node copies :source, so we can verify the source structure
      expect(result.results).toHaveProperty('output');
      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      expect(outputResult.result).toEqual({
        user_input: user_input,
        job_params: job_params,
      });
    });

    it('should inject empty object for job_params when not provided', async () => {
      const user_input = { query: 'test query' };

      const result = await runGraphAI(user_input, 'test/model', undefined, undefined);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
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
      expect(outputResult.result).toEqual({
        user_input: user_input,
        job_params: {},
      });
    });

    it('should preserve user_input structure (object type)', async () => {
      const user_input = {
        email_address: 'test@example.com',
        subject: 'Test Subject',
        body: 'Test Body',
      };
      const job_params = { notification_type: 'email' };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      expect(outputResult.result).toEqual({
        user_input: user_input,
        job_params: job_params,
      });
    });

    it('should preserve user_input structure (string type)', async () => {
      const user_input = 'simple string input';
      const job_params = { format: 'text' };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: unknown } };
      expect(outputResult.result).toEqual({
        user_input: user_input,
        job_params: job_params,
      });
    });

    it('should handle complex nested job_params', async () => {
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
      expect(outputResult.result).toEqual({
        user_input: user_input,
        job_params: job_params,
      });
    });

    it('should allow workflow access to :source.user_input.* properties', async () => {
      const user_input = { query: 'test query', email: 'test@example.com' };
      const job_params = { setting: 'value' };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: { query: string; email: string }; job_params: unknown } };
      expect(outputResult.result.user_input.query).toBe('test query');
      expect(outputResult.result.user_input.email).toBe('test@example.com');
    });

    it('should allow workflow access to :source.job_params.* properties', async () => {
      const user_input = { data: 'test' };
      const job_params = { template_id: 'template-001', debug: true };

      const result = await runGraphAI(user_input, 'test/model', undefined, job_params);

      const outputResult = result.results.output as { result: { user_input: unknown; job_params: { template_id: string; debug: boolean } } };
      expect(outputResult.result.job_params.template_id).toBe('template-001');
      expect(outputResult.result.job_params.debug).toBe(true);
    });
  });
});
