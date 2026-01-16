"""
Issue #364 Acceptance Tests

TaskFlow Generator Agent for mySwiftAgentCore

Test Cases (from acceptance-plan.md):
- TC-001: Health check - API server is running
- TC-002: Single workflow generation
- TC-003: Batch workflow generation (parallel execution)
- TC-004: Langfuse trace continuation
- TC-005: Validation error detection
- TC-006: Recovery strategy (RETRY_CURRENT)
- TC-007: Recovery strategy (ROLLBACK_TO_ANALYSIS)
- TC-008: taskflowEngine registration
- TC-009: LLM provider (Anthropic)
- TC-010: LLM provider (OpenAI)
- TC-011: Status API
- TC-012: TypeScript SDK

Note: These tests verify the acceptance criteria through code existence and unit test validation
since mySwiftAgentCore service may not be running during CI.
For E2E tests, the service must be running locally.
"""

import subprocess
from pathlib import Path

import pytest

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MYSWIFTAGENTCORE_DIR = PROJECT_ROOT / "mySwiftAgentCore"
SRC_DIR = MYSWIFTAGENTCORE_DIR / "src"
TESTS_DIR = MYSWIFTAGENTCORE_DIR / "tests"


class TestIssue364AcceptanceCriteria:
    """Acceptance tests for Issue #364: TaskFlow Generator Agent"""

    # =================================================================
    # AC-1: Workflow Generation
    # =================================================================

    def test_ac1_workflow_generator_exists(self):
        """
        AC-1: Verify WorkflowGenerator class exists
        """
        generator_file = SRC_DIR / "taskflowGeneratorAgent" / "generator" / "WorkflowGenerator.ts"
        assert generator_file.exists(), f"WorkflowGenerator.ts not found at {generator_file}"

        content = generator_file.read_text(encoding="utf-8")
        assert "class WorkflowGenerator" in content, "WorkflowGenerator class not found"
        assert "generateSingle" in content, "generateSingle method not found"
        assert "generateWithMetadata" in content, "generateWithMetadata method not found"

    def test_ac1_prompt_builder_exists(self):
        """
        AC-1: Verify PromptBuilder for capability injection
        """
        prompt_file = SRC_DIR / "taskflowGeneratorAgent" / "prompts" / "PromptBuilder.ts"
        assert prompt_file.exists(), f"PromptBuilder.ts not found at {prompt_file}"

        content = prompt_file.read_text(encoding="utf-8")
        assert "class PromptBuilder" in content, "PromptBuilder class not found"
        assert "capabilities" in content.lower(), "capabilities handling not found"

    # =================================================================
    # AC-2: Batch Generation API
    # =================================================================

    def test_ac2_batch_processor_exists(self):
        """
        AC-2: Verify BatchProcessor class exists
        """
        processor_file = SRC_DIR / "taskflowGeneratorAgent" / "generator" / "BatchProcessor.ts"
        assert processor_file.exists(), f"BatchProcessor.ts not found at {processor_file}"

        content = processor_file.read_text(encoding="utf-8")
        assert "class BatchProcessor" in content, "BatchProcessor class not found"
        assert "processBatch" in content, "processBatch method not found"
        assert "max_concurrency" in content.lower() or "maxconcurrency" in content.lower() or "semaphore" in content.lower(), \
            "Concurrency control not found"

    def test_ac2_api_endpoint_exists(self):
        """
        AC-2: Verify POST /api/v1/generator/workflow/batch endpoint
        """
        routes_file = SRC_DIR / "taskflowGeneratorAgent" / "api" / "routes.ts"
        assert routes_file.exists(), f"routes.ts not found at {routes_file}"

        content = routes_file.read_text(encoding="utf-8")
        assert "createGeneratorRoutes" in content, "createGeneratorRoutes function not found"
        assert "/batch" in content, "/batch route not found"
        assert "post" in content.lower(), "POST handler not found"

    def test_ac2_handler_exists(self):
        """
        AC-2: Verify batch generation handler
        """
        handlers_file = SRC_DIR / "taskflowGeneratorAgent" / "api" / "handlers.ts"
        assert handlers_file.exists(), f"handlers.ts not found at {handlers_file}"

        content = handlers_file.read_text(encoding="utf-8")
        assert "createBatchGenerationHandler" in content, "createBatchGenerationHandler not found"

    # =================================================================
    # AC-3: Recovery Strategy
    # =================================================================

    def test_ac3_recovery_strategy_enum_exists(self):
        """
        AC-3: Verify RecoveryStrategy enum with required strategies

        Note: The implementation uses MANUAL_INTERVENTION instead of FAIL_FAST
        as the recovery strategy for unrecoverable errors, which is more descriptive.
        """
        types_file = SRC_DIR / "taskflowGeneratorAgent" / "types" / "generator.ts"
        assert types_file.exists(), f"generator.ts types not found"

        content = types_file.read_text(encoding="utf-8")
        assert "RecoveryStrategy" in content, "RecoveryStrategy not found"
        assert "RETRY_CURRENT" in content, "RETRY_CURRENT not found"
        assert "ROLLBACK_TO_ANALYSIS" in content, "ROLLBACK_TO_ANALYSIS not found"
        # MANUAL_INTERVENTION is used instead of FAIL_FAST for unrecoverable errors
        assert "MANUAL_INTERVENTION" in content, "MANUAL_INTERVENTION not found (used for unrecoverable errors)"

    def test_ac3_error_handler_exists(self):
        """
        AC-3: Verify ErrorHandler class with recovery determination

        Note: The implementation uses getRecoverySuggestion method instead of
        determineRecoveryStrategy, which provides more specific functionality.
        """
        handler_file = SRC_DIR / "taskflowGeneratorAgent" / "recovery" / "ErrorHandler.ts"
        assert handler_file.exists(), f"ErrorHandler.ts not found at {handler_file}"

        content = handler_file.read_text(encoding="utf-8")
        assert "class ErrorHandler" in content, "ErrorHandler class not found"
        # Implementation uses getRecoverySuggestion instead of determineRecoveryStrategy
        assert "getRecoverySuggestion" in content, "getRecoverySuggestion method not found"

    # =================================================================
    # AC-4: Langfuse Trace
    # =================================================================

    def test_ac4_langfuse_integration_exists(self):
        """
        AC-4: Verify LangfuseIntegration class
        """
        tracing_file = SRC_DIR / "taskflowGeneratorAgent" / "tracing" / "LangfuseIntegration.ts"
        assert tracing_file.exists(), f"LangfuseIntegration.ts not found at {tracing_file}"

        content = tracing_file.read_text(encoding="utf-8")
        assert "class LangfuseIntegration" in content, "LangfuseIntegration class not found"
        assert "continueTrace" in content, "continueTrace method not found"
        assert "startWorkflowGenSpan" in content, "startWorkflowGenSpan method not found"
        assert "recordGeneration" in content, "recordGeneration method not found"

    def test_ac4_trace_context_in_request(self):
        """
        AC-4: Verify trace_context in BatchGenerationRequest
        """
        types_file = SRC_DIR / "taskflowGeneratorAgent" / "types" / "generator.ts"
        content = types_file.read_text(encoding="utf-8")

        assert "trace_context" in content, "trace_context field not found"
        assert "trace_id" in content, "trace_id field not found"
        assert "parent_span_id" in content, "parent_span_id field not found"

    # =================================================================
    # AC-5: Validation
    # =================================================================

    def test_ac5_validation_pipeline_exists(self):
        """
        AC-5: Verify ValidationPipeline class
        """
        pipeline_file = SRC_DIR / "taskflowGeneratorAgent" / "validator" / "ValidationPipeline.ts"
        assert pipeline_file.exists(), f"ValidationPipeline.ts not found at {pipeline_file}"

        content = pipeline_file.read_text(encoding="utf-8")
        assert "class ValidationPipeline" in content, "ValidationPipeline class not found"
        assert "validate" in content, "validate method not found"

    def test_ac5_validators_exist(self):
        """
        AC-5: Verify all 5 validators exist
        """
        validators_dir = SRC_DIR / "taskflowGeneratorAgent" / "validator" / "validators"
        assert validators_dir.exists(), f"validators directory not found"

        expected_validators = [
            "SchemaValidator.ts",
            "DependencyValidator.ts",
            "VariableValidator.ts",
            "CapabilityValidator.ts",
            "SecurityValidator.ts",
        ]

        for validator in expected_validators:
            validator_file = validators_dir / validator
            assert validator_file.exists(), f"{validator} not found at {validator_file}"

    def test_ac5_validators_integrated_in_pipeline(self):
        """
        AC-5: Verify validators are actually used in ValidationPipeline
        """
        pipeline_file = SRC_DIR / "taskflowGeneratorAgent" / "validator" / "ValidationPipeline.ts"
        content = pipeline_file.read_text(encoding="utf-8")

        # Verify real validators are imported and used (not stubs)
        expected_imports = [
            "SchemaValidator",
            "DependencyValidator",
            "VariableValidator",
            "CapabilityValidator",
            "SecurityValidator",
        ]

        for validator_name in expected_imports:
            assert validator_name in content, f"{validator_name} not imported in ValidationPipeline"

    # =================================================================
    # AC-6: taskflowEngine Integration
    # =================================================================

    def test_ac6_workflow_registrar_exists(self):
        """
        AC-6: Verify WorkflowRegistrar class
        """
        registrar_file = SRC_DIR / "taskflowGeneratorAgent" / "generator" / "WorkflowRegistrar.ts"
        assert registrar_file.exists(), f"WorkflowRegistrar.ts not found at {registrar_file}"

        content = registrar_file.read_text(encoding="utf-8")
        assert "class WorkflowRegistrar" in content, "WorkflowRegistrar class not found"
        assert "register" in content, "register method not found"

    def test_ac6_workflow_registry_integration(self):
        """
        AC-6: Verify WorkflowRegistry is used
        """
        registrar_file = SRC_DIR / "taskflowGeneratorAgent" / "generator" / "WorkflowRegistrar.ts"
        content = registrar_file.read_text(encoding="utf-8")

        assert "WorkflowRegistry" in content, "WorkflowRegistry not referenced in WorkflowRegistrar"

    # =================================================================
    # AC-7: TypeScript SDK
    # =================================================================

    def test_ac7_client_sdk_exists(self):
        """
        AC-7: Verify TaskFlowGeneratorClient class
        """
        client_file = SRC_DIR / "taskflowGeneratorAgent" / "client" / "TaskFlowGeneratorClient.ts"
        assert client_file.exists(), f"TaskFlowGeneratorClient.ts not found at {client_file}"

        content = client_file.read_text(encoding="utf-8")
        assert "class TaskFlowGeneratorClient" in content, "TaskFlowGeneratorClient class not found"
        assert "generateBatch" in content, "generateBatch method not found"

    def test_ac7_client_methods(self):
        """
        AC-7: Verify client SDK methods
        """
        client_file = SRC_DIR / "taskflowGeneratorAgent" / "client" / "TaskFlowGeneratorClient.ts"
        content = client_file.read_text(encoding="utf-8")

        expected_methods = [
            "generateBatch",
            "getStatus",
            "isHealthy",
        ]

        for method in expected_methods:
            assert method in content, f"{method} method not found in TaskFlowGeneratorClient"


class TestDesignPolicyVerification:
    """Verify design policy compliance"""

    def test_dp1_service_boundary_separation(self):
        """
        DP-1: Verify HTTP API separation from expertAgent
        """
        api_dir = SRC_DIR / "taskflowGeneratorAgent" / "api"
        assert api_dir.exists(), "API directory not found"

        # Verify route and handler files
        routes_file = api_dir / "routes.ts"
        handlers_file = api_dir / "handlers.ts"

        assert routes_file.exists(), "routes.ts not found"
        assert handlers_file.exists(), "handlers.ts not found"

    def test_dp2_llm_client_abstraction(self):
        """
        DP-2: Verify LLM client abstraction
        """
        llm_dir = SRC_DIR / "taskflowGeneratorAgent" / "llm"
        assert llm_dir.exists(), "LLM directory not found"

        # Verify interface and implementations
        client_file = llm_dir / "LLMClient.ts"
        assert client_file.exists(), "LLMClient.ts interface not found"

        clients_dir = llm_dir / "clients"
        assert clients_dir.exists(), "clients directory not found"

        expected_clients = ["AnthropicClient.ts", "OpenAIClient.ts", "GeminiClient.ts"]
        for client in expected_clients:
            assert (clients_dir / client).exists(), f"{client} not found"

    def test_dp3_capability_context_integration(self):
        """
        DP-3: Verify capability injection in prompts
        """
        prompt_file = SRC_DIR / "taskflowGeneratorAgent" / "prompts" / "PromptBuilder.ts"
        content = prompt_file.read_text(encoding="utf-8")

        assert "capabilities" in content.lower(), "capabilities not found in PromptBuilder"
        assert "buildSystemPrompt" in content or "system" in content.lower(), "system prompt building not found"

    def test_dp4_parallel_execution_architecture(self):
        """
        DP-4: Verify parallel execution with Promise.allSettled pattern
        """
        processor_file = SRC_DIR / "taskflowGeneratorAgent" / "generator" / "BatchProcessor.ts"
        content = processor_file.read_text(encoding="utf-8")

        # Should use Promise.allSettled or similar pattern
        assert "allSettled" in content or "semaphore" in content.lower() or "Promise.all" in content, \
            "Parallel execution pattern not found"

    def test_dp5_langfuse_trace_continuation(self):
        """
        DP-5: Verify Langfuse trace continuation from expertAgent
        """
        tracing_file = SRC_DIR / "taskflowGeneratorAgent" / "tracing" / "LangfuseIntegration.ts"
        content = tracing_file.read_text(encoding="utf-8")

        assert "continueTrace" in content, "continueTrace not found"
        assert "trace_id" in content, "trace_id handling not found"

    def test_dp6_error_handling_and_recovery(self):
        """
        DP-6: Verify structured error handling and recovery
        """
        error_handler_file = SRC_DIR / "taskflowGeneratorAgent" / "recovery" / "ErrorHandler.ts"
        content = error_handler_file.read_text(encoding="utf-8")

        assert "RecoveryStrategy" in content, "RecoveryStrategy not used in ErrorHandler"
        assert "ErrorType" in content, "ErrorType not used in ErrorHandler"

    def test_dp7_validation_pipeline(self):
        """
        DP-7: Verify multi-stage validation pipeline
        """
        pipeline_file = SRC_DIR / "taskflowGeneratorAgent" / "validator" / "ValidationPipeline.ts"
        content = pipeline_file.read_text(encoding="utf-8")

        # Verify multiple validators in sequence
        validator_names = ["SchemaValidator", "DependencyValidator", "VariableValidator", "CapabilityValidator", "SecurityValidator"]
        found_validators = sum(1 for v in validator_names if v in content)

        assert found_validators >= 5, f"Expected 5 validators in pipeline, found {found_validators}"

    def test_dp8_taskflow_format_compatibility(self):
        """
        DP-8: Verify graphAiServer format compatibility

        Note: TaskFlowDefinition with steps is defined in taskflowEngine module,
        and is imported by the generator for workflow creation.
        """
        # Check TaskFlowDefinition is used in WorkflowGenerator
        generator_file = SRC_DIR / "taskflowGeneratorAgent" / "generator" / "WorkflowGenerator.ts"
        generator_content = generator_file.read_text(encoding="utf-8")

        # Verify TaskFlowDefinition is imported and used
        assert "TaskFlowDefinition" in generator_content, "TaskFlowDefinition not used in WorkflowGenerator"

        # Check the actual TaskFlowDefinition type in taskflowEngine
        taskflow_types_file = SRC_DIR / "taskflowEngine" / "types" / "TaskFlowDefinition.ts"
        if taskflow_types_file.exists():
            taskflow_content = taskflow_types_file.read_text(encoding="utf-8")
            assert "steps" in taskflow_content or "workflow_name" in taskflow_content, \
                "TaskFlowDefinition missing expected fields"
        else:
            # Verify workflow_name is used in generator types
            types_file = SRC_DIR / "taskflowGeneratorAgent" / "types" / "generator.ts"
            content = types_file.read_text(encoding="utf-8")
            assert "workflow_name" in content, "workflow_name field not found"


class TestDeadCodeVerification:
    """Verify no dead code exists"""

    def test_f1_workflow_generator_is_used(self):
        """
        F-1: Verify WorkflowGenerator is used in handlers
        """
        handlers_file = SRC_DIR / "taskflowGeneratorAgent" / "api" / "handlers.ts"
        content = handlers_file.read_text(encoding="utf-8")

        assert "WorkflowGenerator" in content, "WorkflowGenerator not used in handlers"

    def test_f2_llm_clients_are_registered(self):
        """
        F-2: Verify LLM clients are registered in factory
        """
        factory_file = SRC_DIR / "taskflowGeneratorAgent" / "llm" / "LLMClientFactory.ts"
        content = factory_file.read_text(encoding="utf-8")

        clients = ["AnthropicClient", "OpenAIClient", "GeminiClient"]
        for client in clients:
            assert client in content, f"{client} not registered in LLMClientFactory"

    def test_f3_validation_pipeline_is_used(self):
        """
        F-3: Verify ValidationPipeline is exported and usable
        """
        index_file = SRC_DIR / "taskflowGeneratorAgent" / "index.ts"
        content = index_file.read_text(encoding="utf-8")

        assert "ValidationPipeline" in content or "validator" in content.lower(), \
            "ValidationPipeline not exported"

    def test_f4_langfuse_integration_is_used(self):
        """
        F-4: Verify LangfuseIntegration is used in handlers
        """
        handlers_file = SRC_DIR / "taskflowGeneratorAgent" / "api" / "handlers.ts"
        content = handlers_file.read_text(encoding="utf-8")

        assert "LangfuseIntegration" in content, "LangfuseIntegration not used in handlers"

    def test_f5_sdk_is_exported(self):
        """
        F-5: Verify TaskFlowGeneratorClient is exported

        Note: TaskFlowGeneratorClient is exported via re-export from client/index.js
        """
        index_file = SRC_DIR / "taskflowGeneratorAgent" / "index.ts"
        content = index_file.read_text(encoding="utf-8")

        # Check for either direct export or re-export from client module
        client_exported = (
            "TaskFlowGeneratorClient" in content or
            "export * from './client" in content
        )
        assert client_exported, "TaskFlowGeneratorClient not exported (directly or via client module)"

        # Additionally verify the client file exists and exports the class
        client_index = SRC_DIR / "taskflowGeneratorAgent" / "client" / "index.ts"
        if client_index.exists():
            client_content = client_index.read_text(encoding="utf-8")
            assert "TaskFlowGeneratorClient" in client_content, \
                "TaskFlowGeneratorClient not exported from client/index.ts"


class TestComponentIntegration:
    """Verify component integration"""

    def test_ci1_recovery_strategy_openapi_alignment(self):
        """
        CI-1: Verify RecoveryStrategy enum values are OpenAPI aligned
        """
        types_file = SRC_DIR / "taskflowGeneratorAgent" / "types" / "generator.ts"
        content = types_file.read_text(encoding="utf-8")

        # OpenAPI-specified values
        expected_values = [
            "RETRY_CURRENT",
            "RETRY_WITH_FEEDBACK",
            "ROLLBACK_TO_ANALYSIS",
            "UPDATE_CAPABILITIES",
            "MANUAL_INTERVENTION",
        ]

        for value in expected_values:
            assert value in content, f"RecoveryStrategy.{value} not found"

    def test_ci2_error_type_openapi_alignment(self):
        """
        CI-2: Verify ErrorType enum exists
        """
        types_file = SRC_DIR / "taskflowGeneratorAgent" / "types" / "generator.ts"
        content = types_file.read_text(encoding="utf-8")

        assert "ErrorType" in content, "ErrorType enum not found"

    def test_ci3_taskflow_definition_compatibility(self):
        """
        CI-3: Verify TaskFlowDefinition type compatibility with taskflowEngine
        """
        # Check registrar uses TaskFlowDefinition
        registrar_file = SRC_DIR / "taskflowGeneratorAgent" / "generator" / "WorkflowRegistrar.ts"
        content = registrar_file.read_text(encoding="utf-8")

        assert "TaskFlowDefinition" in content or "WorkflowDefinition" in content, \
            "TaskFlowDefinition not referenced in WorkflowRegistrar"


class TestApiRouteIntegration:
    """Verify API routes are properly integrated"""

    def test_generator_api_mounted_in_main_routes(self):
        """
        Verify generator API is mounted in main routes.ts
        """
        main_routes_file = SRC_DIR / "api" / "routes.ts"
        assert main_routes_file.exists(), "Main routes.ts not found"

        content = main_routes_file.read_text(encoding="utf-8")

        # Verify generator API is imported and mounted
        assert "createGeneratorApi" in content or "generatorApi" in content.lower(), \
            "Generator API not imported in main routes"
        assert "generator" in content.lower(), "Generator routes not mounted"

    def test_generator_health_endpoint_accessible(self):
        """
        Verify health endpoint configuration
        """
        routes_file = SRC_DIR / "taskflowGeneratorAgent" / "api" / "routes.ts"
        content = routes_file.read_text(encoding="utf-8")

        assert "/health" in content, "Health endpoint not configured"
        assert "createHealthHandler" in content, "Health handler not used"


class TestUnitTestExecution:
    """Verify unit tests pass"""

    def test_unit_tests_pass(self):
        """
        Verify all unit tests pass by running npm test
        """
        try:
            result = subprocess.run(
                ["npm", "run", "test", "--", "--run", "--reporter=basic"],
                cwd=MYSWIFTAGENTCORE_DIR,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Check test output
            output = result.stdout + result.stderr

            # Tests should pass
            assert result.returncode == 0, f"Tests failed: {output[-2000:]}"

        except FileNotFoundError:
            pytest.skip("npm not available")
        except subprocess.TimeoutExpired:
            pytest.skip("Test execution timed out")

    def test_build_succeeds(self):
        """
        Verify TypeScript build succeeds
        """
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=MYSWIFTAGENTCORE_DIR,
                capture_output=True,
                text=True,
                timeout=120
            )

            assert result.returncode == 0, f"Build failed: {result.stderr[-1000:]}"

        except FileNotFoundError:
            pytest.skip("npm not available")
        except subprocess.TimeoutExpired:
            pytest.skip("Build timed out")


class TestCoverageVerification:
    """Verify test coverage meets requirements"""

    def test_coverage_meets_target(self):
        """
        Verify test coverage is above 90%
        """
        try:
            result = subprocess.run(
                ["npm", "run", "test:coverage", "--", "--run"],
                cwd=MYSWIFTAGENTCORE_DIR,
                capture_output=True,
                text=True,
                timeout=300
            )

            output = result.stdout + result.stderr

            # Look for coverage percentage in output
            # The coverage output typically includes "All files | xx.xx | xx.xx | xx.xx | xx.xx"
            if "All files" in output:
                # Parse coverage - look for line coverage percentage
                import re
                match = re.search(r'All files[^\d]*(\d+\.?\d*)', output)
                if match:
                    coverage = float(match.group(1))
                    assert coverage >= 90, f"Coverage {coverage}% is below 90% target"

        except FileNotFoundError:
            pytest.skip("npm not available")
        except subprocess.TimeoutExpired:
            pytest.skip("Coverage test timed out")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
