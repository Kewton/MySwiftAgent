# Issue #342 Phase F 作業計画書

> **Issue**: #342 refactor(expertAgent): Job/Task Generator Agent アーキテクチャ刷新
> **Phase**: F (Workflow Generator V2 LLM統合)
> **作成日**: 2026-01-07
> **設計ドキュメント**: `workflow-gen-v2-design.md`

---

## 1. 概要

### 1.1 目的

V2アーキテクチャに統合された新しいLLMワークフロー生成システムを実装する。V1の`workflowGeneratorAgents`の問題点（複雑なグラフ構造、リトライループ、保守困難）を解決し、「最初から正しく生成する」アプローチを実現する。

### 1.2 スコープ

| 範囲内 | 範囲外 |
|--------|--------|
| WorkflowGenWorkflow V2 LLM統合 | V1 workflowGeneratorAgentsの削除 |
| Few-shot例の作成・管理 | 既存Feature flagの変更 |
| モジュラープロンプトアーキテクチャ | graphAiServerの変更 |
| 単体・結合・受入テスト | 本番環境デプロイ |

### 1.3 前提条件

- Phase A-E が完了していること
- `USE_JOB_GENERATOR_V2=true` でV2が有効化可能であること
- `gemini-3-flash-preview` モデルが利用可能であること

### 1.4 デッドコード防止方針

> **背景**: Issue #338でデッドコードが多発した教訓を反映

#### 1.4.1 デッドコードの定義

| 種別 | 説明 | 例 |
|------|------|-----|
| **未呼出関数** | 定義されているが呼び出されない関数 | `def helper()` が存在するが使用されていない |
| **未使用定数** | 定義されているが参照されない定数 | `MAX_RETRY = 3` が存在するが使用されていない |
| **未統合コード** | 新規作成したが親モジュールに組み込まれていない | SubWorkflowが`__init__.py`でエクスポートされていない |
| **到達不能コード** | 条件分岐で絶対に実行されないパス | `if False: ...` |

#### 1.4.2 防止戦略

| 戦略 | 実施タイミング | 検証方法 |
|------|---------------|---------|
| **存在確認テスト** | 各フェーズ完了時 | `assert hasattr(module, 'function')` |
| **統合確認テスト** | 各フェーズ完了時 | `grep -r "function_name" workflow.py` |
| **呼出確認テスト** | 単体テスト時 | モックで呼出回数を検証 |
| **静的解析** | コミット前 | `ruff check --select=F401,F841` |
| **参照検索** | 統合時 | `find_referencing_symbols` で参照確認 |

#### 1.4.3 各フェーズでの統合チェックリスト

```
□ 新規ファイルが __init__.py でエクスポートされている
□ 新規クラス/関数が親モジュールから呼び出されている
□ 新規定数が実際のコードで使用されている
□ 単体テストに「統合確認テスト」が含まれている
□ grep で参照箇所が1箇所以上確認できる
```

---

## 2. 実装タスク詳細

### 2.1 F.1: Few-shot例の作成・整理

**目的**: LLMが正しいワークフローを生成するための参考例を整備

**成果物**:
```
expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/
└── prompt_builder/
    └── few_shot/
        ├── __init__.py
        ├── loader.py
        ├── search_pattern.yaml
        ├── api_call_pattern.yaml
        ├── llm_chain_pattern.yaml
        └── map_pattern.yaml
```

**タスク詳細**:

| # | タスク | 詳細 |
|---|--------|------|
| 1 | search_pattern.yaml作成 | Google検索 → 結果整形パターン |
| 2 | api_call_pattern.yaml作成 | 汎用API呼出パターン（Gmail送信等） |
| 3 | llm_chain_pattern.yaml作成 | LLM連鎖処理パターン |
| 4 | map_pattern.yaml作成 | 配列処理（mapAgent）パターン |
| 5 | loader.py実装 | スコアリングベースのFew-shot選択ロジック |

**受入条件**:
- [ ] 4種類のFew-shot例が作成されている
- [ ] 各例がGraphAI仕様に準拠している
- [ ] loader.pyがタスク特性に応じて適切な例を選択できる

**デッドコード防止チェック**:
- [ ] `few_shot/__init__.py` で `loader.py` の関数がエクスポートされている
- [ ] `loader.py` の `select_few_shot_examples()` が F.2 で呼び出される

---

### 2.2 F.2: PromptBuilderSubWorkflow

**目的**: モジュラープロンプトアーキテクチャの実装

**成果物**:
```
prompt_builder/
├── __init__.py              # PromptBuilderSubWorkflow クラス
├── assembler.py             # プロンプト組み立てロジック
├── system/
│   └── workflow_generator.py
├── rules/
│   ├── base_rules.py
│   ├── agent_rules.py
│   ├── reference_rules.py
│   └── api_rules.py
└── constraints/
    ├── loader.py
    └── formatter.py
```

**タスク詳細**:

| # | タスク | 詳細 |
|---|--------|------|
| 1 | システムプロンプト作成 | 役割定義（workflow_generator.py） |
| 2 | base_rules.py実装 | version, source, isResultルール |
| 3 | agent_rules.py実装 | Agent別制約（stringTemplateAgent等） |
| 4 | reference_rules.py実装 | 参照ルール（:node.path形式） |
| 5 | api_rules.py実装 | API呼出ルール（fetchAgent設定） |
| 6 | constraints/loader.py実装 | capabilities.yaml読込 |
| 7 | assembler.py実装 | プロンプト組み立てロジック |
| 8 | build_with_errors()実装 | リトライ時のエラーフィードバック |

**受入条件**:
- [ ] 各ルールファイルが独立して修正可能
- [ ] `build()` メソッドが正しくプロンプトを組み立てる
- [ ] `build_with_errors()` がリトライ時にエラー情報を含める

**デッドコード防止チェック**:
- [ ] `prompt_builder/__init__.py` で `PromptBuilderSubWorkflow` がエクスポートされている
- [ ] 各 `rules/*.py` が `assembler.py` から import されている
- [ ] `PromptBuilderSubWorkflow.build()` が F.6 の `WorkflowGenWorkflow` で呼び出される
- [ ] 全ルールファイルの定数/関数が `assembler.py` 内で使用されている

---

### 2.3 F.3: GraphAIWorkflowSchema (Pydantic)

**目的**: 構造化出力でLLM生成品質を担保

**成果物**:
```
workflows/workflow_gen/
├── schemas.py               # Pydanticスキーマ定義
└── errors.py                # ValidationError定義
```

**タスク詳細**:

| # | タスク | 詳細 |
|---|--------|------|
| 1 | NodeDefinition実装 | agent, inputs, params, isResult |
| 2 | GraphAIWorkflowSchema実装 | version, nodesの検証 |
| 3 | to_yaml()実装 | YAML出力メソッド |
| 4 | ValidationError実装 | code, message, location, suggestion |
| 5 | エラーコード定義 | MISSING_SOURCE, INVALID_AGENT等 |

**受入条件**:
- [ ] Pydanticバリデーションが正しく動作する
- [ ] `to_yaml()` が正しいYAMLを出力する
- [ ] ValidationErrorが適切な修正提案を含む

**デッドコード防止チェック**:
- [ ] `schemas.py` の `GraphAIWorkflowSchema` が F.4 `llm_generator.py` で使用されている
- [ ] `errors.py` の `ValidationError` が F.5 `yaml_validator.py` で使用されている
- [ ] 全エラーコード定数が `yaml_validator.py` 内で参照されている

---

### 2.4 F.4: LLMGeneratorSubWorkflow

**目的**: 単一のLLM呼び出しで高品質なYAMLを生成

**成果物**:
```
workflows/workflow_gen/
└── llm_generator.py
```

**タスク詳細**:

| # | タスク | 詳細 |
|---|--------|------|
| 1 | LLMGeneratorSubWorkflow実装 | generate()メソッド |
| 2 | invoke_structured_llm統合 | llm_utils.py活用 |
| 3 | LLMGenerationResult定義 | yaml_content, model_name |
| 4 | 環境変数対応 | WORKFLOW_GENERATOR_V2_MODEL |

**受入条件**:
- [ ] `gemini-3-flash-preview` でYAML生成できる
- [ ] 構造化出力（GraphAIWorkflowSchema）が正しく動作する
- [ ] 環境変数でモデル切り替え可能

**デッドコード防止チェック**:
- [ ] `LLMGeneratorSubWorkflow` が `workflow_gen/__init__.py` でエクスポートされている
- [ ] `LLMGeneratorSubWorkflow.generate()` が F.6 `WorkflowGenWorkflow` で呼び出される
- [ ] `llm_utils.py` の `invoke_structured_llm` が実際に使用されている

---

### 2.5 F.5: YamlValidatorSubWorkflow

**目的**: 軽量な検証で致命的エラーのみ検出

**成果物**:
```
workflows/workflow_gen/
├── yaml_validator.py
└── validators/
    ├── syntax_validator.py
    ├── structure_validator.py
    ├── agent_validator.py
    └── reference_validator.py
```

**タスク詳細**:

| # | タスク | 詳細 |
|---|--------|------|
| 1 | syntax_validator.py実装 | YAML構文検証 |
| 2 | structure_validator.py実装 | source, isResult検証 |
| 3 | agent_validator.py実装 | Agent存在確認 |
| 4 | reference_validator.py実装 | 参照解決検証 |
| 5 | YamlValidatorSubWorkflow統合 | validate()メソッド |

**受入条件**:
- [ ] 各検証が独立して動作する
- [ ] ValidationErrorが適切に生成される
- [ ] 検証エラーが修正提案を含む

**デッドコード防止チェック**:
- [ ] `YamlValidatorSubWorkflow` が `workflow_gen/__init__.py` でエクスポートされている
- [ ] 各 `validators/*.py` が `yaml_validator.py` から import されている
- [ ] `YamlValidatorSubWorkflow.validate()` が F.6 `WorkflowGenWorkflow` で呼び出される
- [ ] 全バリデータクラスが `yaml_validator.py` 内で使用されている

---

### 2.6 F.6: WorkflowGenWorkflow統合

**目的**: 全SubWorkflowを統合しWorkflowProtocol準拠で実装

**成果物**:
```
workflows/workflow_gen/
├── __init__.py              # エクスポート
└── workflow.py              # WorkflowGenWorkflow
```

**タスク詳細**:

| # | タスク | 詳細 |
|---|--------|------|
| 1 | WorkflowGenInput定義 | task_definition, interface_schema |
| 2 | WorkflowGenOutput定義 | yaml_content, workflow_name |
| 3 | execute()実装 | Phase 1-3統合フロー |
| 4 | リトライ処理実装 | ExecutionContext連携 |
| 5 | Option B実装 | enable_execution_test（デフォルトOFF） |
| 6 | config.py更新 | WORKFLOW_GENERATOR_V2_*環境変数追加 |

**受入条件**:
- [ ] WorkflowProtocol準拠
- [ ] ExecutionContextのリトライ管理と連携
- [ ] Feature flagで実行テストON/OFF可能

**デッドコード防止チェック（最重要）**:
- [ ] `WorkflowGenWorkflow` が `jobGeneratorV2/__init__.py` でエクスポートされている
- [ ] `WorkflowGenWorkflow.execute()` が `orchestrator.py` で呼び出される
- [ ] F.1〜F.5 で作成した全SubWorkflowが `workflow.py` で使用されている
- [ ] 環境変数 `WORKFLOW_GENERATOR_V2_*` が `config.py` で定義され、コード内で参照されている
- [ ] **統合検証コマンド実行**:
  ```bash
  # 各SubWorkflowの参照確認
  grep -r "PromptBuilderSubWorkflow" expertAgent/aiagent/langgraph/jobGeneratorV2/
  grep -r "LLMGeneratorSubWorkflow" expertAgent/aiagent/langgraph/jobGeneratorV2/
  grep -r "YamlValidatorSubWorkflow" expertAgent/aiagent/langgraph/jobGeneratorV2/
  grep -r "WorkflowGenWorkflow" expertAgent/aiagent/langgraph/jobGeneratorV2/
  ```

---

### 2.7 F.7: 単体テスト

**目的**: 各コンポーネントの単体テスト作成

**成果物**:
```
tests/unit/test_job_generator_v2/
├── test_workflow_gen_schemas.py
├── test_workflow_gen_prompt_builder.py
├── test_workflow_gen_llm_generator.py
├── test_workflow_gen_yaml_validator.py
├── test_workflow_gen_few_shot_loader.py
└── test_workflow_gen_workflow.py
```

**タスク詳細**:

| # | タスク | テスト数目標 |
|---|--------|------------|
| 1 | schemas.pyテスト | 15+ |
| 2 | prompt_builder/*テスト | 20+ |
| 3 | llm_generator.pyテスト | 10+ |
| 4 | yaml_validator.pyテスト | 15+ |
| 5 | few_shot/loader.pyテスト | 10+ |
| 6 | workflow.pyテスト | 15+ |
| **7** | **統合確認テスト** | **10+** |

**受入条件**:
- [ ] カバレッジ90%以上
- [ ] 全テストパス
- [ ] モック使用でLLM呼出なしでテスト可能

**デッドコード防止: 統合確認テスト（必須）**:

```python
# tests/unit/test_job_generator_v2/test_workflow_gen_integration_check.py

class TestWorkflowGenIntegrationCheck:
    """デッドコード防止: 統合確認テスト"""

    def test_prompt_builder_is_called_in_workflow(self):
        """PromptBuilderSubWorkflowがWorkflowGenWorkflowで呼び出される"""
        with patch.object(PromptBuilderSubWorkflow, 'build') as mock_build:
            workflow = WorkflowGenWorkflow()
            # ... execute workflow ...
            mock_build.assert_called_once()

    def test_llm_generator_is_called_in_workflow(self):
        """LLMGeneratorSubWorkflowがWorkflowGenWorkflowで呼び出される"""
        with patch.object(LLMGeneratorSubWorkflow, 'generate') as mock_gen:
            workflow = WorkflowGenWorkflow()
            # ... execute workflow ...
            mock_gen.assert_called_once()

    def test_yaml_validator_is_called_in_workflow(self):
        """YamlValidatorSubWorkflowがWorkflowGenWorkflowで呼び出される"""
        with patch.object(YamlValidatorSubWorkflow, 'validate') as mock_val:
            workflow = WorkflowGenWorkflow()
            # ... execute workflow ...
            mock_val.assert_called_once()

    def test_workflow_gen_workflow_is_called_in_orchestrator(self):
        """WorkflowGenWorkflowがOrchestratorで呼び出される"""
        # orchestrator.pyでWorkflowGenWorkflowが使用されていることを確認
        from aiagent.langgraph.jobGeneratorV2.orchestrator import JobGenerationOrchestrator
        assert hasattr(JobGenerationOrchestrator, '_workflow_gen_workflow')

    def test_all_error_codes_are_used(self):
        """全エラーコードがバリデータで使用されている"""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
            MISSING_SOURCE, MISSING_RESULT, INVALID_AGENT, INVALID_REFERENCE
        )
        # grep確認またはAST解析で使用箇所を検証
```

---

### 2.8 F.8: 結合テスト・受入テスト

**目的**: エンドツーエンドの動作確認

**成果物**:
```
tests/integration/
└── test_workflow_gen_v2_integration.py

tests/acceptance/
└── test_issue_342_workflow_gen_acceptance.py
```

**タスク詳細**:

| # | タスク | 詳細 |
|---|--------|------|
| 1 | 結合テスト作成 | 全SubWorkflow連携テスト |
| 2 | リトライシナリオテスト | エラー→リトライ→成功フロー |
| 3 | 受入テスト作成 | 実LLM呼出でYAML生成 |
| 4 | 検索系タスクテスト | search_patternの動作確認 |
| 5 | API呼出タスクテスト | api_call_patternの動作確認 |

**受入条件**:
- [ ] 結合テスト全パス
- [ ] 受入テストで実際にYAML生成成功
- [ ] 生成YAMLがgraphAiServerで実行可能

**デッドコード防止チェック**:
- [ ] 結合テストで全SubWorkflow（PromptBuilder, LLMGenerator, YamlValidator）が実際に実行される
- [ ] 受入テストで生成されたYAMLが空でない（`yaml_content` が有効な内容を含む）
- [ ] 結合テストのカバレッジレポートでWorkflowGenWorkflow関連コードが実行されている

---

### 2.9 F.9: 統合検証（デッドコード防止）

**目的**: 全コードが実際に統合され、デッドコードがないことを検証

**タスク詳細**:

| # | タスク | 検証内容 |
|---|--------|---------|
| 1 | エクスポート検証 | 全 `__init__.py` で必要なシンボルがエクスポートされている |
| 2 | 参照検証 | 全クラス/関数が2箇所以上から参照されている（定義+使用） |
| 3 | 定数使用検証 | 全定数がコード内で使用されている |
| 4 | 静的解析 | `ruff check --select=F401,F841` でエラーなし |
| 5 | 統合確認テスト実行 | F.7 で作成した統合確認テストが全パス |
| 6 | 型チェック | `mypy` で到達不能コード・型エラーなし |

**検証スクリプト**:

```bash
#!/bin/bash
# scripts/verify_no_dead_code.sh

echo "=== デッドコード検証 ==="

# 1. 未使用インポート検査
echo "1. 未使用インポート検査..."
cd expertAgent && uv run ruff check --select=F401 aiagent/langgraph/jobGeneratorV2/

# 2. 未使用変数検査
echo "2. 未使用変数検査..."
uv run ruff check --select=F841 aiagent/langgraph/jobGeneratorV2/

# 3. 主要クラスの参照確認
# 閾値「2箇所以上」の根拠:
#   - 1箇所目: 定義箇所（class文）
#   - 2箇所目: 使用箇所（import文または呼び出し）
# 2箇所未満 = 定義のみで使用されていない = デッドコード
echo "3. 主要クラスの参照確認..."
for class in PromptBuilderSubWorkflow LLMGeneratorSubWorkflow YamlValidatorSubWorkflow WorkflowGenWorkflow; do
  count=$(grep -r "$class" aiagent/langgraph/jobGeneratorV2/ --include="*.py" | wc -l)
  if [ "$count" -lt 2 ]; then
    echo "  ❌ $class: 参照が少なすぎます ($count 箇所) - 定義のみで使用されていない可能性"
    exit 1
  else
    echo "  ✅ $class: $count 箇所で参照 (定義+使用)"
  fi
done

# 4. __init__.py エクスポート確認
echo "4. __init__.py エクスポート確認..."
for init in aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/__init__.py; do
  if [ -f "$init" ]; then
    echo "  ✅ $init 存在"
  else
    echo "  ❌ $init が存在しません"
    exit 1
  fi
done

# 5. 統合確認テスト実行
echo "5. 統合確認テスト実行..."
uv run pytest tests/unit/test_job_generator_v2/test_workflow_gen_integration_check.py -v

# 6. 型チェック（到達不能コード検出）
echo "6. 型チェック..."
uv run mypy aiagent/langgraph/jobGeneratorV2/ --ignore-missing-imports

echo "=== 検証完了 ==="
```

**受入条件**:
- [ ] `ruff check --select=F401,F841` でエラーなし
- [ ] `mypy` で型エラー・到達不能コードなし
- [ ] 全主要クラスが2箇所以上で参照されている（定義1箇所+使用1箇所以上）
- [ ] 統合確認テスト全パス
- [ ] 検証スクリプトが正常終了

---

## 3. 依存関係

```
F.1 (Few-shot例)
    │
    ▼
F.2 (PromptBuilder) ──┐
                      │
F.3 (Schemas) ────────┼───▶ F.4 (LLMGenerator)
                      │           │
F.5 (YamlValidator) ──┘           │
                                  ▼
                           F.6 (統合)
                                  │
                                  ▼
                           F.7 (単体テスト)
                                  │
                                  ▼
                      F.8 (結合・受入テスト)
                                  │
                                  ▼
                      F.9 (統合検証・デッドコード防止)
```

---

## 4. 環境変数追加

```python
# core/config.py に追加
WORKFLOW_GENERATOR_V2_MODEL: str = Field(default="gemini-3-flash-preview")
WORKFLOW_GENERATOR_V2_TEMPERATURE: float = Field(default=0.3)
WORKFLOW_GENERATOR_V2_MAX_RETRY: int = Field(default=2)
WORKFLOW_GENERATOR_V2_ENABLE_EXECUTION_TEST: bool = Field(default=False)
```

---

## 5. リスクと対策

| リスク | 対策 | 検出方法 |
|--------|------|---------|
| Few-shot例が不十分で品質低下 | 段階的に例を追加 | 受入テスト失敗率監視 |
| 構造化出力がLLMで失敗 | JSONフォールバック実装 | 結合テストで確認 |
| リトライでも成功しないケース | 詳細エラーログ追加 | Langfuse監視 |
| 新Agent追加時の対応漏れ | AVAILABLE_AGENTS.md同期チェック | CI検証 |
| **デッドコード発生** | F.9統合検証フェーズ + 統合確認テスト | `verify_no_dead_code.sh` |
| **未統合コード** | 各フェーズでのデッドコード防止チェック | grep参照確認 |

---

## 6. 完了基準

### 6.1 必須条件

- [ ] 全単体テストパス（カバレッジ90%以上）
- [ ] 全結合テストパス
- [ ] 受入テストで実LLM呼出成功
- [ ] 静的解析エラーゼロ（Ruff, MyPy）
- [ ] 生成YAMLがgraphAiServerで実行可能

### 6.2 デッドコード防止条件（必須）

- [ ] `ruff check --select=F401` で未使用インポートなし
- [ ] `ruff check --select=F841` で未使用変数なし
- [ ] `mypy` で型エラー・到達不能コードなし
- [ ] 統合確認テスト（`test_workflow_gen_integration_check.py`）全パス
- [ ] 全SubWorkflowが `workflow.py` で実際に呼び出されている
- [ ] 全主要クラスが2箇所以上で参照されている（定義+使用）
- [ ] `verify_no_dead_code.sh` スクリプトが正常終了

### 6.3 推奨条件

- [ ] search_pattern, api_call_patternで90%以上の成功率
- [ ] 平均生成時間15秒以内
- [ ] リトライ率20%以下

---

## 7. タイムライン

| フェーズ | 依存 | 並列可否 |
|---------|------|---------|
| F.1 | なし | 独立実行可 |
| F.2 | F.1 | F.3, F.5と並列可 |
| F.3 | なし | F.2, F.5と並列可 |
| F.4 | F.2, F.3 | 順次 |
| F.5 | F.3 | F.2と並列可 |
| F.6 | F.4, F.5 | 順次 |
| F.7 | F.6 | 順次 |
| F.8 | F.7 | 順次 |
| **F.9** | **F.7, F.8** | **最終検証** |

**並列実行パターン**:
```
┌─────────────────────────────────────────────────────────────┐
│ F.1 → F.2 ─────────────┐                                    │
│                        │                                    │
│ F.3 ───────────────────┼─→ F.4 → F.6 → F.7 → F.8 → F.9     │
│                        │                                    │
│ F.5 ───────────────────┘                                    │
└─────────────────────────────────────────────────────────────┘
```

> **注**: F.7(単体テスト) → F.8(結合・受入テスト) → F.9(統合検証) は順次実行

---

## 8. 参照ドキュメント

| ドキュメント | 用途 |
|-------------|------|
| `workflow-gen-v2-design.md` | 設計方針 |
| `GRAPHAI_WORKFLOW_GENERATION_RULES.md` | GraphAIルール |
| `expert_agent_capabilities.yaml` | API制約 |
| `AVAILABLE_AGENTS.md` | 利用可能Agent一覧 |

---

*Generated: 2026-01-07*
*Updated: 2026-01-07 (デッドコード防止策追加)*
*Updated: 2026-01-07 (レビュー指摘対応: F.8チェック追加、MyPy追加、タイムライン修正、閾値根拠明記)*
*Issue #342 Phase F Work Plan*
