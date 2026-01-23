"""
Issue #395 受入テスト（L3: ローカル受入テスト）

fix(jobGeneratorV2): BodyTemplateValidator がシステム注入フィールド (project) を誤って検証する

受入条件:
- AC-1: ホワイトリスト定数 SYSTEM_INJECTED_FIELDS が定義されている
- AC-2: project フィールドが検証から除外される
- AC-3: ユーザー入力フィールド（user_input 等）は引き続き検証される
- AC-4: 単体テストカバレッジ 90% 以上
- AC-5: E2E でジョブ生成が成功する

前提条件:
- サービスが起動していること (./scripts/dev-hybrid.sh または make dev-all)
- .env に必要なAPIキーが設定されていること
- expertAgentがポート8004で起動していること
- myVaultがポート8003で起動していること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_395_acceptance.py -v -s
  cd expertAgent && uv run pytest tests/acceptance/test_issue_395_acceptance.py -v -k "not e2e"
"""

from typing import Any

import pytest
import requests


@pytest.mark.acceptance
class TestIssue395Acceptance:
    """Issue #395: BodyTemplateValidator がシステム注入フィールドを誤って検証する問題の修正"""

    # サービスURL
    EXPERT_AGENT_URL = "http://localhost:8004"
    MYVAULT_URL = "http://localhost:8003"

    # ==========================================================================
    # TC-001: SYSTEM_INJECTED_FIELDS 定数の存在確認
    # ==========================================================================

    def test_tc_001_system_injected_fields_constant_exists(self) -> None:
        """TC-001: SYSTEM_INJECTED_FIELDS 定数が正しく定義されているか

        受入条件: AC-1 - ホワイトリスト定数 SYSTEM_INJECTED_FIELDS が定義されている
        設計方針: DP-1 - アーキテクチャ整合性（定数定義パターン）

        検証ポイント:
        1. body_template_validator.py に定数が存在すること
        2. 型が frozenset であること
        3. 'project' が含まれていること
        """
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            SYSTEM_INJECTED_FIELDS,
        )

        # Assert: 定数が存在する
        assert SYSTEM_INJECTED_FIELDS is not None, (
            "SYSTEM_INJECTED_FIELDS constant should exist"
        )

        # Assert: 型が frozenset
        assert isinstance(SYSTEM_INJECTED_FIELDS, frozenset), (
            f"Expected frozenset, got {type(SYSTEM_INJECTED_FIELDS)}"
        )

        # Assert: 'project' が含まれる
        assert "project" in SYSTEM_INJECTED_FIELDS, (
            "'project' should be in SYSTEM_INJECTED_FIELDS"
        )

        print(f"[TC-001] SYSTEM_INJECTED_FIELDS verified: {SYSTEM_INJECTED_FIELDS}")

    # ==========================================================================
    # TC-002: SYSTEM_INJECTED_FIELDS の不変性検証
    # ==========================================================================

    def test_tc_002_system_injected_fields_immutability(self) -> None:
        """TC-002: SYSTEM_INJECTED_FIELDS が実行時に変更できないこと

        受入条件: AC-1 - ホワイトリスト定数 SYSTEM_INJECTED_FIELDS が定義されている
        設計方針: DP-3 - セキュリティ設計（ホワイトリスト方式）

        検証ポイント:
        - frozenset.add() を試行すると AttributeError が発生すること
        """
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            SYSTEM_INJECTED_FIELDS,
        )

        # Assert: frozenset は immutable
        with pytest.raises(AttributeError):
            SYSTEM_INJECTED_FIELDS.add("malicious_field")  # type: ignore[attr-defined]

        print(
            "[TC-002] SYSTEM_INJECTED_FIELDS immutability verified: "
            "AttributeError raised on add() attempt"
        )

    # ==========================================================================
    # TC-003: project フィールドの検証スキップ
    # ==========================================================================

    def test_tc_003_project_field_validation_skipped(self) -> None:
        """TC-003: project フィールド（システム注入）が検証から除外されること

        受入条件: AC-2 - project フィールドが検証から除外される
        設計方針: DP-2 - Strategy Pattern 拡張

        検証ポイント:
        - input_schema に project がなくても検証エラーが発生しないこと
        - result.is_valid が True であること
        """
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        # Arrange: input_schema に project を含まない
        body_template: dict[str, Any] = {
            "project": "{{job.body.project}}",  # system-injected field
        }
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {},  # no 'project' field
        }

        # Act
        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert: 検証成功（project はスキップされる）
        assert result.is_valid, (
            f"Expected validation to pass, but errors: "
            f"{[e.message for e in result.errors]}"
        )
        assert len(result.errors) == 0, "Expected no errors for system-injected field"

        print(
            "[TC-003] project field validation skipped: "
            f"is_valid={result.is_valid}, errors={len(result.errors)}"
        )

    # ==========================================================================
    # TC-004: ユーザーフィールドの検証継続（存在しない場合）
    # ==========================================================================

    def test_tc_004_user_field_validation_error(self) -> None:
        """TC-004: ユーザーフィールドが引き続き検証されること（存在しない場合エラー）

        受入条件: AC-3 - ユーザー入力フィールド（user_input 等）は引き続き検証される
        設計方針: DP-2 - Strategy Pattern 拡張

        検証ポイント:
        - input_schema に存在しないユーザーフィールドで MISSING_REFERENCE エラー
        """
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        # Arrange: user_input が input_schema に存在しない
        body_template: dict[str, Any] = {
            "user_input": "{{job.body.user_input}}",
        }
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {},  # no 'user_input' field
        }

        # Act
        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert: 検証失敗（user_input は検証される）
        assert not result.is_valid, "Expected validation to fail for missing user field"
        assert len(result.errors) >= 1, "Expected at least one error"
        assert any("user_input" in e.message for e in result.errors), (
            "Expected error about 'user_input'"
        )
        assert any(e.error_type == "MISSING_REFERENCE" for e in result.errors), (
            "Expected MISSING_REFERENCE error type"
        )

        print(f"[TC-004] User field validation error: {result.errors[0].message}")

    # ==========================================================================
    # TC-005: ユーザーフィールドの検証継続（存在する場合）
    # ==========================================================================

    def test_tc_005_user_field_validation_success(self) -> None:
        """TC-005: ユーザーフィールドが正しく検証を通過すること

        受入条件: AC-3 - ユーザー入力フィールド（user_input 等）は引き続き検証される
        設計方針: DP-2 - Strategy Pattern 拡張

        検証ポイント:
        - input_schema に存在するユーザーフィールドは検証を通過する
        """
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        # Arrange: user_input が input_schema に存在する
        body_template: dict[str, Any] = {
            "user_input": "{{job.body.user_input}}",
        }
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert: 検証成功
        assert result.is_valid, (
            f"Expected validation to pass, but errors: "
            f"{[e.message for e in result.errors]}"
        )

        print(f"[TC-005] User field validation success: is_valid={result.is_valid}")

    # ==========================================================================
    # TC-006: 混在テスト（システムフィールド + ユーザーフィールド）
    # ==========================================================================

    def test_tc_006_mixed_system_and_user_fields(self) -> None:
        """TC-006: システムフィールドとユーザーフィールドが混在する場合

        受入条件: AC-2, AC-3
        設計方針: DP-2 - Strategy Pattern 拡張

        検証ポイント:
        - project（システム）はスキップ
        - user_input（ユーザー、存在）は検証パス
        - 結果として validation は成功
        """
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        # Arrange: project と user_input の混在
        body_template: dict[str, Any] = {
            "project": "{{job.body.project}}",  # system-injected, skip
            "user_input": "{{job.body.user_input}}",  # exists in schema
        }
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
                # 'project' は含まない（システム注入フィールド）
            },
        }

        # Act
        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert: 検証成功
        assert result.is_valid, (
            f"Expected validation to pass, but errors: "
            f"{[e.message for e in result.errors]}"
        )
        # project に関するエラーがないこと
        assert not any("project" in e.message for e in result.errors), (
            "Should not have error about 'project'"
        )

        print(
            "[TC-006] Mixed fields test passed: "
            f"is_valid={result.is_valid}, errors={len(result.errors)}"
        )

    # ==========================================================================
    # TC-006b: 混在テスト（システムフィールド + 欠損ユーザーフィールド）
    # ==========================================================================

    def test_tc_006b_mixed_system_and_missing_user_fields(self) -> None:
        """TC-006b: システムフィールドと欠損ユーザーフィールドが混在する場合

        受入条件: AC-2, AC-3
        設計方針: DP-2 - Strategy Pattern 拡張

        検証ポイント:
        - project（システム）はスキップ
        - missing_field（ユーザー、存在しない）は検証エラー
        - 結果として validation は失敗
        """
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        # Arrange: project と missing_field の混在
        body_template: dict[str, Any] = {
            "project": "{{job.body.project}}",  # system-injected, skip
            "user_input": "{{job.body.user_input}}",  # exists in schema
            "missing": "{{job.body.missing_user_field}}",  # not in schema
        }
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert: 検証失敗（missing_user_field のみ）
        assert not result.is_valid, "Expected validation to fail for missing user field"
        assert len(result.errors) == 1, (
            f"Expected exactly 1 error (missing_user_field), got {len(result.errors)}: "
            f"{[e.message for e in result.errors]}"
        )
        assert "missing_user_field" in result.errors[0].message, (
            f"Expected error about 'missing_user_field', got: {result.errors[0].message}"
        )
        # project に関するエラーがないこと
        assert "project" not in result.errors[0].message, (
            "Should not have error about 'project'"
        )

        print(f"[TC-006b] Mixed fields with error: {result.errors[0].message}")

    # ==========================================================================
    # TC-007: E2E ジョブ生成成功テスト（スキップ可能）
    # ==========================================================================

    @pytest.mark.skip(reason="E2E test requires services - run manually with -k e2e")
    @pytest.mark.e2e
    def test_tc_007_e2e_job_generation_success(self) -> None:
        """TC-007: E2E でジョブ生成が成功すること

        受入条件: AC-5 - E2E でジョブ生成が成功する
        設計方針: 全て

        前提条件:
        - expertAgent が起動していること（localhost:8004）
        - myVault が起動していること（localhost:8003）

        Note: このテストはE2Eテストのため、手動実行が推奨されます。
        実行方法: cd expertAgent && uv run pytest tests/acceptance/test_issue_395_acceptance.py -v -s -k e2e --no-skip
        """
        # Step 1: サービス起動確認
        services = [
            (self.EXPERT_AGENT_URL, "expertAgent"),
            (self.MYVAULT_URL, "myVault"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                assert response.status_code == 200, f"{name} is not healthy"
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running at {url}. "
                    "Run: ./scripts/dev-hybrid.sh or make dev-all"
                )

        # Step 2: Job Generator API 呼び出し
        endpoint = f"{self.EXPERT_AGENT_URL}/v1/job-generator"
        payload: dict[str, Any] = {
            "user_requirement": "天気予報を取得して、その結果をメールで送信する",
            "project_id": "default_project",
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=180,  # LLM呼び出しは時間がかかる
        )

        # Assert: レスポンスが正常形式
        assert response.status_code in [200, 201], (
            f"Job Generator failed: {response.status_code} - {response.text}"
        )
        data = response.json()

        # Assert: job_id または success フィールドが存在
        assert "job_id" in data or "success" in data, (
            f"Unexpected response format: {data}"
        )

        print(f"[TC-007] E2E job generation response: {data}")

    # ==========================================================================
    # TC-008: カバレッジ確認（CI実行）
    # ==========================================================================

    def test_tc_008_coverage_verification(self) -> None:
        """TC-008: 単体テストカバレッジが90%以上であること

        受入条件: AC-4 - 単体テストカバレッジ 90% 以上
        設計方針: N/A

        Note: この検証はCIで自動実行されます。
        ここでは、カバレッジを測定するためのテストファイルが存在することを確認します。

        手動検証コマンド:
          cd expertAgent && uv run pytest tests/unit/langgraph/jobGeneratorV2/validators/test_body_template_validator.py \
            --cov=aiagent/langgraph/jobGeneratorV2/validators/body_template_validator \
            --cov-report=term-missing
        """
        import os

        # テストファイルの存在確認
        unit_test_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "unit",
            "langgraph",
            "jobGeneratorV2",
            "validators",
            "test_body_template_validator.py",
        )

        # 正規化
        unit_test_path = os.path.normpath(unit_test_path)

        assert os.path.exists(unit_test_path), (
            f"Unit test file not found: {unit_test_path}"
        )

        # 実装ファイルの存在確認
        impl_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "aiagent",
            "langgraph",
            "jobGeneratorV2",
            "validators",
            "body_template_validator.py",
        )
        impl_path = os.path.normpath(impl_path)

        assert os.path.exists(impl_path), f"Implementation file not found: {impl_path}"

        print(
            "[TC-008] Files verified:\n"
            f"  Unit test: {unit_test_path}\n"
            f"  Implementation: {impl_path}\n"
            "  Note: Run coverage check manually or via CI"
        )


@pytest.mark.acceptance
class TestIssue395GraphAIStrategy:
    """Issue #395: GraphAIValidationStrategy もシステムフィールドをスキップすること"""

    def test_graphai_strategy_skips_system_fields(self) -> None:
        """GraphAI strategy でも project フィールドがスキップされること

        受入条件: AC-2
        設計方針: DP-2

        検証ポイント:
        - GraphAIValidationStrategy でも SYSTEM_INJECTED_FIELDS が適用される
        """
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )

        # Arrange
        body_template: dict[str, Any] = {
            "project": "{{job.body.project}}",
            "user_input": "{{job.body.user_input}}",
        }
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid, (
            f"GraphAI strategy should also skip system fields: "
            f"{[e.message for e in result.errors]}"
        )

        print(f"[GraphAI] System field skip verified: is_valid={result.is_valid}")
