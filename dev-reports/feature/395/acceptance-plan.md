# 受入テスト計画書

**Issue**: #395
**作成日**: 2026-01-23
**作成者**: acceptance-plan-agent
**フェーズ**: PRE-TDD（TDD実装前計画）

---

## 1. 概要

### 対象Issue
- **番号**: #395
- **タイトル**: fix(jobGeneratorV2): BodyTemplateValidator がシステム注入フィールド (project) を誤って検証する
- **プロジェクト**: expertAgent

### 問題の要約
Job Generator V2 の `BodyTemplateValidator` が全ての `{{job.body.X}}` 参照を `input_schema` で検証するため、システムが注入する `project` フィールドが検証エラーとなる問題。

```
Body template validation failed for task 'ユーザー入力の受け取り':
MISSING_REFERENCE: Field 'project' not found in input_schema
```

### 解決方針
ホワイトリスト方式でシステム注入フィールドを定義し、検証から除外する。

### 参照ドキュメント
- Issue: [#395](https://github.com/Kewton/MySwiftAgent/issues/395)
- 設計方針書: `dev-reports/feature/issue/395/design-policy.md`
- アーキテクチャレビュー: `dev-reports/feature/issue/395/architecture-review.md`
- 関連Issue: #358 (BodyTemplateValidator), #391 (project フィールド注入)

---

## 2. 単体テスト結果レビュー

**注記**: 本セクションはPRE-TDDフェーズのため、TDD実装後に更新されます。

### カバレッジ（TDD実装後に記入）
- 現在: --%
- 目標: 90%
- 判定: 未実施

### テスト品質評価（TDD実装後に記入）
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | -- | - |
| モック使用テスト数 | -- | - |
| モック使用率 | --% | - |
| 実API呼び出しテスト数 | -- | - |

### 期待される単体テスト項目
TDD実装で以下のテストが作成されることを期待：

1. **SYSTEM_INJECTED_FIELDS 定数テスト**
   - 定数が存在すること
   - `project` が含まれること
   - `frozenset` で不変であること

2. **システムフィールド検証スキップテスト**
   - `project` フィールドが検証エラーを起こさないこと
   - デバッグログが出力されること

3. **ユーザーフィールド検証継続テスト**
   - `user_input` 等のユーザーフィールドが引き続き検証されること
   - 存在しないユーザーフィールドで `MISSING_REFERENCE` エラーが発生すること

---

## 3. 受入条件分析

### AC-1: ホワイトリスト定数 SYSTEM_INJECTED_FIELDS が定義されている
- **原文**: ホワイトリスト定数 `SYSTEM_INJECTED_FIELDS` が定義されている
- **分類**: 機能要件（実装確認）
- **テスト方法**: コード検査 + pytest
- **モック使用**: 不可
- **検証ポイント**:
  1. `body_template_validator.py` に定数が存在すること
  2. 型が `frozenset[str]` であること
  3. `project` が含まれていること
  4. Issue #391 のコメントが付与されていること

### AC-2: project フィールドが検証から除外される
- **原文**: `project` フィールドが検証から除外される
- **分類**: 機能要件
- **テスト方法**: pytest + E2E curl
- **モック使用**: 単体テストでは一部可（LLM呼び出し）、E2Eでは不可
- **検証ポイント**:
  1. `{{job.body.project}}` 参照を含むテンプレートで検証エラーが発生しないこと
  2. `input_schema` に `project` がなくても正常に検証が完了すること
  3. デバッグログに「Skipping validation for system-injected field: project」が出力されること

### AC-3: ユーザー入力フィールド（user_input 等）は引き続き検証される
- **原文**: ユーザー入力フィールド（`user_input` 等）は引き続き検証される
- **分類**: 機能要件（回帰テスト）
- **テスト方法**: pytest
- **モック使用**: 一部可
- **検証ポイント**:
  1. `{{job.body.user_input}}` 参照が `input_schema` に存在しない場合、`MISSING_REFERENCE` エラーが発生すること
  2. `{{job.body.user_input}}` が `input_schema` に存在する場合、正常に検証が完了すること
  3. 既存の検証ロジックが影響を受けていないこと

### AC-4: 単体テストカバレッジ 90% 以上
- **原文**: 単体テストカバレッジ 90% 以上
- **分類**: 品質要件
- **テスト方法**: pytest --cov
- **モック使用**: N/A
- **検証ポイント**:
  1. `body_template_validator.py` のカバレッジが 90% 以上
  2. 新規追加コード（システムフィールド判定）が完全にカバーされていること

### AC-5: E2E でジョブ生成が成功する
- **原文**: E2E でジョブ生成が成功する
- **分類**: 機能要件（E2E）
- **テスト方法**: curl + pytest E2E
- **モック使用**: 不可
- **検証ポイント**:
  1. Job Generate API でジョブ生成が成功すること
  2. `project` フィールドを含むワークフローが正常に生成されること
  3. 生成された TaskFlow JSON が妥当であること

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性（定数定義パターン）
- **設計方針**: `SYSTEM_INJECTED_FIELDS: frozenset[str]` をファイルトップに定義
- **検証方法**: コード検査 + テスト
- **テスト項目**:
  1. 定数が `body_template_validator.py` のファイルトップに定義されていること
  2. `security_constants.py` の `ALLOWED_LOCAL_HOSTS` と同様のパターンであること
  3. Issue番号コメントが付与されていること

### DP-2: Strategy Pattern 拡張
- **設計方針**: `TaskFlowValidationStrategy.validate_job_body_reference()` を修正してシステムフィールド判定を追加
- **検証方法**: pytest + コード検査
- **テスト項目**:
  1. `validate_job_body_reference` メソッドにシステムフィールド判定が追加されていること
  2. システムフィールドの場合、早期リターンで空のエラーリストを返すこと
  3. デバッグログが出力されること

### DP-3: セキュリティ設計（ホワイトリスト方式）
- **設計方針**: 明示的ホワイトリストで制御、`frozenset` で不変性保証
- **検証方法**: pytest
- **テスト項目**:
  1. `SYSTEM_INJECTED_FIELDS` が `frozenset` であること
  2. 実行時に変更を試みると `AttributeError` が発生すること
  3. ホワイトリストにないフィールドは検証されること

### DP-4: パフォーマンス（O(1) 検索）
- **設計方針**: `frozenset` による O(1) のフィールド判定
- **検証方法**: コード検査
- **テスト項目**:
  1. `in` 演算子でフィールド判定を行っていること
  2. ループや線形検索を使用していないこと

---

## 5. デッドコード検証計画

### F-1: SYSTEM_INJECTED_FIELDS 定数
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py`
- **種別**: constant
- **期待される呼び出し元**: `TaskFlowValidationStrategy.validate_job_body_reference()`
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -rn "SYSTEM_INJECTED_FIELDS" expertAgent/ --include="*.py" | grep -v "^.*:.*#"
  ```
- **E2E確認**: Job Generate API 呼び出しで `project` フィールドが正常に処理されることを確認

### F-2: システムフィールドスキップロジック
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py`
- **種別**: 条件分岐（if文）
- **期待される呼び出し元**: `BodyTemplateValidator.validate()` -> `_validate_job_body_references()` -> `validate_job_body_reference()`
- **検証方法**:
  1. 単体テストで `project` フィールドをスキップする分岐が実行されること
  2. カバレッジレポートで該当行がカバーされていること
- **E2E確認**: `{{job.body.project}}` を含むテンプレートでエラーが発生しないこと

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| expertAgent | http://localhost:8004 | GET /health |
| myVault | http://localhost:8003 | GET /health |

### 起動コマンド（E2Eテスト用 - 必須）

**重要**: E2Eテストは以下の環境で実行すること。

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

これにより:
- mySwiftAgentCore, expertAgent: ローカル直接起動
- myVault: Dockerコンテナで起動（default_projectを使用）

### シークレット・設定情報

**E2Eテストで使用するシークレットは、コンテナ起動のmyVaultのdefault_projectから取得**します。

| 項目 | 取得元 |
|------|--------|
| OPENAI_API_KEY | myVault (default_project) |
| LLM_API_KEY | myVault (default_project) |
| ANTHROPIC_API_KEY | myVault (default_project) |

myVaultへのシークレット登録（事前設定が必要な場合）:
```bash
curl -X POST http://localhost:8003/api/v1/secrets \
  -H "Content-Type: application/json" \
  -d '{"project": "default_project", "key": "OPENAI_API_KEY", "value": "sk-xxx"}'
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | (true) |
| MYVAULT_BASE_URL | MyVault URL | (http://localhost:8003) |

### テストデータ
- `project`: `default_project`（myVault に登録済みのプロジェクト）
- ワークフロー定義: `{{job.body.project}}` を含むテンプレート

---

## 7. テスト項目

### TC-001: SYSTEM_INJECTED_FIELDS 定数の存在確認
- **テスト観点**: 定数が正しく定義されているか
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了していること
- **テスト手順**:
  1. `body_template_validator.py` をインポート
  2. `SYSTEM_INJECTED_FIELDS` が存在することを確認
  3. 型が `frozenset` であることを確認
  4. `project` が含まれていることを確認
- **期待結果**:
  - `SYSTEM_INJECTED_FIELDS` が存在する
  - 型が `frozenset[str]`
  - `"project"` が含まれている
- **pytestメソッド**: `test_tc_001_system_injected_fields_constant_exists`

### TC-002: SYSTEM_INJECTED_FIELDS の不変性検証
- **テスト観点**: 定数が実行時に変更できないこと
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了していること
- **テスト手順**:
  1. `SYSTEM_INJECTED_FIELDS.add("malicious")` を試行
  2. `AttributeError` が発生することを確認
- **期待結果**:
  - `AttributeError` が発生する
- **pytestメソッド**: `test_tc_002_system_injected_fields_immutability`

### TC-003: project フィールドの検証スキップ
- **テスト観点**: システムフィールドが検証から除外されること
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了していること
- **テスト手順**:
  1. `input_schema` に `project` を含まないスキーマを用意
  2. `body_template` に `{{job.body.project}}` を含むテンプレートを用意
  3. `BodyTemplateValidator.validate()` を実行
  4. 検証結果を確認
- **期待結果**:
  - `result.is_valid` が `True`
  - `result.errors` が空
- **pytestメソッド**: `test_tc_003_project_field_validation_skipped`

### TC-004: ユーザーフィールドの検証継続（存在しない場合）
- **テスト観点**: ユーザーフィールドが引き続き検証されること
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了していること
- **テスト手順**:
  1. `input_schema` に `user_input` を含まないスキーマを用意
  2. `body_template` に `{{job.body.user_input}}` を含むテンプレートを用意
  3. `BodyTemplateValidator.validate()` を実行
  4. 検証結果を確認
- **期待結果**:
  - `result.is_valid` が `False`
  - `result.errors` に `MISSING_REFERENCE` エラーが含まれる
- **pytestメソッド**: `test_tc_004_user_field_validation_error`

### TC-005: ユーザーフィールドの検証継続（存在する場合）
- **テスト観点**: 正しいユーザーフィールドが検証を通過すること
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了していること
- **テスト手順**:
  1. `input_schema` に `user_input` を含むスキーマを用意
  2. `body_template` に `{{job.body.user_input}}` を含むテンプレートを用意
  3. `BodyTemplateValidator.validate()` を実行
  4. 検証結果を確認
- **期待結果**:
  - `result.is_valid` が `True`
  - `result.errors` が空
- **pytestメソッド**: `test_tc_005_user_field_validation_success`

### TC-006: 混在テスト（システムフィールド + ユーザーフィールド）
- **テスト観点**: システムフィールドとユーザーフィールドが混在する場合の動作
- **関連する受入条件**: AC-2, AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了していること
- **テスト手順**:
  1. `input_schema` に `user_input` のみを含むスキーマを用意
  2. `body_template` に `{{job.body.project}}` と `{{job.body.user_input}}` を含むテンプレートを用意
  3. `BodyTemplateValidator.validate()` を実行
  4. 検証結果を確認
- **期待結果**:
  - `result.is_valid` が `True`
  - `result.errors` が空
  - `project` はスキップされ、`user_input` のみ検証される
- **pytestメソッド**: `test_tc_006_mixed_system_and_user_fields`

### TC-007: E2E ジョブ生成成功テスト
- **テスト観点**: 実際のAPIでジョブ生成が成功すること
- **関連する受入条件**: AC-5
- **関連する設計方針**: 全て
- **テスト種別**: E2E
- **テスト方法**: curl + pytest
- **前提条件**:
  1. expertAgent が起動していること（localhost:8004）
  2. myVault が起動していること（localhost:8003）
  3. mySwiftAgentCore が起動していること（localhost:8006）
  4. myVault に `default_project` の API キーが登録されていること
- **テスト手順**:
  1. Job Generate API を呼び出し
  2. ステータスポーリングでジョブ完了を待機
  3. 結果を確認
- **期待結果**:
  - HTTPステータス: 200
  - `status` が `completed`
  - 生成された TaskFlow JSON が妥当
- **curlコマンド**:
  ```bash
  # ジョブ生成リクエスト
  curl -s -X POST http://localhost:8004/v1/jobs/generate \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "天気予報を取得して、その結果をメールで送信する",
      "project": "default_project"
    }'

  # ステータス確認（job_id を置き換え）
  curl -s http://localhost:8004/v1/jobs/{job_id}/status
  ```
- **pytestメソッド**: `test_tc_007_e2e_job_generation_success`

### TC-008: カバレッジ確認
- **テスト観点**: 単体テストカバレッジが90%以上であること
- **関連する受入条件**: AC-4
- **関連する設計方針**: N/A
- **テスト種別**: 品質検証
- **テスト方法**: pytest --cov
- **前提条件**:
  1. TDD実装が完了していること
- **テスト手順**:
  1. カバレッジ付きでテスト実行
  2. `body_template_validator.py` のカバレッジを確認
- **期待結果**:
  - カバレッジが 90% 以上
- **コマンド**:
  ```bash
  cd expertAgent && uv run pytest tests/unit/langgraph/jobGeneratorV2/validators/test_body_template_validator.py \
    --cov=aiagent/langgraph/jobGeneratorV2/validators/body_template_validator \
    --cov-report=term-missing
  ```
- **pytestメソッド**: N/A（CI で自動実行）

---

## 8. コンポーネント間整合性検証

### CI-1: バリデータ整合性
- **検証対象**: `TaskFlowValidationStrategy` と `GraphAIValidationStrategy`
- **検証方法**:
  ```bash
  # 両ストラテジーの validate_job_body_reference メソッドを比較
  grep -A 30 "def validate_job_body_reference" expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py
  ```
- **確認項目**:
  - [ ] TaskFlowValidationStrategy にシステムフィールド判定が追加されている
  - [ ] GraphAIValidationStrategy にも同様の判定が追加されている（または将来の対応として TODO コメント）

### CI-2: 定数定義整合性
- **検証対象**: `SYSTEM_INJECTED_FIELDS` と他の定数定義
- **検証方法**:
  ```bash
  # 類似パターンの定数を確認
  grep -rn "frozenset" expertAgent/aiagent/langgraph/jobGeneratorV2/validators/ --include="*.py"
  ```
- **確認項目**:
  - [ ] 定数定義パターンが `security_constants.py` と一致している
  - [ ] Issue 番号コメントが付与されている

---

## 9. サービス間データフロー検証

### DF-1: project フィールドのデータフロー
| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| クライアント | project | expertAgent | リクエストボディ | 要検証 |
| expertAgent | project | JobMaster.body | 内部設定 | 要検証 |
| JobMaster | {{job.body.project}} | TaskMaster | テンプレート解決 | 要検証 |
| TaskMaster | project | myVault | シークレット解決 | 要検証 |

### DF-2: 検証フロー確認
- [ ] `BodyTemplateValidator` が `{{job.body.project}}` を検出
- [ ] `SYSTEM_INJECTED_FIELDS` でスキップ判定
- [ ] エラーなしで検証完了
- [ ] TaskMaster 作成成功

---

## 10. テスト実行計画

### 実行順序
1. **サービス起動確認**
   ```bash
   # ヘルスチェック
   curl -s http://localhost:8003/health  # myVault
   curl -s http://localhost:8004/health  # expertAgent
   curl -s http://localhost:8006/health  # mySwiftAgentCore
   ```

2. **単体テスト実行**
   ```bash
   cd expertAgent && uv run pytest tests/unit/langgraph/jobGeneratorV2/validators/test_body_template_validator.py -v
   ```

3. **カバレッジ確認**
   ```bash
   cd expertAgent && uv run pytest tests/unit/langgraph/jobGeneratorV2/validators/test_body_template_validator.py \
     --cov=aiagent/langgraph/jobGeneratorV2/validators/body_template_validator \
     --cov-report=term-missing
   ```

4. **結合テスト実行**
   ```bash
   cd expertAgent && uv run pytest tests/integration/test_registration_validation.py -v
   ```

5. **E2Eテスト実行**
   ```bash
   cd expertAgent && uv run pytest tests/acceptance/test_issue_395_acceptance.py -v -s
   ```

### 成功基準
- [ ] すべての単体テスト（TC-001 ~ TC-006）がパス
- [ ] カバレッジが 90% 以上（TC-008）
- [ ] E2Eテスト（TC-007）がパス
- [ ] すべての受入条件（AC-1 ~ AC-5）が検証済み
- [ ] デッドコードが検出されないこと（F-1, F-2）
- [ ] コンポーネント間整合性が確認されていること（CI-1, CI-2）

---

## 11. 補足事項

### GraphAI への将来対応
- 現在の実装は `TaskFlowValidationStrategy` のみを修正
- `GraphAIValidationStrategy` で同様の問題が発生した場合は、同じパターンで修正可能
- アーキテクチャレビューで「発生時対応」と判断済み

### テストファイル配置
- 単体テスト: `expertAgent/tests/unit/langgraph/jobGeneratorV2/validators/test_body_template_validator.py`
- 結合テスト: `expertAgent/tests/integration/test_registration_validation.py`
- 受入テスト: `expertAgent/tests/acceptance/test_issue_395_acceptance.py`

### 実装完了後の更新
本計画書の「2. 単体テスト結果レビュー」セクションは、TDD実装完了後に実際の結果で更新すること。

---

**計画作成完了: 2026-01-23**
