/**
 * System Prompt Template
 *
 * Issue #364: System prompt for workflow generation
 */

import { TASKFLOW_RULES } from './taskflow-rules.js';

/**
 * Build system prompt with capabilities
 *
 * @param capabilitiesSection - Formatted capabilities section
 * @returns Complete system prompt
 */
export function buildSystemPromptTemplate(capabilitiesSection: string): string {
  return `${TASKFLOW_RULES}

## Available Capabilities

The following capabilities are available for use in your workflow.
**IMPORTANT**: Use the full URL endpoint (not capability_id) when creating api_rest steps.

${capabilitiesSection}

## Instructions

1. Analyze the task requirements carefully
2. Design a workflow that accomplishes the task
3. For api_rest steps, ALWAYS use full URL (e.g., http://localhost:8004/v1/utility/google_search)
4. NEVER use capability_id - it is not supported
5. Put request body directly in config.body, not in params
6. Ensure all variable references use \${...} syntax
7. Output ONLY the JSON workflow definition
8. Do not include any explanation or markdown formatting around the JSON
`;
}

/**
 * Default system prompt when no capabilities are provided
 */
export const DEFAULT_SYSTEM_PROMPT = `${TASKFLOW_RULES}

## Instructions

1. Analyze the task requirements carefully
2. Design a workflow that accomplishes the task
3. Use appropriate step types for each operation
4. Ensure all variable references are valid
5. Output ONLY the JSON workflow definition
6. Do not include any explanation or markdown formatting around the JSON
`;
