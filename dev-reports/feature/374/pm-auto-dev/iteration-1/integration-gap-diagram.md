# Integration Gap Diagram - Issue #374

## Current State (Dead Code Problem)

```
┌─────────────────────────────────────────────────────────────┐
│ WorkflowGenerator.generateSingle()                          │
│                                                              │
│  1. promptBuilder.buildPrompt(task, capabilities)           │
│     └─> buildSystemPrompt() ───> formatCapabilities()       │
│         (NOT using formatCapabilitiesEnhanced)              │
│         (NOT calling selectRelevantCapabilities)            │
│                                                              │
│  2. llmClient.generateStructured(prompt, schema)            │
│                                                              │
│  3. validationPipeline.validate(workflow, context)          │
│     └─> SchemaValidator                   ✓ CALLED          │
│     └─> DependencyValidator               ✓ CALLED          │
│     └─> VariableValidator                 ✓ CALLED          │
│     └─> CapabilityValidator               ✓ CALLED          │
│     └─> WorkflowCapabilityValidator       ✗ NOT ADDED       │ <- DEAD CODE
│     └─> SecurityValidator                 ✓ CALLED          │
│                                                              │
│  4. if (!validationResult.isValid)                          │
│       throw WorkflowValidationError(...)                    │
│       (NOT catching WorkflowCapabilityError)                │
│       (NOT calling buildFeedbackPrompt)                     │ <- DEAD CODE
│                                                              │
│  5. return workflow                                         │
│     (NO metrics collected)                                  │ <- DEAD CODE
└─────────────────────────────────────────────────────────────┘
```

---

## Dead Code Components

```
┌────────────────────────────────────────────────────────────┐
│ DEFINED BUT NEVER CALLED                                   │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  WorkflowCapabilityValidator (F9)                          │
│  ├─> Exported from validator/index.ts                      │
│  ├─> Has unit test ✓                                       │
│  └─> NOT in ValidationPipeline.createDefaultValidators()   │
│                                                             │
│  buildFeedbackPrompt (F7)                                  │
│  ├─> Public method in PromptBuilder                        │
│  ├─> Has unit test ✓                                       │
│  └─> Never called in WorkflowGenerator                     │
│      └─> formatCapabilitiesEnhanced (F6) <- Also unused    │
│                                                             │
│  selectRelevantCapabilities (F8)                           │
│  ├─> Public method in PromptBuilder                        │
│  ├─> Has unit test ✓                                       │
│  └─> Never called in buildPrompt/buildSystemPrompt         │
│      └─> MAX_CAPABILITIES_PER_PROMPT (F4) <- Also unused   │
│                                                             │
│  GenerationMetricsCollector (F10)                          │
│  ├─> Exported from generator/index.ts                      │
│  ├─> Has unit test ✓                                       │
│  └─> Never instantiated in WorkflowGenerator               │
│                                                             │
│  MetricsAggregator (F11)                                   │
│  ├─> Exported from generator/index.ts                      │
│  ├─> Has unit test ✓                                       │
│  └─> Never instantiated anywhere                           │
│                                                             │
│  WorkflowCapabilityError (F2)                              │
│  ├─> Exported from types/index.ts                          │
│  ├─> Has unit test ✓                                       │
│  └─> Never thrown or instantiated                          │
│                                                             │
│  MAX_RETRY_COUNT (F5)                                      │
│  ├─> Exported from constants.ts                            │
│  ├─> Has unit test ✓                                       │
│  └─> Not imported anywhere (hardcoded 3 used instead)      │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## Expected Integration (What Should Happen)

```
┌─────────────────────────────────────────────────────────────┐
│ WorkflowGenerator.generateSingle()                          │
│                                                              │
│  1. promptBuilder.buildPrompt(task, capabilities)           │
│     └─> buildSystemPrompt()                                 │
│         ├─> IF capabilities.length > MAX_CAPABILITIES_PER_PROMPT
│         │   selectRelevantCapabilities() <- F8, F4          │
│         └─> formatCapabilities()                            │
│                                                              │
│  2. metricsCollector = new GenerationMetricsCollector() <- F10
│     metricsCollector.startGeneration()                      │
│                                                              │
│  3. retryStrategy.execute(async (attempt) => {              │
│       metricsCollector.recordAttempt()                      │
│                                                              │
│       llmClient.generateStructured(prompt, schema)          │
│                                                              │
│       validationPipeline.validate(workflow, context)        │
│       └─> SchemaValidator                                   │
│       └─> DependencyValidator                               │
│       └─> VariableValidator                                 │
│       └─> CapabilityValidator                               │
│       └─> WorkflowCapabilityValidator <- F9 INTEGRATED      │
│       └─> SecurityValidator                                 │
│                                                              │
│       if (!validationResult.isValid) {                      │
│         const capErrors = errors.filter(e => e.capability)  │
│         if (capErrors.length > 0) {                         │
│           throw new WorkflowCapabilityError(...) <- F2      │
│         }                                                    │
│         throw WorkflowValidationError(...)                  │
│       }                                                      │
│                                                              │
│       metricsCollector.recordSuccess()                      │
│       return workflow                                       │
│     })                                                       │
│     .catch(error => {                                       │
│       if (error instanceof WorkflowCapabilityError) {       │
│         metricsCollector.recordError(error)                 │
│         // Build feedback prompt with enhanced capability info
│         const feedbackPrompt =                              │
│           promptBuilder.buildFeedbackPrompt(               │
│             originalPrompt,                                 │
│             error,                                          │
│             capabilities <- F7, F6, F1                      │
│           )                                                  │
│         // Retry with feedback prompt                       │
│         // ...                                              │
│       }                                                      │
│     })                                                       │
│                                                              │
│  4. const metrics = metricsCollector.finalize() <- F3       │
│     return { workflow, metrics }                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration Points Required

| Feature | Integration Point | File | Line | Action |
|---------|------------------|------|------|--------|
| F9: WorkflowCapabilityValidator | ValidationPipeline.createDefaultValidators() | ValidationPipeline.ts | 116 | Add `new WorkflowCapabilityValidator()` |
| F7: buildFeedbackPrompt | WorkflowGenerator retry catch block | WorkflowGenerator.ts | 117 | Call on WorkflowCapabilityError |
| F6: formatCapabilitiesEnhanced | Called by buildFeedbackPrompt | PromptBuilder.ts | 367 | Already called (transitive) |
| F8: selectRelevantCapabilities | PromptBuilder.buildSystemPrompt | PromptBuilder.ts | 61 | Call when caps > MAX_CAPABILITIES_PER_PROMPT |
| F4: MAX_CAPABILITIES_PER_PROMPT | PromptBuilder.buildSystemPrompt | PromptBuilder.ts | 61 | Use in condition |
| F10: GenerationMetricsCollector | WorkflowGenerator.generateWithMetadata | WorkflowGenerator.ts | 142 | Instantiate and use |
| F11: MetricsAggregator | API routes or BatchProcessor | routes.ts (not found) | - | Create metrics endpoint |
| F2: WorkflowCapabilityError | WorkflowCapabilityValidator.validate | WorkflowCapabilityValidator.ts | 75 | Throw on validation failure |
| F5: MAX_RETRY_COUNT | WorkflowGenerator constructor | WorkflowGenerator.ts | 66 | Use instead of hardcoded 3 |

---

## Test Coverage Gap

```
┌─────────────────────────────────────────────────────────────┐
│ Test Type       │ Expected                │ Actual         │
├─────────────────┼─────────────────────────┼────────────────┤
│ Unit Tests      │ 11 features             │ 11 ✓           │
│ Integration     │ 4 integration tests     │ 0 ✗            │
│ Acceptance      │ 1 acceptance test       │ 0 ✗            │
└─────────────────────────────────────────────────────────────┘

Missing Integration Tests:
  1. feedbackLoop.test.ts
     - Test buildFeedbackPrompt is called on validation failure
     - Test WorkflowCapabilityError triggers feedback
     - Test retry with enhanced prompt

  2. capabilitySelection.test.ts
     - Test selectRelevantCapabilities with > 50 capabilities
     - Test MAX_CAPABILITIES_PER_PROMPT limit
     - Test relevance scoring

  3. validatorPipeline.test.ts
     - Test WorkflowCapabilityValidator is in pipeline
     - Test it runs during validation
     - Test it throws WorkflowCapabilityError

  4. metricsCollection.test.ts
     - Test GenerationMetricsCollector lifecycle
     - Test metrics are collected during generation
     - Test MetricsAggregator aggregates results

Missing Acceptance Test:
  - test_issue_374_acceptance.py
    - E2E test of all 11 features in real workflow generation
    - Verify feedback loop works end-to-end
    - Verify metrics are collected in production
```

---

## Conclusion

**Problem**: All 11 features are DEFINED and have UNIT TESTS, but 8 are DEAD CODE.

**Root Cause**: TDD phase created isolated features without integration tasks.

**Solution**: Re-run TDD phase with integration tasks that wire up all features.
