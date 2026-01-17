/**
 * PathValidator Unit Tests
 *
 * Issue #370: Path validation for security
 * TDD Phase: Red - Write failing tests first
 */

import { describe, it, expect } from 'vitest';
import {
  PathValidator,
  createPathValidator,
  PathValidationError,
  type PathValidatorConfig,
} from '../../../../src/utils/validation/PathValidator.js';

describe('PathValidator', () => {
  let validator: PathValidator;

  beforeEach(() => {
    validator = createPathValidator();
  });

  describe('valid paths', () => {
    it('should accept valid alphanumeric path', () => {
      expect(validator.validate('validPath123')).toBe(true);
    });

    it('should accept path with hyphens', () => {
      expect(validator.validate('valid-path-123')).toBe(true);
    });

    it('should accept path with underscores', () => {
      expect(validator.validate('valid_path_123')).toBe(true);
    });

    it('should accept path starting with letter', () => {
      expect(validator.validate('myProject')).toBe(true);
    });

    it('should accept path starting with number', () => {
      expect(validator.validate('123project')).toBe(true);
    });
  });

  describe('path traversal attacks', () => {
    it('should reject path with double dots', () => {
      expect(() => validator.validate('..')).toThrow(PathValidationError);
    });

    it('should reject path containing ../', () => {
      expect(() => validator.validate('path/../secret')).toThrow(PathValidationError);
    });

    it('should reject path containing /..', () => {
      expect(() => validator.validate('path/..')).toThrow(PathValidationError);
    });

    it('should reject path with forward slash', () => {
      expect(() => validator.validate('path/to/file')).toThrow(PathValidationError);
    });

    it('should reject path with backslash', () => {
      expect(() => validator.validate('path\\to\\file')).toThrow(PathValidationError);
    });

    it('should reject path with tilde', () => {
      expect(() => validator.validate('~user')).toThrow(PathValidationError);
    });
  });

  describe('prototype pollution attacks', () => {
    it('should reject __proto__', () => {
      expect(() => validator.validate('__proto__')).toThrow(PathValidationError);
    });

    it('should reject constructor', () => {
      expect(() => validator.validate('constructor')).toThrow(PathValidationError);
    });

    it('should reject prototype', () => {
      expect(() => validator.validate('prototype')).toThrow(PathValidationError);
    });
  });

  describe('length validation', () => {
    it('should accept path at max length (128)', () => {
      const maxPath = 'a'.repeat(128);
      expect(validator.validate(maxPath)).toBe(true);
    });

    it('should reject path exceeding max length', () => {
      const longPath = 'a'.repeat(129);
      expect(() => validator.validate(longPath)).toThrow(PathValidationError);
    });

    it('should reject empty path', () => {
      expect(() => validator.validate('')).toThrow(PathValidationError);
    });
  });

  describe('custom configuration', () => {
    it('should accept custom max length', () => {
      const customValidator = createPathValidator({ maxLength: 10 });
      expect(() => customValidator.validate('a'.repeat(11))).toThrow(PathValidationError);
      expect(customValidator.validate('a'.repeat(10))).toBe(true);
    });

    it('should accept additional blocked patterns', () => {
      const customValidator = createPathValidator({
        additionalBlockedPatterns: ['admin', 'root'],
      });
      expect(() => customValidator.validate('admin')).toThrow(PathValidationError);
      expect(() => customValidator.validate('root')).toThrow(PathValidationError);
    });
  });

  describe('error details', () => {
    it('should include path in error', () => {
      try {
        validator.validate('../attack');
        expect.fail('Should have thrown');
      } catch (e) {
        expect(e).toBeInstanceOf(PathValidationError);
        expect((e as PathValidationError).path).toBe('../attack');
      }
    });

    it('should include reason in error', () => {
      try {
        validator.validate('../attack');
        expect.fail('Should have thrown');
      } catch (e) {
        expect(e).toBeInstanceOf(PathValidationError);
        expect((e as PathValidationError).reason).toBeDefined();
      }
    });
  });

  describe('sanitize method', () => {
    it('should return validated path if valid', () => {
      expect(validator.sanitize('validPath')).toBe('validPath');
    });

    it('should throw for invalid path', () => {
      expect(() => validator.sanitize('../attack')).toThrow(PathValidationError);
    });
  });
});

describe('createPathValidator factory', () => {
  it('should create a PathValidator instance', () => {
    const validator = createPathValidator();
    expect(validator).toBeInstanceOf(PathValidator);
  });

  it('should use default max length of 128', () => {
    const validator = createPathValidator();
    expect(validator.validate('a'.repeat(128))).toBe(true);
  });
});
