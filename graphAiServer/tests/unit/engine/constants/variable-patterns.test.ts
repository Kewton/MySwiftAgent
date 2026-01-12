/**
 * Unit Tests for TaskFlow Variable Pattern Definitions
 *
 * Tests for the centralized variable pattern validation module.
 *
 * @module tests/unit/engine/constants/variable-patterns
 * @see Issue #352 - URL variable reference validation fix
 */

import {
  TASKFLOW_VARIABLE_PATTERN,
  TASKFLOW_VARIABLE_EXTRACT_PATTERN,
  isValidTaskflowVariable,
  extractVariableReference,
  startsWithValidVariable,
  URL_VALIDATION_ERROR_MESSAGE,
  URL_VALIDATION_SHORT_MESSAGE,
} from '../../../../src/engine/constants/variable-patterns';

describe('TaskFlow Variable Patterns', () => {
  // ============================================================
  // TASKFLOW_VARIABLE_PATTERN - Exact Match
  // ============================================================

  describe('TASKFLOW_VARIABLE_PATTERN', () => {
    describe('Valid patterns', () => {
      const validPatterns = [
        '${a}',
        '${_}',
        '${inputs}',
        '${inputs.query}',
        '${inputs.user_id}',
        '${step_001.output}',
        '${step_001.output.data}',
        '${step_001.output.data.name}',
        '${step-001.output}',
        '${step-001.output.data-field}',
        '${secrets.API_KEY}',
        '${secrets.MY_SECRET_123}',
        '${env.BASE_URL}',
        '${env.NODE_ENV}',
        '${_private.field}',
        '${CamelCase.Field}',
      ];

      it.each(validPatterns)('should match valid pattern: %s', (pattern) => {
        expect(TASKFLOW_VARIABLE_PATTERN.test(pattern)).toBe(true);
      });
    });

    describe('Invalid patterns', () => {
      const invalidPatterns = [
        '${}',               // empty
        '${123}',            // starts with number
        '${.invalid}',       // starts with dot
        '${invalid.}',       // ends with dot
        '${in valid}',       // contains space
        '${a..b}',           // double dot
        '${a.}',             // trailing dot
        '${.a}',             // leading dot in first segment
        '${inputs.url}/path', // has trailing content
        'inputs.query',      // missing ${}
        '$inputs.query',     // missing {}
        '{inputs.query}',    // missing $
      ];
      // Note: ${in-} is actually valid - hyphens are allowed in identifiers

      it.each(invalidPatterns)('should NOT match invalid pattern: %s', (pattern) => {
        expect(TASKFLOW_VARIABLE_PATTERN.test(pattern)).toBe(false);
      });
    });
  });

  // ============================================================
  // isValidTaskflowVariable
  // ============================================================

  describe('isValidTaskflowVariable', () => {
    describe('Valid variable references', () => {
      it('should return true for ${inputs.url}', () => {
        expect(isValidTaskflowVariable('${inputs.url}')).toBe(true);
      });

      it('should return true for ${step_001.output.data}', () => {
        expect(isValidTaskflowVariable('${step_001.output.data}')).toBe(true);
      });

      it('should return true for ${env.BASE_URL}', () => {
        expect(isValidTaskflowVariable('${env.BASE_URL}')).toBe(true);
      });

      it('should return true for ${secrets.API_KEY}', () => {
        expect(isValidTaskflowVariable('${secrets.API_KEY}')).toBe(true);
      });

      it('should return true for minimal valid pattern ${a}', () => {
        expect(isValidTaskflowVariable('${a}')).toBe(true);
      });

      it('should return true for underscore start ${_}', () => {
        expect(isValidTaskflowVariable('${_}')).toBe(true);
      });

      it('should return true for hyphenated step ID ${step-001.output}', () => {
        expect(isValidTaskflowVariable('${step-001.output}')).toBe(true);
      });
    });

    describe('Invalid variable references', () => {
      it('should return false for empty ${}', () => {
        expect(isValidTaskflowVariable('${}')).toBe(false);
      });

      it('should return false for number start ${123}', () => {
        expect(isValidTaskflowVariable('${123}')).toBe(false);
      });

      it('should return false for dot start ${.invalid}', () => {
        expect(isValidTaskflowVariable('${.invalid}')).toBe(false);
      });

      it('should return false for trailing path ${inputs.url}/path', () => {
        expect(isValidTaskflowVariable('${inputs.url}/path')).toBe(false);
      });

      it('should return false for space ${in valid}', () => {
        expect(isValidTaskflowVariable('${in valid}')).toBe(false);
      });

      it('should return false for plain string', () => {
        expect(isValidTaskflowVariable('https://example.com')).toBe(false);
      });
    });
  });

  // ============================================================
  // extractVariableReference
  // ============================================================

  describe('extractVariableReference', () => {
    it('should extract variable from simple reference', () => {
      expect(extractVariableReference('${inputs.url}')).toBe('${inputs.url}');
    });

    it('should extract variable from URL with path', () => {
      expect(extractVariableReference('${inputs.url}/api/v1')).toBe('${inputs.url}');
    });

    it('should extract variable from URL with query', () => {
      expect(extractVariableReference('${env.BASE_URL}?query=1')).toBe('${env.BASE_URL}');
    });

    it('should extract variable from complex path', () => {
      expect(extractVariableReference('${step_001.output.api_url}/users/123'))
        .toBe('${step_001.output.api_url}');
    });

    it('should return null for non-variable URL', () => {
      expect(extractVariableReference('https://example.com')).toBeNull();
    });

    it('should return null for empty string', () => {
      expect(extractVariableReference('')).toBeNull();
    });

    it('should return null for partial variable', () => {
      expect(extractVariableReference('$inputs.url')).toBeNull();
    });
  });

  // ============================================================
  // startsWithValidVariable
  // ============================================================

  describe('startsWithValidVariable', () => {
    describe('Valid URLs starting with variable', () => {
      it('should return true for simple variable', () => {
        expect(startsWithValidVariable('${inputs.url}')).toBe(true);
      });

      it('should return true for variable with path', () => {
        expect(startsWithValidVariable('${inputs.url}/api/v1')).toBe(true);
      });

      it('should return true for variable with query', () => {
        expect(startsWithValidVariable('${env.BASE_URL}?query=1')).toBe(true);
      });

      it('should return true for step output variable', () => {
        expect(startsWithValidVariable('${step_001.output.url}')).toBe(true);
      });

      it('should return true for step output with path', () => {
        expect(startsWithValidVariable('${step_001.output.api_url}/users/123')).toBe(true);
      });

      it('should return true for env variable', () => {
        expect(startsWithValidVariable('${env.API_BASE_URL}')).toBe(true);
      });

      it('should return true for secrets variable', () => {
        expect(startsWithValidVariable('${secrets.PRIVATE_URL}')).toBe(true);
      });

      it('should return true for hyphenated step ID', () => {
        expect(startsWithValidVariable('${step-001.output}/path')).toBe(true);
      });
    });

    describe('Invalid URLs', () => {
      it('should return false for HTTPS URL', () => {
        expect(startsWithValidVariable('https://example.com')).toBe(false);
      });

      it('should return false for HTTP URL', () => {
        expect(startsWithValidVariable('http://example.com')).toBe(false);
      });

      it('should return false for invalid variable ${123}', () => {
        expect(startsWithValidVariable('${123}/path')).toBe(false);
      });

      it('should return false for invalid variable ${.invalid}', () => {
        expect(startsWithValidVariable('${.invalid}/path')).toBe(false);
      });

      it('should return false for empty variable ${}', () => {
        expect(startsWithValidVariable('${}/path')).toBe(false);
      });

      it('should return false for empty string', () => {
        expect(startsWithValidVariable('')).toBe(false);
      });

      it('should return false for plain text', () => {
        expect(startsWithValidVariable('not-a-url')).toBe(false);
      });
    });
  });

  // ============================================================
  // Error Messages
  // ============================================================

  describe('Error Messages', () => {
    it('should have informative URL_VALIDATION_ERROR_MESSAGE', () => {
      expect(URL_VALIDATION_ERROR_MESSAGE).toContain('HTTPS');
      expect(URL_VALIDATION_ERROR_MESSAGE).toContain('${inputs.field}');
      expect(URL_VALIDATION_ERROR_MESSAGE).toContain('${step_id.output.field}');
      expect(URL_VALIDATION_ERROR_MESSAGE).toContain('${env.VAR}');
      expect(URL_VALIDATION_ERROR_MESSAGE).toContain('${secrets.KEY}');
    });

    it('should have concise URL_VALIDATION_SHORT_MESSAGE', () => {
      expect(URL_VALIDATION_SHORT_MESSAGE).toContain('HTTPS');
      expect(URL_VALIDATION_SHORT_MESSAGE).toContain('${inputs.*}');
      expect(URL_VALIDATION_SHORT_MESSAGE).toContain('${step_id.output.*}');
    });
  });

  // ============================================================
  // Edge Cases
  // ============================================================

  describe('Edge Cases', () => {
    it('should handle deeply nested paths', () => {
      expect(isValidTaskflowVariable('${step.output.data.user.address.city}')).toBe(true);
    });

    it('should handle mixed case identifiers', () => {
      expect(isValidTaskflowVariable('${MyStep.Output.DataField}')).toBe(true);
    });

    it('should handle numbers in identifiers (not at start)', () => {
      expect(isValidTaskflowVariable('${step123.output456}')).toBe(true);
    });

    it('should handle underscores throughout', () => {
      expect(isValidTaskflowVariable('${_step_001_.output_data_}')).toBe(true);
    });

    it('should handle hyphens in step IDs', () => {
      expect(isValidTaskflowVariable('${my-step-id.output}')).toBe(true);
    });

    it('should reject double dots', () => {
      expect(isValidTaskflowVariable('${step..output}')).toBe(false);
    });

    it('should reject trailing dot', () => {
      expect(isValidTaskflowVariable('${step.output.}')).toBe(false);
    });

    it('should reject leading dot in first segment', () => {
      expect(isValidTaskflowVariable('${.step.output}')).toBe(false);
    });
  });
});
