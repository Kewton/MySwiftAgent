/**
 * EvaluationDetailsPanel Component Tests
 * Issue #305: Task Workflow Traces Summary Feature
 *
 * Tests for the evaluation details panel that shows LLM evaluation results.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import EvaluationDetailsPanel from '$lib/components/generation/EvaluationDetailsPanel.svelte';
import type { EvaluationSummary } from '$lib/types/workflow-summary';

// Mock $app/stores
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({
				url: { pathname: '/projects/proj_001/workbenches/wb_001/generate' },
				params: { projectId: 'proj_001', workbenchId: 'wb_001' }
			});
			return () => {};
		})
	}
}));

describe('EvaluationDetailsPanel', () => {
	const createHighScoreEvaluation = (): EvaluationSummary => ({
		score: 92,
		structural_score: 95,
		requirement_score: 90,
		output_quality_score: 88,
		error_handling_score: 85,
		test_data_quality_score: 94,
		strengths: [
			'Excellent API parameter configuration',
			'Proper data flow between nodes',
			'Well-structured YAML output'
		],
		weaknesses: ['Missing timeout configuration'],
		suggestions: [
			'Consider adding retry logic for API calls',
			'Add input validation for edge cases'
		],
		confidence: 0.95
	});

	const createMediumScoreEvaluation = (): EvaluationSummary => ({
		score: 72,
		structural_score: 80,
		requirement_score: 75,
		output_quality_score: 65,
		error_handling_score: 60,
		test_data_quality_score: 78,
		strengths: ['Basic functionality works'],
		weaknesses: ['Poor error handling', 'Missing edge case coverage'],
		suggestions: ['Improve error handling', 'Add more test cases'],
		confidence: 0.85
	});

	const createLowScoreEvaluation = (): EvaluationSummary => ({
		score: 45,
		structural_score: 50,
		requirement_score: 40,
		output_quality_score: 42,
		error_handling_score: 35,
		test_data_quality_score: 48,
		strengths: [],
		weaknesses: [
			'Does not meet requirements',
			'Major structural issues',
			'No error handling'
		],
		suggestions: [
			'Redesign workflow structure',
			'Review requirements carefully'
		],
		confidence: 0.7
	});

	describe('Overall Score Display', () => {
		it('should display overall score prominently', () => {
			const evaluation = createHighScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			expect(screen.getByText('92')).toBeDefined();
		});

		it('should use green color for high scores (90-100)', () => {
			const evaluation = createHighScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should have green styling class
			const scoreElement = container.querySelector('.score-high, .score-excellent, [class*="green"]');
			expect(scoreElement).not.toBeNull();
		});

		it('should use blue color for medium scores (70-89)', () => {
			const evaluation = createMediumScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should have blue styling class
			const scoreElement = container.querySelector('.score-medium, .score-good, [class*="blue"]');
			expect(scoreElement).not.toBeNull();
		});

		it('should use yellow color for low-medium scores (50-69)', () => {
			const evaluation: EvaluationSummary = {
				...createMediumScoreEvaluation(),
				score: 55
			};
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should have fair (yellow) styling class
			const scoreElement = container.querySelector('.score-fair');
			expect(scoreElement).not.toBeNull();
		});

		it('should use red color for very low scores (0-49)', () => {
			const evaluation = createLowScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should have poor (red) styling class
			const scoreElement = container.querySelector('.score-poor');
			expect(scoreElement).not.toBeNull();
		});

		it('should handle null score gracefully', () => {
			const evaluation: EvaluationSummary = {
				...createHighScoreEvaluation(),
				score: null
			};
			render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should show N/A
			expect(screen.getByText('N/A')).toBeDefined();
		});
	});

	describe('Component Scores', () => {
		it('should display all 5 component scores', () => {
			const evaluation = createHighScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			// Check for score labels
			expect(screen.getByText(/structural/i)).toBeDefined();
			expect(screen.getByText(/requirement/i)).toBeDefined();
			expect(screen.getByText(/output.*quality/i)).toBeDefined();
			expect(screen.getByText(/error.*handling/i)).toBeDefined();
			expect(screen.getByText(/test.*data/i)).toBeDefined();
		});

		it('should display component score values', () => {
			const evaluation = createHighScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			expect(screen.getByText('95')).toBeDefined(); // structural
			expect(screen.getByText('90')).toBeDefined(); // requirement
			expect(screen.getByText('88')).toBeDefined(); // output_quality
			expect(screen.getByText('85')).toBeDefined(); // error_handling
			expect(screen.getByText('94')).toBeDefined(); // test_data_quality
		});

		it('should render progress bars for each component', () => {
			const evaluation = createHighScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should have progress bar elements
			const progressBars = container.querySelectorAll('[role="progressbar"], .progress-bar, .progress');
			expect(progressBars.length).toBeGreaterThanOrEqual(5);
		});

		it('should handle null component scores', () => {
			const evaluation: EvaluationSummary = {
				...createHighScoreEvaluation(),
				structural_score: null,
				error_handling_score: null
			};
			render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should not crash and show some indication
			expect(screen.getByText(/structural/i)).toBeDefined();
		});
	});

	describe('Strengths List', () => {
		it('should display all strengths', () => {
			const evaluation = createHighScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			expect(screen.getByText(/Excellent API parameter configuration/)).toBeDefined();
			expect(screen.getByText(/Proper data flow between nodes/)).toBeDefined();
			expect(screen.getByText(/Well-structured YAML output/)).toBeDefined();
		});

		it('should use success styling for strengths', () => {
			const evaluation = createHighScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Strengths section should have green/success styling
			const strengthsSection = container.querySelector('.strengths, [class*="strength"]');
			expect(strengthsSection).not.toBeNull();
		});

		it('should handle empty strengths list', () => {
			const evaluation = createLowScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should show "No strengths identified" or hide section
			expect(screen.queryByText(/Excellent/)).toBeNull();
		});
	});

	describe('Weaknesses List', () => {
		it('should display all weaknesses', () => {
			const evaluation = createMediumScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			expect(screen.getByText(/Poor error handling/)).toBeDefined();
			expect(screen.getByText(/Missing edge case coverage/)).toBeDefined();
		});

		it('should use warning styling for weaknesses', () => {
			const evaluation = createMediumScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Weaknesses section should have amber/warning styling
			const weaknessesSection = container.querySelector('.weaknesses, [class*="weakness"]');
			expect(weaknessesSection).not.toBeNull();
		});

		it('should handle empty weaknesses list', () => {
			const evaluation: EvaluationSummary = {
				...createHighScoreEvaluation(),
				weaknesses: []
			};
			render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should show "No weaknesses" or hide section
			expect(screen.queryByText(/Poor error handling/)).toBeNull();
		});
	});

	describe('Suggestions List', () => {
		it('should display all suggestions', () => {
			const evaluation = createHighScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			expect(screen.getByText(/Consider adding retry logic/)).toBeDefined();
			expect(screen.getByText(/Add input validation/)).toBeDefined();
		});

		it('should use info styling for suggestions', () => {
			const evaluation = createHighScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Suggestions section should have blue/info styling
			const suggestionsSection = container.querySelector('.suggestions, [class*="suggestion"]');
			expect(suggestionsSection).not.toBeNull();
		});

		it('should handle empty suggestions list', () => {
			const evaluation: EvaluationSummary = {
				...createHighScoreEvaluation(),
				suggestions: []
			};
			render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should hide suggestions section
			expect(screen.queryByText(/Consider adding/)).toBeNull();
		});
	});

	describe('Confidence Indicator', () => {
		it('should display confidence value', () => {
			const evaluation = createHighScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			// 0.95 should be displayed as 95% or 0.95
			expect(screen.getByText(/0\.95|95%/)).toBeDefined();
		});

		it('should handle null confidence', () => {
			const evaluation: EvaluationSummary = {
				...createHighScoreEvaluation(),
				confidence: null
			};
			render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should not crash
			expect(screen.getByText('92')).toBeDefined();
		});

		it('should show visual indicator for confidence level', () => {
			const evaluation = createHighScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should have some visual confidence indicator
			const confidenceIndicator = container.querySelector('.confidence, [class*="confidence"]');
			expect(confidenceIndicator).not.toBeNull();
		});
	});

	describe('Accessibility', () => {
		it('should have proper ARIA roles', () => {
			const evaluation = createHighScoreEvaluation();
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Section with aria-label is implicitly a region
			const section = container.querySelector('section[aria-label*="Evaluation"]');
			expect(section).not.toBeNull();
		});

		it('should have proper heading structure', () => {
			const evaluation = createHighScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			const headings = screen.getAllByRole('heading');
			expect(headings.length).toBeGreaterThanOrEqual(1);
		});

		it('should have proper list roles for strengths/weaknesses', () => {
			const evaluation = createHighScoreEvaluation();
			render(EvaluationDetailsPanel, { props: { evaluation } });

			const lists = screen.getAllByRole('list');
			expect(lists.length).toBeGreaterThanOrEqual(1);
		});
	});

	describe('Edge Cases', () => {
		it('should handle all null scores', () => {
			const evaluation: EvaluationSummary = {
				score: null,
				structural_score: null,
				requirement_score: null,
				output_quality_score: null,
				error_handling_score: null,
				test_data_quality_score: null,
				strengths: [],
				weaknesses: [],
				suggestions: [],
				confidence: null
			};
			const { container } = render(EvaluationDetailsPanel, { props: { evaluation } });

			// Should not crash
			const section = container.querySelector('section[aria-label*="Evaluation"]');
			expect(section).not.toBeNull();
		});

		it('should handle score of 0', () => {
			const evaluation: EvaluationSummary = {
				...createLowScoreEvaluation(),
				score: 0
			};
			render(EvaluationDetailsPanel, { props: { evaluation } });

			expect(screen.getByText('0')).toBeDefined();
		});

		it('should handle score of 100', () => {
			const evaluation: EvaluationSummary = {
				...createHighScoreEvaluation(),
				score: 100
			};
			render(EvaluationDetailsPanel, { props: { evaluation } });

			expect(screen.getByText('100')).toBeDefined();
		});
	});
});
