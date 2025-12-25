/**
 * Status Utilities Tests
 * Issue #292: Review Page (JobVersion Detail)
 */

import { describe, it, expect } from 'vitest';
import { getStatusConfig, canActivate, canStartRun, JOB_VERSION_STATUS } from '$lib/utils/status';

describe('JOB_VERSION_STATUS', () => {
	it('should have all expected statuses', () => {
		expect(JOB_VERSION_STATUS).toHaveProperty('generating');
		expect(JOB_VERSION_STATUS).toHaveProperty('success');
		expect(JOB_VERSION_STATUS).toHaveProperty('failed');
		expect(JOB_VERSION_STATUS).toHaveProperty('active');
		expect(JOB_VERSION_STATUS).toHaveProperty('deprecated');
		expect(JOB_VERSION_STATUS).toHaveProperty('default');
	});

	it('should have correct structure for each status', () => {
		Object.values(JOB_VERSION_STATUS).forEach((config) => {
			expect(config).toHaveProperty('label');
			expect(config).toHaveProperty('class');
			expect(config).toHaveProperty('color');
			expect(config).toHaveProperty('bgColor');
		});
	});

	it('should have status classes prefixed with "status-"', () => {
		Object.values(JOB_VERSION_STATUS).forEach((config) => {
			expect(config.class).toMatch(/^status-/);
		});
	});
});

describe('getStatusConfig', () => {
	it('should return correct config for "generating"', () => {
		const config = getStatusConfig('generating');
		expect(config.label).toBe('Generating');
		expect(config.class).toBe('status-generating');
		expect(config.color).toBe('#92400e');
		expect(config.bgColor).toBe('#fef3c7');
	});

	it('should return correct config for "success"', () => {
		const config = getStatusConfig('success');
		expect(config.label).toBe('Success');
		expect(config.class).toBe('status-success');
	});

	it('should return correct config for "failed"', () => {
		const config = getStatusConfig('failed');
		expect(config.label).toBe('Failed');
		expect(config.class).toBe('status-failed');
	});

	it('should return correct config for "active"', () => {
		const config = getStatusConfig('active');
		expect(config.label).toBe('Active');
		expect(config.class).toBe('status-active');
	});

	it('should return correct config for "deprecated"', () => {
		const config = getStatusConfig('deprecated');
		expect(config.label).toBe('Deprecated');
		expect(config.class).toBe('status-deprecated');
	});

	it('should return default config with original status as label for unknown status', () => {
		const config = getStatusConfig('unknown_status');
		expect(config.label).toBe('unknown_status');
		expect(config.class).toBe('status-default');
	});

	it('should handle empty string status', () => {
		const config = getStatusConfig('');
		expect(config.label).toBe('');
		expect(config.class).toBe('status-default');
	});
});

describe('canActivate', () => {
	it('should return true for "success" status', () => {
		expect(canActivate('success')).toBe(true);
	});

	it('should return true for "deprecated" status', () => {
		expect(canActivate('deprecated')).toBe(true);
	});

	it('should return false for "generating" status', () => {
		expect(canActivate('generating')).toBe(false);
	});

	it('should return false for "failed" status', () => {
		expect(canActivate('failed')).toBe(false);
	});

	it('should return false for "active" status', () => {
		expect(canActivate('active')).toBe(false);
	});

	it('should return false for unknown status', () => {
		expect(canActivate('unknown')).toBe(false);
	});

	it('should return false for empty string', () => {
		expect(canActivate('')).toBe(false);
	});
});

describe('canStartRun', () => {
	it('should return true for "active" status', () => {
		expect(canStartRun('active')).toBe(true);
	});

	it('should return false for "success" status', () => {
		expect(canStartRun('success')).toBe(false);
	});

	it('should return false for "generating" status', () => {
		expect(canStartRun('generating')).toBe(false);
	});

	it('should return false for "failed" status', () => {
		expect(canStartRun('failed')).toBe(false);
	});

	it('should return false for "deprecated" status', () => {
		expect(canStartRun('deprecated')).toBe(false);
	});

	it('should return false for unknown status', () => {
		expect(canStartRun('unknown')).toBe(false);
	});

	it('should return false for empty string', () => {
		expect(canStartRun('')).toBe(false);
	});
});
