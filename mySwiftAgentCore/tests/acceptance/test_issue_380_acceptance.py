"""
Issue #380 受入テスト（L3: ローカル受入テスト）

対象: feat(taskflowGenerator): Capability出力スキーマの正確な定義とカタログ整備
- CapabilityCatalogGenerator によるカタログ生成
- JSON/YAML/Markdown 形式でのエクスポート
- ResponseSchemaValidator による JSON Schema Draft-07 準拠検証
- AIプロンプトへの注入形式

前提条件:
- mySwiftAgentCore サービスが起動していること (npm run dev)
- expertAgent サービスが起動していること
- myVault サービスが起動していること

実行方法:
  cd mySwiftAgentCore
  python -m pytest tests/acceptance/test_issue_380_acceptance.py -v
"""
import json
import subprocess
import os
from pathlib import Path
from typing import Any

import yaml
import pytest
import requests


class TestIssue380Acceptance:
    """Issue #380: Capability出力スキーマの正確な定義とカタログ整備"""

    # プロジェクトルートパス
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # カタログファイルパス
    CATALOG_DIR = PROJECT_ROOT / "config" / "capabilities" / "catalog"
    CATALOG_JSON = CATALOG_DIR / "capabilities-catalog.json"
    CATALOG_YAML = CATALOG_DIR / "capabilities-catalog.yaml"
    CATALOG_MD = CATALOG_DIR / "capabilities-catalog.md"

    # サービスURL
    EXPERT_AGENT_URL = "http://localhost:8004"
    MY_VAULT_URL = "http://localhost:8003"

    # ==========================================================================
    # TC-001: カタログ生成コマンド実行
    # ==========================================================================

    def test_tc_001_catalog_generation_command(self) -> None:
        """TC-001: npm run generate:catalog が正常に動作し、カタログが生成されること

        受入条件: AC-3 (Capabilityカタログを生成するスクリプトを作成)
        設計方針: DP-4 (カタログ生成アーキテクチャ)
        """
        # package.json で generate:catalog スクリプトが定義されているか確認
        package_json_path = self.PROJECT_ROOT / "package.json"
        assert package_json_path.exists(), "package.json が存在しません"

        with open(package_json_path) as f:
            package_json = json.load(f)

        scripts = package_json.get("scripts", {})
        assert "generate:catalog" in scripts, (
            "npm script 'generate:catalog' が定義されていません"
        )

        # カタログ生成コマンドを実行
        result = subprocess.run(
            ["npm", "run", "generate:catalog"],
            capture_output=True,
            text=True,
            cwd=self.PROJECT_ROOT,
            timeout=60,
        )

        assert result.returncode == 0, (
            f"npm run generate:catalog failed with exit code {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # カタログディレクトリが存在するか確認
        assert self.CATALOG_DIR.exists(), (
            f"カタログディレクトリが存在しません: {self.CATALOG_DIR}"
        )

        # 3つのファイルが生成されているか確認
        assert self.CATALOG_JSON.exists(), (
            f"JSON形式カタログが生成されていません: {self.CATALOG_JSON}"
        )
        assert self.CATALOG_YAML.exists(), (
            f"YAML形式カタログが生成されていません: {self.CATALOG_YAML}"
        )
        assert self.CATALOG_MD.exists(), (
            f"Markdown形式カタログが生成されていません: {self.CATALOG_MD}"
        )

    # ==========================================================================
    # TC-002: JSON形式カタログの妥当性検証
    # ==========================================================================

    def test_tc_002_json_catalog_validity(self) -> None:
        """TC-002: 生成されたJSONカタログが正しい形式であること

        受入条件: AC-4 (JSON/YAML形式でエクスポート可能), AC-1 (全Capabilityにresponseschema追加)
        設計方針: DP-2 (JSON Schema Draft-07準拠)
        """
        assert self.CATALOG_JSON.exists(), (
            f"JSON形式カタログが存在しません: {self.CATALOG_JSON}"
        )

        # JSONをパース
        with open(self.CATALOG_JSON) as f:
            catalog = json.load(f)

        # 必須フィールドの存在確認
        assert "version" in catalog, "version フィールドがありません"
        assert "capabilities" in catalog, "capabilities フィールドがありません"
        assert "summary" in catalog, "summary フィールドがありません"

        # Capability数の確認 (4以上)
        capabilities = catalog.get("capabilities", [])
        assert len(capabilities) >= 4, (
            f"Capability数が不足しています。期待: >= 4, 実際: {len(capabilities)}"
        )

        # 各CapabilityにresponseSchemaが定義されているか確認
        missing_schema = []
        for cap in capabilities:
            cap_id = cap.get("id", "unknown")
            if "responseSchema" not in cap or cap["responseSchema"] is None:
                missing_schema.append(cap_id)

        assert len(missing_schema) == 0, (
            f"以下のCapabilityにresponseSchemaが定義されていません: {missing_schema}"
        )

        # summaryの整合性確認
        summary = catalog.get("summary", {})
        assert summary.get("total") == len(capabilities), (
            "summary.total と capabilities の数が一致しません"
        )
        assert summary.get("withResponseSchema") == len(capabilities), (
            "summary.withResponseSchema が全Capability数と一致しません"
        )
        assert summary.get("withoutResponseSchema") == 0, (
            "summary.withoutResponseSchema が 0 ではありません"
        )

    # ==========================================================================
    # TC-003: YAML形式カタログの妥当性検証
    # ==========================================================================

    def test_tc_003_yaml_catalog_validity(self) -> None:
        """TC-003: 生成されたYAMLカタログが正しい形式であること

        受入条件: AC-4 (JSON/YAML形式でエクスポート可能)
        """
        assert self.CATALOG_YAML.exists(), (
            f"YAML形式カタログが存在しません: {self.CATALOG_YAML}"
        )

        # YAMLをパース
        with open(self.CATALOG_YAML) as f:
            catalog = yaml.safe_load(f)

        # 必須フィールドの存在確認
        assert "version" in catalog, "version フィールドがありません"
        assert "capabilities" in catalog, "capabilities フィールドがありません"

        # Capability数の確認
        capabilities = catalog.get("capabilities", [])
        assert len(capabilities) >= 4, (
            f"Capability数が不足しています。期待: >= 4, 実際: {len(capabilities)}"
        )

        # JSONカタログと同等の内容か確認
        with open(self.CATALOG_JSON) as f:
            json_catalog = json.load(f)

        assert len(capabilities) == len(json_catalog.get("capabilities", [])), (
            "YAML と JSON のCapability数が一致しません"
        )

        # 各CapabilityのIDが一致するか確認
        yaml_ids = {cap["id"] for cap in capabilities}
        json_ids = {cap["id"] for cap in json_catalog.get("capabilities", [])}
        assert yaml_ids == json_ids, (
            f"YAML と JSON のCapability IDが一致しません。"
            f"YAML only: {yaml_ids - json_ids}, JSON only: {json_ids - yaml_ids}"
        )

    # ==========================================================================
    # TC-004: ResponseSchemaValidator動作確認
    # ==========================================================================

    def test_tc_004_response_schema_validator(self) -> None:
        """TC-004: ResponseSchemaValidatorがajvを使用してスキーマ検証を行うこと

        受入条件: AC-1 (全CapabilityにresponseSchemaを追加), AC-2 (出力フィールド名を正確に定義)
        設計方針: DP-2 (JSON Schema Draft-07準拠)
        """
        # ajvパッケージがインストールされているか確認
        package_json_path = self.PROJECT_ROOT / "package.json"
        with open(package_json_path) as f:
            package_json = json.load(f)

        dependencies = package_json.get("dependencies", {})
        assert "ajv" in dependencies, "ajv パッケージが依存関係に含まれていません"
        assert "ajv-formats" in dependencies, (
            "ajv-formats パッケージが依存関係に含まれていません"
        )

        # ResponseSchemaValidator が実装されているか確認
        validator_path = (
            self.PROJECT_ROOT
            / "src"
            / "taskflowGeneratorAgent"
            / "validator"
            / "validators"
            / "ResponseSchemaValidator.ts"
        )
        assert validator_path.exists(), (
            f"ResponseSchemaValidator.ts が存在しません: {validator_path}"
        )

        content = validator_path.read_text()

        # ajv のインポートを確認
        assert "import Ajv" in content or "from 'ajv'" in content, (
            "ResponseSchemaValidator に ajv がインポートされていません"
        )

        # validate メソッドが存在することを確認
        assert "validate" in content, (
            "ResponseSchemaValidator に validate メソッドが存在しません"
        )

        # ValidationPipeline に統合されているか確認
        pipeline_path = (
            self.PROJECT_ROOT
            / "src"
            / "taskflowGeneratorAgent"
            / "validator"
            / "ValidationPipeline.ts"
        )
        assert pipeline_path.exists(), (
            f"ValidationPipeline.ts が存在しません: {pipeline_path}"
        )

        pipeline_content = pipeline_path.read_text()
        assert "ResponseSchemaValidator" in pipeline_content, (
            "ValidationPipeline に ResponseSchemaValidator が統合されていません"
        )

    # ==========================================================================
    # TC-005: google_search Capabilityの出力スキーマ検証
    # ==========================================================================

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS", "").lower() in ("true", "1"),
        reason="API tests require RUN_API_TESTS=true environment variable"
    )
    def test_tc_005_google_search_schema_validation(self) -> None:
        """TC-005: google_searchの実際の出力がresponseSchemaと一致すること

        受入条件: AC-2 (出力フィールド名を正確に定義)
        設計方針: DP-1 (用語統一)

        Note: このテストはAPI呼び出しを行うため、環境変数 RUN_API_TESTS=true が必要
        """
        # サービス健全性確認
        health_response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
        assert health_response.status_code == 200, "expertAgent が利用できません"

        # google_search API を呼び出し
        response = requests.post(
            f"{self.EXPERT_AGENT_URL}/v1/utility/google_search",
            json={"queries": ["TypeScript testing"], "num": 1},
            timeout=180,  # LLMナレッジ抽出があるため長めに設定
        )

        assert response.status_code == 200, (
            f"google_search API failed: {response.status_code} - {response.text}"
        )

        result = response.json()

        # responseSchema で定義されたフィールドが存在するか確認
        assert "search_results" in result, (
            "レスポンスに search_results フィールドがありません"
        )
        assert "search_results_count" in result, (
            "レスポンスに search_results_count フィールドがありません"
        )

        # search_results の構造を確認
        search_results = result["search_results"]
        assert isinstance(search_results, list), "search_results は配列であるべきです"

        if len(search_results) > 0:
            first_result = search_results[0]
            expected_fields = ["title", "link", "knowledge"]
            for field in expected_fields:
                assert field in first_result, (
                    f"search_results[0] に {field} フィールドがありません"
                )

    # ==========================================================================
    # TC-006: direct_llm Capabilityの出力スキーマ検証
    # ==========================================================================

    @pytest.mark.skipif(
        not os.environ.get("RUN_API_TESTS", "").lower() in ("true", "1"),
        reason="API tests require RUN_API_TESTS=true environment variable"
    )
    def test_tc_006_direct_llm_schema_validation(self) -> None:
        """TC-006: direct_llmの実際の出力がresponseSchemaと一致すること

        受入条件: AC-2 (出力フィールド名を正確に定義)
        設計方針: DP-1 (用語統一)

        Note: このテストはAPI呼び出しを行うため、環境変数 RUN_API_TESTS=true が必要
        """
        # サービス健全性確認
        health_response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
        assert health_response.status_code == 200, "expertAgent が利用できません"

        # direct_llm API を呼び出し
        response = requests.post(
            f"{self.EXPERT_AGENT_URL}/v1/mylllm",
            json={"user_input": "Hello", "model": "gpt-4o-mini"},
            timeout=60,
        )

        assert response.status_code == 200, (
            f"direct_llm API failed: {response.status_code} - {response.text}"
        )

        result = response.json()

        # responseSchema で定義されたフィールドが存在するか確認
        assert "result" in result, "レスポンスに result フィールドがありません"
        assert isinstance(result["result"], str), "result は文字列であるべきです"

    # ==========================================================================
    # TC-007: AIプロンプト注入形式の検証
    # ==========================================================================

    def test_tc_007_prompt_injection_format(self) -> None:
        """TC-007: カタログがPromptBuilderで正しく読み込まれ、プロンプトに注入されること

        受入条件: AC-5 (AIプロンプトに注入できる形式で出力)
        設計方針: DP-1, DP-3 (用語統一、ディレクトリ構造)
        """
        # カタログJSONが存在し、正しい形式であることを確認
        assert self.CATALOG_JSON.exists(), (
            f"JSON形式カタログが存在しません: {self.CATALOG_JSON}"
        )

        with open(self.CATALOG_JSON) as f:
            catalog = json.load(f)

        # 各Capabilityにプロンプト注入に必要な情報が含まれているか確認
        capabilities = catalog.get("capabilities", [])
        for cap in capabilities:
            cap_id = cap.get("id", "unknown")

            # 必須フィールドの確認
            assert "id" in cap, f"Capability {cap_id} に id がありません"
            assert "name" in cap, f"Capability {cap_id} に name がありません"
            assert "description" in cap, (
                f"Capability {cap_id} に description がありません"
            )
            assert "parameters" in cap, (
                f"Capability {cap_id} に parameters がありません"
            )
            assert "responseSchema" in cap, (
                f"Capability {cap_id} に responseSchema がありません"
            )

            # responseSchema の構造確認
            response_schema = cap["responseSchema"]
            assert isinstance(response_schema, dict), (
                f"Capability {cap_id} の responseSchema は object であるべきです"
            )

            # 少なくとも1つのフィールドが定義されているか確認
            assert len(response_schema) > 0, (
                f"Capability {cap_id} の responseSchema にフィールドが定義されていません"
            )

        # PromptBuilder が存在し、カタログを読み込む機能があるか確認
        prompt_builder_path = (
            self.PROJECT_ROOT
            / "src"
            / "taskflowGeneratorAgent"
            / "prompts"
            / "PromptBuilder.ts"
        )
        assert prompt_builder_path.exists(), (
            f"PromptBuilder.ts が存在しません: {prompt_builder_path}"
        )

        prompt_builder_content = prompt_builder_path.read_text()

        # responseSchema 関連の処理があるか確認
        assert "responseSchema" in prompt_builder_content or "Response Schema" in prompt_builder_content, (
            "PromptBuilder に responseSchema 関連の処理がありません"
        )

    # ==========================================================================
    # TC-008: カタログバージョンとタイムスタンプ
    # ==========================================================================

    def test_tc_008_catalog_metadata(self) -> None:
        """TC-008: 生成されたカタログにメタデータが含まれること

        受入条件: AC-4 (JSON/YAML形式でエクスポート可能)
        設計方針: DP-4 (カタログ生成アーキテクチャ)
        """
        assert self.CATALOG_JSON.exists(), (
            f"JSON形式カタログが存在しません: {self.CATALOG_JSON}"
        )

        with open(self.CATALOG_JSON) as f:
            catalog = json.load(f)

        # version フィールドの確認
        assert "version" in catalog, "version フィールドがありません"
        version = catalog["version"]
        assert isinstance(version, str), "version は文字列であるべきです"
        assert len(version) > 0, "version が空です"

        # generated/generatedAt フィールドの確認
        generated_key = "generatedAt" if "generatedAt" in catalog else "generated"
        assert generated_key in catalog, (
            f"生成日時フィールド ({generated_key}) がありません"
        )

        generated = catalog[generated_key]
        assert isinstance(generated, str), "生成日時は文字列であるべきです"

        # ISO 8601 形式の確認（簡易チェック）
        assert "T" in generated, "生成日時はISO 8601形式であるべきです"
        assert "Z" in generated or "+" in generated, (
            "生成日時にタイムゾーン情報が含まれるべきです"
        )

    # ==========================================================================
    # TC-009: Markdown形式カタログの可読性
    # ==========================================================================

    def test_tc_009_markdown_catalog_readability(self) -> None:
        """TC-009: 生成されたMarkdownが人間可読であること

        受入条件: AC-4 (JSON/YAML形式でエクスポート可能)
        """
        assert self.CATALOG_MD.exists(), (
            f"Markdown形式カタログが存在しません: {self.CATALOG_MD}"
        )

        content = self.CATALOG_MD.read_text()

        # タイトルヘッダーの確認
        assert "# Capability Catalog" in content, (
            "Markdown にタイトルヘッダーがありません"
        )

        # バージョン情報の確認
        assert "Version" in content, "Markdown にバージョン情報がありません"

        # Summary セクションの確認
        assert "## Summary" in content or "Summary" in content, (
            "Markdown に Summary セクションがありません"
        )

        # Capabilities セクションの確認
        assert "## Capabilities" in content or "Capabilities" in content, (
            "Markdown に Capabilities セクションがありません"
        )

        # 各 Capability の記載確認
        expected_capabilities = ["google_search", "direct_llm", "gmail_send", "json_output_agent"]
        for cap_id in expected_capabilities:
            assert cap_id in content, (
                f"Markdown に {cap_id} の記載がありません"
            )

        # Response Schema セクションの確認
        assert "Response Schema" in content, (
            "Markdown に Response Schema セクションがありません"
        )

        # Parameters テーブルの確認
        assert "| Name | Type | Required | Description |" in content, (
            "Markdown に Parameters テーブルがありません"
        )

    # ==========================================================================
    # TC-010: 不正スキーマ検出テスト
    # ==========================================================================

    def test_tc_010_invalid_schema_detection(self) -> None:
        """TC-010: ResponseSchemaValidatorが不正なスキーマを検出できること

        受入条件: AC-1 (全CapabilityにresponseSchemaを追加)
        設計方針: DP-2 (JSON Schema Draft-07準拠)
        """
        # ResponseSchemaValidator のテストファイルが存在するか確認
        validator_test_path = (
            self.PROJECT_ROOT
            / "tests"
            / "unit"
            / "capabilities"
            / "catalog"
            / "ResponseSchemaValidator.test.ts"
        )

        assert validator_test_path.exists(), (
            f"ResponseSchemaValidator のテストファイルが存在しません: {validator_test_path}"
        )

        content = validator_test_path.read_text()

        # 不正スキーマ検出のテストケースが存在するか確認
        invalid_schema_tests = [
            "invalid",
            "error",
            "fail",
            "missing",
            "incorrect",
        ]

        has_invalid_test = any(
            keyword.lower() in content.lower() for keyword in invalid_schema_tests
        )
        assert has_invalid_test, (
            "ResponseSchemaValidator のテストに不正スキーマ検出のテストケースがありません"
        )

        # vitest でテストを実行して検証
        result = subprocess.run(
            [
                "npm",
                "test",
                "--",
                "--run",
                "tests/unit/capabilities/catalog/ResponseSchemaValidator.test.ts",
            ],
            capture_output=True,
            text=True,
            cwd=self.PROJECT_ROOT,
            timeout=60,
        )

        assert result.returncode == 0, (
            f"ResponseSchemaValidator のテストが失敗しました。\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # ==========================================================================
    # 設計方針検証: DP-1 用語統一（responseSchema）
    # ==========================================================================

    def test_dp_001_terminology_unified(self) -> None:
        """DP-1: 用語統一（responseSchema）の検証

        検証方法: 新規実装コードで output_schema が使用されていないこと
        """
        # src/capabilities/ 配下で output_schema が使用されていないか確認
        result = subprocess.run(
            [
                "grep",
                "-rn",
                "output_schema",
                str(self.PROJECT_ROOT / "src" / "capabilities"),
                "--include=*.ts",
            ],
            capture_output=True,
            text=True,
            cwd=self.PROJECT_ROOT,
        )

        # 検索結果が空であることを確認（output_schema が使用されていない）
        output = result.stdout.strip()
        assert output == "", (
            f"src/capabilities/ で output_schema が使用されています: {output}"
        )

        # YAML ファイルで responseSchema が使用されているか確認
        result = subprocess.run(
            [
                "grep",
                "-rn",
                "responseSchema",
                str(self.PROJECT_ROOT / "config" / "capabilities" / "default_project"),
                "--include=*.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=self.PROJECT_ROOT,
        )

        # responseSchema が使用されていることを確認
        assert result.stdout.strip() != "", (
            "YAML ファイルで responseSchema が使用されていません"
        )

    # ==========================================================================
    # デッドコード検証: F-1 CapabilityCatalogGenerator
    # ==========================================================================

    def test_f_001_catalog_generator_not_dead_code(self) -> None:
        """F-1: CapabilityCatalogGenerator がデッドコードでないことを検証

        期待される呼び出し元: scripts/generate-catalog.ts
        """
        # CapabilityCatalogGenerator の使用箇所を検索
        result = subprocess.run(
            [
                "grep",
                "-rn",
                "CapabilityCatalogGenerator",
                str(self.PROJECT_ROOT / "scripts"),
                "--include=*.ts",
            ],
            capture_output=True,
            text=True,
            cwd=self.PROJECT_ROOT,
        )

        output = result.stdout.strip()
        assert "generate-catalog.ts" in output, (
            "CapabilityCatalogGenerator は generate-catalog.ts で使用されるべきです"
        )

        # import または new での使用を確認
        assert "import" in output or "new CapabilityCatalogGenerator" in output, (
            "CapabilityCatalogGenerator が実際に使用されていません"
        )

    # ==========================================================================
    # デッドコード検証: F-2 ResponseSchemaValidator
    # ==========================================================================

    def test_f_002_response_schema_validator_not_dead_code(self) -> None:
        """F-2: ResponseSchemaValidator がデッドコードでないことを検証

        期待される呼び出し元: ValidationPipeline
        """
        # ResponseSchemaValidator の使用箇所を検索（定義ファイル以外）
        result = subprocess.run(
            [
                "grep",
                "-rn",
                "ResponseSchemaValidator",
                str(self.PROJECT_ROOT / "src"),
                "--include=*.ts",
            ],
            capture_output=True,
            text=True,
            cwd=self.PROJECT_ROOT,
        )

        output_lines = result.stdout.strip().split("\n")
        # 定義ファイル以外での使用を確認
        usage_lines = [
            line
            for line in output_lines
            if "ResponseSchemaValidator.ts" not in line and line
        ]

        assert len(usage_lines) >= 1, (
            f"ResponseSchemaValidator は少なくとも1つのファイルで使用されるべきです。"
            f"実際の使用箇所: {usage_lines}"
        )

        # ValidationPipeline.ts または index.ts での使用を確認
        has_expected_usage = any(
            "ValidationPipeline.ts" in line or "index.ts" in line
            for line in usage_lines
        )
        assert has_expected_usage, (
            "ResponseSchemaValidator は ValidationPipeline または index.ts で使用されるべきです"
        )
