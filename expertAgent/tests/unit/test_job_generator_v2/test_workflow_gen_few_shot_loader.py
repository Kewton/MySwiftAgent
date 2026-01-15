"""Tests for Few-shot loader.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot import (
    FewShotExample,
    get_example_by_api,
    load_all_examples,
    load_example,
    select_few_shot_examples,
)


class TestFewShotExample:
    """Tests for FewShotExample dataclass."""

    def test_create_example(self):
        """Test creating a FewShotExample."""
        example = FewShotExample(
            name="test_pattern",
            description="Test description",
            applicable_apis=["test_api"],
            task_example={"name": "Test"},
            workflow_yaml="version: 0.5\nnodes: {}",
        )
        assert example.name == "test_pattern"
        assert example.description == "Test description"
        assert "test_api" in example.applicable_apis
        assert "version" in example.workflow_yaml


class TestLoadExample:
    """Tests for load_example function."""

    def test_load_search_pattern(self):
        """Test loading search_pattern example."""
        example = load_example("search_pattern")
        assert example is not None
        assert example.name == "search_pattern"
        assert "google_search" in example.applicable_apis

    def test_load_api_call_pattern(self):
        """Test loading api_call_pattern example."""
        example = load_example("api_call_pattern")
        assert example is not None
        assert example.name == "api_call_pattern"
        assert "gmail_send" in example.applicable_apis

    def test_load_llm_chain_pattern(self):
        """Test loading llm_chain_pattern example."""
        example = load_example("llm_chain_pattern")
        assert example is not None
        assert example.name == "llm_chain_pattern"

    def test_load_map_pattern(self):
        """Test loading map_pattern example."""
        example = load_example("map_pattern")
        assert example is not None
        assert example.name == "map_pattern"

    def test_load_nonexistent_pattern(self):
        """Test loading nonexistent pattern returns None."""
        example = load_example("nonexistent_pattern")
        assert example is None


class TestLoadAllExamples:
    """Tests for load_all_examples function."""

    def test_load_all_examples(self):
        """Test loading all examples."""
        examples = load_all_examples()
        assert len(examples) >= 4  # At least 4 patterns
        names = [e.name for e in examples]
        assert "search_pattern" in names
        assert "api_call_pattern" in names

    def test_all_examples_have_workflow_yaml(self):
        """Test all examples have workflow_yaml."""
        examples = load_all_examples()
        for example in examples:
            assert example.workflow_yaml
            assert len(example.workflow_yaml) > 10


class TestSelectFewShotExamples:
    """Tests for select_few_shot_examples function."""

    def test_select_for_search_api(self):
        """Test selecting examples for search API."""
        examples = select_few_shot_examples(
            recommended_apis=["google_search"],
        )
        assert len(examples) > 0
        # Should select search_pattern
        names = [e.name for e in examples]
        assert "search_pattern" in names

    def test_select_for_gmail_send(self):
        """Test selecting examples for gmail send."""
        examples = select_few_shot_examples(
            recommended_apis=["gmail/send"],
        )
        assert len(examples) > 0

    def test_select_for_array_output(self):
        """Test selecting examples for array output."""
        examples = select_few_shot_examples(
            output_schema={"type": "array", "items": {"type": "object"}},
        )
        assert len(examples) > 0
        # Should favor map_pattern
        names = [e.name for e in examples]
        assert "map_pattern" in names

    def test_select_for_llm_api(self):
        """Test selecting examples for LLM API."""
        examples = select_few_shot_examples(
            recommended_apis=["jsonoutput"],
        )
        assert len(examples) > 0
        names = [e.name for e in examples]
        assert "llm_chain_pattern" in names

    def test_select_default_when_no_match(self):
        """Test selecting default when no specific match."""
        examples = select_few_shot_examples()
        assert len(examples) > 0
        # Should return at least api_call_pattern as default

    def test_select_max_examples(self):
        """Test selecting respects max_examples."""
        examples = select_few_shot_examples(
            recommended_apis=["google_search", "gmail_send", "jsonoutput"],
            max_examples=1,
        )
        assert len(examples) == 1

    def test_select_with_complex_criteria(self):
        """Test selecting with multiple criteria."""
        examples = select_few_shot_examples(
            recommended_apis=["google_search"],
            input_schema={"type": "object", "properties": {"items": {"type": "array"}}},
            output_schema={
                "type": "object",
                "properties": {"results": {"type": "array"}},
            },
            dependencies=["task_1", "task_2", "task_3"],
        )
        assert len(examples) > 0


class TestGetExampleByApi:
    """Tests for get_example_by_api function."""

    def test_get_by_google_search(self):
        """Test getting example by google_search API."""
        example = get_example_by_api("google_search")
        assert example is not None
        # Should return search_pattern or api_call_pattern

    def test_get_by_gmail_send(self):
        """Test getting example by gmail_send API."""
        example = get_example_by_api("gmail_send")
        assert example is not None

    def test_get_by_unknown_api(self):
        """Test getting example by unknown API returns default."""
        example = get_example_by_api("unknown_api_xyz")
        # Should return default api_call_pattern
        assert example is not None
