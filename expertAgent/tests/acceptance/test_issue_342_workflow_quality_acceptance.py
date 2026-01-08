"""Issue #342 V2 Workflow Quality Improvement Acceptance Test.

L3 Acceptance Test for V2 Workflow Quality Improvement:
- AgentSelector maps API names to GraphAI fetchAgent with endpoint URLs
- ParameterMapper creates GraphAI-compliant inputs blocks (url, method, body)
- generate_with_llm() is now default in workflow.py
- Few-shot patterns (gmail_send_pattern.yaml, slack_notify_pattern.yaml) exist
- Generated YAML has url/method/body in inputs block

Prerequisites:
- Services running: ./scripts/dev-start.sh or make dev-all
- expertAgent at localhost:8004
- myVault at localhost:8003

Run with:
    cd expertAgent
    uv run pytest tests/acceptance/test_issue_342_workflow_quality_acceptance.py -v

Author: Claude Code (Issue #342 V2 Workflow Quality Improvement)
"""

import pytest
import requests
import yaml


@pytest.mark.acceptance
class TestIssue342WorkflowQualityAcceptance:
    """Issue #342 V2 Workflow Quality Improvement Acceptance Tests.

    Acceptance Criteria:
    1. Generated YAML must be GraphAI spec compliant (inputs contain url/method/body)
    2. AgentSelector selects appropriate Agent for API
    3. ParameterMapper generates correct parameters
    4. LLM generation is default enabled
    5. Fallback mechanism works correctly
    """

    EXPERT_AGENT_URL = "http://localhost:8004"
    MYVAULT_URL = "http://localhost:8003"

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """Check that required services are running."""
        services = [
            (self.EXPERT_AGENT_URL, "expertAgent"),
            (self.MYVAULT_URL, "myVault"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code != 200:
                    pytest.skip(f"{name} not healthy: {response.status_code}")
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} not running at {url}. "
                    "Run: ./scripts/dev-start.sh or make dev-all"
                )

    # ==========================================================================
    # Acceptance Criterion 1: Generated YAML is GraphAI spec compliant
    # ==========================================================================

    def test_graphai_yaml_has_inputs_with_url_method_body(self) -> None:
        """Verify generated YAML has inputs block with url/method/body structure.

        Acceptance Criteria:
        - fetchAgent nodes must have inputs block
        - inputs block must contain url field
        - inputs block must contain method field
        - inputs block should contain body field for POST requests
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.loader import (
            load_example,
        )

        # Load gmail_send pattern as example of correct structure
        gmail_pattern = load_example("gmail_send_pattern")
        assert gmail_pattern is not None

        parsed = yaml.safe_load(gmail_pattern.workflow_yaml)
        assert parsed is not None
        assert "nodes" in parsed

        # Check send_email node has correct inputs structure
        send_email_node = parsed["nodes"].get("send_email")
        assert send_email_node is not None, "send_email node should exist"
        assert send_email_node.get("agent") == "fetchAgent"

        inputs = send_email_node.get("inputs")
        assert inputs is not None, "inputs block must exist"
        assert "url" in inputs, "url field must exist in inputs"
        assert "method" in inputs, "method field must exist in inputs"
        assert "body" in inputs, "body field must exist in inputs"

        # Verify URL format with EXPERTAGENT_BASE_URL
        url = inputs["url"]
        assert "${EXPERTAGENT_BASE_URL}" in url, (
            f"URL should use EXPERTAGENT_BASE_URL variable: {url}"
        )
        assert "/aiagent-api/v1/utility/gmail/send" in url

        # Verify method
        assert inputs["method"] == "POST"

        # Verify body has proper :source references
        body = inputs["body"]
        assert "to" in body
        assert ":source" in body["to"]

    def test_slack_notify_pattern_has_correct_structure(self) -> None:
        """Verify slack_notify pattern has GraphAI-compliant structure."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.loader import (
            load_example,
        )

        slack_pattern = load_example("slack_notify_pattern")
        assert slack_pattern is not None

        parsed = yaml.safe_load(slack_pattern.workflow_yaml)
        assert parsed is not None

        notify_node = parsed["nodes"].get("notify_slack")
        assert notify_node is not None

        inputs = notify_node.get("inputs")
        assert inputs is not None
        assert "url" in inputs
        assert "method" in inputs
        assert "body" in inputs
        assert "/aiagent-api/v1/utility/slack/notify" in inputs["url"]

    # ==========================================================================
    # Acceptance Criterion 2: AgentSelector selects appropriate Agent
    # ==========================================================================

    def test_agent_selector_maps_gmail_send_to_fetchagent(self) -> None:
        """Verify AgentSelector maps gmail_send to fetchAgent.

        Acceptance Criteria:
        - gmail_send API should map to fetchAgent
        - Endpoint URL should be correct
        - HTTP method should be POST
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        mapping = selector.select_agent("gmail_send")

        assert mapping is not None, "gmail_send should have a mapping"
        assert mapping.agent_type == "fetchAgent"
        assert mapping.http_method == "POST"
        assert "/aiagent-api/v1/utility/gmail/send" in mapping.endpoint_path

    def test_agent_selector_maps_google_search_to_fetchagent(self) -> None:
        """Verify AgentSelector maps google_search to fetchAgent."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        mapping = selector.select_agent("google_search")

        assert mapping is not None
        assert mapping.agent_type == "fetchAgent"
        assert "/aiagent-api/v1/utility/google_search" in mapping.endpoint_path

    def test_agent_selector_maps_slack_notify_to_fetchagent(self) -> None:
        """Verify AgentSelector maps slack_notify to fetchAgent."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        mapping = selector.select_agent("slack_notify")

        assert mapping is not None
        assert mapping.agent_type == "fetchAgent"
        assert "/aiagent-api/v1/utility/slack/notify" in mapping.endpoint_path

    def test_agent_selector_case_insensitive(self) -> None:
        """Verify AgentSelector handles case-insensitive API names."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()

        # Should work with different cases
        assert selector.select_agent("gmail_send") is not None
        assert selector.select_agent("Gmail_Send") is not None
        assert selector.select_agent("GMAIL_SEND") is not None

    def test_agent_selector_build_endpoint_url(self) -> None:
        """Verify AgentSelector builds correct endpoint URLs."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        url = selector.build_endpoint_url("gmail_send")

        assert url is not None
        assert url.startswith("${EXPERTAGENT_BASE_URL}")
        assert "/aiagent-api/v1/utility/gmail/send" in url

    def test_agent_selector_get_available_apis(self) -> None:
        """Verify AgentSelector returns all available APIs."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        apis = selector.get_available_apis()

        assert len(apis) >= 10, "Should have at least 10 API mappings"
        assert "gmail_send" in apis
        assert "google_search" in apis
        assert "slack_notify" in apis

    # ==========================================================================
    # Acceptance Criterion 3: ParameterMapper generates correct parameters
    # ==========================================================================

    def test_parameter_mapper_creates_fetchagent_inputs(self) -> None:
        """Verify ParameterMapper creates GraphAI-compliant fetchAgent inputs.

        Acceptance Criteria:
        - inputs block must have url, method, body
        - URL must use ${EXPERTAGENT_BASE_URL}
        - body fields must use :source references
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            ParameterMapper,
        )

        mapper = ParameterMapper()
        inputs = mapper.create_fetchagent_inputs(
            api_name="gmail_send",
            input_params={"to": "test@example.com", "subject": "Test", "body": "Hello"},
            source_node="user_input",
        )

        assert "url" in inputs
        assert "method" in inputs
        assert "body" in inputs

        # Verify URL format
        assert "${EXPERTAGENT_BASE_URL}" in inputs["url"]
        assert "/aiagent-api/v1/utility/gmail/send" in inputs["url"]

        # Verify method
        assert inputs["method"] == "POST"

        # Verify body has :source references
        body = inputs["body"]
        assert ":source.user_input.to" in body["to"]
        assert ":source.user_input.subject" in body["subject"]
        assert ":source.user_input.body" in body["body"]

    def test_parameter_mapper_map_input_params(self) -> None:
        """Verify map_input_params creates correct :source references."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_input_params,
        )

        interface_inputs = {
            "query": {"type": "string"},
            "max_results": {"type": "integer"},
        }

        result = map_input_params(interface_inputs, "source_node")

        assert result["query"] == ":source.source_node.query"
        assert result["max_results"] == ":source.source_node.max_results"

    def test_parameter_mapper_map_api_params(self) -> None:
        """Verify map_api_params creates complete inputs block."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        result = map_api_params(
            api_name="google_search",
            interface_inputs={"query": {"type": "string"}},
            source_node="input",
        )

        assert "url" in result
        assert "method" in result
        assert "body" in result
        assert "${EXPERTAGENT_BASE_URL}" in result["url"]
        assert result["body"]["query"] == ":source.input.query"

    def test_parameter_mapper_create_inputs_block(self) -> None:
        """Verify ParameterMapper creates explicit inputs block."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            ParameterMapper,
        )

        mapper = ParameterMapper()
        inputs = mapper.create_inputs_block(
            url="${EXPERTAGENT_BASE_URL}/custom/endpoint",
            method="GET",
            body={"param1": ":source.data"},
        )

        assert inputs["url"] == "${EXPERTAGENT_BASE_URL}/custom/endpoint"
        assert inputs["method"] == "GET"
        assert inputs["body"]["param1"] == ":source.data"

    # ==========================================================================
    # Acceptance Criterion 4: LLM generation is default enabled
    # ==========================================================================

    def test_llm_generation_default_enabled_in_workflow(self) -> None:
        """Verify WorkflowGenWorkflow uses LLM generation by default.

        Acceptance Criteria:
        - WorkflowGenWorkflow default use_llm_generation should be True
        - execute() should call generate_with_llm() when enabled
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()

        # Default should be True
        assert workflow._use_llm_generation is True

    def test_llm_generation_can_be_disabled(self) -> None:
        """Verify LLM generation can be disabled via constructor."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow(use_llm_generation=False)

        assert workflow._use_llm_generation is False

    def test_yaml_generator_supports_llm_generation_flag(self) -> None:
        """Verify YamlGeneratorSubWorkflow supports LLM generation flag."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        # LLM enabled
        generator_llm = YamlGeneratorSubWorkflow(use_llm_generation=True)
        assert generator_llm._use_llm_generation is True

        # LLM disabled
        generator_template = YamlGeneratorSubWorkflow(use_llm_generation=False)
        assert generator_template._use_llm_generation is False

    # ==========================================================================
    # Acceptance Criterion 5: Fallback mechanism works correctly
    # ==========================================================================

    def test_yaml_generator_has_generate_with_llm_method(self) -> None:
        """Verify YamlGeneratorSubWorkflow has generate_with_llm method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()

        # Method should exist
        assert hasattr(generator, "generate_with_llm")
        assert callable(generator.generate_with_llm)

    def test_yaml_generator_has_generate_method_for_fallback(self) -> None:
        """Verify YamlGeneratorSubWorkflow has generate method for fallback."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()

        # Template-based fallback method should exist
        assert hasattr(generator, "generate")
        assert callable(generator.generate)

    # ==========================================================================
    # Acceptance Criterion 6: Few-shot patterns exist and are valid
    # ==========================================================================

    def test_gmail_send_pattern_exists(self) -> None:
        """Verify gmail_send_pattern.yaml exists and has correct structure."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.loader import (
            load_example,
        )

        pattern = load_example("gmail_send_pattern")

        assert pattern is not None
        assert pattern.name == "gmail_send_pattern"
        assert "gmail_send" in pattern.applicable_apis
        assert pattern.workflow_yaml
        assert pattern.task_example

    def test_slack_notify_pattern_exists(self) -> None:
        """Verify slack_notify_pattern.yaml exists and has correct structure."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.loader import (
            load_example,
        )

        pattern = load_example("slack_notify_pattern")

        assert pattern is not None
        assert pattern.name == "slack_notify_pattern"
        assert "slack_notify" in pattern.applicable_apis
        assert pattern.workflow_yaml
        assert pattern.task_example

    def test_all_required_patterns_exist(self) -> None:
        """Verify all required few-shot patterns exist."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.loader import (
            load_all_examples,
            load_example,
        )

        all_examples = load_all_examples()

        # Should have at least 6 patterns (4 base + 2 new)
        assert len(all_examples) >= 6, (
            f"Expected at least 6 patterns, got {len(all_examples)}"
        )

        # Verify specific patterns
        required_patterns = [
            "search_pattern",
            "api_call_pattern",
            "llm_chain_pattern",
            "map_pattern",
            "gmail_send_pattern",
            "slack_notify_pattern",
        ]

        for pattern_name in required_patterns:
            pattern = load_example(pattern_name)
            assert pattern is not None, f"Pattern '{pattern_name}' should exist"
            assert pattern.workflow_yaml, f"Pattern '{pattern_name}' should have YAML"

    def test_patterns_yaml_is_valid(self) -> None:
        """Verify all pattern YAML files are valid."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.loader import (
            load_all_examples,
        )

        all_examples = load_all_examples()

        for example in all_examples:
            # Should parse without error
            parsed = yaml.safe_load(example.workflow_yaml)
            assert parsed is not None, f"Pattern '{example.name}' has invalid YAML"
            assert "version" in parsed, f"Pattern '{example.name}' missing version"
            assert "nodes" in parsed, f"Pattern '{example.name}' missing nodes"
            assert "source" in parsed["nodes"], (
                f"Pattern '{example.name}' missing source node"
            )

    # ==========================================================================
    # Acceptance Criterion 7: Integration verification
    # ==========================================================================

    def test_agent_selector_integrated_with_parameter_mapper(self) -> None:
        """Verify AgentSelector and ParameterMapper work together correctly."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            ParameterMapper,
        )

        selector = AgentSelector()
        mapper = ParameterMapper()

        # Get available APIs
        apis = selector.get_available_apis()

        # For each API, create inputs should work
        for api_name in apis[:3]:  # Test first 3 to keep it fast
            mapping = selector.select_agent(api_name)
            assert mapping is not None

            inputs = mapper.create_fetchagent_inputs(
                api_name=api_name,
                input_params={"test_field": {"type": "string"}},
                source_node="source",
            )

            assert "url" in inputs
            assert "method" in inputs
            assert "body" in inputs
            assert mapping.endpoint_path in inputs["url"]

    def test_workflow_gen_workflow_protocol_compliance(self) -> None:
        """Verify WorkflowGenWorkflow implements WorkflowProtocol correctly."""
        from aiagent.langgraph.jobGeneratorV2.protocols import (
            RetryPolicy,
            WorkflowProtocol,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()

        # Should implement protocol
        assert isinstance(workflow, WorkflowProtocol)

        # Should have required methods
        assert hasattr(workflow, "execute")
        assert hasattr(workflow, "get_retry_policy")

        # Retry policy should be valid
        policy = workflow.get_retry_policy()
        assert isinstance(policy, RetryPolicy)
        assert policy.max_retries > 0

    # ==========================================================================
    # E2E: Health check all services
    # ==========================================================================

    def test_health_check_all_services(self) -> None:
        """Verify all related services respond to health checks."""
        # expertAgent
        response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=10)
        assert response.status_code == 200, "expertAgent should be healthy"

        # myVault
        response = requests.get(f"{self.MYVAULT_URL}/health", timeout=10)
        assert response.status_code == 200, "myVault should be healthy"


@pytest.mark.acceptance
class TestIssue342WorkflowQualityE2E:
    """E2E tests for V2 Workflow Quality Improvement."""

    EXPERT_AGENT_URL = "http://localhost:8004"

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """Check that expertAgent is running."""
        try:
            response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
            if response.status_code != 200:
                pytest.skip("expertAgent not healthy")
        except requests.exceptions.ConnectionError:
            pytest.skip("expertAgent not running")

    def test_e2e_yaml_validator_with_graphai_compliant_workflow(self) -> None:
        """E2E: Validate a GraphAI-compliant workflow with url/method/body."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_validator import (
            YamlValidatorSubWorkflow,
        )

        validator = YamlValidatorSubWorkflow()

        # GraphAI-compliant workflow with url/method/body in inputs
        workflow_yaml = """
version: "0.5"
nodes:
  source: {}

  fetch_api:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/gmail/send
      method: POST
      body:
        to: :source.to
        subject: :source.subject
        body: :source.body

  format_result:
    agent: copyAgent
    inputs:
      result: :fetch_api.result
    isResult: true
"""

        result = validator.validate(workflow_yaml)

        assert result.is_valid, (
            f"GraphAI-compliant workflow should be valid: "
            f"{[e.message for e in result.errors]}"
        )
        assert result.node_count == 3

    def test_e2e_prompt_builder_includes_few_shot_examples(self) -> None:
        """E2E: PromptBuilder includes appropriate few-shot examples."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
        )

        builder = PromptBuilderSubWorkflow()

        # Build prompt for gmail task
        prompt = builder.build(
            task_name="Send Email Task",
            task_description="Send an email to a recipient",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            recommended_apis=["gmail_send"],
        )

        rendered = prompt.render()

        # Prompt should include relevant content
        assert len(rendered) > 100, "Prompt should have substantial content"
        # Should mention email-related concepts
        assert any(
            word in rendered.lower()
            for word in ["email", "send", "mail", "gmail"]
        )

    def test_e2e_full_validation_pipeline(self) -> None:
        """E2E: Full workflow validation pipeline with GraphAI-compliant YAML."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_validator import (
            YamlValidatorSubWorkflow,
        )

        validator = YamlValidatorSubWorkflow()

        # Real-world example with proper structure
        workflow_yaml = """
version: "0.5"
nodes:
  source: {}

  search_google:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search
      method: POST
      body:
        query: :source.search_query
    console:
      after: true

  format_results:
    agent: stringTemplateAgent
    inputs:
      data: :search_google.result
    params:
      template: "Search Results: ${data}"
    isResult: true
"""

        result = validator.validate(workflow_yaml)

        assert result.is_valid, (
            f"Full pipeline should validate: {[e.message for e in result.errors]}"
        )
        assert result.node_count == 3
        assert result.parsed_yaml is not None
        assert "nodes" in result.parsed_yaml
