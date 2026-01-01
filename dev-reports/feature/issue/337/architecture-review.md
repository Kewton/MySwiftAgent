# Issue #337: タスクチェーン Ready-to-Use Output 原則の導入 - アーキテクチャレビュー

## 1. 設計の妥当性評価

### 1.1 SOLID原則への適合

| 原則 | 評価 | 根拠 |
|------|------|------|
| **S** 単一責任 | ✅ | derived_fields は「下流タスク用データ変換」という単一責任 |
| **O** 開放閉鎖 | ✅ | 既存 InterfaceMaster を変更せず拡張（x-derived-fields） |
| **L** リスコフ置換 | ✅ | derived_fields なしの InterfaceMaster も完全動作 |
| **I** インターフェース分離 | ✅ | 既存API変更なし |
| **D** 依存性逆転 | ✅ | 抽象（JSON Schema）に依存、具体実装に依存しない |

### 1.2 設計原則への適合

| 原則 | 評価 | 根拠 |
|------|------|------|
| **KISS** | ✅ | 既存 stringTemplateAgent を活用、新規Agent不要 |
| **YAGNI** | ✅ | Phase 1 は最小限実装、自動推論は Phase 2 |
| **DRY** | ✅ | テンプレート定義は一箇所（output_schema内） |

## 2. リスク評価

### 2.1 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| LLMが derived_fields を無視 | 中 | 中 | 評価ノードでチェック、明示的プロンプト |
| テンプレート構文エラー | 低 | 中 | バリデーション関数で事前チェック |
| ワークフロー複雑化 | 中 | 低 | derived_fields 数の制限ガイドライン |

### 2.2 運用リスク

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| 既存ワークフロー互換性 | 低 | 低 | x-derived-fields はオプショナル |
| デバッグ困難化 | 中 | 中 | Langfuse でトレーシング |

## 3. 影響範囲分析

### 3.1 変更対象コンポーネント

```
expertAgent/
├── aiagent/langgraph/jobTaskGeneratorAgents/
│   ├── prompts/
│   │   └── interface_schema.py  ◀── 変更: DerivedFieldDefinition追加
│   │   └── workflow_generation.py ◀── 変更: derived_fields処理ルール追加
│   └── nodes/
│       └── interface_definition.py ◀── 軽微変更: derived_fields パススルー
└── tests/
    └── unit/
        └── test_interface_schema.py ◀── 追加: derived_fields テスト
```

### 3.2 影響を受けないコンポーネント

- **jobqueue**: スキーマ変更なし（x-derived-fields は JSON 内）
- **graphAiServer**: 変更なし（stringTemplateAgent は既存）
- **myAgentDesk**: 表示のみの変更（オプショナル）

## 4. パフォーマンス影響

### 4.1 LLM呼び出し

| フェーズ | トークン増加 | 影響 |
|----------|-------------|------|
| interface_definition | +300〜500 | プロンプト拡張分 |
| workflow_generation | +200〜400 | derived_fields 処理ルール分 |

**総評**: 許容範囲内（既存プロンプトの 10% 未満）

### 4.2 ワークフロー実行

| 処理 | 追加ノード数 | 実行時間影響 |
|------|-------------|-------------|
| stringTemplateAgent | 1〜3ノード/タスク | +10〜30ms/ノード |

**総評**: 文字列置換のみのため影響最小限

## 5. テスト戦略

### 5.1 単体テスト

```python
# tests/unit/test_derived_fields.py

class TestDerivedFieldsSchema:
    """derived_fields スキーマのテスト"""

    def test_derived_field_definition_valid(self):
        """正常な derived_field 定義"""
        field = DerivedFieldDefinition(
            template="件名: {summary_text}",
            type="string"
        )
        assert field.template == "件名: {summary_text}"

    def test_extract_derived_fields(self):
        """output_schema から x-derived-fields を抽出"""
        output_schema = {
            "properties": {"summary": {"type": "string"}},
            "x-derived-fields": {
                "email_subject": {"template": "{summary}", "type": "string"}
            }
        }
        derived = extract_derived_fields(output_schema)
        assert "email_subject" in derived

    def test_validate_template_references(self):
        """テンプレート参照の検証"""
        allowed = {"summary", "query"}
        assert validate_template("結果: {summary}", allowed) == True
        assert validate_template("結果: {unknown}", allowed) == False
```

### 5.2 結合テスト

```python
# tests/integration/test_derived_fields_workflow.py

class TestDerivedFieldsWorkflow:
    """derived_fields を含むワークフロー生成テスト"""

    async def test_workflow_with_derived_fields(self):
        """derived_fields がワークフローに正しく展開される"""
        # interface_definition で derived_fields を生成
        # workflow_generation で stringTemplateAgent ノードが追加される
        # 下流タスクが derived_field を参照できる
```

### 5.3 受入テスト

```python
# tests/acceptance/test_issue_337_acceptance.py

@pytest.mark.acceptance
class TestIssue337Acceptance:
    """Issue #337 受入テスト"""

    async def test_email_task_uses_derived_fields(self):
        """メール送信タスクが derived_fields を使用"""
        # 1. Job生成（検索 → 要約 → メール送信）
        # 2. 要約タスクの output_schema に x-derived-fields 確認
        # 3. メール送信ワークフローが stringTemplateAgent 経由でデータ取得
        # 4. 送信成功
```

## 6. 移行計画

### 6.1 後方互換性

- **既存 InterfaceMaster**: 変更不要、そのまま動作
- **既存ワークフロー**: 変更不要、derived_fields なしで動作
- **新規ワークフロー**: derived_fields ありで生成可能

### 6.2 段階的導入

1. **Phase 1**: 手動定義（LLMプロンプトで誘導）
2. **Phase 2**: 自動推論（タスクパターン認識）
3. **Phase 3**: テンプレートライブラリ化

## 7. 承認チェックリスト

- [x] SOLID原則への適合
- [x] 後方互換性の確保
- [x] パフォーマンス影響の許容範囲
- [x] テスト戦略の妥当性
- [x] リスク軽減策の妥当性

## 8. 結論

**推奨**: 実装を承認

**理由**:
1. 既存アーキテクチャへの影響が最小限
2. 後方互換性が完全に維持される
3. 段階的導入が可能
4. 根本的な問題（GraphAI fetchAgent の文字列補間制限）を回避する現実的な解決策

---

**レビュー日**: 2026-01-01
**レビュアー**: Claude Code
