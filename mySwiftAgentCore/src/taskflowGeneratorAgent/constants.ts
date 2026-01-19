/**
 * Constants - Configuration constants for taskflowGeneratorAgent
 *
 * Issue #374: Prompt size limits and feedback loop configuration
 */

/**
 * Maximum number of capabilities to include in a prompt
 *
 * When the total capability count exceeds this limit,
 * capabilities are filtered by relevance to the task
 */
export const MAX_CAPABILITIES_PER_PROMPT = 50;

/**
 * Maximum description length for a single capability
 * Includes examples and all metadata
 */
export const MAX_CAPABILITY_DESCRIPTION_LENGTH = 2000;

/**
 * Maximum number of retry attempts for validation failures
 */
export const MAX_RETRY_COUNT = 3;

/**
 * Default timeout per generation attempt (milliseconds)
 */
export const DEFAULT_GENERATION_TIMEOUT_MS = 30000;

/**
 * Timeout multiplier for retry attempts
 * Each retry gets more time: baseTimeout * RETRY_TIMEOUT_MULTIPLIER^attempt
 */
export const RETRY_TIMEOUT_MULTIPLIER = 1.5;

/**
 * Stop words to exclude from keyword extraction
 */
export const STOP_WORDS = [
  'the', 'a', 'an', 'to', 'for', 'of', 'with', 'and', 'or',
  'in', 'on', 'at', 'by', 'from', 'that', 'this', 'is', 'are',
  'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
  'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
  'might', 'must', 'shall', 'can', 'it', 'its', 'they', 'them',
];

/**
 * Scoring weights for capability relevance
 */
export const RELEVANCE_SCORING = {
  NAME_MATCH: 10,
  DESCRIPTION_MATCH: 5,
  CATEGORY_MATCH: 3,
  USE_CASE_MATCH: 7,
  FREQUENT_CATEGORY_BONUS: 2,
};

/**
 * Frequently used capability categories
 */
export const FREQUENT_CATEGORIES = ['llm', 'search', 'communication', 'utility', 'api'];
