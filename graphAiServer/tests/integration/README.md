# GraphAI Server Integration Tests (DEPRECATED)

> **WARNING: These tests are deprecated.**
>
> Integration tests have been migrated to the repository root:
> `tests/integration/typescript/`
>
> Please use the new location for all new tests and modifications.

## Migration Information

- **New Location**: `tests/integration/typescript/api/`
- **New Framework**: Vitest (migrated from Jest)
- **Migration Date**: 2025-12-03
- **Issue**: #212

## Migrated Files

| Original File | New Location |
|--------------|--------------|
| `app.test.ts` | `tests/integration/typescript/api/graphaiserver-api.test.ts` |
| `workflow.test.ts` | `tests/integration/typescript/api/graphaiserver-workflow.test.ts` |

## Running Tests

To run integration tests, use the new centralized location:

```bash
cd tests/integration/typescript
npm install
npm test
```

## Removal Plan

These deprecated test files will be removed in a future release once all teams have migrated to using the new test location.
