#!/bin/bash
# verify_no_dead_code.sh
# Verifies that new code in workflow_gen is properly integrated
# Issue #342 Phase F: WorkflowGen V2 LLM Integration

set -e

echo "=========================================="
echo "Dead Code Verification - Workflow Gen V2"
echo "=========================================="
echo ""

WORKFLOW_GEN_DIR="aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen"
cd "$(dirname "$0")/.."

# 1. Check that all new modules are exported from __init__.py
echo "1. Checking module exports from __init__.py..."
INIT_FILE="${WORKFLOW_GEN_DIR}/__init__.py"

if grep -q "PromptBuilderSubWorkflow" "$INIT_FILE" && \
   grep -q "LLMGeneratorSubWorkflow" "$INIT_FILE" && \
   grep -q "YamlValidatorSubWorkflow" "$INIT_FILE" && \
   grep -q "GraphAIWorkflowSchema" "$INIT_FILE" && \
   grep -q "ValidationError" "$INIT_FILE"; then
    echo "   [PASS] All new modules are exported"
else
    echo "   [FAIL] Some modules are missing from __init__.py"
    exit 1
fi

# 2. Check that prompt_builder package exports are correct
echo "2. Checking prompt_builder exports..."
PROMPT_BUILDER_INIT="${WORKFLOW_GEN_DIR}/prompt_builder/__init__.py"

if grep -q "PromptBuilderSubWorkflow" "$PROMPT_BUILDER_INIT" && \
   grep -q "WorkflowPrompt" "$PROMPT_BUILDER_INIT"; then
    echo "   [PASS] prompt_builder exports are correct"
else
    echo "   [FAIL] prompt_builder exports are incorrect"
    exit 1
fi

# 3. Check that few_shot examples exist
echo "3. Checking few_shot examples exist..."
FEW_SHOT_DIR="${WORKFLOW_GEN_DIR}/prompt_builder/few_shot"

if [[ -f "${FEW_SHOT_DIR}/search_pattern.yaml" ]] && \
   [[ -f "${FEW_SHOT_DIR}/api_call_pattern.yaml" ]] && \
   [[ -f "${FEW_SHOT_DIR}/llm_chain_pattern.yaml" ]] && \
   [[ -f "${FEW_SHOT_DIR}/map_pattern.yaml" ]]; then
    echo "   [PASS] All few_shot examples exist"
else
    echo "   [FAIL] Some few_shot examples are missing"
    exit 1
fi

# 4. Check that validators package exports are correct
echo "4. Checking validators exports..."
VALIDATORS_INIT="${WORKFLOW_GEN_DIR}/validators/__init__.py"

if grep -q "validate_yaml_syntax" "$VALIDATORS_INIT" && \
   grep -q "validate_structure" "$VALIDATORS_INIT" && \
   grep -q "validate_agents" "$VALIDATORS_INIT" && \
   grep -q "validate_references" "$VALIDATORS_INIT"; then
    echo "   [PASS] validators exports are correct"
else
    echo "   [FAIL] validators exports are incorrect"
    exit 1
fi

# 5. Check that config.py has V2 settings
echo "5. Checking config.py has V2 settings..."
CONFIG_FILE="core/config.py"

if grep -q "WORKFLOW_GENERATOR_V2_MODEL" "$CONFIG_FILE" && \
   grep -q "WORKFLOW_GENERATOR_V2_TEMPERATURE" "$CONFIG_FILE" && \
   grep -q "WORKFLOW_GENERATOR_V2_MAX_RETRY" "$CONFIG_FILE"; then
    echo "   [PASS] Config has V2 settings"
else
    echo "   [FAIL] Config is missing V2 settings"
    exit 1
fi

# 6. Check that rules are defined
echo "6. Checking rules modules..."
RULES_DIR="${WORKFLOW_GEN_DIR}/prompt_builder/rules"

if [[ -f "${RULES_DIR}/base_rules.py" ]] && \
   [[ -f "${RULES_DIR}/agent_rules.py" ]] && \
   [[ -f "${RULES_DIR}/reference_rules.py" ]] && \
   [[ -f "${RULES_DIR}/api_rules.py" ]]; then
    echo "   [PASS] All rule modules exist"
else
    echo "   [FAIL] Some rule modules are missing"
    exit 1
fi

# 7. Check that schemas.py defines AVAILABLE_AGENTS
echo "7. Checking schemas.py has AVAILABLE_AGENTS..."
SCHEMAS_FILE="${WORKFLOW_GEN_DIR}/schemas.py"

if grep -q "AVAILABLE_AGENTS" "$SCHEMAS_FILE" && \
   grep -q "fetchAgent" "$SCHEMAS_FILE"; then
    echo "   [PASS] AVAILABLE_AGENTS is defined"
else
    echo "   [FAIL] AVAILABLE_AGENTS is not properly defined"
    exit 1
fi

# 8. Check that unit tests exist
echo "8. Checking unit tests exist..."
UNIT_TEST_DIR="tests/unit/test_job_generator_v2"

if [[ -f "${UNIT_TEST_DIR}/test_workflow_gen_schemas.py" ]] && \
   [[ -f "${UNIT_TEST_DIR}/test_workflow_gen_prompt_builder.py" ]] && \
   [[ -f "${UNIT_TEST_DIR}/test_workflow_gen_llm_generator.py" ]] && \
   [[ -f "${UNIT_TEST_DIR}/test_workflow_gen_yaml_validator.py" ]] && \
   [[ -f "${UNIT_TEST_DIR}/test_workflow_gen_few_shot_loader.py" ]] && \
   [[ -f "${UNIT_TEST_DIR}/test_workflow_gen_workflow.py" ]] && \
   [[ -f "${UNIT_TEST_DIR}/test_workflow_gen_integration_check.py" ]]; then
    echo "   [PASS] All unit test files exist"
else
    echo "   [FAIL] Some unit test files are missing"
    exit 1
fi

# 9. Check that integration test exists
echo "9. Checking integration test exists..."
INTEGRATION_TEST="tests/integration/test_workflow_gen_v2_integration.py"

if [[ -f "$INTEGRATION_TEST" ]]; then
    echo "   [PASS] Integration test file exists"
else
    echo "   [FAIL] Integration test file is missing"
    exit 1
fi

# 10. Run Python import check
echo "10. Checking Python imports work..."
python -c "
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
    WorkflowGenWorkflow,
    YamlGeneratorSubWorkflow,
    PromptBuilderSubWorkflow,
    LLMGeneratorSubWorkflow,
    YamlValidatorSubWorkflow,
    GraphAIWorkflowSchema,
    NodeDefinition,
    ErrorCode,
    ValidationError,
)
print('   [PASS] All imports successful')
"

echo ""
echo "=========================================="
echo "All Dead Code Checks Passed!"
echo "=========================================="
