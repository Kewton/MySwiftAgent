/**
 * CapabilityCatalogGenerator - Generates capability catalogs from YAML files
 *
 * Issue #380: Capability Catalog generation
 * Scans YAML files, extracts responseSchema, and exports in multiple formats
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import * as yaml from 'js-yaml';
import type {
  CatalogCapability,
  CatalogOptions,
  CatalogGenerationResult,
  CapabilityCatalog,
  CatalogSummary,
  ResponseSchema,
  CapabilityScanResult,
} from '../types/catalog.js';
import { CatalogCapabilitySchema } from '../types/catalog.js';

/**
 * CapabilityCatalogGenerator - Main class for catalog generation
 */
export class CapabilityCatalogGenerator {
  private basePath: string;

  constructor(basePath?: string) {
    this.basePath = basePath ?? process.cwd();
  }

  /**
   * Scan capability files from a project directory
   */
  async scanCapabilities(projectId: string): Promise<CapabilityScanResult> {
    const capabilities: CatalogCapability[] = [];
    const warnings: string[] = [];

    const projectDir = path.join(this.basePath, projectId);

    try {
      const entries = await fs.readdir(projectDir, { withFileTypes: true });

      for (const entry of entries) {
        // Skip non-YAML files and index.yaml
        if (!entry.isFile()) continue;
        if (!entry.name.endsWith('.yaml') && !entry.name.endsWith('.yml')) continue;
        if (entry.name === 'index.yaml' || entry.name === 'index.yml') continue;

        const filePath = path.join(projectDir, entry.name);

        try {
          const content = await fs.readFile(filePath, 'utf-8');
          const parsed = yaml.load(content) as Record<string, unknown>;

          // Validate and transform to CatalogCapability
          const capability = this.parseCapability(parsed, entry.name);
          if (capability) {
            capabilities.push(capability);
          } else {
            warnings.push(`Failed to parse capability from ${entry.name}: Invalid structure`);
          }
        } catch (error) {
          warnings.push(`Error reading/parsing ${entry.name}: ${(error as Error).message}`);
        }
      }
    } catch (error) {
      warnings.push(`Error reading directory ${projectDir}: ${(error as Error).message}`);
    }

    return { capabilities, warnings };
  }

  /**
   * Parse raw YAML content into CatalogCapability
   */
  private parseCapability(raw: Record<string, unknown>, filename: string): CatalogCapability | null {
    try {
      // Map YAML fields to CatalogCapability structure
      const capability = {
        id: raw.id ?? raw.name ?? path.basename(filename, path.extname(filename)),
        name: raw.name,
        description: raw.description,
        version: raw.version,
        category: raw.category,
        status: raw.status,
        parameters: raw.parameters ?? [],
        returnType: raw.returnType,
        responseSchema: raw.responseSchema,
        tags: raw.tags,
        examples: raw.examples,
        metadata: raw.metadata,
      };

      // Validate against schema
      const result = CatalogCapabilitySchema.safeParse(capability);
      if (result.success) {
        return result.data;
      }

      return null;
    } catch {
      return null;
    }
  }

  /**
   * Extract responseSchema from capability
   */
  extractResponseSchema(capability: CatalogCapability): ResponseSchema | undefined {
    return capability.responseSchema;
  }

  /**
   * Generate catalog from scanned capabilities
   */
  async generateCatalog(projectId: string, options: CatalogOptions): Promise<CatalogGenerationResult> {
    const scanResult = await this.scanCapabilities(projectId);
    const warnings = [...scanResult.warnings];
    const errors: string[] = [];
    const generatedFiles: string[] = [];

    if (scanResult.capabilities.length === 0 && warnings.length > 0) {
      return {
        success: false,
        catalogPath: '',
        generatedFiles: [],
        warnings,
        errors: ['No capabilities found'],
      };
    }

    // Build catalog
    const catalog: CapabilityCatalog = {
      version: '1.0.0',
      generatedAt: new Date().toISOString(),
      capabilities: scanResult.capabilities,
      summary: this.calculateSummary(scanResult.capabilities),
    };

    // Export to requested formats
    try {
      await fs.mkdir(options.outputDir, { recursive: true });

      for (const format of options.outputFormats) {
        try {
          switch (format) {
            case 'json':
              await this.exportToJson(catalog, options.outputDir);
              generatedFiles.push('capabilities-catalog.json');
              break;
            case 'yaml':
              await this.exportToYaml(catalog, options.outputDir);
              generatedFiles.push('capabilities-catalog.yaml');
              break;
            case 'markdown':
              await this.exportToMarkdown(catalog, options.outputDir);
              generatedFiles.push('capabilities-catalog.md');
              break;
          }
        } catch (error) {
          errors.push(`Failed to export ${format}: ${(error as Error).message}`);
        }
      }
    } catch (error) {
      errors.push(`Failed to create output directory: ${(error as Error).message}`);
      return {
        success: false,
        catalogPath: options.outputDir,
        generatedFiles: [],
        warnings,
        errors,
      };
    }

    if (errors.length > 0) {
      return {
        success: false,
        catalogPath: options.outputDir,
        catalog,
        generatedFiles,
        warnings,
        errors,
      };
    }

    return {
      success: true,
      catalogPath: path.join(options.outputDir, 'capabilities-catalog.json'),
      catalog,
      generatedFiles,
      warnings,
    };
  }

  /**
   * Calculate summary statistics
   */
  private calculateSummary(capabilities: CatalogCapability[]): CatalogSummary {
    const byCategory: Record<string, number> = {};
    const byStatus = { available: 0, unavailable: 0, deprecated: 0 };
    let withResponseSchema = 0;
    let withoutResponseSchema = 0;

    for (const cap of capabilities) {
      // Count by category
      byCategory[cap.category] = (byCategory[cap.category] ?? 0) + 1;

      // Count by status
      byStatus[cap.status]++;

      // Count responseSchema presence
      if (cap.responseSchema && Object.keys(cap.responseSchema).length > 0) {
        withResponseSchema++;
      } else {
        withoutResponseSchema++;
      }
    }

    return {
      total: capabilities.length,
      byCategory,
      byStatus,
      withResponseSchema,
      withoutResponseSchema,
    };
  }

  /**
   * Export catalog to JSON format
   */
  async exportToJson(catalog: CapabilityCatalog, outputDir: string): Promise<void> {
    const filePath = path.join(outputDir, 'capabilities-catalog.json');
    const content = JSON.stringify(catalog, null, 2);
    await fs.writeFile(filePath, content, 'utf-8');
  }

  /**
   * Export catalog to YAML format
   */
  async exportToYaml(catalog: CapabilityCatalog, outputDir: string): Promise<void> {
    const filePath = path.join(outputDir, 'capabilities-catalog.yaml');
    const content = yaml.dump(catalog, {
      indent: 2,
      lineWidth: 120,
      noRefs: true,
    });
    await fs.writeFile(filePath, content, 'utf-8');
  }

  /**
   * Export catalog to Markdown format
   */
  async exportToMarkdown(catalog: CapabilityCatalog, outputDir: string): Promise<void> {
    const filePath = path.join(outputDir, 'capabilities-catalog.md');
    const content = this.generateMarkdown(catalog);
    await fs.writeFile(filePath, content, 'utf-8');
  }

  /**
   * Generate Markdown content from catalog
   */
  private generateMarkdown(catalog: CapabilityCatalog): string {
    const lines: string[] = [];

    // Header
    lines.push('# Capability Catalog');
    lines.push('');
    lines.push(`**Version**: ${catalog.version}`);
    lines.push(`**Generated**: ${catalog.generatedAt}`);
    lines.push('');

    // Summary
    lines.push('## Summary');
    lines.push('');
    lines.push(`- **Total Capabilities**: ${catalog.summary.total}`);
    lines.push(`- **With Response Schema**: ${catalog.summary.withResponseSchema}`);
    lines.push(`- **Without Response Schema**: ${catalog.summary.withoutResponseSchema}`);
    lines.push('');

    // By Category
    lines.push('### By Category');
    lines.push('');
    for (const [category, count] of Object.entries(catalog.summary.byCategory)) {
      lines.push(`- **${category}**: ${count}`);
    }
    lines.push('');

    // By Status
    lines.push('### By Status');
    lines.push('');
    lines.push(`- **Available**: ${catalog.summary.byStatus.available}`);
    lines.push(`- **Unavailable**: ${catalog.summary.byStatus.unavailable}`);
    lines.push(`- **Deprecated**: ${catalog.summary.byStatus.deprecated}`);
    lines.push('');

    // Capabilities
    lines.push('## Capabilities');
    lines.push('');

    for (const cap of catalog.capabilities) {
      lines.push(`### ${cap.name} (\`${cap.id}\`)`);
      lines.push('');
      lines.push(`**Description**: ${cap.description}`);
      lines.push('');
      lines.push(`- **Version**: ${cap.version}`);
      lines.push(`- **Category**: ${cap.category}`);
      lines.push(`- **Status**: ${cap.status}`);
      if (cap.tags && cap.tags.length > 0) {
        lines.push(`- **Tags**: ${cap.tags.join(', ')}`);
      }
      lines.push('');

      // Parameters
      if (cap.parameters && cap.parameters.length > 0) {
        lines.push('#### Parameters');
        lines.push('');
        lines.push('| Name | Type | Required | Description |');
        lines.push('|------|------|----------|-------------|');
        for (const param of cap.parameters) {
          lines.push(
            `| \`${param.name}\` | ${param.type} | ${param.required ? 'Yes' : 'No'} | ${param.description ?? ''} |`
          );
        }
        lines.push('');
      }

      // Response Schema
      if (cap.responseSchema && Object.keys(cap.responseSchema).length > 0) {
        lines.push('#### Response Schema');
        lines.push('');
        lines.push('```yaml');
        lines.push(yaml.dump(cap.responseSchema, { indent: 2 }));
        lines.push('```');
        lines.push('');
      }

      lines.push('---');
      lines.push('');
    }

    return lines.join('\n');
  }

  /**
   * Format catalog for AI prompt injection
   */
  formatForAIPrompt(catalog: CapabilityCatalog): string {
    const availableCapabilities = catalog.capabilities.filter((cap) => cap.status === 'available');

    const lines: string[] = [];
    lines.push('## Available Capabilities');
    lines.push('');

    for (const cap of availableCapabilities) {
      lines.push(`### ${cap.id}: ${cap.name}`);
      lines.push(`Description: ${cap.description}`);
      lines.push(`Category: ${cap.category}`);
      lines.push('');

      // Parameters
      if (cap.parameters && cap.parameters.length > 0) {
        lines.push('Parameters:');
        for (const param of cap.parameters) {
          const reqStr = param.required ? '(required)' : '(optional)';
          lines.push(`- ${param.name} [${param.type}] ${reqStr}: ${param.description ?? ''}`);
        }
        lines.push('');
      }

      // Response Schema
      if (cap.responseSchema && Object.keys(cap.responseSchema).length > 0) {
        lines.push('Response Fields:');
        for (const [fieldName, fieldDef] of Object.entries(cap.responseSchema)) {
          lines.push(`- ${fieldName} [${fieldDef.type}]: ${fieldDef.description ?? ''}`);
        }
        lines.push('');
      }

      lines.push('');
    }

    return lines.join('\n');
  }
}

/**
 * Factory function for creating CapabilityCatalogGenerator
 */
export function createCapabilityCatalogGenerator(basePath?: string): CapabilityCatalogGenerator {
  return new CapabilityCatalogGenerator(basePath);
}
