/**
 * NodeConfigValidator - Validates node configuration based on type specifications
 *
 * Issue #375: Ensures each node type has required configuration
 * Issue #375 (iteration-2): Loads specs from config/node_types_spec.yaml
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import * as yaml from 'js-yaml';
import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type {
  ValidationResult,
  ValidationError,
  ValidationWarning,
} from '../../types/generator.js';
import type {
  TaskFlowDefinition,
  TaskFlowStep,
  NodeType,
} from '../../../taskflowEngine/types/TaskFlowDefinition.js';

// ESM compatibility: __dirname is not available in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Node type specification for validation
 */
export interface NodeTypeSpec {
  requiredConfig: string[];
  optionalConfig: string[];
  mutuallyExclusive?: string[][];
  oneOfRequired?: string[][];
  unsupportedConfig?: string[];
}

/**
 * YAML structure for a single node type
 */
interface YamlNodeTypeConfig {
  description?: string;
  supported_config?: Record<string, { type?: string; required?: boolean; description?: string }>;
  unsupported_config?: string[];
  validation_rules?: {
    rule: string;
    fields: string[];
    message?: string;
  }[];
}

/**
 * YAML root structure
 */
interface NodeTypesYaml {
  node_types: Record<string, YamlNodeTypeConfig>;
}

/**
 * Default fallback specs when YAML loading fails
 * These are kept for backward compatibility and testing
 */
const FALLBACK_NODE_TYPE_SPECS: Record<NodeType, NodeTypeSpec> = {
  transform: {
    requiredConfig: [],
    optionalConfig: ['template', 'mapping'],
    oneOfRequired: [['template', 'mapping']],
    unsupportedConfig: ['expression'],
  },
  api_rest: {
    requiredConfig: [],
    optionalConfig: ['capability_id', 'url', 'method', 'headers', 'body'],
    oneOfRequired: [['capability_id', 'url']],
  },
  llm: {
    requiredConfig: ['prompt'],
    optionalConfig: ['model', 'temperature', 'max_tokens', 'system_prompt'],
  },
  code_js: {
    requiredConfig: ['code'],
    optionalConfig: ['timeout', 'sandbox'],
  },
  parallel: {
    requiredConfig: ['branches'],
    optionalConfig: ['maxConcurrency', 'failFast'],
  },
  action: {
    requiredConfig: ['action_type'],
    optionalConfig: ['action_params', 'async'],
  },
};

/**
 * Load node type specifications from YAML file
 *
 * @param yamlPath - Path to the YAML configuration file
 * @returns Parsed NodeTypeSpec records or null if loading fails
 */
export function loadNodeTypeSpecsFromYaml(
  yamlPath: string
): Record<NodeType, NodeTypeSpec> | null {
  try {
    const content = fs.readFileSync(yamlPath, 'utf-8');
    const parsed = yaml.load(content) as NodeTypesYaml;

    if (!parsed?.node_types) {
      return null;
    }

    const specs: Partial<Record<NodeType, NodeTypeSpec>> = {};

    for (const [nodeType, config] of Object.entries(parsed.node_types)) {
      const spec: NodeTypeSpec = {
        requiredConfig: [],
        optionalConfig: [],
      };

      // Extract from supported_config
      if (config.supported_config) {
        for (const [fieldName, fieldConfig] of Object.entries(config.supported_config)) {
          if (fieldConfig.required) {
            spec.requiredConfig.push(fieldName);
          } else {
            spec.optionalConfig.push(fieldName);
          }
        }
      }

      // Extract unsupported config
      if (config.unsupported_config) {
        spec.unsupportedConfig = [...config.unsupported_config];
      }

      // Extract validation rules
      if (config.validation_rules) {
        for (const rule of config.validation_rules) {
          if (rule.rule === 'oneOf' && rule.fields) {
            spec.oneOfRequired ??= [];
            spec.oneOfRequired.push([...rule.fields]);
          } else if (rule.rule === 'required' && rule.fields) {
            // Add to requiredConfig if not already present
            for (const field of rule.fields) {
              if (!spec.requiredConfig.includes(field)) {
                spec.requiredConfig.push(field);
              }
            }
          }
        }
      }

      specs[nodeType as NodeType] = spec;
    }

    return specs as Record<NodeType, NodeTypeSpec>;
  } catch {
    return null;
  }
}

/**
 * Get NODE_TYPE_SPECS, loading from YAML if available
 * Falls back to hardcoded specs if YAML loading fails
 */
function getNodeTypeSpecs(): Record<NodeType, NodeTypeSpec> {
  // Try to load from YAML file
  const yamlPaths = [
    path.resolve(process.cwd(), 'config', 'node_types_spec.yaml'),
    path.resolve(__dirname, '../../../../config', 'node_types_spec.yaml'),
  ];

  for (const yamlPath of yamlPaths) {
    const specs = loadNodeTypeSpecsFromYaml(yamlPath);
    if (specs) {
      return specs;
    }
  }

  // Fallback to hardcoded specs
  return FALLBACK_NODE_TYPE_SPECS;
}

// Initialize NODE_TYPE_SPECS once at module load
let NODE_TYPE_SPECS: Record<NodeType, NodeTypeSpec> | null = null;

/**
 * Get cached or load NODE_TYPE_SPECS
 */
function getCachedNodeTypeSpecs(): Record<NodeType, NodeTypeSpec> {
  NODE_TYPE_SPECS ??= getNodeTypeSpecs();
  return NODE_TYPE_SPECS;
}

/**
 * Reset cached specs (for testing purposes)
 */
export function resetNodeTypeSpecsCache(): void {
  NODE_TYPE_SPECS = null;
}

/**
 * NodeConfigValidator - Validates node configurations
 *
 * Checks:
 * - Required config fields are present
 * - One-of-required fields have at least one present
 * - Unsupported config fields are not used
 * - Node-specific validation rules
 */
export class NodeConfigValidator implements Validator {
  readonly name = 'NodeConfigValidator';
  private readonly specs: Record<NodeType, NodeTypeSpec>;

  constructor() {
    this.specs = getCachedNodeTypeSpecs();
  }

  async validate(
    workflow: TaskFlowDefinition,
    _context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    const steps = workflow.steps ?? [];

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      if (!step) continue;

      this.validateStep(step, i, errors, warnings);
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Validate a single step's configuration
   */
  private validateStep(
    step: TaskFlowStep,
    stepIndex: number,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    const spec = this.specs[step.type];
    if (!spec) {
      warnings.push({
        code: 'UNKNOWN_NODE_TYPE',
        message: `Step "${step.id}" has unknown node type "${step.type}"`,
      });
      return;
    }

    const config = step.config;

    // Check required config
    for (const requiredKey of spec.requiredConfig) {
      if (!(requiredKey in config)) {
        const errorCode = this.getErrorCode(step.type, 'missing', requiredKey);
        errors.push({
          code: errorCode,
          message: `Step "${step.id}" (${step.type}) is missing required config "${requiredKey}"`,
          path: `steps[${stepIndex}].config.${requiredKey}`,
        });
      }
    }

    // Check one-of-required
    if (spec.oneOfRequired) {
      for (const oneOfGroup of spec.oneOfRequired) {
        const hasOne = oneOfGroup.some((key) => key in config && config[key] !== undefined);
        if (!hasOne) {
          const firstField = oneOfGroup[0] ?? 'unknown';
          const errorCode = this.getErrorCode(step.type, 'missing_one_of', firstField);
          errors.push({
            code: errorCode,
            message: `Step "${step.id}" (${step.type}) requires one of: ${oneOfGroup.join(', ')}`,
            path: `steps[${stepIndex}].config`,
          });
        }
      }
    }

    // Check unsupported config
    if (spec.unsupportedConfig) {
      for (const unsupportedKey of spec.unsupportedConfig) {
        if (unsupportedKey in config) {
          const errorCode = this.getErrorCode(step.type, 'unsupported', unsupportedKey);
          errors.push({
            code: errorCode,
            message: `Step "${step.id}" (${step.type}) uses unsupported config "${unsupportedKey}"`,
            path: `steps[${stepIndex}].config.${unsupportedKey}`,
          });
        }
      }
    }

    // Node-specific validation
    this.validateNodeSpecific(step, stepIndex, errors, warnings);
  }

  /**
   * Node-specific validation rules
   */
  private validateNodeSpecific(
    step: TaskFlowStep,
    stepIndex: number,
    errors: ValidationError[],
    _warnings: ValidationWarning[]
  ): void {
    switch (step.type) {
      case 'parallel':
        this.validateParallelNode(step, stepIndex, errors);
        break;
      // Add more node-specific validations as needed
    }
  }

  /**
   * Validate parallel node specific rules
   */
  private validateParallelNode(
    step: TaskFlowStep,
    stepIndex: number,
    errors: ValidationError[]
  ): void {
    const branches = step.config['branches'] as unknown[];
    if (branches && Array.isArray(branches) && branches.length === 0) {
      errors.push({
        code: 'PARALLEL_EMPTY_BRANCHES',
        message: `Step "${step.id}" (parallel) has empty branches array`,
        path: `steps[${stepIndex}].config.branches`,
      });
    }
  }

  /**
   * Generate error code based on node type and error type
   */
  private getErrorCode(nodeType: NodeType, errorType: string, field: string): string {
    const nodeTypeUpper = nodeType.toUpperCase().replace(/-/g, '_');

    switch (errorType) {
      case 'missing':
        return this.getMissingConfigErrorCode(nodeType, field);
      case 'missing_one_of':
        return this.getMissingOneOfErrorCode(nodeType);
      case 'unsupported':
        return `${nodeTypeUpper}_UNSUPPORTED_CONFIG`;
      default:
        return `${nodeTypeUpper}_CONFIG_ERROR`;
    }
  }

  /**
   * Get specific error code for missing required config
   */
  private getMissingConfigErrorCode(nodeType: NodeType, field: string): string {
    switch (nodeType) {
      case 'llm':
        if (field === 'prompt') return 'LLM_MISSING_PROMPT';
        break;
      case 'code_js':
        if (field === 'code') return 'CODE_JS_MISSING_CODE';
        break;
      case 'action':
        if (field === 'action_type') return 'ACTION_MISSING_TYPE';
        break;
    }
    return `${nodeType.toUpperCase()}_MISSING_${field.toUpperCase()}`;
  }

  /**
   * Get specific error code for missing one-of required config
   */
  private getMissingOneOfErrorCode(nodeType: NodeType): string {
    switch (nodeType) {
      case 'transform':
        return 'TRANSFORM_MISSING_CONFIG';
      case 'api_rest':
        return 'API_REST_MISSING_CONFIG';
      default:
        return `${nodeType.toUpperCase()}_MISSING_CONFIG`;
    }
  }

  /**
   * Get the current specs (for testing and debugging)
   */
  getSpecs(): Record<NodeType, NodeTypeSpec> {
    return this.specs;
  }
}

/**
 * Factory function
 */
export function createNodeConfigValidator(): NodeConfigValidator {
  return new NodeConfigValidator();
}
