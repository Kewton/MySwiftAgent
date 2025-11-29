"""Scenario tests for Issue #177 - End-to-end validation of prompt YAML integration.

This test module verifies all 4 business scenarios work correctly with the new
YAML-based prompt system:

Scenario 1: 企業IR分析
Scenario 2: WebサイトPDF抽出
Scenario 3: Gmail検索ポッドキャスト生成
Scenario 4: キーワードポッドキャスト生成

Each scenario tests:
- jobTaskGeneratorAgents creates JobMaster/TaskMaster/InterfaceMaster
- workflowGeneratorAgents generates and executes LLM workflow

Note: These tests require external API keys (ANTHROPIC_API_KEY) and are skipped
in CI environments where these are not available.
"""

import os

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents import (
    create_initial_state,
    create_job_task_generator_agent,
)
from aiagent.langgraph.workflowGeneratorAgents import generate_workflow

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Skip all tests if running in CI without API keys
SKIP_REASON = "Skipped: requires ANTHROPIC_API_KEY for LLM invocation"
requires_api_key = pytest.mark.skipif(
    os.environ.get("CI") == "true"
    and not os.environ.get("ANTHROPIC_API_KEY_REAL"),
    reason=SKIP_REASON,
)


class TestScenario1_CorporateIRAnalysis:
    """Test Scenario 1: 企業IR分析 (Corporate IR Analysis)."""

    @requires_api_key
    @pytest.mark.asyncio
    async def test_job_task_generation(self):
        """Test JobMaster/TaskMaster creation for corporate IR analysis scenario."""
        user_requirement = (
            "指定した企業とそのIR情報が掲載されているサイトから"
            "過去5年の売り上げとビジネスモデルの変化を分析してメール送信する"
        )

        # Create initial state
        initial_state = create_initial_state(user_requirement=user_requirement)
        assert initial_state["user_requirement"] == user_requirement

        # Create and invoke agent
        agent = create_job_task_generator_agent()
        final_state = await agent.ainvoke(
            initial_state, config={"recursion_limit": 100}
        )

        # Verify job creation
        assert final_state.get("job_master_id") is not None, (
            "JobMaster should be created"
        )
        assert final_state.get("task_breakdown") is not None, "Tasks should be created"

        # Verify task breakdown structure
        task_breakdown = final_state["task_breakdown"]
        if isinstance(task_breakdown, dict):
            tasks = task_breakdown.get("tasks", [])
        else:
            tasks = task_breakdown

        assert len(tasks) > 0, "At least one task should be created"

        # Verify interface definitions exist
        interface_definitions = final_state.get("interface_definitions", {})
        assert len(interface_definitions) > 0, "Interface definitions should be created"

    @requires_api_key
    @pytest.mark.asyncio
    async def test_workflow_generation(self):
        """Test workflow generation for corporate IR analysis scenario (mock TaskMaster)."""
        # Mock TaskMaster data
        task_data = {
            "task_master_id": "tm_test_scenario1",
            "name": "Analyze corporate IR data",
            "description": "Fetch and analyze corporate IR information from website",
            "input_interface": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "ir_url": {"type": "string"},
                },
                "required": ["company_name", "ir_url"],
            },
            "output_interface": {
                "type": "object",
                "properties": {
                    "analysis_result": {"type": "string"},
                    "revenue_trend": {"type": "array"},
                },
                "required": ["analysis_result"],
            },
        }

        # Generate workflow
        final_state = await generate_workflow(
            task_master_id="tm_test_scenario1",
            task_data=task_data,
            max_retry=3,
        )

        # Verify workflow generation
        assert final_state.get("yaml_content") is not None, "YAML should be generated"
        assert final_state.get("workflow_name") is not None, (
            "Workflow name should exist"
        )

        # If validation passed, check status
        if final_state.get("is_valid"):
            assert final_state["status"] == "success", (
                "Status should be success when valid"
            )


class TestScenario2_WebsitePDFExtraction:
    """Test Scenario 2: WebサイトPDF抽出 (Website PDF Extraction)."""

    @requires_api_key
    @pytest.mark.asyncio
    async def test_job_task_generation(self):
        """Test JobMaster/TaskMaster creation for PDF extraction scenario."""
        user_requirement = (
            "指定したWebサイトからすべてのPDFファイルを抽出し、"
            "各pdfファイルを指定したGoogle Driveのディレクトリに"
            "サブディレクトリを作成してアップロードしメールで通知する"
        )

        initial_state = create_initial_state(user_requirement=user_requirement)
        agent = create_job_task_generator_agent()
        final_state = await agent.ainvoke(
            initial_state, config={"recursion_limit": 100}
        )

        # Verify results
        assert final_state.get("job_master_id") is not None
        assert final_state.get("task_breakdown") is not None

        task_breakdown = final_state["task_breakdown"]
        if isinstance(task_breakdown, dict):
            tasks = task_breakdown.get("tasks", [])
        else:
            tasks = task_breakdown

        assert len(tasks) > 0

    @requires_api_key
    @pytest.mark.asyncio
    async def test_workflow_generation(self):
        """Test workflow generation for PDF extraction scenario."""
        task_data = {
            "task_master_id": "tm_test_scenario2",
            "name": "Extract PDFs from website",
            "description": "Scan website and extract all PDF files",
            "input_interface": {
                "type": "object",
                "properties": {
                    "website_url": {"type": "string"},
                    "drive_folder_id": {"type": "string"},
                },
                "required": ["website_url", "drive_folder_id"],
            },
            "output_interface": {
                "type": "object",
                "properties": {
                    "pdf_count": {"type": "integer"},
                    "upload_status": {"type": "string"},
                },
                "required": ["pdf_count"],
            },
        }

        final_state = await generate_workflow(
            task_master_id="tm_test_scenario2",
            task_data=task_data,
            max_retry=3,
        )

        assert final_state.get("yaml_content") is not None
        assert final_state.get("workflow_name") is not None


class TestScenario3_GmailPodcastGeneration:
    """Test Scenario 3: Gmail検索ポッドキャスト生成 (Gmail Search Podcast)."""

    @requires_api_key
    @pytest.mark.asyncio
    async def test_job_task_generation(self):
        """Test JobMaster/TaskMaster creation for Gmail podcast scenario."""
        user_requirement = (
            "This workflow searches for a newsletter in Gmail using a keyword, "
            "summarizes it, converts it to an MP3 podcast"
        )

        initial_state = create_initial_state(user_requirement=user_requirement)
        agent = create_job_task_generator_agent()
        final_state = await agent.ainvoke(
            initial_state, config={"recursion_limit": 100}
        )

        assert final_state.get("job_master_id") is not None
        assert final_state.get("task_breakdown") is not None

        task_breakdown = final_state["task_breakdown"]
        if isinstance(task_breakdown, dict):
            tasks = task_breakdown.get("tasks", [])
        else:
            tasks = task_breakdown

        assert len(tasks) > 0

    @requires_api_key
    @pytest.mark.asyncio
    async def test_workflow_generation(self):
        """Test workflow generation for Gmail podcast scenario."""
        task_data = {
            "task_master_id": "tm_test_scenario3",
            "name": "Convert Gmail newsletter to podcast",
            "description": "Search Gmail, summarize, and convert to MP3",
            "input_interface": {
                "type": "object",
                "properties": {
                    "search_keyword": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["search_keyword"],
            },
            "output_interface": {
                "type": "object",
                "properties": {
                    "podcast_url": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["podcast_url"],
            },
        }

        final_state = await generate_workflow(
            task_master_id="tm_test_scenario3",
            task_data=task_data,
            max_retry=3,
        )

        assert final_state.get("yaml_content") is not None
        assert final_state.get("workflow_name") is not None


class TestScenario4_KeywordPodcastGeneration:
    """Test Scenario 4: キーワードポッドキャスト生成 (Keyword Podcast Generation)."""

    @requires_api_key
    @pytest.mark.asyncio
    async def test_job_task_generation(self):
        """Test JobMaster/TaskMaster creation for keyword podcast scenario."""
        user_requirement = (
            "ユーザーがキーワード入力するとそれに関連するポッドキャストを"
            "生成してそのリンクをメール送信する"
        )

        initial_state = create_initial_state(user_requirement=user_requirement)
        agent = create_job_task_generator_agent()
        final_state = await agent.ainvoke(
            initial_state, config={"recursion_limit": 100}
        )

        assert final_state.get("job_master_id") is not None
        assert final_state.get("task_breakdown") is not None

        task_breakdown = final_state["task_breakdown"]
        if isinstance(task_breakdown, dict):
            tasks = task_breakdown.get("tasks", [])
        else:
            tasks = task_breakdown

        assert len(tasks) > 0

    @requires_api_key
    @pytest.mark.asyncio
    async def test_workflow_generation(self):
        """Test workflow generation for keyword podcast scenario."""
        task_data = {
            "task_master_id": "tm_test_scenario4",
            "name": "Generate podcast from keyword",
            "description": "Create podcast content based on user keyword",
            "input_interface": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "user_email": {"type": "string"},
                },
                "required": ["keyword", "user_email"],
            },
            "output_interface": {
                "type": "object",
                "properties": {
                    "podcast_link": {"type": "string"},
                    "email_sent": {"type": "boolean"},
                },
                "required": ["podcast_link"],
            },
        }

        final_state = await generate_workflow(
            task_master_id="tm_test_scenario4",
            task_data=task_data,
            max_retry=3,
        )

        assert final_state.get("yaml_content") is not None
        assert final_state.get("workflow_name") is not None
