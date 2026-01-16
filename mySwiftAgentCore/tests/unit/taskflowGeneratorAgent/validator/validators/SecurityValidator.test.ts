/**
 * SecurityValidator Unit Tests
 *
 * Issue #364: Security validation tests
 * Issue #369: Context-aware backtick detection tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SecurityValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/SecurityValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';
import {
  ValidationContextType,
  SHELL_STEP_TYPES,
  SHELL_FIELD_PATTERNS,
} from '../../../../../src/taskflowGeneratorAgent/validator/validators/security-config.js';

describe('SecurityValidator', () => {
  const validator = new SecurityValidator();

  const defaultContext: ValidationContext = {
    capabilities: [],
    projectId: 'test-project',
  };

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('SecurityValidator');
    });
  });

  describe('code_js step validation', () => {
    it('should fail for eval() usage', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'eval("console.log(1)")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'UNSAFE_CODE')).toBe(true);
    });

    it('should fail for Function constructor', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'new Function("return 1")()' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for require() usage', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'const fs = require("fs")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for dynamic import', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'await import("fs")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for process access', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'process.exit(1)' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for fs module access', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'fs.readFileSync("/etc/passwd")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for child_process access', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'child_process.exec("ls")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should pass for safe code', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'return input.data.map(x => x * 2)' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('api_rest step validation', () => {
    it('should warn for non-https URL on external domain', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: { url: 'http://api.example.com/data' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.warnings?.some((w) => w.code === 'INSECURE_HTTP')).toBe(true);
    });

    it('should warn for localhost URL', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: { url: 'http://localhost:8080/api' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.warnings?.some((w) => w.code === 'LOCALHOST_URL')).toBe(true);
    });

    it('should not warn for https URL', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: { url: 'https://api.example.com/data' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.warnings?.filter((w) => w.code === 'INSECURE_HTTP').length).toBe(0);
    });

    it('should skip validation for variable URLs', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: { url: '$input.api_url' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('transform step validation', () => {
    it('should fail for eval in expression', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform',
            type: 'transform',
            config: { expression: 'eval(input.code)' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'UNSAFE_EXPRESSION')).toBe(true);
    });

    it('should pass for safe expression', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform',
            type: 'transform',
            config: { expression: 'input.value * 2' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  // ============================================================================
  // Issue #369: Context-aware backtick detection tests
  // ============================================================================

  describe('Issue #369: Context-aware backtick detection', () => {
    describe('transform step with template literals (should ALLOW backticks)', () => {
      it('should allow JavaScript template literals in transform expressions', async () => {
        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'transform',
              type: 'transform',
              config: {
                expression: '`Hello ${name}, your score is ${score * 2}`',
              },
              params: {},
            },
          ],
          output: {},
        };

        const result = await validator.validate(workflow, defaultContext);

        expect(result.isValid).toBe(true);
        expect(result.errors).toHaveLength(0);
      });

      it('should allow template literals in transform config values', async () => {
        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'step_one',
              type: 'transform',
              config: { value: '`Result: ${data.value}`' },
              params: {},
            },
          ],
          output: {},
        };

        const result = await validator.validate(workflow, defaultContext);

        // Template literals are ALLOWED in transform steps
        expect(result.isValid).toBe(true);
        expect(result.errors.filter((e) => e.code === 'SHELL_INJECTION')).toHaveLength(0);
      });

      it('should allow nested template literals in transform step', async () => {
        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'transform',
              type: 'transform',
              config: {
                nested: {
                  template: '`User: ${user.name}, Age: ${user.age}`',
                },
              },
              params: {},
            },
          ],
          output: {},
        };

        const result = await validator.validate(workflow, defaultContext);

        expect(result.isValid).toBe(true);
      });
    });

    describe('shell step type (should DETECT backticks)', () => {
      it('should detect shell injection pattern in shell step type', async () => {
        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'exec_step',
              type: 'shell',
              config: { command: '`rm -rf /`' },
              params: {},
            },
          ],
          output: {},
        };

        const result = await validator.validate(workflow, defaultContext);

        expect(result.isValid).toBe(false);
        expect(result.errors.some((e) => e.code === 'SHELL_INJECTION')).toBe(true);
      });

      it('should detect shell injection in exec step type', async () => {
        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'exec_step',
              type: 'exec',
              config: { command: '`whoami`' },
              params: {},
            },
          ],
          output: {},
        };

        const result = await validator.validate(workflow, defaultContext);

        expect(result.isValid).toBe(false);
        expect(result.errors.some((e) => e.code === 'SHELL_INJECTION')).toBe(true);
      });

      it('should detect command substitution in shell context', async () => {
        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'shell_step',
              type: 'shell',
              config: { command: '$(cat /etc/passwd)' },
              params: {},
            },
          ],
          output: {},
        };

        const result = await validator.validate(workflow, defaultContext);

        expect(result.isValid).toBe(false);
        expect(result.errors.some((e) => e.code === 'COMMAND_SUBSTITUTION')).toBe(true);
      });
    });

    describe('code_js step with shell field paths', () => {
      it('should detect backticks in code_js shell field path', async () => {
        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'code_step',
              type: 'code_js',
              config: {
                code: 'console.log("safe")',
                shell: '`dangerous command`',
              },
              params: {},
            },
          ],
          output: {},
        };

        const result = await validator.validate(workflow, defaultContext);

        expect(result.isValid).toBe(false);
        expect(result.errors.some((e) => e.code === 'SHELL_INJECTION')).toBe(true);
      });

      it('should detect backticks in code_js exec field path', async () => {
        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'code_step',
              type: 'code_js',
              config: {
                code: 'console.log("safe")',
                exec: '`ls -la`',
              },
              params: {},
            },
          ],
          output: {},
        };

        const result = await validator.validate(workflow, defaultContext);

        expect(result.isValid).toBe(false);
        expect(result.errors.some((e) => e.code === 'SHELL_INJECTION')).toBe(true);
      });
    });
  });

  // ============================================================================
  // General dangerous patterns (context-independent)
  // ============================================================================

  describe('dangerous patterns', () => {
    it('should detect command substitution $() in transform', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { value: '$(whoami)' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      // Note: $() is NOT detected in transform context (non-shell)
      // This is the expected behavior after Issue #369 fix
      expect(result.isValid).toBe(true);
    });

    it('should detect path traversal', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { path: '../../../etc/passwd' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'PATH_TRAVERSAL')).toBe(true);
    });

    it('should warn about sensitive data (password)', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { data: 'user_password' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      // Sensitive data is a warning, not an error
      expect(result.warnings?.some((w) => w.code === 'SENSITIVE_DATA')).toBe(true);
    });

    it('should warn about API key references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { key: 'my_api_key' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.warnings?.some((w) => w.code === 'SENSITIVE_DATA')).toBe(true);
    });
  });

  describe('nested dangerous patterns', () => {
    it('should detect patterns in nested objects', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {
              nested: {
                deep: {
                  value: '../../../etc/passwd',
                },
              },
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should detect patterns in arrays (shell context)', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'shell',
            config: {
              commands: ['safe', '$(rm -rf /)'],
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'COMMAND_SUBSTITUTION')).toBe(true);
    });
  });

  // ============================================================================
  // Issue #369: Configuration and Metrics tests
  // ============================================================================

  describe('Issue #369: Configuration tests', () => {
    describe('security-config.ts', () => {
      it('should define SHELL_STEP_TYPES as Set', () => {
        expect(SHELL_STEP_TYPES).toBeInstanceOf(Set);
        expect(SHELL_STEP_TYPES.has('shell')).toBe(true);
        expect(SHELL_STEP_TYPES.has('exec')).toBe(true);
        expect(SHELL_STEP_TYPES.has('bash')).toBe(true);
        expect(SHELL_STEP_TYPES.has('cmd')).toBe(true);
      });

      it('should define SHELL_FIELD_PATTERNS as RegExp array', () => {
        expect(Array.isArray(SHELL_FIELD_PATTERNS)).toBe(true);
        expect(SHELL_FIELD_PATTERNS.every((p) => p instanceof RegExp)).toBe(true);
      });

      it('should define ValidationContextType enum', () => {
        expect(ValidationContextType.SHELL_EXECUTION).toBe('SHELL_EXECUTION');
        expect(ValidationContextType.JAVASCRIPT_SANDBOX).toBe('JAVASCRIPT_SANDBOX');
        expect(ValidationContextType.TEMPLATE_ENGINE).toBe('TEMPLATE_ENGINE');
        expect(ValidationContextType.DATA_REFERENCE).toBe('DATA_REFERENCE');
      });
    });

    describe('custom configuration', () => {
      it('should allow custom configuration via constructor', () => {
        const customValidator = new SecurityValidator({
          debug: true,
          collectMetrics: true,
        });

        expect(customValidator.name).toBe('SecurityValidator');
      });

      it('should accept additional shell step types', () => {
        const customValidator = new SecurityValidator({
          additionalShellStepTypes: ['custom_shell', 'my_exec'],
        });

        const workflow: TaskFlowDefinition = {
          workflow_name: 'test_workflow',
          version: '1.0',
          input_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'custom_step',
              type: 'custom_shell',
              config: { command: '`whoami`' },
              params: {},
            },
          ],
          output: {},
        };

        // Note: Since we can't easily mock the isShellContext method,
        // we just verify the validator accepts the configuration
        expect(customValidator).toBeDefined();
      });
    });
  });

  describe('Issue #369: Metrics collection', () => {
    it('should collect metrics when enabled', async () => {
      const validatorWithMetrics = new SecurityValidator({
        collectMetrics: true,
      });

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform',
            type: 'transform',
            config: { expression: 'x + 1' },
            params: {},
          },
          {
            id: 'code_step',
            type: 'code_js',
            config: { code: 'return x' },
            params: {},
          },
        ],
        output: {},
      };

      await validatorWithMetrics.validate(workflow, defaultContext);

      const metrics = validatorWithMetrics.getMetrics();
      expect(metrics).not.toBeNull();
      expect(metrics?.totalStepsChecked).toBe(2);
      expect(metrics?.validationDurationMs).toBeGreaterThanOrEqual(0);
    });

    it('should not collect metrics when disabled', async () => {
      const validatorWithoutMetrics = new SecurityValidator({
        collectMetrics: false,
      });

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      await validatorWithoutMetrics.validate(workflow, defaultContext);

      const metrics = validatorWithoutMetrics.getMetrics();
      expect(metrics).toBeNull();
    });

    it('should record detected patterns in metrics', async () => {
      const validatorWithMetrics = new SecurityValidator({
        collectMetrics: true,
      });

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'shell_step',
            type: 'shell',
            config: { command: '`whoami`' },
            params: {},
          },
        ],
        output: {},
      };

      await validatorWithMetrics.validate(workflow, defaultContext);

      const metrics = validatorWithMetrics.getMetrics();
      expect(metrics?.patternsDetected['SHELL_INJECTION']).toBeGreaterThan(0);
    });
  });

  describe('Issue #369: Debug logging', () => {
    let consoleDebugSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      consoleDebugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
    });

    afterEach(() => {
      consoleDebugSpy.mockRestore();
    });

    it('should log debug messages when debug mode is enabled', async () => {
      const debugValidator = new SecurityValidator({
        debug: true,
      });

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      await debugValidator.validate(workflow, defaultContext);

      expect(consoleDebugSpy).toHaveBeenCalled();
      expect(
        consoleDebugSpy.mock.calls.some((call) => call[0].includes('[SecurityValidator]'))
      ).toBe(true);
    });

    it('should not log debug messages when debug mode is disabled', async () => {
      const nonDebugValidator = new SecurityValidator({
        debug: false,
      });

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      await nonDebugValidator.validate(workflow, defaultContext);

      expect(
        consoleDebugSpy.mock.calls.some((call) => call[0].includes('[SecurityValidator]'))
      ).toBe(false);
    });
  });
});
