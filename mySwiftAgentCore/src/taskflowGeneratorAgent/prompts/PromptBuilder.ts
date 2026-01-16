/**
 * PromptBuilder - Constructs prompts for workflow generation
 *
 * Issue #364: Prompt construction with capability injection
 */

import type { LLMPrompt } from '../types/llm.js';
import type { TaskGenerationRequest, Capability } from '../types/generator.js';
import { buildSystemPromptTemplate, DEFAULT_SYSTEM_PROMPT } from './templates/system.js';

/**
 * PromptBuilder - Builds prompts for LLM workflow generation
 *
 * Features:
 * - System prompt with TaskFlow rules
 * - Capability injection into prompts
 * - Task-specific user prompts
 */
export class PromptBuilder {
  /**
   * Build complete prompt for task generation
   *
   * @param task - Task generation request
   * @param capabilities - Available capabilities
   * @returns LLM prompt
   */
  buildPrompt(task: TaskGenerationRequest, capabilities: Capability[]): LLMPrompt {
    return {
      system: this.buildSystemPrompt(capabilities),
      user: this.buildUserPrompt(task),
    };
  }

  /**
   * Build system prompt with capabilities
   *
   * @param capabilities - Available capabilities
   * @returns System prompt string
   */
  buildSystemPrompt(capabilities: Capability[]): string {
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
      if (!grouped[category]) {
        grouped[category] = [];
      }
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
}

/**
 * Factory function
 */
export function createPromptBuilder(): PromptBuilder {
  return new PromptBuilder();
}
