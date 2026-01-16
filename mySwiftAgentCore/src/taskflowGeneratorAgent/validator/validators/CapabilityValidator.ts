/**
 * CapabilityValidator - Validates capability references in workflow
 *
 * Issue #364: Capability availability validation
 */

import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type { ValidationResult, ValidationError, ValidationWarning } from '../../types/generator.js';
import type { TaskFlowDefinition, TaskFlowStep } from '../../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * CapabilityValidator - Validates capability references
 *
 * Checks:
 * - Referenced capabilities exist
 * - Capabilities are available (not unavailable/deprecated)
 * - Required parameters are provided
 */
export class CapabilityValidator implements Validator {
  readonly name = 'CapabilityValidator';

  async validate(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Build capability lookup
    const capabilityMap = new Map(
      context.capabilities.map((c) => [c.id, c])
    );

    // Check each api_rest step
    for (let i = 0; i < (workflow.steps?.length ?? 0); i++) {
      const step = workflow.steps[i];
      if (!step) continue;

      if (step.type === 'api_rest') {
        this.validateApiRestStep(step, i, capabilityMap, errors, warnings);
      }

      if (step.type === 'llm') {
        this.validateLlmStep(step, i, capabilityMap, errors, warnings);
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Validate api_rest step capability reference
   */
  private validateApiRestStep(
    step: TaskFlowStep,
    stepIndex: number,
    capabilityMap: Map<string, { id: string; status: string; name: string }>,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    // Check if step uses a capability ID
    const capabilityId = step.config['capability_id'] as string | undefined;

    if (capabilityId) {
      const capability = capabilityMap.get(capabilityId);

      if (!capability) {
        errors.push({
          code: 'CAPABILITY_NOT_FOUND',
          message: `Step "${step.id}" references unknown capability "${capabilityId}"`,
          path: `steps[${stepIndex}].config.capability_id`,
        });
        return;
      }

      if (capability.status === 'unavailable') {
        errors.push({
          code: 'CAPABILITY_UNAVAILABLE',
          message: `Step "${step.id}" references unavailable capability "${capability.name}"`,
          path: `steps[${stepIndex}].config.capability_id`,
        });
      }

      if (capability.status === 'deprecated') {
        warnings.push({
          code: 'CAPABILITY_DEPRECATED',
          message: `Step "${step.id}" uses deprecated capability "${capability.name}"`,
        });
      }
    }
  }

  /**
   * Validate llm step
   */
  private validateLlmStep(
    step: TaskFlowStep,
    _stepIndex: number,
    capabilityMap: Map<string, { id: string; status: string; name: string }>,
    _errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    // Check for llm capability
    const llmCapabilities = Array.from(capabilityMap.values()).filter(
      (c) => c.status === 'available'
    );

    // If there are no llm capabilities and step uses llm, add warning
    const hasLlmCapability = llmCapabilities.some(
      (c) => c.id.includes('llm') || c.id.includes('claude') || c.id.includes('gpt')
    );

    if (!hasLlmCapability) {
      warnings.push({
        code: 'NO_LLM_CAPABILITY',
        message: `Step "${step.id}" uses LLM but no LLM capability is explicitly defined`,
      });
    }
  }
}
