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
Use these capability IDs when creating api_rest steps.

${capabilitiesSection}

## Instructions

1. Analyze the task requirements carefully
2. Design a workflow that accomplishes the task
3. Use available capabilities where appropriate
4. Ensure all variable references are valid
5. Output ONLY the JSON workflow definition
6. Do not include any explanation or markdown formatting around the JSON
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
