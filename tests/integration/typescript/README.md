# TypeScript Integration Tests

This directory contains TypeScript integration tests for MySwiftAgent services, migrated from individual project directories to a centralized location.

## Overview

- **Framework**: Vitest (migrated from Jest)
- **Language**: TypeScript with ESM modules
- **Test Runner**: `npm test`

## Directory Structure

```
tests/integration/typescript/
├── api/                           # API integration tests
│   ├── graphaiserver-api.test.ts  # GraphAI Server API tests
│   └── graphaiserver-workflow.test.ts  # Workflow registration tests
├── helpers/                       # Test utilities
│   ├── index.ts                   # Helper exports
│   └── test-utils.ts              # Common test utilities
├── package.json                   # Dependencies
├── tsconfig.json                  # TypeScript configuration
├── vitest.config.ts               # Vitest configuration
├── setup.ts                       # Test setup file
└── README.md                      # This file
```

## Getting Started

### Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0

### Installation

```bash
cd tests/integration/typescript
npm install
```

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Type check
npm run typecheck

# Lint
npm run lint
```

## Test Files

### graphaiserver-api.test.ts

Tests for GraphAI Server API endpoints:
- `GET /health` - Health check endpoint
- `GET /` - Root endpoint
- `GET /api/v1/` - API version info
- `POST /api/v1/myagent` - Legacy agent endpoint
- `POST /api/v1/myagent/:category/:model` - New agent endpoint with path parameters

### graphaiserver-workflow.test.ts

Tests for workflow registration:
- Workflow creation with valid YAML
- Workflow overwrite functionality
- Input validation (missing fields, special characters)
- Path traversal protection
- YAML syntax validation
- Conflict handling (409 errors)

## Migration Notes

These tests were migrated from:
- `graphAiServer/tests/integration/app.test.ts`
- `graphAiServer/tests/integration/workflow.test.ts`

### Changes from Jest to Vitest

1. **Import statements**: Changed from Jest globals to explicit Vitest imports
   ```typescript
   // Before (Jest)
   describe('test', () => { ... });

   // After (Vitest)
   import { describe, it, expect } from 'vitest';
   describe('test', () => { ... });
   ```

2. **Configuration**: Changed from `jest.config.js` to `vitest.config.ts`

3. **Setup files**: Changed from `jest.setup.js` to `setup.ts`

4. **Test execution**: The tests import the app directly from `graphAiServer/src/app.js`

## Important Notes

### Working Directory

Tests run from `tests/integration/typescript/` directory. The GraphAI Server app uses `process.cwd()` for path resolution, so:
- Workflow files are created in `tests/integration/typescript/config/graphai/`
- Tests clean up these files after each test run

### Service Dependencies

Some tests require external services to be running:
- For full workflow execution tests, you may need API keys configured
- Health check and validation tests work without external dependencies

## Troubleshooting

### Common Issues

1. **Module not found errors**
   - Ensure `graphAiServer/node_modules` is installed: `cd graphAiServer && npm install`
   - Ensure test dependencies are installed: `cd tests/integration/typescript && npm install`

2. **Test files not cleaned up**
   - Run `rm -rf tests/integration/typescript/config` to manually clean up

3. **TypeScript errors**
   - Run `npm run typecheck` to identify type issues
   - Ensure `tsconfig.json` includes proper module resolution settings

## Contributing

When adding new integration tests:
1. Follow the existing test structure
2. Use descriptive test names
3. Clean up any created resources in `afterEach` or `afterAll` hooks
4. Import utilities from `./helpers/index.js`
