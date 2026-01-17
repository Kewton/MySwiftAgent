# Issue #372 Integration Gap Diagram

## Current Implementation (BROKEN)

```
TaskFlowEngine
  └─> WorkflowExecutor
       └─> ContextManager.getContext()
            └─> Returns: {
                 workflowId: string
                 stepResults: {...}
                 variables: {...}
                 secrets: {...}
                 // ❌ capabilityExecutor: MISSING!
               }
                 └─> ApiRestNode.execute(config, params, context)
                      └─> if (capability_id) {
                           ❌ context.capabilityExecutor is undefined!
                           ❌ Returns EXECUTOR_NOT_AVAILABLE error
                         }

// Dead Code (never instantiated):
❌ EndpointConfigManager - defined but never created
❌ URLResolver - defined but never created  
❌ CapabilityExecutor - defined but never created
```

---

## Required Integration (FIX)

```
TaskFlowEngine (NEEDS UPDATE)
  ├─> constructor() {
  │    ✅ configManager = createEndpointConfigManager(basePath)
  │    ✅ urlResolver = createURLResolver(configManager, projectId)
  │    ✅ this.capabilityExecutor = createCapabilityExecutor(urlResolver)
  │    │
  │    └─> this.executor = new WorkflowExecutor({
  │         nodeRegistry,
  │         defaultTimeout,
  │         ✅ capabilityExecutor: this.capabilityExecutor // ADD THIS
  │       })
  │   }
  │
  └─> WorkflowExecutor (NEEDS UPDATE)
       ├─> constructor(config) {
       │    ✅ this.capabilityExecutor = config.capabilityExecutor
       │   }
       │
       └─> execute(workflow, options) {
            └─> contextManager = new ContextManager(workflow, {
                 secrets,
                 variables,
                 ✅ capabilityExecutor: this.capabilityExecutor // ADD THIS
               })
                 │
                 └─> ContextManager.getContext() (NEEDS UPDATE)
                      └─> Returns: {
                           workflowId,
                           stepResults,
                           variables,
                           secrets,
                           ✅ capabilityExecutor: this.capabilityExecutor // ADD THIS
                         }
                           │
                           └─> ApiRestNode.execute(config, params, context)
                                └─> if (capability_id) {
                                     ✅ context.capabilityExecutor.execute(...)
                                          └─> CapabilityExecutor
                                               └─> URLResolver.resolve(capabilityId)
                                                    └─> EndpointConfigManager.load()
                                                         └─> Returns full URL
                                                              └─> HTTP Request
                                   }
```

---

## Files Requiring Changes

### P0 - Critical Integration

| File | Change | Lines |
|------|--------|-------|
| `taskflowEngine/nodes/BaseNode.ts` | Add `capabilityExecutor?: CapabilityExecutor` to ExecutionContext | ~15 |
| `taskflowEngine/nodes/index.ts` | Export `createCapabilityExecutor` | ~1 |
| `taskflowEngine/TaskFlowEngine.ts` | Initialize capability components in constructor | ~10 |
| `taskflowEngine/executor/ContextManager.ts` | Accept and provide capabilityExecutor | ~8 |
| `taskflowEngine/executor/WorkflowExecutor.ts` | Accept capabilityExecutor in config | ~5 |

**Total LOC for Integration**: ~39 lines

---

## Data Flow (After Fix)

```
1. TaskFlowEngine.constructor()
   └─> Creates: EndpointConfigManager → URLResolver → CapabilityExecutor

2. TaskFlowEngine.execute(workflow)
   └─> WorkflowExecutor.execute(workflow, { capabilityExecutor })
        └─> ContextManager(workflow, { capabilityExecutor })
             └─> getContext() → { ..., capabilityExecutor }

3. ApiRestNode.execute(config, params, context)
   └─> IF capability_id:
        └─> context.capabilityExecutor.execute(capabilityId, params)
             └─> URLResolver.resolve(capabilityId)
                  └─> EndpointConfigManager.getEndpoint(capabilityId)
                       └─> Returns: { base_url, path, method, ... }
                            └─> Constructs full URL
                                 └─> Executes HTTP request
                                      └─> Returns result
```

---

## Test Pyramid (Current vs Required)

### Current (BROKEN)

```
         /\
        /  \  ❌ Acceptance Tests: 0
       /____\
      /      \  ❌ Integration Tests: 0
     /________\
    /          \
   /   Unit     \ ✅ Unit Tests: 4 files (all pass with mocks)
  /______________\
```

**Problem**: Unit tests pass because they mock `capabilityExecutor`, but integration is broken!

---

### Required (WORKING)

```
         /\
        /  \  ✅ Acceptance: 1 E2E test with real workflow
       /____\
      /      \  ✅ Integration: Full pipeline test
     /________\
    /          \
   /   Unit     \ ✅ Unit Tests: 4 files (verify components work)
  /______________\
```

**Solution**: Add integration test to verify the full execution pipeline works end-to-end.

---

## Verification Checklist

After implementing the fix, verify:

- [ ] TaskFlowEngine creates EndpointConfigManager instance
- [ ] TaskFlowEngine creates URLResolver instance
- [ ] TaskFlowEngine creates CapabilityExecutor instance
- [ ] WorkflowExecutor receives capabilityExecutor in config
- [ ] ContextManager receives capabilityExecutor in config
- [ ] ContextManager.getContext() returns capabilityExecutor
- [ ] ApiRestNode can access context.capabilityExecutor
- [ ] Integration test passes: workflow with capability_id executes successfully
- [ ] Acceptance test passes: E2E workflow execution works

---

## Key Files (for reference)

**Feature Implementation**:
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/src/capabilityManagement/endpoint/EndpointConfigManager.ts`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/src/capabilityManagement/endpoint/URLResolver.ts`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/src/taskflowEngine/nodes/CapabilityExecutor.ts`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/src/taskflowEngine/nodes/ApiRestNode.ts`

**Integration Points** (require changes):
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/src/taskflowEngine/nodes/BaseNode.ts`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/src/taskflowEngine/TaskFlowEngine.ts`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/src/taskflowEngine/executor/ContextManager.ts`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/src/taskflowEngine/executor/WorkflowExecutor.ts`

**Verification Reports**:
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/dev-reports/feature/issue/372/pm-auto-dev/iteration-1/implementation-verification-result.json`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/dev-reports/feature/issue/372/pm-auto-dev/iteration-1/verification-summary.md`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/dev-reports/feature/issue/372/pm-auto-dev/iteration-1/integration-gap-diagram.md` (this file)
