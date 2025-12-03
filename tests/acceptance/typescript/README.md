# TypeScript Acceptance Tests

Playwright-based acceptance tests for MySwiftAgent Frontend (myAgentDesk).

## Prerequisites

- Node.js 18+
- npm or pnpm
- Playwright browsers installed

## Quick Start

```bash
# Install dependencies
npm install

# Install Playwright browsers (first time only)
npx playwright install chromium

# Run all tests
npx playwright test

# Run tests with UI mode
npx playwright test --ui
```

## Directory Structure

```
tests/acceptance/typescript/
├── ui/                       # UI smoke tests
│   ├── myagentdesk-smoke.spec.ts  # Basic page load tests
│   └── health-check.spec.ts       # Service health checks
├── e2e/                      # End-to-end tests
│   └── smoke.spec.ts              # E2E smoke tests
├── package.json              # npm dependencies
├── playwright.config.ts      # Playwright configuration
├── tsconfig.json             # TypeScript configuration
└── README.md                 # This file
```

## Running Tests

### Basic Commands

```bash
# Run all tests
npx playwright test

# Run UI tests only
npm run test:ui

# Run E2E tests only
npm run test:e2e

# Run tests with browser visible
npm run test:headed

# Run tests in debug mode
npm run test:debug

# Show HTML report
npm run report
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MYAGENTDESK_URL` | `http://localhost:5173` | myAgentDesk base URL |
| `EXPERTAGENT_URL` | `http://localhost:8004` | ExpertAgent API URL |
| `JOBQUEUE_URL` | `http://localhost:8001` | JobQueue API URL |
| `MYVAULT_URL` | `http://localhost:8003` | MyVault API URL |
| `CHECK_BACKEND_HEALTH` | (unset) | Enable backend health checks |

### Running with Custom URLs

```bash
# Use custom myAgentDesk URL
MYAGENTDESK_URL=http://localhost:3000 npx playwright test

# Enable backend health checks
CHECK_BACKEND_HEALTH=1 npx playwright test
```

## Test Categories

### UI Smoke Tests (`ui/`)

Basic tests to verify the frontend is accessible and functioning:

- Page loading
- Title verification
- JavaScript error detection
- Response time checks

### E2E Tests (`e2e/`)

End-to-end tests that verify user workflows:

- Application container rendering
- Navigation functionality
- Responsive design
- Network handling

## Makefile Integration

From the project root:

```bash
# Run frontend acceptance tests
make acceptance-test-frontend

# Run all acceptance tests (Python + TypeScript)
make acceptance-test-all
```

## Playwright Configuration

Key settings in `playwright.config.ts`:

- **Test timeout**: 60 seconds
- **Expect timeout**: 10 seconds
- **Action timeout**: 15 seconds
- **Navigation timeout**: 30 seconds
- **Browser**: Chromium (default)
- **Screenshots**: On failure only
- **Videos**: Retained on failure
- **Traces**: On first retry

## Writing New Tests

### UI Test Template

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test('should do something', async ({ page }) => {
    await page.goto('/');
    // Test logic here
    expect(something).toBeTruthy();
  });
});
```

### Best Practices

1. **Use descriptive test names** - Describe expected behavior
2. **Keep tests independent** - Each test should work in isolation
3. **Handle service availability** - Tests should gracefully handle missing services
4. **Use appropriate timeouts** - Adjust timeouts for slow operations
5. **Log useful information** - Use `console.log` for debugging info

## Troubleshooting

### Service Not Running

If you see "Connection refused" errors:

```bash
# Start myAgentDesk
cd myAgentDesk && npm run dev

# Or use the unified start script
./scripts/unified-start.sh start
```

### Browser Installation Issues

```bash
# Install Playwright browsers with dependencies
npx playwright install --with-deps chromium

# Or install all browsers
npx playwright install
```

### Test Report Not Opening

```bash
# Manually show the report
npx playwright show-report ../../../reports/playwright-report
```

## CI/CD Notes

These tests are **NOT** run in CI by default because they require:

1. Running services (myAgentDesk, backend APIs)
2. Potentially API keys for full E2E scenarios

For CI integration, use the Python acceptance tests in `tests/acceptance/python/`.

## Related Documentation

- [Playwright Documentation](https://playwright.dev/)
- [myAgentDesk README](../../../myAgentDesk/README.md)
- [Acceptance Testing Guide](../../../docs/spec/acceptance-testing.md)
