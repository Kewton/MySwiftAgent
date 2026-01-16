/**
 * ScriptWhitelist Unit Tests
 *
 * Issue #363: Script whitelist management
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ScriptWhitelist,
  createScriptWhitelist,
  type ScriptWhitelistEntry,
} from '../../../../src/taskflowEngine/sandbox/ScriptWhitelist.js';

describe('ScriptWhitelist', () => {
  let whitelist: ScriptWhitelist;

  const sampleEntry: ScriptWhitelistEntry = {
    path: 'calculators/risk_model.js',
    hash: 'sha256:abc123def456',
    description: 'Risk model calculator',
  };

  beforeEach(() => {
    whitelist = new ScriptWhitelist();
  });

  describe('add', () => {
    it('should add a script to the whitelist', () => {
      whitelist.add(sampleEntry);

      expect(whitelist.isWhitelisted('calculators/risk_model.js')).toBe(true);
    });

    it('should update existing entry', () => {
      whitelist.add(sampleEntry);
      whitelist.add({ ...sampleEntry, hash: 'sha256:newHash' });

      expect(whitelist.getHash('calculators/risk_model.js')).toBe('sha256:newHash');
    });
  });

  describe('remove', () => {
    beforeEach(() => {
      whitelist.add(sampleEntry);
    });

    it('should remove a script from the whitelist', () => {
      const result = whitelist.remove('calculators/risk_model.js');

      expect(result).toBe(true);
      expect(whitelist.isWhitelisted('calculators/risk_model.js')).toBe(false);
    });

    it('should return false for non-existent script', () => {
      const result = whitelist.remove('non_existent.js');

      expect(result).toBe(false);
    });
  });

  describe('isWhitelisted', () => {
    beforeEach(() => {
      whitelist.add(sampleEntry);
    });

    it('should return true for whitelisted script', () => {
      expect(whitelist.isWhitelisted('calculators/risk_model.js')).toBe(true);
    });

    it('should return false for non-whitelisted script', () => {
      expect(whitelist.isWhitelisted('unknown.js')).toBe(false);
    });

    it('should detect path traversal attempts', () => {
      expect(whitelist.isWhitelisted('../secret.js')).toBe(false);
      expect(whitelist.isWhitelisted('calculators/../../../etc/passwd')).toBe(false);
    });

    it('should normalize paths before checking', () => {
      whitelist.add({ path: 'scripts/test.js', hash: 'abc' });

      expect(whitelist.isWhitelisted('./scripts/test.js')).toBe(true);
    });
  });

  describe('getHash', () => {
    beforeEach(() => {
      whitelist.add(sampleEntry);
    });

    it('should return hash for whitelisted script', () => {
      expect(whitelist.getHash('calculators/risk_model.js')).toBe('sha256:abc123def456');
    });

    it('should return undefined for non-whitelisted script', () => {
      expect(whitelist.getHash('unknown.js')).toBeUndefined();
    });
  });

  describe('getEntry', () => {
    beforeEach(() => {
      whitelist.add(sampleEntry);
    });

    it('should return entry for whitelisted script', () => {
      const entry = whitelist.getEntry('calculators/risk_model.js');

      expect(entry?.path).toBe('calculators/risk_model.js');
      expect(entry?.description).toBe('Risk model calculator');
    });

    it('should return undefined for non-whitelisted script', () => {
      expect(whitelist.getEntry('unknown.js')).toBeUndefined();
    });
  });

  describe('listAll', () => {
    it('should return all entries', () => {
      whitelist.add(sampleEntry);
      whitelist.add({ path: 'utils/helper.js', hash: 'hash2' });

      const entries = whitelist.listAll();

      expect(entries).toHaveLength(2);
      expect(entries.map(e => e.path)).toContain('calculators/risk_model.js');
      expect(entries.map(e => e.path)).toContain('utils/helper.js');
    });

    it('should return empty array when no entries', () => {
      expect(whitelist.listAll()).toEqual([]);
    });
  });

  describe('clear', () => {
    it('should clear all entries', () => {
      whitelist.add(sampleEntry);
      whitelist.clear();

      expect(whitelist.listAll()).toHaveLength(0);
    });
  });

  describe('size', () => {
    it('should return number of entries', () => {
      expect(whitelist.size()).toBe(0);

      whitelist.add(sampleEntry);
      expect(whitelist.size()).toBe(1);

      whitelist.add({ path: 'other.js', hash: 'hash' });
      expect(whitelist.size()).toBe(2);
    });
  });
});

describe('createScriptWhitelist factory', () => {
  it('should create a ScriptWhitelist instance', () => {
    const whitelist = createScriptWhitelist();
    expect(whitelist).toBeInstanceOf(ScriptWhitelist);
  });

  it('should create whitelist with initial entries', () => {
    const entries: ScriptWhitelistEntry[] = [
      { path: 'a.js', hash: 'hash1' },
      { path: 'b.js', hash: 'hash2' },
    ];

    const whitelist = createScriptWhitelist(entries);

    expect(whitelist.size()).toBe(2);
    expect(whitelist.isWhitelisted('a.js')).toBe(true);
  });
});
