# Issue #404 受入テスト計画書

## 1. 概要

| 項目 | 内容 |
|------|------|
| Issue番号 | #404 |
| Issue名 | feat(expertAgent): taskflowGeneratorAgentの生成ワークフローがinterfaceDefinitionsと整合しない問題 |
| 設計方針書 | `dev-reports/feature/issue/404/design-policy.md` |
| 作成日 | 2025-01-26 |

### 問題の概要

TaskFlow生成における`derived_fields`（派生フィールド）の情報欠落により、マルチタスクワークフローでデータフローが断絶する問題の修正。

主要な修正箇所:
1. `adapter._convert_interfaces()`: derived_fieldsの保持
2. `taskflow_generator._build_user_prompt()`: derived_fieldsのプロンプト化
3. `taskflow_generator`: パススルーロジックの追加（`_enhance_output_schema_with_passthrough`）
4. 型注釈の`InterfaceDefinition`への統一

---

## 2. 単体テスト結果レビュー

### 2.1 既存の関連テストファイル

| ファイル | テスト数 | カバレッジ | 検証内容 |
|---------|---------|-----------|---------|
| `expertAgent/tests/unit/test_derived_fields.py` | 12 | 90%+ | DerivedFieldDefinition, InterfaceSchemaDefinition |
| `expertAgent/tests/integration/test_issue_338_derived_fields.py` | 8 | 80%+ | derived_fields graceful degradation |
| `expertAgent/tests/unit/test_job_generator_v2/test_adapter_conversion.py` | 8 | 85%+ | _convert_interfaces(), _convert_tasks_to_breakdown() |

### 2.2 新規追加が必要なテスト

| テストファイル | テストケース | 対応AC |
|--------------|-------------|--------|
| `test_adapter_conversion.py` | derived_fields保持テスト | AC-10, AC-13 |
| `test_taskflow_generator.py` | derived_fieldsプロンプト出力テスト | AC-11, AC-14 |
| `test_taskflow_generator.py` | `_enhance_output_schema_with_passthrough`テスト | AC-7, AC-8 |

### 2.3 単体テスト結果確認コマンド

```bash
cd expertAgent && uv run pytest tests/unit/test_derived_fields.py tests/unit/test_job_generator_v2/test_adapter_conversion.py -v --cov
```

---

## 3. 受入条件分析

### 3.1 グループA: 基盤修正（Step 1-2, 4）

| AC | 説明 | 優先度 | テスト方法 |
|----|------|--------|-----------|
| AC-10 | `adapter._convert_interfaces()`で`derived_fields`が保持される | 🔴 高 | 単体テスト |
| AC-11 | `taskflow_generator._build_user_prompt()`で`derived_fields`がプロンプトに含まれる | 🔴 高 | 単体テスト |
| AC-12 | 型注釈が`InterfaceDefinition`に統一される | 🟡 中 | 静的解析（mypy） |

### 3.2 グループB: パススルー機能（Step 3）

| AC | 説明 | 優先度 | テスト方法 |
|----|------|--------|-----------|
| AC-1 | 生成されるワークフローJSONの`input_schema`がinterfaceDefinitionsと一致 | 🔴 高 | 結合テスト |
| AC-2 | 後続タスクで必要なフィールドが自動的にパススルーとして`output_schema`に追加される | 🔴 高 | 結合テスト |
| AC-3 | ユーザー入力から提供される`recipient_email`が、必要なタスクに正しく伝播される | 🔴 高 | E2Eテスト |

### 3.3 グループC: 後方互換性

| AC | 説明 | 優先度 | テスト方法 |
|----|------|--------|-----------|
| AC-5 | 既存のワークフロー（パススルー不要なもの）の動作に影響しない | 🔴 高 | 既存テスト実行 |
| AC-6 | interfacesが存在しないタスクの場合、従来の動作にフォールバックする | 🟡 中 | 単体テスト |

### 3.4 グループD: テスト

| AC | 説明 | 優先度 | テスト方法 |
|----|------|--------|-----------|
| AC-7 | 単体テスト - `_enhance_output_schema_with_passthrough`の正常系・異常系 | 🔴 高 | 単体テスト |
| AC-8 | 単体テスト - パススルーフィールド追加の検証 | 🔴 高 | 単体テスト |
| AC-13 | 単体テスト - `_convert_interfaces()`でderived_fields保持の検証 | 🔴 高 | 単体テスト |
| AC-14 | 単体テスト - `_build_user_prompt()`でderived_fields出力の検証 | 🔴 高 | 単体テスト |
| AC-9 | 結合テスト - 複数依存を持つワークフロー生成のE2Eテスト | 🔴 高 | 結合テスト |

### 3.5 グループE: E2E検証

| AC | 説明 | 優先度 | テスト方法 |
|----|------|--------|-----------|
| AC-4 | クロスサービスE2Eテストでメール送信が成功する | 🔴 高 | E2Eテスト（#403完了後） |

---

## 4. 設計方針検証項目

### 4.1 設計方針（design-policy.md）との整合性

| 設計方針 | 検証項目 | 検証方法 |
|---------|---------|---------|
| Fail-Safe設計 | エラー発生時に元のスキーマを返却する | 異常系単体テスト |
| 後方互換性維持 | 既存ワークフローに影響がない | 既存テスト全パス確認 |
| Post-Processing | LLM生成後の後処理でパススルー追加 | 結合テスト |
| 段階的移行 | InterfaceDefinition型への段階的統一 | 型注釈確認 |

### 4.2 アーキテクチャ整合性

| 検証項目 | 期待値 | 検証方法 |
|---------|--------|---------|
| adapter層での変換 | derived_fields保持 | 単体テスト |
| プロンプト生成 | derived_fields情報含む | 単体テスト |
| 後処理追加 | パススルーフィールド自動追加 | 結合テスト |

---

## 5. デッドコード検証計画

### 5.1 新規追加関数の統合確認

| 関数名 | 配置ファイル | 呼び出し元 | 検証方法 |
|--------|------------|-----------|---------|
| `_enhance_output_schema_with_passthrough()` | `taskflow_generator.py` | `generate()` | Grep確認 + 結合テスト |

### 5.2 統合確認コマンド

```bash
# 新規関数が実際に呼び出されていることを確認
cd expertAgent && grep -rn "_enhance_output_schema_with_passthrough" aiagent/

# derived_fieldsが変換で保持されていることを確認
cd expertAgent && grep -rn "derived_fields" aiagent/langgraph/jobGeneratorV2/adapter.py
```

---

## 6. テスト環境・方法

### 6.1 テスト環境

| 項目 | 設定 |
|------|------|
| Python | 3.12+ |
| 仮想環境 | uv |
| テストフレームワーク | pytest |
| カバレッジ | pytest-cov |

### 6.2 サービス起動要件

| テストレベル | サービス要件 |
|-------------|-------------|
| 単体テスト | 不要（モック使用） |
| 結合テスト | 不要（モック使用） |
| 受入テスト（L3） | `./scripts/dev-hybrid.sh start --local-only` |
| E2Eテスト | `./scripts/dev-hybrid.sh start --local-only` + API Keys |

### 6.3 前提条件（E2Eテスト）

- Issue #403（body_template生成の改善）が完了していること
- `test_issue_403_acceptance.py` が全パスしていること
- myVaultに必要なAPIキーが設定されていること

---

## 7. テスト項目

### 7.1 単体テスト（AC-7, AC-8, AC-13, AC-14）

#### 7.1.1 `_convert_interfaces()` derived_fields保持テスト

| TC | テストケース | 入力 | 期待結果 |
|----|------------|------|---------|
| UT-001 | derived_fieldsが保持される | InterfaceDefinition with derived_fields | 変換結果にderived_fields含む |
| UT-002 | 空derived_fields処理 | InterfaceDefinition with empty derived_fields | 空dictが保持される |
| UT-003 | derived_fieldsがNone | InterfaceDefinition with None | 空dictに変換される |

#### 7.1.2 `_build_user_prompt()` derived_fieldsプロンプト出力テスト

| TC | テストケース | 入力 | 期待結果 |
|----|------------|------|---------|
| UT-004 | derived_fieldsがプロンプトに含まれる | interfaces with derived_fields | "Derived Fields" セクション含む |
| UT-005 | 空derived_fieldsの場合 | interfaces with empty derived_fields | セクション省略 |
| UT-006 | 複数タスクのderived_fields | 複数interfaces | 各タスクのderived_fields出力 |

#### 7.1.3 `_enhance_output_schema_with_passthrough()` テスト

| TC | テストケース | 入力 | 期待結果 |
|----|------------|------|---------|
| UT-007 | 正常系パススルー追加 | 後続タスクが必要なフィールド | output_schemaにフィールド追加 |
| UT-008 | 空タスクリスト | all_tasks=[] | 元のスキーマを返却 |
| UT-009 | 空インターフェース | all_interfaces={} | 元のスキーマを返却 |
| UT-010 | 後続タスクなし | 最終タスク | パススルー追加なし |
| UT-011 | 複数後続タスク | 3タスクチェーン | 全てのフィールド追加 |
| UT-012 | 循環参照検出 | 循環依存 | 警告ログ + スキップ |
| UT-013 | 重複フィールド名 | 同名フィールド複数 | 最初の定義を維持 |
| UT-014 | 不正なtask_order_map | 無効なマップ | エラーにならない |
| UT-015 | 例外フォールバック | 内部例外発生 | 元のスキーマを返却 |

### 7.2 結合テスト（AC-1, AC-2, AC-9）

| TC | テストケース | 入力 | 期待結果 |
|----|------------|------|---------|
| IT-001 | 複数依存ワークフロー生成 | 3タスク依存チェーン | 各タスクのoutput_schemaにパススルーフィールド含む |
| IT-002 | input_schema整合性 | 生成ワークフロー | interface_definitionsと一致 |
| IT-003 | パススルーフィールド自動追加 | task_001→task_005→task_006 | recipient_emailが伝播 |

### 7.3 後方互換性テスト（AC-5, AC-6）

| TC | テストケース | 入力 | 期待結果 |
|----|------------|------|---------|
| BT-001 | 既存テスト全パス | 既存テストスイート | 全テストパス |
| BT-002 | interfacesなしフォールバック | interfaces=None | 従来動作 |
| BT-003 | derived_fieldsなしインターフェース | 空derived_fields | 従来通り処理 |

### 7.4 E2Eテスト（AC-4）

| TC | テストケース | 入力 | 期待結果 |
|----|------------|------|---------|
| E2E-001 | クロスサービスメール送信 | keyword + recipient_email | メール送信成功 |
| E2E-002 | データフロー完全性 | マルチタスクワークフロー | 全タスクでデータ伝播 |

**前提条件**:
- Issue #403完了
- サービス起動済み
- APIキー設定済み

---

## 8. テスト実行計画

### 8.1 実行順序

| Phase | テスト種別 | 対応AC | 実行コマンド |
|-------|-----------|--------|-------------|
| 1 | 単体テスト | AC-7,8,13,14 | `cd expertAgent && uv run pytest tests/unit/test_issue_404_*.py -v` |
| 2 | 後方互換性 | AC-5,6 | `cd expertAgent && uv run pytest tests/unit/test_job_generator_v2/ -v` |
| 3 | 結合テスト | AC-1,2,9 | `cd expertAgent && uv run pytest tests/integration/test_issue_404_*.py -v` |
| 4 | 受入テスト（L3） | AC-10,11,12 | `cd expertAgent && uv run pytest tests/acceptance/test_issue_404_acceptance.py -v -s` |
| 5 | E2Eテスト | AC-4 | `./scripts/e2e/cross-service/test_full_workflow_e2e.sh` |

### 8.2 テストファイル配置計画

| ファイル | 配置場所 | 内容 |
|---------|---------|------|
| `test_issue_404_unit.py` | `expertAgent/tests/unit/` | UT-001〜UT-015 |
| `test_issue_404_integration.py` | `expertAgent/tests/integration/` | IT-001〜IT-003 |
| `test_issue_404_acceptance.py` | `expertAgent/tests/acceptance/` | BT-001〜BT-003, E2E-001〜E2E-002 |

### 8.3 成功基準

| 基準 | 目標値 |
|------|--------|
| 単体テストカバレッジ | 90%以上 |
| 結合テストカバレッジ | 50%以上 |
| 全テストパス率 | 100% |
| 静的解析エラー | 0件 |

---

## 9. リスクと対策

| リスク | 可能性 | 影響度 | 対策 |
|-------|--------|--------|------|
| #403未完了 | 中 | 高 | E2Eテストは#403完了後に実行 |
| 後方互換性破損 | 低 | 高 | 既存テスト全パス確認 |
| パフォーマンス低下 | 低 | 中 | パフォーマンステストで検証 |

---

## 10. 完了条件チェックリスト

- [ ] 単体テスト全パス（AC-7, AC-8, AC-13, AC-14）
- [ ] 結合テスト全パス（AC-1, AC-2, AC-9）
- [ ] 後方互換性テスト全パス（AC-5, AC-6）
- [ ] 型注釈統一確認（AC-12）
- [ ] derived_fields保持確認（AC-10）
- [ ] プロンプト出力確認（AC-11）
- [ ] recipient_email伝播確認（AC-3）
- [ ] E2Eメール送信成功（AC-4） ※#403完了後
- [ ] カバレッジ90%以上
- [ ] 静的解析エラーゼロ
- [ ] デッドコードなし確認

---

## 11. 参照ドキュメント

| ドキュメント | パス |
|-------------|------|
| Issue本文 | GitHub Issue #404 |
| 設計方針書 | `dev-reports/feature/issue/404/design-policy.md` |
| 影響範囲分析 | `.serena/memories/issue_404_impact_analysis.md` |
| Issue #403受入テスト | `expertAgent/tests/acceptance/test_issue_403_acceptance.py` |
| derived_fields単体テスト | `expertAgent/tests/unit/test_derived_fields.py` |
| derived_fields結合テスト | `expertAgent/tests/integration/test_issue_338_derived_fields.py` |
