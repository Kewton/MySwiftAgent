# myAgentDesk E2E Tests (Deprecated)

> **DEPRECATION WARNING**: These tests are being migrated to the centralized
> acceptance test infrastructure at `tests/acceptance/typescript/`.
>
> New E2E tests should be created in `tests/acceptance/typescript/e2e/`.

## Migration Status

The centralized acceptance test infrastructure provides:

- Unified Playwright configuration
- Consistent test patterns across the project
- Integration with Makefile targets (`make acceptance-test-frontend`)
- Cross-service E2E testing capabilities

## Current Tests

The following tests exist in this directory but should be migrated:

- `create-job.test.ts` - Job creation flow tests
- `home.test.ts` - Home page tests
- `schedule.test.ts` - Schedule management tests
- `slides.test.ts` - Slides generation tests
- `port8003-interaction.spec.ts` - Backend interaction tests
- `mlops/` - MLOps feature tests

## Running Legacy Tests

If you still need to run these tests:

```bash
cd myAgentDesk
npm run test:e2e
```

## New Location

For new E2E tests, use:

```bash
# Navigate to centralized test directory
cd tests/acceptance/typescript

# Run tests
npx playwright test

# Or from project root
make acceptance-test-frontend
```

## See Also

- [Centralized Acceptance Tests](../../../tests/acceptance/typescript/README.md)
- [Acceptance Testing Guide](../../../docs/spec/acceptance-testing.md)
