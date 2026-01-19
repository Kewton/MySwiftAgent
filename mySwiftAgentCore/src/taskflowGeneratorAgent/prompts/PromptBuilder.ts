/**
 * PromptBuilder - Constructs prompts for workflow generation
 *
 * Issue #364: Prompt construction with capability injection
 * Issue #374: Enhanced capability formatting and feedback loop support
 */

import type { LLMPrompt } from '../types/llm.js';
import type { TaskGenerationRequest, Capability, CapabilityForPrompt } from '../types/generator.js';
import { buildSystemPromptTemplate, DEFAULT_SYSTEM_PROMPT } from './templates/system.js';
import { WorkflowCapabilityError } from '../types/errors.js';
import {
  STOP_WORDS,
  RELEVANCE_SCORING,
  FREQUENT_CATEGORIES,
  MAX_CAPABILITIES_PER_PROMPT,
} from '../constants.js';

/**
 * PromptBuilder - Builds prompts for LLM workflow generation
 *
 * Features:
 * - System prompt with TaskFlow rules
 * - Capability injection into prompts
 * - Task-specific user prompts
 * - Issue #374: Enhanced capability formatting
 * - Issue #374: Feedback prompt for validation retries
 * - Issue #374: Intelligent capability selection
 */
export class PromptBuilder {
  /**
   * Build complete prompt for task generation
   *
   * Issue #374: Uses selectRelevantCapabilities to filter capabilities
   * based on task description when count exceeds MAX_CAPABILITIES_PER_PROMPT
   *
   * @param task - Task generation request
   * @param capabilities - Available capabilities
   * @returns LLM prompt
   */
  buildPrompt(task: TaskGenerationRequest, capabilities: Capability[]): LLMPrompt {
    // Issue #374: Select relevant capabilities based on task
    const enhancedCapabilities = capabilities as CapabilityForPrompt[];
    const selectedCapabilities = this.selectRelevantCapabilities(
      task,
      enhancedCapabilities,
      MAX_CAPABILITIES_PER_PROMPT
    );

    return {
      system: this.buildSystemPromptWithCapabilities(selectedCapabilities as Capability[]),
      user: this.buildUserPrompt(task),
    };
  }

  /**
   * Build system prompt with capabilities (public API)
   *
   * @param capabilities - Available capabilities
   * @returns System prompt string
   */
  buildSystemPrompt(capabilities: Capability[]): string {
    return this.buildSystemPromptWithCapabilities(capabilities);
  }

  /**
   * Build system prompt with capabilities (internal)
   *
   * @param capabilities - Pre-filtered capabilities
   * @returns System prompt string
   */
  private buildSystemPromptWithCapabilities(capabilities: Capability[]): string {
    // Filter to only available capabilities
    const availableCapabilities = capabilities.filter(
      (c) => c.status === 'available'
    );

    if (availableCapabilities.length === 0) {
      return DEFAULT_SYSTEM_PROMPT;
    }

    const capabilitiesSection = this.formatCapabilities(availableCapabilities);
    return buildSystemPromptTemplate(capabilitiesSection);
  }

  /**
   * Build user prompt for task
   *
   * @param task - Task generation request
   * @returns User prompt string
   */
  buildUserPrompt(task: TaskGenerationRequest): string {
    const sections: string[] = [];

    // Task header
    sections.push(`# Task: ${task.name}`);
    sections.push('');

    // Task ID
    sections.push(`**Task ID**: ${task.task_id}`);
    if (task.task_master_id) {
      sections.push(`**Task Master ID**: ${task.task_master_id}`);
    }
    sections.push('');

    // Description
    sections.push('## Description');
    sections.push(task.description);
    sections.push('');

    // Dependencies
    if (task.dependencies && task.dependencies.length > 0) {
      sections.push('## Dependencies');
      sections.push(`This task depends on: ${task.dependencies.join(', ')}`);
      sections.push('You may reference outputs from these tasks using $steps.<task_id>.<field>');
      sections.push('');
    }

    // Interface
    sections.push('## Interface Definition');
    sections.push('');
    sections.push('### Input');
    sections.push(this.formatInterface(task.interface.input));
    sections.push('');
    sections.push('### Output');
    sections.push(this.formatInterface(task.interface.output));
    sections.push('');

    // Instructions
    sections.push('## Instructions');
    sections.push('Generate a TaskFlow workflow JSON that:');
    sections.push(`1. Has workflow_name: "${this.generateWorkflowName(task)}"`);
    sections.push('2. Accepts the input schema defined above');
    sections.push('3. Produces the output schema defined above');
    sections.push('4. Uses available capabilities where appropriate');
    sections.push('');
    sections.push('Output ONLY the JSON workflow definition, no additional text.');

    return sections.join('\n');
  }

  /**
   * Format capabilities for prompt
   *
   * @param capabilities - Capabilities to format
   * @returns Formatted capabilities string
   */
  formatCapabilities(capabilities: Capability[]): string {
    // Group by category
    const byCategory = this.groupByCategory(capabilities);

    const sections: string[] = [];

    for (const [category, caps] of Object.entries(byCategory)) {
      sections.push(`### ${this.formatCategoryName(category)}`);
      sections.push('');

      for (const cap of caps) {
        sections.push(`#### ${cap.name} (\`${cap.id}\`)`);
        if (cap.description) {
          sections.push(cap.description);
        }
        sections.push(`- **Category**: ${cap.category}`);

        if (cap.parameters && cap.parameters.length > 0) {
          sections.push('- **Parameters**:');
          for (const param of cap.parameters) {
            const required = param.required ? '(required)' : '(optional)';
            const desc = param.description ? ` - ${param.description}` : '';
            sections.push(`  - \`${param.name}\`: ${param.type} ${required}${desc}`);
          }
        }
        sections.push('');
      }
    }

    return sections.join('\n');
  }

  /**
   * Group capabilities by category
   */
  private groupByCategory(capabilities: Capability[]): Record<string, Capability[]> {
    const grouped: Record<string, Capability[]> = {};

    for (const cap of capabilities) {
      const category = cap.category;
      grouped[category] ??= [];
      grouped[category].push(cap);
    }

    return grouped;
  }

  /**
   * Format category name for display
   */
  private formatCategoryName(category: string): string {
    return category.charAt(0).toUpperCase() + category.slice(1) + ' Capabilities';
  }

  /**
   * Format interface definition
   */
  private formatInterface(iface: Record<string, string> | undefined): string {
    if (!iface || Object.keys(iface).length === 0) {
      return '(none)';
    }

    const lines: string[] = [];
    for (const [key, type] of Object.entries(iface)) {
      lines.push(`- \`${key}\`: ${type}`);
    }
    return lines.join('\n');
  }

  /**
   * Generate workflow name from task
   */
  private generateWorkflowName(task: TaskGenerationRequest): string {
    // Convert task name to snake_case and append task_id
    const baseName = task.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');

    return `${baseName}_${task.task_id}`;
  }

  // ==================================================
  // Issue #374: Enhanced Capability Formatting
  // ==================================================

  /**
   * Format capabilities with enhanced details for LLM prompt
   *
   * Issue #374: Enhanced formatting includes:
   * - Validation constraints (min, max, enum)
   * - Default values
   * - Response schema
   * - TaskFlow step examples
   * - Use cases from metadata
   *
   * @param capabilities - Enhanced capabilities to format
   * @returns Formatted capabilities string
   */
  formatCapabilitiesEnhanced(capabilities: CapabilityForPrompt[]): string {
    const byCategory = this.groupByCategory(capabilities as Capability[]);
    const sections: string[] = [];

    for (const [category, caps] of Object.entries(byCategory)) {
      sections.push(`### ${this.formatCategoryName(category)}`);
      sections.push('');

      for (const cap of caps) {
        const capEnhanced = cap as unknown as CapabilityForPrompt;
        sections.push(`#### ${cap.name} (\`${cap.id}\`)`);

        if (cap.description) {
          sections.push(cap.description);
        }

        sections.push(`- **Category**: ${cap.category}`);

        // Parameters with validation constraints
        if (cap.parameters && cap.parameters.length > 0) {
          sections.push('- **Parameters**:');
          for (const param of cap.parameters) {
            const required = param.required ? '(required)' : '(optional)';
            const desc = param.description ? ` - ${param.description}` : '';
            let line = `  - \`${param.name}\`: ${param.type} ${required}${desc}`;

            // Add default value
            if (param.defaultValue !== undefined) {
              line += ` (default: ${JSON.stringify(param.defaultValue)})`;
            }

            // Add validation constraints
            if (param.validation) {
              const constraints: string[] = [];
              if (param.validation.min !== undefined) {
                constraints.push(`min: ${param.validation.min}`);
              }
              if (param.validation.max !== undefined) {
                constraints.push(`max: ${param.validation.max}`);
              }
              if (param.validation.enum) {
                constraints.push(`enum: [${param.validation.enum.map(v => JSON.stringify(v)).join(', ')}]`);
              }
              if (param.validation.pattern) {
                constraints.push(`pattern: ${param.validation.pattern}`);
              }
              if (constraints.length > 0) {
                line += ` [${constraints.join(', ')}]`;
              }
            }

            sections.push(line);
          }
        }

        // Response Schema
        if (capEnhanced.responseSchema) {
          sections.push('- **Response Schema**:');
          sections.push('  ```json');
          sections.push('  ' + JSON.stringify(capEnhanced.responseSchema, null, 2).replace(/\n/g, '\n  '));
          sections.push('  ```');
        }

        // Use Cases
        if (capEnhanced.metadata?.use_cases && capEnhanced.metadata.use_cases.length > 0) {
          sections.push('- **Use Cases**:');
          for (const useCase of capEnhanced.metadata.use_cases) {
            sections.push(`  - ${useCase}`);
          }
        }

        // TaskFlow Examples
        if (capEnhanced.examples && capEnhanced.examples.length > 0) {
          sections.push('- **TaskFlow Example**:');
          for (const example of capEnhanced.examples) {
            // Issue #374: Skip examples without taskflow_step
            if (!example.taskflow_step) {
              continue;
            }
            sections.push(`  - ${example.description}:`);
            sections.push('  ```json');
            const stepJson = JSON.stringify(example.taskflow_step, null, 2);
            sections.push('  ' + (stepJson ?? '{}').replace(/\n/g, '\n  '));
            sections.push('  ```');
          }
        }

        sections.push('');
      }
    }

    return sections.join('\n');
  }

  /**
   * Build feedback prompt for retry with validation errors
   *
   * Issue #374: Creates a prompt that includes:
   * - Original requirements
   * - Previous attempt output
   * - Detailed validation errors
   * - Enhanced capability info for problem areas
   *
   * @param originalPrompt - Original user prompt
   * @param error - LLMValidationError from previous attempt
   * @param capabilities - Available capabilities
   * @returns Feedback prompt string
   */
  buildFeedbackPrompt(
    originalPrompt: string,
    error: WorkflowCapabilityError,
    capabilities: CapabilityForPrompt[]
  ): string {
    const sections: string[] = [];

    // Error summary from the error class
    sections.push(error.toFeedbackSummary());
    sections.push('');

    // Original requirements
    sections.push('## Original Requirements');
    sections.push(originalPrompt);
    sections.push('');

    // Previous attempt
    sections.push('## Previous Attempt (Failed)');
    sections.push('```json');
    sections.push(error.rawContent);
    sections.push('```');
    sections.push('');

    // Extract problem capabilities from errors
    const problemCapabilityIds = new Set<string>();
    for (const err of error.validationResult.errors ?? []) {
      // Check if error has capability field (extended error)
      const errAny = err as Record<string, unknown>;
      if (typeof errAny['capability'] === 'string') {
        problemCapabilityIds.add(errAny['capability']);
      }
    }

    // Show problem capabilities with enhanced details
    if (problemCapabilityIds.size > 0) {
      sections.push('## Relevant Capabilities (Review Carefully)');
      const problemCaps = capabilities.filter(c => problemCapabilityIds.has(c.id));
      if (problemCaps.length > 0) {
        sections.push(this.formatCapabilitiesEnhanced(problemCaps));
      }
    } else {
      // Show all capabilities if no specific ones identified
      sections.push('## Available Capabilities');
      sections.push(this.formatCapabilitiesEnhanced(capabilities));
    }

    sections.push('');
    sections.push('## Instructions');
    sections.push('Please fix the validation errors and generate a corrected workflow.');
    sections.push('Pay special attention to:');
    sections.push('1. Required parameters must be provided');
    sections.push('2. Parameter types must match the specification');
    sections.push('3. Parameter values must be within valid ranges');
    sections.push('');
    sections.push('Output ONLY the corrected JSON workflow definition.');

    return sections.join('\n');
  }

  /**
   * Select relevant capabilities based on task description
   *
   * Issue #374: Intelligent capability selection to reduce prompt size
   * Uses keyword matching and scoring to prioritize relevant capabilities
   *
   * @param task - Task generation request
   * @param capabilities - All available capabilities
   * @param maxCount - Maximum capabilities to include (default: MAX_CAPABILITIES_PER_PROMPT)
   * @returns Selected capabilities sorted by relevance
   */
  selectRelevantCapabilities(
    task: TaskGenerationRequest,
    capabilities: CapabilityForPrompt[],
    maxCount: number = MAX_CAPABILITIES_PER_PROMPT
  ): CapabilityForPrompt[] {
    // If under limit, return all
    if (capabilities.length <= maxCount) {
      return [...capabilities];
    }

    // Extract keywords from task
    const keywords = this.extractKeywords(`${task.name} ${task.description}`);

    // Score and sort capabilities
    const scored = capabilities.map(cap => ({
      capability: cap,
      score: this.calculateRelevanceScore(cap, keywords),
    }));

    scored.sort((a, b) => b.score - a.score);

    // Return top N
    return scored.slice(0, maxCount).map(s => s.capability);
  }

  /**
   * Extract keywords from text
   *
   * Issue #374: Extract meaningful keywords for capability matching
   * Removes stop words and short words
   *
   * @param text - Text to extract keywords from
   * @returns Array of lowercase keywords
   */
  extractKeywords(text: string): string[] {
    // Normalize: lowercase, split on non-word chars (including hyphens/underscores)
    const words = text
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter(w => w.length >= 3) // Filter short words
      .filter(w => !STOP_WORDS.includes(w)); // Filter stop words

    // Return unique
    return [...new Set(words)];
  }

  /**
   * Calculate relevance score for a capability
   *
   * Issue #374: Scoring based on keyword matches and category
   *
   * @param capability - Capability to score
   * @param keywords - Keywords from task
   * @returns Relevance score (higher = more relevant)
   */
  calculateRelevanceScore(capability: CapabilityForPrompt, keywords: string[]): number {
    let score = 0;

    const capName = capability.name.toLowerCase();
    const capDesc = (capability.description ?? '').toLowerCase();
    const capId = capability.id.toLowerCase();

    for (const keyword of keywords) {
      // Name matches (highest weight)
      if (capName.includes(keyword) || capId.includes(keyword)) {
        score += RELEVANCE_SCORING.NAME_MATCH;
      }

      // Description matches
      if (capDesc.includes(keyword)) {
        score += RELEVANCE_SCORING.DESCRIPTION_MATCH;
      }

      // Category matches
      if (capability.category.toLowerCase().includes(keyword)) {
        score += RELEVANCE_SCORING.CATEGORY_MATCH;
      }

      // Use case matches
      const useCases = capability.metadata?.use_cases ?? [];
      for (const useCase of useCases) {
        if (useCase.toLowerCase().includes(keyword)) {
          score += RELEVANCE_SCORING.USE_CASE_MATCH;
          break; // Only count once per keyword
        }
      }
    }

    // Bonus for frequent categories
    if (FREQUENT_CATEGORIES.includes(capability.category.toLowerCase())) {
      score += RELEVANCE_SCORING.FREQUENT_CATEGORY_BONUS;
    }

    return score;
  }
}

/**
 * Factory function
 */
export function createPromptBuilder(): PromptBuilder {
  return new PromptBuilder();
}
