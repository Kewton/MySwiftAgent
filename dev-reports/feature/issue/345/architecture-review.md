# アーキテクチャレビュー: Issue #345 LLMプロンプトのAgent出力形式誤記載修正

**レビュー日**: 2026-01-10
**レビュアー**: Claude Code (AI Architecture Reviewer)
**対象ドキュメント**: `dev-reports/feature/issue/345/design-policy.md`

---

## 1. 設計原則の遵守確認

### SOLID原則チェック

| 原則 | 評価 | コメント |
|------|:----:|---------|
| **S**ingle Responsibility | :white_check_mark: | 各ルールファイルが単一の責任を持っている（reference_rules, agent_rules, api_rules） |
| **O**pen/Closed | :white_check_mark: | ファクトリ関数パターンにより拡張に開いている |
| **L**iskov Substitution | N/A | 継承は使用されていない |
| **I**nterface Segregation | :white_check_mark: | get_*_rules()関数で必要なルールのみ取得可能 |
| **D**ependency Inversion | :white_check_mark: | 定数とファクトリ関数による疎結合設計 |

### その他の原則

| 原則 | 評価 | コメント |
|------|:----:|---------|
| **KISS** | :white_check_mark: | シンプルな文字列定数と関数による設計 |
| **YAGNI** | :white_check_mark: | 必要な機能のみ実装 |
| **DRY** | :warning: | 同じ誤った情報が複数ファイルに重複（今回の問題の原因） |

---

## 2. アーキテクチャ評価

### 構造的品質

| 評価項目 | スコア(1-5) | コメント |
|---------|:----------:|----------|
| モジュール性 | 4 | rules/, few_shot/, system/に適切に分離 |
| 結合度 | 4 | 低結合（定数とファクトリ関数） |
| 凝集度 | 4 | 各モジュールが関連機能を集約 |
| 拡張性 | 4 | 新規Agent追加が容易 |
| 保守性 | 3 | **複数ファイルの整合性維持が課題** |

### パフォーマンス観点

本Issueはプロンプト修正のみのため、パフォーマンスへの影響はなし。

---

## 3. セキュリティレビュー

本Issueはセキュリティに関連なし。プロンプト修正のみで、認証・認可・データ保護に影響しない。

---

## 4. 既存システムとの整合性

### 統合ポイント確認

| 確認項目 | 状態 | コメント |
|---------|:----:|---------|
| GRAPHAI_WORKFLOW_GENERATION_RULES.md | :white_check_mark: | 正しい情報が記載済み |
| COMMON_ERRORS.md | :white_check_mark: | 正しい情報が記載済み |
| 既存テストとの整合性 | :warning: | テストは存在確認のみ、内容検証なし |

### 技術スタックの適合性

変更なし。既存の Python + YAML構成を維持。

---

## 5. リスク評価

| リスク種別 | 内容 | 影響度 | 発生確率 | 対策優先度 |
|-----------|------|:------:|:--------:|:----------:|
| **技術的リスク** | 修正漏れによる不整合 | 高 | 中 | **高** |
| **技術的リスク** | テストで検出できない回帰 | 中 | 高 | **高** |
| **運用リスク** | 既存ワークフローの動作不良 | 中 | 低 | 低 |
| **ビジネスリスク** | ワークフロー生成品質の変動 | 中 | 低 | 中 |

### リスク詳細

#### リスク1: 修正漏れ（高優先度）

**発見事項**: 設計方針書に **`api_rules.py` の修正が含まれていない**

現在の grep 結果:
```
expertAgent/.../prompt_builder/rules/api_rules.py:66: API responses are wrapped in `.result`:
expertAgent/.../prompt_builder/rules/api_rules.py:69: # Access: :api_node.result.messages
```

**影響**: この修正漏れにより、LLMに誤った情報が渡り続ける。

#### リスク2: テストカバレッジ不足（高優先度）

現在のテスト (`test_workflow_gen_prompt_builder.py`) は**存在確認のみ**:
- `assert "fetchAgent" in rules` - 存在確認
- `assert ":" in REFERENCE_RULES` - 構文確認

**欠落しているテスト**:
- `.result.` パターンが含まれていないことの検証
- `item_source` が含まれていないことの検証
- 正しい参照パターンの検証

---

## 6. 改善提案

### 必須改善項目（Must Fix）

#### 1. `api_rules.py` を修正対象に追加

**ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/prompt_builder/rules/api_rules.py`

```python
# 修正前 (L66-69)
### Response Access
API responses are wrapped in `.result`:
```yaml
# Response: { "messages": [...] }
# Access: :api_node.result.messages
```

# 修正後
### Response Access
fetchAgent returns HTTP response body directly:
```yaml
# Response: { "messages": [...] }
# Access: :api_node.messages
```
```

**設計方針書の受入条件に追加すべき項目**:
- [ ] `api_rules.py`のResponse Access説明を修正（`.result`削除）

#### 2. プロンプト内容検証テストの追加

```python
# test_workflow_gen_prompt_builder.py に追加

class TestPromptContentValidation:
    """Validate prompt content doesn't contain incorrect patterns."""

    def test_reference_rules_no_result_wrapper(self):
        """Ensure reference rules don't mention .result wrapper for fetchAgent."""
        assert ".result.field" not in REFERENCE_RULES
        assert "wrapped in .result" not in REFERENCE_RULES.lower()

    def test_agent_rules_no_result_wrapper(self):
        """Ensure agent rules don't mention .result wrapper."""
        assert ":node_name.result.field" not in ALL_AGENT_RULES

    def test_api_rules_no_result_wrapper(self):
        """Ensure API rules don't mention .result wrapper."""
        assert "wrapped in `.result`" not in API_RULES
        assert ":api_node.result." not in API_RULES

    def test_map_agent_uses_row(self):
        """Ensure mapAgent rules use 'row' not 'item_source'."""
        # Check for recommended pattern
        assert ":row" in ALL_AGENT_RULES
        # Optionally warn if item_source is used
```

### 推奨改善項目（Should Fix）

#### 3. Few-Shot YAMLファイルの自動検証

```python
# tests/unit/test_job_generator_v2/test_few_shot_validation.py (新規)

import yaml
from pathlib import Path

class TestFewShotPatternValidation:
    """Validate few-shot pattern files for common errors."""

    FEW_SHOT_DIR = Path("expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/prompt_builder/few_shot")

    def test_no_double_result_references(self):
        """Ensure no .result.result patterns in few-shot files."""
        for yaml_file in self.FEW_SHOT_DIR.glob("*.yaml"):
            content = yaml_file.read_text()
            assert ".result.result" not in content, f"Double .result in {yaml_file.name}"
            assert ".result.message_id" not in content, f"Wrong pattern in {yaml_file.name}"
            assert ".result.status" not in content, f"Wrong pattern in {yaml_file.name}"

    def test_map_pattern_uses_row(self):
        """Ensure map_pattern.yaml uses 'row' not 'item_source'."""
        map_pattern = self.FEW_SHOT_DIR / "map_pattern.yaml"
        content = map_pattern.read_text()
        assert "item_source: {}" not in content
        assert ":item_source." not in content
```

#### 4. ドキュメント整合性チェックの自動化（CI/CD）

Issue #345の「備考」で推奨されている通り:

```yaml
# .github/workflows/doc-consistency.yml (新規または追加)
- name: Check prompt-doc consistency
  run: |
    # GRAPHAI_WORKFLOW_GENERATION_RULES.md と prompt_builder の整合性チェック
    ./scripts/check-prompt-doc-consistency.sh
```

### 検討事項（Consider）

#### 5. Single Source of Truth の導入

現在、正しい情報が複数ファイルに分散:
- `GRAPHAI_WORKFLOW_GENERATION_RULES.md`
- `COMMON_ERRORS.md`
- `prompt_builder/rules/*.py`
- `prompt_builder/few_shot/*.yaml`

**将来的な改善案**:
- ルール定義を1箇所に集約し、各ファイルから参照
- または、自動生成スクリプトで整合性を保証

---

## 7. ベストプラクティスとの比較

### 業界標準との差異

| 観点 | 現状 | 業界標準 | 推奨 |
|------|------|---------|------|
| ドキュメント管理 | 複数ファイルに分散 | Single Source of Truth | 検討 |
| テスト | 存在確認のみ | 内容検証含む | **改善必要** |
| CI/CD検証 | なし | 自動整合性チェック | **追加推奨** |

### 代替アーキテクチャ案

#### 案A: 現行方式維持（推奨）

**メリット**:
- 修正範囲が限定的
- 既存テストへの影響なし
- 実装コストが低い

**デメリット**:
- 将来的な整合性維持コスト

#### 案B: ルール定義の一元化

**メリット**:
- 整合性維持が容易
- 再発防止効果が高い

**デメリット**:
- 大規模リファクタリングが必要
- 本Issueの範囲外

**結論**: Issue #345 では案Aを採用し、一元化は将来の改善として検討。

---

## 8. 総合評価

### レビューサマリ

| 項目 | 評価 |
|------|------|
| **全体評価** | :star::star::star::star: (4/5) |
| **設計品質** | 良好 - 既存アーキテクチャを維持した適切な修正設計 |
| **リスク管理** | 要改善 - 修正漏れとテスト不足 |

### 強み
- 問題の根本原因を特定し、明確な修正方針を策定
- 既存アーキテクチャとの整合性を維持
- 実装フェーズが明確に定義されている
- 受入条件が具体的

### 弱み
- **修正対象ファイルに `api_rules.py` が含まれていない（重大）**
- テスト設計が不十分（内容検証テストがない）
- 再発防止策（CI/CD）が未検討

### 総評

設計方針は概ね適切だが、**`api_rules.py` の修正漏れ**が重大な問題。この修正が漏れると、LLMに誤った情報が渡り続け、Issue #345 が完全に解決しない。テスト追加により、同様の問題の再発を防止することを強く推奨。

---

## 9. 承認判定

### :warning: 条件付き承認（Conditionally Approved）

以下の条件を満たした場合、実装を開始可能：

1. **必須**: `api_rules.py` を修正対象ファイルリストに追加
2. **必須**: 受入条件に「`api_rules.py`のResponse Access説明を修正」を追加
3. **推奨**: プロンプト内容検証テストの追加を計画

### 次のステップ

1. [ ] 設計方針書を更新し、`api_rules.py` を修正対象に追加
2. [ ] 受入条件を更新
3. [ ] 実装着手
4. [ ] テスト追加（推奨）
5. [ ] 既存単体テストの実行と確認

---

## 付録: 全修正対象ファイル（更新版）

| ファイル | 修正内容 | 設計書記載 |
|---------|---------|:----------:|
| `reference_rules.py` | `.result`記述削除 | :white_check_mark: |
| `agent_rules.py` | fetchAgent/mapAgentルール修正 | :white_check_mark: |
| `api_rules.py` | Response Access説明修正 | :x: **追加必要** |
| `workflow_generator.py` | システムプロンプト修正 | :white_check_mark: |
| `api_call_pattern.yaml` | `.result.`参照修正 | :white_check_mark: |
| `search_pattern.yaml` | `.result.`参照修正 | :white_check_mark: |
| `gmail_send_pattern.yaml` | `.result.`参照修正 | :white_check_mark: |
| `slack_notify_pattern.yaml` | `.result.`参照修正 | :white_check_mark: |
| `llm_chain_pattern.yaml` | `.result.`参照修正 | :white_check_mark: |
| `map_pattern.yaml` | `item_source`→`row`修正 | :white_check_mark: |
