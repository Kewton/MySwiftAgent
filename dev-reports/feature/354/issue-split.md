# Feature #354: TaskFlow スキーマ統一化 - Issue 分割計画書

**作成日**: 2026-01-12
**親Issue**: #354
**関連**: #353 (`__PENDING__` 問題の根本原因調査)

---

## 1. 概要

GraphAiServer と ExpertAgent 間の TaskFlow スキーマ不整合を段階的に解決するための Issue 分割計画。

---

## 2. Issue 一覧

### Issue #354-1: TaskFlow Adapter Layer 実装

| 項目 | 内容 |
|------|------|
| **タイトル** | TaskFlow Adapter Layer 実装 |
| **概要** | ExpertAgent出力をGraphAiServer形式に変換するAdapterパターン実装 |
| **サイズ** | M |
| **優先度** | High |
| **作業見積** | 4h |
| **Phase** | Phase 1 |
| **依存** | なし（即座に着手可能） |

#### スコープ

- [x] `adapter/` ディレクトリ構造作成
- [x] `TaskFlowAdapter` クラス実装
- [x] JSON文字列→オブジェクト変換ロジック
- [x] `workflow_registrar.py` への統合
- [x] 単体テスト作成（カバレッジ90%以上）

#### 技術スタック

- Python 3.11+
- Pydantic V2
- pytest

#### 受入基準 (Acceptance Criteria)

##### 🤖 自動検証可能な基準（pm-auto-devが実施）

**機能要件**:
- [ ] `TaskFlowAdapter.convert()` が JSON文字列フィールドをオブジェクトに変換
- [ ] 変換エラー時に詳細なエラーメッセージを返却
- [ ] `workflow_registrar.py` がAdapterを使用して変換を実行

**品質基準**:
- [ ] 単体テストカバレッジ 90% 以上
- [ ] Ruff/MyPy エラーゼロ
- [ ] 既存テストが全てパス

**テストケース**:
- [ ] `input_schema` が JSON文字列の場合、オブジェクトに変換される
- [ ] `output_schema` が JSON文字列の場合、オブジェクトに変換される
- [ ] `output` が JSON文字列の場合、オブジェクトに変換される
- [ ] `steps[*].config.body` が JSON文字列の場合、オブジェクトに変換される
- [ ] 既にオブジェクトの場合、そのまま保持される
- [ ] 不正なJSONの場合、エラーを返却

##### 👤 手動検証が必要な基準（ユーザーが実施）

**E2E検証**:
- [ ] Job Generator V2 でジョブ生成 → ワークフロー登録成功
- [ ] 登録されたワークフローが GraphAiServer で実行可能

---

### Issue #354-2: TaskFlow Contract Tests 実装

| 項目 | 内容 |
|------|------|
| **タイトル** | TaskFlow Contract Tests 実装 |
| **概要** | ExpertAgent/GraphAiServer間のスキーマ整合性を自動検証するContract Tests |
| **サイズ** | M |
| **優先度** | High |
| **作業見積** | 4h |
| **Phase** | Phase 2 |
| **依存** | #354-1（Adapter Layer） |

#### スコープ

- [x] `tests/contract/` ディレクトリ構造作成
- [x] 契約テスト実装（JSON文字列変換、Pydantic互換性、GraphAiServer検証）
- [x] テストフィクスチャ作成
- [x] CI/CD ワークフロー設定

#### 技術スタック

- Python 3.11+
- pytest, pytest-asyncio
- httpx（GraphAiServer API呼び出し）
- GitHub Actions

#### 受入基準 (Acceptance Criteria)

##### 🤖 自動検証可能な基準（pm-auto-devが実施）

**機能要件**:
- [ ] JSON文字列フィールド変換の契約テストが存在
- [ ] Pydanticモデル出力互換性の契約テストが存在
- [ ] GraphAiServer検証の契約テスト（integration mark）が存在

**品質基準**:
- [ ] 契約テストが全てパス
- [ ] テストフィクスチャが3種類以上

**テストケース**:
- [ ] `test_json_string_fields_are_converted` が存在しパス
- [ ] `test_pydantic_model_output_is_convertible` が存在しパス
- [ ] `test_converted_workflow_passes_graphai_validation` が存在

##### 👤 手動検証が必要な基準（ユーザーが実施）

**CI検証**:
- [ ] PRでスキーマ関連ファイル変更時にContract Testsが実行される
- [ ] Contract Tests失敗時にPRがブロックされる

---

### Issue #354-3: JSON Schema Single Source of Truth 導入

| 項目 | 内容 |
|------|------|
| **タイトル** | JSON Schema Single Source of Truth 導入 |
| **概要** | JSON Schemaを唯一の定義とし、TypeScript/Pythonスキーマを自動生成 |
| **サイズ** | L |
| **優先度** | Medium |
| **作業見積** | 8h |
| **Phase** | Phase 3 |
| **依存** | #354-2（Contract Tests） |

#### スコープ

- [x] `shared/schemas/taskflow/` ディレクトリ構造作成
- [x] JSON Schema定義（workflow.schema.json）
- [x] TypeScript型生成スクリプト
- [x] Pydanticモデル生成スクリプト
- [x] 生成パイプラインのCI統合

#### 技術スタック

- JSON Schema Draft 2020-12
- json-schema-to-typescript（TypeScript生成）
- datamodel-code-generator（Pydantic生成）
- GitHub Actions

#### 受入基準 (Acceptance Criteria)

##### 🤖 自動検証可能な基準（pm-auto-devが実施）

**機能要件**:
- [ ] `shared/schemas/taskflow/v1/workflow.schema.json` が存在
- [ ] `scripts/generate_schemas.py` が存在
- [ ] TypeScript型ファイルが自動生成される
- [ ] Pydanticモデルファイルが自動生成される

**品質基準**:
- [ ] 生成されたスキーマが既存テストをパス
- [ ] JSON Schema妥当性検証がパス

**テストケース**:
- [ ] `python scripts/generate_schemas.py` が正常終了
- [ ] 生成されたTypeScript型がコンパイルエラーなし
- [ ] 生成されたPydanticモデルがインポート可能

##### 👤 手動検証が必要な基準（ユーザーが実施）

**運用検証**:
- [ ] JSON Schema変更 → 生成スクリプト実行 → 各システムで動作確認
- [ ] スキーマバージョニング戦略が文書化されている

---

## 3. 依存関係マトリクス

```
#354-1 (Adapter Layer)
    ↓
#354-2 (Contract Tests)  ← #354-1 完了後に着手
    ↓
#354-3 (JSON Schema SSOT) ← #354-2 完了後に着手
```

| Issue | 依存先 | ブロック対象 |
|-------|--------|-------------|
| #354-1 | なし | #354-2 |
| #354-2 | #354-1 | #354-3 |
| #354-3 | #354-2 | なし |

---

## 4. Phase 構成

### Phase 1: Adapter Layer（Week 1）

**目標**: 現在の `__PENDING__` 問題を解決

| Issue | タイトル | 見積 | 並列可否 |
|-------|----------|------|---------|
| #354-1 | TaskFlow Adapter Layer 実装 | 4h | - |

**Phase完了条件**:
- [ ] Adapter Layer が実装され、単体テストが全てパス
- [ ] `workflow_registrar.py` がAdapterを使用

---

### Phase 2: Contract Tests（Week 1-2）

**目標**: スキーマ整合性の自動検証

| Issue | タイトル | 見積 | 並列可否 |
|-------|----------|------|---------|
| #354-2 | TaskFlow Contract Tests 実装 | 4h | - |

**Phase完了条件**:
- [ ] Contract Tests が CI で実行される
- [ ] スキーマ変更時に自動検証

---

### Phase 3: JSON Schema SSOT（Week 2-3）

**目標**: スキーマ定義の一元管理

| Issue | タイトル | 見積 | 並列可否 |
|-------|----------|------|---------|
| #354-3 | JSON Schema Single Source of Truth 導入 | 8h | - |

**Phase完了条件**:
- [ ] JSON Schema から TypeScript/Python スキーマが自動生成
- [ ] 生成パイプラインが CI に統合

---

## 5. 総見積

| Phase | 見積工数 | 累計 |
|-------|---------|------|
| Phase 1 | 4h | 4h |
| Phase 2 | 4h | 8h |
| Phase 3 | 8h | 16h |
| **合計** | **16h** | **約2日** |

---

## 6. リスクと対策

| リスク | 対策 |
|--------|------|
| JSON Schema生成ツールの制限 | 複雑な型は手動補完 |
| OpenAI Structured Output制約 | Adapter Layerで吸収 |
| 既存コードへの影響 | 段階的移行、互換性維持 |

---

## 7. 次のアクション

1. `/issue-create 354` で子Issueを一括作成
2. `/pm-auto-dev #354-1` で Phase 1 を自動開発
3. Phase 1 完了後に Phase 2 へ進行
