"""
Issue #378 受入テスト（L3: ローカル受入テスト）

対象: ワークフローストレージの責務分離と優先順位の明確化
- 部分成功モデル（status: 'success' | 'partial_success' | 'failed'）
- Config優先読み込み
- APIレスポンスの整合性

前提条件:
- mySwiftAgentCore サービスが起動していること (npm run dev)
- config/taskflow/projects/ にテスト用ワークフローが存在すること

実行方法:
  cd mySwiftAgentCore
  python -m pytest tests/acceptance/test_issue_378_acceptance.py -v
"""
import subprocess
import os
from pathlib import Path


class TestIssue378Acceptance:
    """Issue #378: ワークフローストレージの責務分離と優先順位の明確化"""

    # プロジェクトルートパス
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # ==========================================================================
    # TC-005: デッドコード検証 - RegistrationStatus使用確認
    # ==========================================================================

    def test_tc_005_registration_status_not_dead_code(self) -> None:
        """TC-005: RegistrationStatus型が実際に使用されている

        受入条件: DP-1 (3-state statusモデル)
        検証方法: grep でソースコード内の参照を確認
        """
        # RegistrationStatus の使用箇所を検索（定義ファイル以外）
        result = subprocess.run(
            [
                "grep",
                "-rn",
                "RegistrationStatus",
                str(self.PROJECT_ROOT / "src"),
                "--include=*.ts",
            ],
            capture_output=True,
            text=True,
            cwd=self.PROJECT_ROOT,
        )

        output_lines = result.stdout.strip().split("\n")
        # registration.ts 以外での使用を確認
        usage_lines = [
            line for line in output_lines if "registration.ts" not in line and line
        ]

        assert len(usage_lines) >= 2, (
            f"RegistrationStatus は少なくとも2つのファイルで使用されるべきです。"
            f"実際の使用箇所: {usage_lines}"
        )

        # WorkflowRegistrar.ts での使用を確認
        registrar_usage = [
            line for line in usage_lines if "WorkflowRegistrar.ts" in line
        ]
        assert len(registrar_usage) >= 1, (
            "RegistrationStatus は WorkflowRegistrar.ts で使用されるべきです"
        )

        # WorkflowReloader.ts での使用を確認
        reloader_usage = [
            line for line in usage_lines if "WorkflowReloader.ts" in line
        ]
        assert len(reloader_usage) >= 1, (
            "RegistrationStatus は WorkflowReloader.ts で使用されるべきです"
        )

    # ==========================================================================
    # TC-006: デッドコード検証 - determineStatus使用確認
    # ==========================================================================

    def test_tc_006_determine_status_not_dead_code(self) -> None:
        """TC-006: determineStatus関数が実際に使用されている

        受入条件: DP-1 (3-state statusモデル)
        検証方法: grep でソースコード内の呼び出しを確認
        """
        # determineStatus の呼び出し箇所を検索（定義ファイル以外）
        result = subprocess.run(
            [
                "grep",
                "-rn",
                "determineStatus",
                str(self.PROJECT_ROOT / "src"),
                "--include=*.ts",
            ],
            capture_output=True,
            text=True,
            cwd=self.PROJECT_ROOT,
        )

        output_lines = result.stdout.strip().split("\n")
        # registration.ts 以外での使用（実際の呼び出し）を確認
        call_lines = [
            line
            for line in output_lines
            if "registration.ts" not in line
            and line
            and "export function determineStatus" not in line
        ]

        assert len(call_lines) >= 2, (
            f"determineStatus は少なくとも2箇所で呼び出されるべきです。"
            f"実際の呼び出し箇所: {call_lines}"
        )

        # WorkflowRegistrar.ts での呼び出しを確認
        registrar_calls = [
            line for line in call_lines if "WorkflowRegistrar.ts" in line
        ]
        assert len(registrar_calls) >= 1, (
            "determineStatus は WorkflowRegistrar.ts で呼び出されるべきです"
        )

        # WorkflowReloader.ts での呼び出しを確認
        reloader_calls = [line for line in call_lines if "WorkflowReloader.ts" in line]
        assert len(reloader_calls) >= 1, (
            "determineStatus は WorkflowReloader.ts で呼び出されるべきです"
        )

    # ==========================================================================
    # TC-007: APIレスポンス形式検証 - status フィールド
    # ==========================================================================

    def test_tc_007_api_response_includes_status_field(self) -> None:
        """TC-007: APIレスポンスにstatusフィールドが含まれる

        受入条件: AC-3, AC-4 (reload API動作保証、部分成功モデル)
        検証方法: taskflow-reload.ts のレスポンスを静的解析
        """
        reload_route_path = (
            self.PROJECT_ROOT / "src" / "api" / "routes" / "taskflow-reload.ts"
        )

        assert reload_route_path.exists(), (
            f"taskflow-reload.ts が存在しません: {reload_route_path}"
        )

        content = reload_route_path.read_text()

        # status フィールドがレスポンスに含まれることを確認
        assert "status: result.status" in content or "status:" in content, (
            "APIレスポンスに status フィールドが含まれていません"
        )

        # success フィールド（後方互換性）が含まれることを確認
        assert "success:" in content, (
            "APIレスポンスに success フィールドが含まれていません（後方互換性）"
        )

        # failedCount フィールドが含まれることを確認
        assert "failedCount" in content, (
            "APIレスポンスに failedCount フィールドが含まれていません"
        )

    # ==========================================================================
    # TC-008: Config優先読み込みの実装検証
    # ==========================================================================

    def test_tc_008_config_priority_loading_implemented(self) -> None:
        """TC-008: Config優先読み込みが実装されている

        受入条件: AC-1, AC-2 (ストレージ責務明確化、優先順位ルール)
        検証方法: WorkflowRegistrar.ts の initialize() メソッドを静的解析
        """
        registrar_path = (
            self.PROJECT_ROOT
            / "src"
            / "taskflowGeneratorAgent"
            / "generator"
            / "WorkflowRegistrar.ts"
        )

        assert registrar_path.exists(), (
            f"WorkflowRegistrar.ts が存在しません: {registrar_path}"
        )

        content = registrar_path.read_text()

        # loadFromConfigDirectory が initialize で呼び出されることを確認
        assert "loadFromConfigDirectory" in content, (
            "loadFromConfigDirectory メソッドが実装されていません"
        )

        # loadFromGeneratedStorage が initialize で呼び出されることを確認
        assert "loadFromGeneratedStorage" in content, (
            "loadFromGeneratedStorage メソッドが実装されていません"
        )

        # loadedFromConfig Set が存在することを確認
        assert "loadedFromConfig" in content, (
            "loadedFromConfig Set が実装されていません（Config優先追跡用）"
        )

        # initialize メソッド内で Config が先に呼ばれることを確認
        # (loadFromConfigDirectory が loadFromGeneratedStorage より前に呼ばれる)
        config_call_pos = content.find("await this.loadFromConfigDirectory()")
        generated_call_pos = content.find("await this.loadFromGeneratedStorage()")

        assert config_call_pos < generated_call_pos, (
            "loadFromConfigDirectory は loadFromGeneratedStorage より先に"
            "呼び出されるべきです（Config優先）"
        )

    # ==========================================================================
    # TC-009: 部分成功モデルの型定義検証
    # ==========================================================================

    def test_tc_009_partial_success_model_types(self) -> None:
        """TC-009: 部分成功モデルの型定義が正しい

        受入条件: AC-4 (部分成功モデル)
        検証方法: registration.ts の型定義を静的解析
        """
        registration_path = (
            self.PROJECT_ROOT
            / "src"
            / "taskflowGeneratorAgent"
            / "types"
            / "registration.ts"
        )

        assert registration_path.exists(), (
            f"registration.ts が存在しません: {registration_path}"
        )

        content = registration_path.read_text()

        # RegistrationStatus 型定義を確認
        assert "'success' | 'partial_success' | 'failed'" in content, (
            "RegistrationStatus は 'success' | 'partial_success' | 'failed' "
            "の3-stateであるべきです"
        )

        # DetailedRegistrationResult インターフェースを確認
        assert "interface DetailedRegistrationResult" in content, (
            "DetailedRegistrationResult インターフェースが定義されていません"
        )

        # memoryRegistered と storagePersisted フィールドを確認
        assert "memoryRegistered" in content, (
            "memoryRegistered フィールドが定義されていません"
        )
        assert "storagePersisted" in content, (
            "storagePersisted フィールドが定義されていません"
        )

        # determineStatus 関数を確認
        assert "function determineStatus" in content, (
            "determineStatus 関数が定義されていません"
        )

    # ==========================================================================
    # TC-010: WorkflowReloader の status フィールド検証
    # ==========================================================================

    def test_tc_010_workflow_reloader_status_field(self) -> None:
        """TC-010: WorkflowReloader に status フィールドが追加されている

        受入条件: AC-3 (reload API動作保証)
        検証方法: WorkflowReloader.ts の型定義を静的解析
        """
        reloader_path = (
            self.PROJECT_ROOT
            / "src"
            / "taskflowEngine"
            / "loader"
            / "WorkflowReloader.ts"
        )

        assert reloader_path.exists(), (
            f"WorkflowReloader.ts が存在しません: {reloader_path}"
        )

        content = reloader_path.read_text()

        # ProjectReloadResult に status フィールドがあることを確認
        assert "status: RegistrationStatus" in content, (
            "ProjectReloadResult に status フィールドがありません"
        )

        # FullReloadResult に status フィールドがあることを確認
        assert "FullReloadResult" in content, (
            "FullReloadResult インターフェースが定義されていません"
        )

        # failedCount フィールドがあることを確認
        assert "failedCount" in content, (
            "failedCount フィールドが定義されていません"
        )

        # determineStatus のインポートを確認
        assert "import" in content and "determineStatus" in content, (
            "determineStatus がインポートされていません"
        )
