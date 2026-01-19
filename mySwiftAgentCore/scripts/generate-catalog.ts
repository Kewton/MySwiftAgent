#!/usr/bin/env npx tsx
/**
 * Generate Capability Catalog CLI Script
 *
 * Issue #380: CLI tool to generate capability catalogs
 *
 * Usage:
 *   npx tsx scripts/generate-catalog.ts [options]
 *
 * Options:
 *   --project, -p    Project ID (default: default_project)
 *   --formats, -f    Output formats: json,yaml,markdown (default: all)
 *   --output, -o     Output directory (default: config/capabilities/catalog)
 *   --help, -h       Show help
 */

import * as path from 'path';
import { CapabilityCatalogGenerator } from '../src/capabilities/catalog/CapabilityCatalogGenerator.js';
import type { CatalogOutputFormat, CatalogOptions } from '../src/capabilities/types/catalog.js';

interface CliArgs {
  project: string;
  formats: CatalogOutputFormat[];
  output: string;
  help: boolean;
}

function parseArgs(): CliArgs {
  const args = process.argv.slice(2);
  const result: CliArgs = {
    project: 'default_project',
    formats: ['json', 'yaml', 'markdown'],
    output: 'config/capabilities/catalog',
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    const nextArg = args[i + 1];

    switch (arg) {
      case '--project':
      case '-p':
        if (nextArg) {
          result.project = nextArg;
          i++;
        }
        break;

      case '--formats':
      case '-f':
        if (nextArg) {
          const formats = nextArg.split(',').map((f) => f.trim().toLowerCase()) as CatalogOutputFormat[];
          const validFormats = formats.filter((f) => ['json', 'yaml', 'markdown'].includes(f));
          if (validFormats.length > 0) {
            result.formats = validFormats;
          }
          i++;
        }
        break;

      case '--output':
      case '-o':
        if (nextArg) {
          result.output = nextArg;
          i++;
        }
        break;

      case '--help':
      case '-h':
        result.help = true;
        break;
    }
  }

  return result;
}

function showHelp(): void {
  console.log(`
Capability Catalog Generator

Usage:
  npx tsx scripts/generate-catalog.ts [options]

Options:
  --project, -p    Project ID (default: default_project)
  --formats, -f    Output formats: json,yaml,markdown (default: all)
  --output, -o     Output directory (default: config/capabilities/catalog)
  --help, -h       Show help

Examples:
  # Generate all formats for default project
  npx tsx scripts/generate-catalog.ts

  # Generate only JSON for specific project
  npx tsx scripts/generate-catalog.ts -p my_project -f json

  # Generate to custom output directory
  npx tsx scripts/generate-catalog.ts -o ./output/catalog
`);
}

async function main(): Promise<void> {
  const args = parseArgs();

  if (args.help) {
    showHelp();
    process.exit(0);
  }

  console.log('========================================');
  console.log('  Capability Catalog Generator');
  console.log('========================================');
  console.log('');
  console.log(`Project: ${args.project}`);
  console.log(`Formats: ${args.formats.join(', ')}`);
  console.log(`Output:  ${args.output}`);
  console.log('');

  // Create generator
  const basePath = path.join(process.cwd(), 'config/capabilities');
  const generator = new CapabilityCatalogGenerator(basePath);

  // Build options
  const options: CatalogOptions = {
    outputFormats: args.formats,
    outputDir: path.join(process.cwd(), args.output),
    includeExamples: true,
    includeMetadata: true,
  };

  console.log('Scanning capabilities...');

  try {
    // Generate catalog
    const result = await generator.generateCatalog(args.project, options);

    // Show warnings
    if (result.warnings.length > 0) {
      console.log('');
      console.log('Warnings:');
      for (const warning of result.warnings) {
        console.log(`  - ${warning}`);
      }
    }

    // Show errors
    if (result.errors && result.errors.length > 0) {
      console.log('');
      console.log('Errors:');
      for (const error of result.errors) {
        console.log(`  - ${error}`);
      }
    }

    // Show result
    console.log('');
    if (result.success) {
      console.log('SUCCESS: Catalog generated successfully!');
      console.log('');
      console.log('Generated files:');
      for (const file of result.generatedFiles) {
        console.log(`  - ${path.join(args.output, file)}`);
      }

      if (result.catalog) {
        console.log('');
        console.log('Summary:');
        console.log(`  Total capabilities: ${result.catalog.summary.total}`);
        console.log(`  With responseSchema: ${result.catalog.summary.withResponseSchema}`);
        console.log(`  Without responseSchema: ${result.catalog.summary.withoutResponseSchema}`);
        console.log('');
        console.log('  By Category:');
        for (const [category, count] of Object.entries(result.catalog.summary.byCategory)) {
          console.log(`    - ${category}: ${count}`);
        }
        console.log('');
        console.log('  By Status:');
        console.log(`    - available: ${result.catalog.summary.byStatus.available}`);
        console.log(`    - unavailable: ${result.catalog.summary.byStatus.unavailable}`);
        console.log(`    - deprecated: ${result.catalog.summary.byStatus.deprecated}`);
      }

      process.exit(0);
    } else {
      console.log('FAILED: Catalog generation failed');
      process.exit(1);
    }
  } catch (error) {
    console.error('');
    console.error('Fatal error:', error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

main();
