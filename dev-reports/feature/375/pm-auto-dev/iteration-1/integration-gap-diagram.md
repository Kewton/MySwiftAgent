# Integration Gap Diagram - Issue #375

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Main Application                             │
│                      src/index.ts + src/api/routes.ts                │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ createApiRoutes()
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API Router (Hono)                            │
├─────────────────────────────────────────────────────────────────────┤
│  ✅ /health                     - Health checks                      │
│  ✅ /api/v1/generator           - TaskFlow Generator                │
│  ✅ /api/v1/taskflow/execute    - Execute workflows                 │
│  ✅ /api/v1/taskflow/workflows  - List/Get workflows                │
│  ❌ /api/v1/taskflow/reload     - Reload workflows (MISSING!)       │
└─────────────────────────────────────────────────────────────────────┘
                      │                            │
                      │ ✅ Mounted                 │ ❌ NOT Mounted
                      ▼                            ▼
        ┌──────────────────────┐      ┌──────────────────────────┐
        │  TaskFlow Engine     │      │  TaskFlow Reload API      │
        │  Routes              │      │  (DEAD CODE)              │
        │                      │      │                           │
        │  createTaskFlowRoutes│      │  createTaskFlowReloadApi  │
        │  (INTEGRATED ✅)     │      │  (NOT INTEGRATED ❌)      │
        └──────────────────────┘      └──────────────────────────┘
                                                   │
                                                   │ requires
                                                   ▼
                                      ┌──────────────────────────┐
                                      │  WorkflowReloader        │
                                      │  (EXISTS, NOT USED ⚠️)   │
                                      └──────────────────────────┘
                                                   │
                                                   │ requires
                                                   ▼
                                      ┌──────────────────────────┐
                                      │  WorkflowLoader          │
                                      │  (NOT CREATED ❌)        │
                                      └──────────────────────────┘
```

---

## Validation Pipeline Integration

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ValidationPipeline                              │
│                  createDefaultValidators()                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ creates
                                   ▼
        ┌──────────────────────────────────────────────────┐
        │          Validator Instances                     │
        ├──────────────────────────────────────────────────┤
        │  ✅ SchemaValidator                              │
        │  ✅ DependencyValidator                          │
        │  ✅ VariableValidator                            │
        │  ✅ CapabilityValidator                          │
        │  ✅ SecurityValidator                            │
        │  ✅ OutputMappingValidator      (Issue #375)     │
        │  ✅ NodeConfigValidator         (Issue #375)     │
        │  ✅ WorkflowCapabilityValidator (Issue #374)     │
        └──────────────────────────────────────────────────┘

Status: ✅ FULLY INTEGRATED
```

---

## Node Config Validation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                   NodeConfigValidator                                │
│             (Hardcoded NODE_TYPE_SPECS)                              │
└─────────────────────────────────────────────────────────────────────┘
                    │                            │
                    │ Should load from           │ Currently uses
                    ▼                            ▼
    ┌────────────────────────┐      ┌────────────────────────┐
    │  node_types_spec.yaml  │      │  Hardcoded constant    │
    │  (DEAD CODE ❌)        │      │  NODE_TYPE_SPECS       │
    │                        │      │  (IN USE ✅)           │
    │  Complete spec exists  │      │  Same content as YAML  │
    │  Never loaded          │      │  Duplicated logic      │
    └────────────────────────┘      └────────────────────────┘

Problem: Inconsistency between documented spec (YAML) and implementation (code)
Solution: Choose one source of truth
```

---

## Integration Gap Details

### Gap G1: Reload API Not Accessible

**Current State**:
```
src/api/routes.ts (createApiRoutes)
  │
  ├── ✅ app.route('/', healthRoutes)
  ├── ✅ app.route('/', generatorApi)
  ├── ✅ app.route('/api/v1/taskflow', taskFlowRoutes)
  └── ❌ MISSING: app.route('/', reloadApi)
```

**Required State**:
```
src/api/routes.ts (createApiRoutes)
  │
  ├── ✅ app.route('/', healthRoutes)
  ├── ✅ app.route('/', generatorApi)
  ├── ✅ app.route('/api/v1/taskflow', taskFlowRoutes)
  └── ✅ app.route('/', reloadApi)  ← ADD THIS
```

**Required Code**:
```typescript
// 1. Import reload API
import { createTaskFlowReloadApi } from './routes/taskflow-reload.js';
import { createWorkflowReloader } from '../taskflowEngine/loader/WorkflowReloader.js';
import { createWorkflowLoader } from '../taskflowEngine/loader/WorkflowLoader.js';

// 2. Create dependencies
const workflowLoader = createWorkflowLoader({ 
  /* config */ 
});
const reloader = createWorkflowReloader(workflowLoader, generatorDeps.registry);

// 3. Create and mount API
const reloadApi = createTaskFlowReloadApi({ reloader });
app.route('/', reloadApi);
```

---

### Gap G2: node_types_spec.yaml Not Used

**Current State**:
```
mySwiftAgentCore/config/node_types_spec.yaml
  │
  │ Contains: Complete node type specifications
  │           - transform, api_rest, llm, code_js, parallel, action
  │           - Required/optional config for each type
  │           - Validation rules
  │           - Examples
  │
  └── ❌ NOT LOADED BY ANY CODE

NodeConfigValidator.ts:34
  │
  └── Hardcoded: const NODE_TYPE_SPECS = { ... }
                 Same content as YAML but duplicated
```

**Option 1: Use YAML as Source of Truth**
```typescript
// NodeConfigValidator.ts
import fs from 'fs';
import yaml from 'yaml';
import path from 'path';

const specPath = path.resolve(process.cwd(), 'config/node_types_spec.yaml');
const specContent = fs.readFileSync(specPath, 'utf8');
const loadedSpec = yaml.parse(specContent);
const NODE_TYPE_SPECS: Record<NodeType, NodeTypeSpec> = loadedSpec.node_types;
```

**Option 2: Remove YAML (Code is Source of Truth)**
```bash
# Remove redundant file
rm mySwiftAgentCore/config/node_types_spec.yaml

# Update documentation to reference code
# Document that specs are defined in NodeConfigValidator.ts
```

---

### Gap G3: WorkflowLoader Not Created

**Current State**:
```
src/api/routes.ts
  │
  └── WorkflowRegistry created ✅
      WorkflowLoader NOT created ❌
      
createTaskFlowReloadApi requires:
  {
    reloader: WorkflowReloader  ← Needs WorkflowLoader to instantiate
  }
```

**Required State**:
```typescript
// In createApiRoutes()

// 1. Create WorkflowLoader
const workflowsBasePath = path.resolve(process.cwd(), 'config', 'taskflow', 'workflows');
const workflowLoader = createWorkflowLoader({
  basePath: workflowsBasePath,
  registry: generatorDeps.registry,
});

// 2. Create WorkflowReloader
const reloader = createWorkflowReloader(workflowLoader, generatorDeps.registry);

// 3. Create reload API
const reloadApi = createTaskFlowReloadApi({ reloader });

// 4. Mount reload API
app.route('/', reloadApi);
```

---

## Dependency Chain for Reload Feature

```
POST /api/v1/taskflow/reload
  │
  │ handled by
  ▼
createTaskFlowReloadApi
  │
  │ requires
  ▼
WorkflowReloader
  │
  │ requires
  ├─── WorkflowLoader (to load workflows from disk)
  │      │
  │      │ reads from
  │      ▼
  │    config/taskflow/workflows/*.json
  │
  └─── WorkflowRegistry (to register loaded workflows)
         │
         │ stores
         ▼
       In-memory workflow definitions

Current Status:
  ❌ WorkflowLoader - NOT created in API setup
  ✅ WorkflowRegistry - Created and shared
  ✅ WorkflowReloader - Class exists but not instantiated
  ✅ createTaskFlowReloadApi - Function exists but not mounted
```

---

## File System Structure

```
mySwiftAgentCore/
├── src/
│   ├── api/
│   │   ├── routes.ts                    ← ❌ Missing reload API mount
│   │   └── routes/
│   │       └── taskflow-reload.ts       ← ✅ Exists but unused (DEAD CODE)
│   │
│   └── taskflowEngine/
│       ├── loader/
│       │   ├── WorkflowLoader.ts        ← ✅ Exists
│       │   ├── WorkflowReloader.ts      ← ✅ Exists but not instantiated
│       │   └── index.ts                 ← ✅ Exports both
│       │
│       └── watcher/
│           ├── FileSystemWatcher.ts     ← ✅ Exists and exported
│           └── index.ts                 ← ✅ Exports watcher
│
└── config/
    └── node_types_spec.yaml             ← ❌ Exists but never loaded (DEAD CODE)
```

---

## Summary of Integration Issues

| Gap | Component | Status | Impact | Fix Effort |
|-----|-----------|--------|--------|------------|
| G1 | Reload API Endpoint | NOT MOUNTED | High | Small |
| G2 | node_types_spec.yaml | NOT LOADED | Medium | Small |
| G3 | WorkflowLoader Instance | NOT CREATED | High | Small |

**Total Estimated Fix Time**: 2-4 hours
