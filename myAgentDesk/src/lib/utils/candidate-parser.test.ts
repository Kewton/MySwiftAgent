/**
 * candidate-parser.test.ts - Unit tests for LLM response candidate parser
 *
 * Issue #192: Create Job MLOps UI integration
 * Task 2.1: Parser unit tests
 */

import { describe, it, expect } from 'vitest';
import {
	parseCandidatesFromResponse,
	extractCandidateSection,
	parseCandidate,
	type ParsedCandidate
} from './candidate-parser';

describe('candidate-parser', () => {
	describe('parseCandidatesFromResponse', () => {
		it('should return empty array for empty response', () => {
			const result = parseCandidatesFromResponse('');
			expect(result).toEqual([]);
		});

		it('should return empty array for response without candidates', () => {
			const response = 'This is a normal chat response without any candidates.';
			const result = parseCandidatesFromResponse(response);
			expect(result).toEqual([]);
		});

		it('should parse single candidate from response', () => {
			const response = `Based on your requirements, here is my interpretation:

[CANDIDATE:1]
Label: Data Analysis Pipeline
Description: A pipeline that processes CSV files and outputs Excel reports
Confidence: 0.85
Requirements:
  - data_source: CSV files from S3 bucket
  - process_description: Aggregate sales data by region
  - output_format: Excel report with charts
  - schedule: Daily at 9:00 AM
[/CANDIDATE]

Please confirm if this matches your needs.`;

			const result = parseCandidatesFromResponse(response);

			expect(result).toHaveLength(1);
			expect(result[0].id).toBe('candidate-1');
			expect(result[0].label).toBe('Data Analysis Pipeline');
			expect(result[0].description).toBe('A pipeline that processes CSV files and outputs Excel reports');
			expect(result[0].confidence).toBe(0.85);
			expect(result[0].requirements.data_source).toBe('CSV files from S3 bucket');
			expect(result[0].requirements.process_description).toBe('Aggregate sales data by region');
			expect(result[0].requirements.output_format).toBe('Excel report with charts');
			expect(result[0].requirements.schedule).toBe('Daily at 9:00 AM');
		});

		it('should parse multiple candidates from response', () => {
			const response = `I have identified two possible interpretations:

[CANDIDATE:1]
Label: Batch Processing
Description: Process data in batches overnight
Confidence: 0.75
Requirements:
  - data_source: Database tables
  - process_description: ETL pipeline
  - output_format: Parquet files
  - schedule: Nightly at 2:00 AM
[/CANDIDATE]

[CANDIDATE:2]
Label: Real-time Processing
Description: Stream processing with immediate output
Confidence: 0.65
Requirements:
  - data_source: Kafka stream
  - process_description: Real-time aggregation
  - output_format: Dashboard metrics
  - schedule: Continuous
[/CANDIDATE]

Which interpretation better matches your requirements?`;

			const result = parseCandidatesFromResponse(response);

			expect(result).toHaveLength(2);
			expect(result[0].id).toBe('candidate-1');
			expect(result[0].label).toBe('Batch Processing');
			expect(result[0].confidence).toBe(0.75);
			expect(result[1].id).toBe('candidate-2');
			expect(result[1].label).toBe('Real-time Processing');
			expect(result[1].confidence).toBe(0.65);
		});

		it('should handle malformed candidate sections gracefully', () => {
			const response = `Here's an interpretation:

[CANDIDATE:1]
Label: Incomplete Candidate
[/CANDIDATE]

This candidate is missing required fields.`;

			const result = parseCandidatesFromResponse(response);

			// Should still parse what's available
			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('Incomplete Candidate');
			expect(result[0].description).toBe('');
			expect(result[0].confidence).toBe(0);
		});

		it('should handle confidence as percentage', () => {
			const response = `[CANDIDATE:1]
Label: Test
Description: Test description
Confidence: 85%
Requirements:
  - data_source: Test
[/CANDIDATE]`;

			const result = parseCandidatesFromResponse(response);

			expect(result[0].confidence).toBe(0.85);
		});

		it('should handle confidence as decimal string', () => {
			const response = `[CANDIDATE:1]
Label: Test
Description: Test description
Confidence: 0.92
Requirements:
  - data_source: Test
[/CANDIDATE]`;

			const result = parseCandidatesFromResponse(response);

			expect(result[0].confidence).toBe(0.92);
		});
	});

	describe('extractCandidateSection', () => {
		it('should extract candidate section from text', () => {
			const text = `Some text before
[CANDIDATE:1]
Label: Test
[/CANDIDATE]
Some text after`;

			const sections = extractCandidateSection(text);

			expect(sections).toHaveLength(1);
			expect(sections[0]).toContain('Label: Test');
		});

		it('should extract multiple candidate sections', () => {
			const text = `[CANDIDATE:1]
Label: First
[/CANDIDATE]
Middle text
[CANDIDATE:2]
Label: Second
[/CANDIDATE]`;

			const sections = extractCandidateSection(text);

			expect(sections).toHaveLength(2);
			expect(sections[0]).toContain('Label: First');
			expect(sections[1]).toContain('Label: Second');
		});

		it('should return empty array when no candidates found', () => {
			const text = 'No candidates here';
			const sections = extractCandidateSection(text);

			expect(sections).toEqual([]);
		});
	});

	describe('parseCandidate', () => {
		it('should parse complete candidate section', () => {
			const section = `Label: Complete Job
Description: A fully specified job
Confidence: 0.9
Requirements:
  - data_source: API endpoint
  - process_description: Transform and validate
  - output_format: JSON
  - schedule: Hourly`;

			const result = parseCandidate(section, 1);

			expect(result).not.toBeNull();
			expect(result!.id).toBe('candidate-1');
			expect(result!.label).toBe('Complete Job');
			expect(result!.description).toBe('A fully specified job');
			expect(result!.confidence).toBe(0.9);
			expect(result!.requirements.data_source).toBe('API endpoint');
			expect(result!.requirements.process_description).toBe('Transform and validate');
			expect(result!.requirements.output_format).toBe('JSON');
			expect(result!.requirements.schedule).toBe('Hourly');
		});

		it('should handle missing optional fields', () => {
			const section = `Label: Minimal Job
Requirements:
  - data_source: CSV`;

			const result = parseCandidate(section, 1);

			expect(result).not.toBeNull();
			expect(result!.label).toBe('Minimal Job');
			expect(result!.description).toBe('');
			expect(result!.confidence).toBe(0);
			expect(result!.requirements.data_source).toBe('CSV');
			expect(result!.requirements.process_description).toBeNull();
		});

		it('should calculate completeness based on filled requirements', () => {
			const section = `Label: Partial Requirements
Requirements:
  - data_source: CSV
  - output_format: Excel`;

			const result = parseCandidate(section, 1);

			// 2 out of 4 requirements = 0.5 completeness
			expect(result!.requirements.completeness).toBe(0.5);
		});

		it('should set completeness to 1 when all requirements are filled', () => {
			const section = `Label: Complete Requirements
Requirements:
  - data_source: CSV
  - process_description: Process data
  - output_format: Excel
  - schedule: Daily`;

			const result = parseCandidate(section, 1);

			expect(result!.requirements.completeness).toBe(1);
		});

		it('should handle multiline descriptions', () => {
			const section = `Label: Multiline Test
Description: This is a long description
that spans multiple lines
and should be joined together
Confidence: 0.8
Requirements:
  - data_source: Test`;

			const result = parseCandidate(section, 1);

			expect(result!.description).toContain('that spans multiple lines');
		});

		it('should trim whitespace from values', () => {
			const section = `Label:   Whitespace Test
Description:   Description with spaces
Requirements:
  - data_source:   Trimmed Source   `;

			const result = parseCandidate(section, 1);

			expect(result!.label).toBe('Whitespace Test');
			expect(result!.description).toBe('Description with spaces');
			expect(result!.requirements.data_source).toBe('Trimmed Source');
		});
	});

	describe('edge cases', () => {
		it('should handle Japanese text in candidates', () => {
			const response = `[CANDIDATE:1]
Label: データ分析パイプライン
Description: CSVファイルを処理してExcelレポートを出力
Confidence: 0.9
Requirements:
  - data_source: S3バケットのCSVファイル
  - process_description: 地域別売上データを集計
  - output_format: グラフ付きExcelレポート
  - schedule: 毎日9時
[/CANDIDATE]`;

			const result = parseCandidatesFromResponse(response);

			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('データ分析パイプライン');
			expect(result[0].requirements.schedule).toBe('毎日9時');
		});

		it('should handle special characters in values', () => {
			const response = `[CANDIDATE:1]
Label: Test with "quotes" and 'apostrophes'
Description: Description with <html> & special chars
Requirements:
  - data_source: s3://bucket/path/to/file.csv
[/CANDIDATE]`;

			const result = parseCandidatesFromResponse(response);

			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('Test with "quotes" and \'apostrophes\'');
			expect(result[0].requirements.data_source).toBe('s3://bucket/path/to/file.csv');
		});

		it('should handle empty requirements section', () => {
			const response = `[CANDIDATE:1]
Label: No Requirements
Description: A candidate without explicit requirements
Confidence: 0.5
Requirements:
[/CANDIDATE]`;

			const result = parseCandidatesFromResponse(response);

			expect(result).toHaveLength(1);
			expect(result[0].requirements.completeness).toBe(0);
		});

		it('should ignore invalid candidate numbers', () => {
			const response = `[CANDIDATE:abc]
Label: Invalid Number
[/CANDIDATE]`;

			const result = parseCandidatesFromResponse(response);

			// Should still parse with auto-generated ID
			expect(result).toHaveLength(1);
		});
	});
});
