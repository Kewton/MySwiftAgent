"""Unit tests for MasterManagerSubWorkflow.

Issue #342 Phase 1: Tests for body_template fix.
- Task 0 should use {{job.body.user_input}} for user_input field (GraphAI)
- Task 1+ should use {{tasks[N].output_data}} for user_input field (GraphAI)

Issue #350: Added TaskFlow V2 body_template tests.
- TaskFlow uses inputs, workflow_name, project format
"""

from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
    MasterManagerSubWorkflow,
)


class TestBuildBodyTemplate:
    """Tests for _build_body_template method (GraphAI engine)."""

    def test_build_body_template_task_0_uses_user_input(self) -> None:
        """Task 0 body_template (GraphAI) should use {{job.body.user_input}} for user_input field.

        This is the critical fix for Issue #342 - body_template double nesting problem.
        Previously: user_input = {{job.body}} caused double nesting when Task 0
        wraps job.body in user_input, making :source.user_input.query fail.

        Expected: user_input = {{job.body.user_input}} to access user_input directly.
        """
        manager = MasterManagerSubWorkflow(engine="graphai")
        body_template = manager._build_body_template(order=0)

        # Critical assertion: user_input should reference job.body.user_input
        # NOT job.body (which would cause double nesting)
        assert body_template["user_input"] == "{{job.body.user_input}}", (
            "Task 0 user_input should be '{{job.body.user_input}}' to avoid double nesting. "
            f"Got: {body_template['user_input']}"
        )

        # job_params should still reference entire job.body
        assert body_template["job_params"] == "{{job.body}}"

    def test_build_body_template_task_1_uses_previous_output(self) -> None:
        """Task 1 body_template (GraphAI) should reference previous task's output.

        Task 1 should get data from tasks[0].output_data.
        """
        manager = MasterManagerSubWorkflow(engine="graphai")
        body_template = manager._build_body_template(order=1)

        # Task 1 should reference tasks[0].output_data
        assert body_template["user_input"] == "{{tasks[0].output_data}}"
        assert body_template["job_params"] == "{{job.body}}"

    def test_build_body_template_task_2_uses_previous_output(self) -> None:
        """Task 2 body_template (GraphAI) should reference previous task's output.

        Task 2 should get data from tasks[1].output_data.
        """
        manager = MasterManagerSubWorkflow(engine="graphai")
        body_template = manager._build_body_template(order=2)

        # Task 2 should reference tasks[1].output_data
        assert body_template["user_input"] == "{{tasks[1].output_data}}"
        assert body_template["job_params"] == "{{job.body}}"

    def test_build_body_template_structure(self) -> None:
        """Body template (GraphAI) should always have user_input and job_params keys."""
        manager = MasterManagerSubWorkflow(engine="graphai")

        for order in range(5):
            body_template = manager._build_body_template(order=order)
            assert "user_input" in body_template
            assert "job_params" in body_template
            assert len(body_template) == 2, "Body template should only have 2 keys"

    def test_build_body_template_task_0_does_not_double_nest(self) -> None:
        """Verify Task 0 template (GraphAI) doesn't cause double nesting issue.

        When job.body = {"user_input": {"query": "test"}}:
        - WRONG: {{job.body}} -> {"user_input": {"query": "test"}}
                 Then :source.user_input.query fails (needs :source.user_input.user_input.query)
        - RIGHT: {{job.body.user_input}} -> {"query": "test"}
                 Then :source.user_input.query works correctly
        """
        manager = MasterManagerSubWorkflow(engine="graphai")
        body_template = manager._build_body_template(order=0)

        # The user_input value should NOT be "{{job.body}}"
        # because that would cause double nesting
        assert body_template["user_input"] != "{{job.body}}", (
            "Task 0 user_input should NOT be '{{job.body}}' - this causes double nesting"
        )

        # It should be "{{job.body.user_input}}" to properly extract user_input
        assert "user_input" in body_template["user_input"], (
            "Task 0 user_input template should reference 'user_input' path"
        )


class TestBuildBodyTemplateTaskFlow:
    """Tests for _build_body_template method (TaskFlow V2 engine).

    Issue #350: TaskFlow V2 uses different body_template format.
    """

    def test_build_body_template_task_0_taskflow(self) -> None:
        """Task 0 body_template (TaskFlow) should use inputs, workflow, project.

        Issue #390: Changed from workflow_name to workflow for mySwiftAgentCore API.
        Issue #391: Changed from {{job.project}} to {{job.body.project}}.
        """
        manager = MasterManagerSubWorkflow(engine="taskflow")
        body_template = manager._build_body_template(order=0)

        # TaskFlow uses different keys
        # Issue #390: mySwiftAgentCore expects "workflow" field (not "workflow_name")
        # Issue #391: project uses {{job.body.project}} (Job model has no project attr)
        assert body_template["workflow"] == "__PENDING__"
        assert body_template["inputs"] == "{{job.body}}"
        assert body_template["project"] == "{{job.body.project}}"
        assert len(body_template) == 3

    def test_build_body_template_task_1_taskflow(self) -> None:
        """Task 1 body_template (TaskFlow) should use previous task output as inputs.

        Issue #390: Changed from workflow_name to workflow for mySwiftAgentCore API.
        Issue #391: Changed from {{job.project}} to {{job.body.project}}.
        """
        manager = MasterManagerSubWorkflow(engine="taskflow")
        body_template = manager._build_body_template(order=1)

        # Issue #390: mySwiftAgentCore expects "workflow" field (not "workflow_name")
        # Issue #391: project uses {{job.body.project}} (Job model has no project attr)
        assert body_template["workflow"] == "__PENDING__"
        assert body_template["inputs"] == "{{tasks[0].output_data}}"
        assert body_template["project"] == "{{job.body.project}}"

    def test_build_body_template_structure_taskflow(self) -> None:
        """Body template (TaskFlow) should always have workflow, inputs, project keys.

        Issue #390: Changed from workflow_name to workflow for mySwiftAgentCore API.
        """
        manager = MasterManagerSubWorkflow(engine="taskflow")

        for order in range(5):
            body_template = manager._build_body_template(order=order)
            # Issue #390: mySwiftAgentCore expects "workflow" field (not "workflow_name")
            assert "workflow" in body_template
            assert "inputs" in body_template
            assert "project" in body_template
            assert len(body_template) == 3
