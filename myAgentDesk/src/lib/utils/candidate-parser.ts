/**
 * candidate-parser.ts - LLM response candidate parser
 *
 * Parses candidate interpretations from LLM responses in the format:
 * [CANDIDATE:N]
 * Label: ...
 * Description: ...
 * Confidence: ...
 * Requirements:
 *   - data_source: ...
 *   - process_description: ...
 *   - output_format: ...
 *   - schedule: ...
 * [/CANDIDATE]
 *
 * Issue #192: Create Job MLOps UI integration
 * Task 1.1: LLM response parser implementation
 */

import type { RequirementState } from '$lib/mlops/types';

/**
 * Parsed candidate structure matching the Candidate type from MLOps types
 */
export interface ParsedCandidate {
	id: string;
	label: string;
	description: string;
	confidence: number;
	requirements: RequirementState;
}

/**
 * Regular expression patterns for parsing candidates
 */
const CANDIDATE_BLOCK_PATTERN = /\[CANDIDATE:(\d+|[a-zA-Z]+)\]([\s\S]*?)\[\/CANDIDATE\]/g;

/**
 * Parses candidates from an LLM response string
 *
 * @param response - The full LLM response text
 * @returns Array of parsed candidates
 */
export function parseCandidatesFromResponse(response: string): ParsedCandidate[] {
	if (!response || response.trim() === '') {
		return [];
	}

	const sections = extractCandidateSection(response);
	if (sections.length === 0) {
		return [];
	}

	const candidates: ParsedCandidate[] = [];
	let index = 1;

	for (const section of sections) {
		const parsed = parseCandidate(section, index);
		if (parsed) {
			candidates.push(parsed);
			index++;
		}
	}

	return candidates;
}

/**
 * Extracts candidate sections from text
 *
 * @param text - Text containing candidate blocks
 * @returns Array of candidate section contents (without the delimiters)
 */
export function extractCandidateSection(text: string): string[] {
	const sections: string[] = [];
	const pattern = new RegExp(CANDIDATE_BLOCK_PATTERN.source, 'g');
	let match;

	while ((match = pattern.exec(text)) !== null) {
		// match[2] contains the content between [CANDIDATE:N] and [/CANDIDATE]
		sections.push(match[2].trim());
	}

	return sections;
}

/**
 * Parses a single candidate section into a ParsedCandidate
 *
 * @param section - The content of a candidate section (without delimiters)
 * @param index - The candidate index (1-based)
 * @returns Parsed candidate or null if parsing fails
 */
export function parseCandidate(section: string, index: number): ParsedCandidate | null {
	const lines = section.split('\n');

	let label = '';
	let description = '';
	let confidence = 0;
	let inRequirements = false;
	let inDescription = false;
	const descriptionLines: string[] = [];

	const requirements: RequirementState = {
		data_source: null,
		process_description: null,
		output_format: null,
		schedule: null,
		completeness: 0
	};

	for (const line of lines) {
		const trimmedLine = line.trim();

		// Check for Label
		if (trimmedLine.startsWith('Label:')) {
			label = trimmedLine.substring('Label:'.length).trim();
			inDescription = false;
			inRequirements = false;
			continue;
		}

		// Check for Description start
		if (trimmedLine.startsWith('Description:')) {
			const descContent = trimmedLine.substring('Description:'.length).trim();
			if (descContent) {
				descriptionLines.push(descContent);
			}
			inDescription = true;
			inRequirements = false;
			continue;
		}

		// Check for Confidence
		if (trimmedLine.startsWith('Confidence:')) {
			const confStr = trimmedLine.substring('Confidence:'.length).trim();
			confidence = parseConfidence(confStr);
			inDescription = false;
			inRequirements = false;
			continue;
		}

		// Check for Requirements section start
		if (trimmedLine.startsWith('Requirements:')) {
			inRequirements = true;
			inDescription = false;
			continue;
		}

		// Handle multiline description
		if (inDescription && trimmedLine && !trimmedLine.startsWith('-')) {
			descriptionLines.push(trimmedLine);
			continue;
		}

		// Handle requirement items
		if (inRequirements && trimmedLine.startsWith('-')) {
			const reqLine = trimmedLine.substring(1).trim();
			const colonIndex = reqLine.indexOf(':');
			if (colonIndex > 0) {
				const key = reqLine.substring(0, colonIndex).trim();
				const value = reqLine.substring(colonIndex + 1).trim();

				if (key === 'data_source' && value) {
					requirements.data_source = value;
				} else if (key === 'process_description' && value) {
					requirements.process_description = value;
				} else if (key === 'output_format' && value) {
					requirements.output_format = value;
				} else if (key === 'schedule' && value) {
					requirements.schedule = value;
				}
			}
		}
	}

	// Join description lines
	description = descriptionLines.join(' ').trim();

	// Label is required
	if (!label) {
		return null;
	}

	// Calculate completeness
	requirements.completeness = calculateCompleteness(requirements);

	return {
		id: `candidate-${index}`,
		label,
		description,
		confidence,
		requirements
	};
}

/**
 * Parses a confidence value from string
 *
 * @param confStr - Confidence string (e.g., "0.85", "85%", "85")
 * @returns Normalized confidence value between 0 and 1
 */
function parseConfidence(confStr: string): number {
	if (!confStr) return 0;

	// Remove % if present
	if (confStr.endsWith('%')) {
		const num = parseFloat(confStr.slice(0, -1));
		return isNaN(num) ? 0 : num / 100;
	}

	const num = parseFloat(confStr);
	if (isNaN(num)) return 0;

	// If value is > 1, assume it's a percentage
	if (num > 1) {
		return num / 100;
	}

	return num;
}

/**
 * Calculates the completeness score based on filled requirements
 *
 * @param requirements - The RequirementState object
 * @returns Completeness score between 0 and 1
 */
function calculateCompleteness(requirements: RequirementState): number {
	const fields: (keyof Omit<RequirementState, 'completeness'>)[] = [
		'data_source',
		'process_description',
		'output_format',
		'schedule'
	];

	const filledCount = fields.filter((field) => requirements[field] !== null).length;
	return filledCount / fields.length;
}

/**
 * Checks if a response contains any candidate markers
 *
 * @param response - The LLM response text
 * @returns True if candidates are present
 */
export function hasCandidates(response: string): boolean {
	// Create a new RegExp instance to avoid global state issues with lastIndex
	const pattern = new RegExp(CANDIDATE_BLOCK_PATTERN.source);
	return pattern.test(response);
}
