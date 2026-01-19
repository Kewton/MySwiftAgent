# 受入テスト計画書

**Issue**: #381
**作成日**: 2026-01-20
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #381
- **タイトル**: feat(taskflowGenerator): 生成ワークフローの事前バリデーション強化
- **プロジェクト**: mySwiftAgentCore

### 参照ドキュメント
- Issue: #381
- 設計方針書: `dev-reports/feature/issue/381/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/381/work-plan.md`
- アーキテクチャレビュー: `dev-reports/feature/issue/381/architecture-review.md`

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: TDD実装前（未計測）
- 目標: 90%
- 判定: 🔄 TDD実装後に確認

### テスト品質評価
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | TBD | - |
| モック使用テスト数 | TBD | - |
| モック使用率 | TBD | ⚠️/✅ |
| 実API呼び出しテスト数 | TBD | - |

### モック使用の妥当性
- TDD実装後に確認予定
- 外部API呼び出し（LLM等）のモックは許容
- 内部バリデータのモックは最小限に抑える

### 単体テストでカバーされていない項目（予測）
1. 実際のワークフロー生成APIを通したバリデーション実行
2. 複数バリデータの統合動作
3. パフォーマンス目標の達成確認（50ステップ < 150ms）

---

## 3. 受入条件分析

### AC-1: capability_id存在チェック
- **原文**: 参照されているcapability_idが存在するか
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可（実API呼び出し）
- **検証ポイント**:
  1. 存在するcapability_idの参照がエラーにならないこと
  2. 存在しないcapability_idの参照でエラーが返ること
  3. エラーメッセージに具体的な情報が含まれること

### AC-2: 出力フィールド名チェック
- **原文**: `$steps.xxx.yyy`の`yyy`が実際の出力スキーマに存在するか
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. 存在するフィールド参照がエラーにならないこと
  2. 存在しないフィールド参照でエラーが返ること
  3. エラーメッセージに利用可能なフィールド一覧が含まれること
  4. 類似フィールド名の修正提案が含まれること（Levenshtein距離）

### AC-3: テンプレート構文チェック
- **原文**: `{{steps.xxx}}`と`$.steps.xxx`の使い分けが正しいか
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. 正しい構文がエラーにならないこと
  2. 不正な構文でエラーが返ること
  3. Transform nodeの特別な検証が動作すること

### AC-4: スキーマ一致チェック
- **原文**: 前ステップの出力が次ステップの入力と型が一致するか
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. 型が一致する場合にエラーにならないこと
  2. 型が不一致の場合にエラーまたは警告が返ること

### AC-5: 循環参照検出（アーキテクチャレビュー追加）
- **原文**: アーキテクチャレビューで追加された改善項目
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. 循環参照がある場合にエラーが返ること
  2. エラーメッセージに循環パスが含まれること
  3. 深さ制限が正しく機能すること

### AC-6: エラーメッセージ改善（アーキテクチャレビュー追加）
- **原文**: バリデーションエラー時に具体的な修正提案を返す
- **分類**: 機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. エラーに`suggestion`フィールドが含まれること
  2. `availableOptions`に利用可能な選択肢が含まれること
  3. `closestMatch`に最も近いマッチが含まれること

### AC-7: デバッグモード（アーキテクチャレビュー追加）
- **原文**: アーキテクチャレビューで追加された改善項目
- **分類**: 非機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. `debugMode: true`でパフォーマンスメトリクスが返ること
  2. 各バリデータの実行時間が取得できること

### AC-8: パフォーマンス目標
- **原文**: アーキテクチャレビューの改善項目
- **分類**: 非機能要件
- **テスト方法**: pytest / curl
- **モック使用**: 不可
- **検証ポイント**:
  1. 50ステップのワークフローで150ms以内に処理が完了すること
  2. 10ステップ以下のワークフローで50ms以内に処理が完了すること

---

## 4. 設計方針検証

### DP-1: Composite Pattern（ComponentIntegrityValidator）
- **設計方針**: 5つのサブバリデータを統合するComposite Pattern
- **検証方法**: コード構造確認 / APIテスト
- **テスト項目**:
  1. ComponentIntegrityValidatorが5つのサブバリデータを含むこと
  2. すべてのサブバリデータが順次実行されること
  3. エラーが集約されて返却されること

### DP-2: 既存ValidationPipelineとの統合
- **設計方針**: 既存9バリデータの後に実行
- **検証方法**: APIテスト
- **テスト項目**:
  1. ValidationPipelineにComponentIntegrityValidatorが含まれること
  2. 実行順序が正しいこと（既存バリデータ → ComponentIntegrityValidator）

### DP-3: RegexPatternCache（Flyweight Pattern）
- **設計方針**: 正規表現の事前コンパイルとキャッシュ
- **検証方法**: 単体テスト / パフォーマンステスト
- **テスト項目**:
  1. Singletonインスタンスが共有されること
  2. パターンがキャッシュから取得されること

### DP-4: SuggestionHelper（Levenshtein距離）
- **設計方針**: エラーメッセージに類似候補を提案
- **検証方法**: 単体テスト / APIテスト
- **テスト項目**:
  1. Levenshtein距離が正しく計算されること
  2. 最も近いマッチが提案されること

### DP-5: SharedValidationCache
- **設計方針**: バリデータ間でキャッシュを共有
- **検証方法**: パフォーマンステスト
- **テスト項目**:
  1. capabilityMap, stepMapが共有されること
  2. 重複計算が回避されること

---

## 5. デッドコード検証計画

### F-1: ComponentIntegrityValidator
- **ファイル**: `src/taskflowGeneratorAgent/validator/ComponentIntegrityValidator.ts`
- **種別**: class
- **期待される呼び出し元**: ValidationPipeline
- **検証方法**:
  ```bash
  grep -rn "ComponentIntegrityValidator" --include="*.ts" | grep -v "class ComponentIntegrityValidator"
  ```
- **E2E確認**: ValidationPipeline経由でバリデーションAPIを呼び出し、エラーが検出されること

### F-2: StepReferenceValidator
- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/StepReferenceValidator.ts`
- **種別**: class
- **期待される呼び出し元**: ComponentIntegrityValidator
- **検証方法**:
  ```bash
  grep -rn "StepReferenceValidator" --include="*.ts" | grep -v "class StepReferenceValidator"
  ```
- **E2E確認**: 存在しないステップ参照を含むワークフローでエラーが返ること

### F-3: CircularReferenceValidator
- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/CircularReferenceValidator.ts`
- **種別**: class
- **期待される呼び出し元**: ComponentIntegrityValidator
- **検証方法**:
  ```bash
  grep -rn "CircularReferenceValidator" --include="*.ts" | grep -v "class CircularReferenceValidator"
  ```
- **E2E確認**: 循環参照を含むワークフローでエラーが返ること

### F-4: RegexPatternCache
- **ファイル**: `src/taskflowGeneratorAgent/validator/utils/RegexPatternCache.ts`
- **種別**: class (Singleton)
- **期待される呼び出し元**: StepReferenceValidator, CircularReferenceValidator
- **検証方法**:
  ```bash
  grep -rn "RegexPatternCache" --include="*.ts" | grep -v "class RegexPatternCache"
  ```
- **E2E確認**: バリデーション実行時にキャッシュが使用されること

### F-5: SuggestionHelper
- **ファイル**: `src/taskflowGeneratorAgent/validator/utils/SuggestionHelper.ts`
- **種別**: class (static methods)
- **期待される呼び出し元**: StepReferenceValidator
- **検証方法**:
  ```bash
  grep -rn "SuggestionHelper" --include="*.ts" | grep -v "class SuggestionHelper"
  ```
- **E2E確認**: エラーレスポンスに`suggestion`フィールドが含まれること

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |

### 起動コマンド
```bash
# 1. mySwiftAgentCoreディレクトリに移動
cd mySwiftAgentCore

# 2. 依存関係インストール
npm install

# 3. 開発サーバー起動
npm run dev

# 4. サービス起動確認
curl -sf http://localhost:8006/health && echo "✅ mySwiftAgentCore healthy"
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| NODE_ENV | 実行環境 | ✅ (development) |
| PORT | サーバーポート | ❌ (default: 8006) |

### テストデータ
- `config/capabilities/default_project/google_search.yaml` - テスト用Capability定義
- テスト用ワークフローJSON（テストコード内で定義）

---

## 7. テスト項目

### TC-001: 有効なワークフローのバリデーション
- **テスト観点**: 正常なワークフローがエラーなくバリデーションを通過すること
- **関連する受入条件**: AC-1, AC-2, AC-3, AC-4
- **関連する設計方針**: DP-1, DP-2
- **テスト種別**: E2E
- **テスト方法**: pytest / curl
- **前提条件**:
  1. mySwiftAgentCoreが起動していること
  2. google_search capabilityが登録されていること
- **テスト手順**:
  1. 有効なワークフローJSONを作成
  2. バリデーションAPIを呼び出す
  3. レスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - `isValid: true`
  - `errors: []`
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/validate \
    -H "Content-Type: application/json" \
    -d '{
      "workflow": {
        "workflow_name": "valid_test",
        "steps": [
          {
            "id": "step_001",
            "type": "api_rest",
            "config": {
              "step_type": "api_rest",
              "capability_id": "google_search",
              "method": "GET",
              "url": "https://example.com"
            }
          }
        ],
        "input_schema": {"query": "string"},
        "output_schema": {"result": "string"},
        "output": {"result": "${step_001.output.data}"}
      },
      "capabilities": [],
      "options": {
        "enableComponentIntegrityValidation": true
      }
    }' | jq '.isValid'
  ```
- **pytestメソッド**: `test_tc_001_valid_workflow_validation`

### TC-002: 存在しないステップ参照の検出
- **テスト観点**: 存在しないステップへの参照がエラーとして検出されること
- **関連する受入条件**: AC-2, AC-6
- **関連する設計方針**: DP-1, DP-4
- **テスト種別**: E2E
- **テスト方法**: pytest / curl
- **前提条件**:
  1. mySwiftAgentCoreが起動していること
- **テスト手順**:
  1. 存在しないステップを参照するワークフローを作成
  2. バリデーションAPIを呼び出す
  3. エラーレスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - `isValid: false`
  - エラーに`STEP_REFERENCE_NOT_FOUND`または`OUTPUT_FIELD_NOT_FOUND`が含まれる
  - `suggestion`に修正提案が含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/validate \
    -H "Content-Type: application/json" \
    -d '{
      "workflow": {
        "workflow_name": "invalid_step_ref",
        "steps": [
          {
            "id": "step_001",
            "type": "transform",
            "config": {
              "step_type": "transform",
              "template": "{{$steps.nonexistent_step.output}}"
            }
          }
        ],
        "input_schema": {"query": "string"},
        "output_schema": {"result": "string"},
        "output": {"result": "${step_001.output}"}
      },
      "options": {
        "enableComponentIntegrityValidation": true
      }
    }' | jq '{isValid: .isValid, errors: .errors}'
  ```
- **pytestメソッド**: `test_tc_002_invalid_step_reference`

### TC-003: 存在しないフィールド参照の検出
- **テスト観点**: 存在しない出力フィールドへの参照がエラーとして検出されること
- **関連する受入条件**: AC-2, AC-6
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: pytest / curl
- **前提条件**:
  1. mySwiftAgentCoreが起動していること
  2. google_search capabilityが登録されていること
- **テスト手順**:
  1. 存在しないフィールドを参照するワークフローを作成
  2. バリデーションAPIを呼び出す
  3. エラーレスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - `isValid: false`
  - エラーコード: `OUTPUT_FIELD_NOT_FOUND`
  - `suggestion.availableOptions`に利用可能なフィールド一覧が含まれる
  - `suggestion.closestMatch`に類似フィールド名が含まれる（存在する場合）
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/validate \
    -H "Content-Type: application/json" \
    -d '{
      "workflow": {
        "workflow_name": "invalid_field_ref",
        "steps": [
          {
            "id": "step_001",
            "type": "api_rest",
            "config": {
              "step_type": "api_rest",
              "capability_id": "google_search",
              "method": "GET",
              "url": "https://example.com"
            }
          },
          {
            "id": "step_002",
            "type": "transform",
            "config": {
              "step_type": "transform",
              "template": "Result: {{$steps.step_001.nonexistent_field}}"
            }
          }
        ],
        "input_schema": {"query": "string"},
        "output_schema": {"result": "string"},
        "output": {"result": "${step_002.output}"}
      },
      "options": {
        "enableComponentIntegrityValidation": true
      }
    }' | jq '.errors[] | select(.errorCode == "OUTPUT_FIELD_NOT_FOUND")'
  ```
- **pytestメソッド**: `test_tc_003_invalid_field_reference`

### TC-004: 循環参照の検出
- **テスト観点**: ステップ間の循環参照がエラーとして検出されること
- **関連する受入条件**: AC-5, AC-6
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest / curl
- **前提条件**:
  1. mySwiftAgentCoreが起動していること
- **テスト手順**:
  1. 循環参照を含むワークフローを作成
  2. バリデーションAPIを呼び出す
  3. エラーレスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - `isValid: false`
  - エラーコード: `CIRCULAR_REFERENCE_DETECTED`
  - `context.circularPath`に循環パスが含まれる
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/validate \
    -H "Content-Type: application/json" \
    -d '{
      "workflow": {
        "workflow_name": "circular_reference",
        "steps": [
          {
            "id": "step_a",
            "type": "transform",
            "config": {
              "step_type": "transform",
              "template": "{{$steps.step_b.output}}"
            }
          },
          {
            "id": "step_b",
            "type": "transform",
            "config": {
              "step_type": "transform",
              "template": "{{$steps.step_a.output}}"
            }
          }
        ],
        "input_schema": {"input": "string"},
        "output_schema": {"result": "string"},
        "output": {"result": "${step_a.output}"}
      },
      "options": {
        "enableComponentIntegrityValidation": true,
        "enableCircularReferenceCheck": true
      }
    }' | jq '.errors[] | select(.errorCode == "CIRCULAR_REFERENCE_DETECTED")'
  ```
- **pytestメソッド**: `test_tc_004_circular_reference_detection`

### TC-005: デバッグモードでのパフォーマンスメトリクス取得
- **テスト観点**: デバッグモードでバリデーション実行時間が取得できること
- **関連する受入条件**: AC-7
- **関連する設計方針**: DP-5
- **テスト種別**: E2E
- **テスト方法**: pytest / curl
- **前提条件**:
  1. mySwiftAgentCoreが起動していること
- **テスト手順**:
  1. デバッグモードを有効にしてバリデーションAPIを呼び出す
  2. パフォーマンスメトリクスを検証
- **期待結果**:
  - HTTPステータス: 200
  - `performanceMetrics.totalDurationMs`が返ること
  - `performanceMetrics.validatorMetrics`に各バリデータの実行時間が含まれること
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/validate \
    -H "Content-Type: application/json" \
    -d '{
      "workflow": {
        "workflow_name": "debug_test",
        "steps": [
          {
            "id": "step_001",
            "type": "transform",
            "config": {
              "step_type": "transform",
              "template": "test"
            }
          }
        ],
        "input_schema": {"input": "string"},
        "output_schema": {"result": "string"},
        "output": {"result": "${step_001.output}"}
      },
      "options": {
        "enableComponentIntegrityValidation": true,
        "debugMode": true,
        "collectPerformanceMetrics": true
      }
    }' | jq '.performanceMetrics'
  ```
- **pytestメソッド**: `test_tc_005_debug_mode_metrics`

### TC-006: パフォーマンステスト（50ステップ）
- **テスト観点**: 50ステップのワークフローが150ms以内に処理されること
- **関連する受入条件**: AC-8
- **関連する設計方針**: DP-3, DP-5
- **テスト種別**: E2E / パフォーマンス
- **テスト方法**: pytest / curl
- **前提条件**:
  1. mySwiftAgentCoreが起動していること
- **テスト手順**:
  1. 50ステップのワークフローを生成
  2. デバッグモードでバリデーションAPIを呼び出す
  3. 処理時間を検証
- **期待結果**:
  - `performanceMetrics.totalDurationMs < 150`
- **curlコマンド**:
  ```bash
  # 50ステップのワークフローを生成してテスト
  # （テストコード内で動的生成）
  ```
- **pytestメソッド**: `test_tc_006_performance_50_steps`

### TC-007: テンプレート構文エラーの検出
- **テスト観点**: 不正なテンプレート構文がエラーとして検出されること
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: pytest / curl
- **前提条件**:
  1. mySwiftAgentCoreが起動していること
- **テスト手順**:
  1. 不正なテンプレート構文を含むワークフローを作成
  2. バリデーションAPIを呼び出す
  3. エラーレスポンスを検証
- **期待結果**:
  - HTTPステータス: 200
  - `isValid: false`
  - エラーコード: `TEMPLATE_SYNTAX_ERROR`
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8006/api/v1/taskflow/validate \
    -H "Content-Type: application/json" \
    -d '{
      "workflow": {
        "workflow_name": "invalid_template",
        "steps": [
          {
            "id": "step_001",
            "type": "transform",
            "config": {
              "step_type": "transform",
              "template": "{{invalid syntax"
            }
          }
        ],
        "input_schema": {"input": "string"},
        "output_schema": {"result": "string"},
        "output": {"result": "${step_001.output}"}
      },
      "options": {
        "enableComponentIntegrityValidation": true,
        "enableTemplateValidation": true
      }
    }' | jq '.errors[] | select(.errorCode == "TEMPLATE_SYNTAX_ERROR")'
  ```
- **pytestメソッド**: `test_tc_007_template_syntax_error`

### TC-008: 修正提案の検証（Levenshtein距離）
- **テスト観点**: 類似フィールド名に対する修正提案が正しく生成されること
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: pytest / curl
- **前提条件**:
  1. mySwiftAgentCoreが起動していること
  2. 出力フィールドを持つcapabilityが登録されていること
- **テスト手順**:
  1. 類似した名前（タイポ）のフィールドを参照するワークフローを作成
  2. バリデーションAPIを呼び出す
  3. 修正提案を検証
- **期待結果**:
  - `suggestion.closestMatch`に正しいフィールド名が含まれる
  - `suggestion.message`に「Did you mean」が含まれる
- **curlコマンド**:
  ```bash
  # search_results → searh_results (typo) のケース
  curl -s -X POST http://localhost:8006/api/v1/taskflow/validate \
    -H "Content-Type: application/json" \
    -d '{
      "workflow": {
        "workflow_name": "typo_test",
        "steps": [
          {
            "id": "step_001",
            "type": "api_rest",
            "config": {
              "step_type": "api_rest",
              "capability_id": "google_search",
              "method": "GET",
              "url": "https://example.com"
            }
          },
          {
            "id": "step_002",
            "type": "transform",
            "config": {
              "step_type": "transform",
              "template": "{{$steps.step_001.searh_results}}"
            }
          }
        ],
        "input_schema": {"query": "string"},
        "output_schema": {"result": "string"},
        "output": {"result": "${step_002.output}"}
      },
      "options": {
        "enableComponentIntegrityValidation": true
      }
    }' | jq '.errors[0].suggestion'
  ```
- **pytestメソッド**: `test_tc_008_levenshtein_suggestion`

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. pytest受入テスト実行
3. 追加curlテスト実行（手動確認）

### 実行コマンド

```bash
# 1. サービス起動確認
cd mySwiftAgentCore
npm run dev &
sleep 5
curl -sf http://localhost:8006/health && echo "✅ Service healthy"

# 2. pytest受入テスト実行
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent
uv run pytest mySwiftAgentCore/tests/acceptance/test_issue_381_acceptance.py -v -s

# 3. 追加手動確認（オプション）
# 各TCのcurlコマンドを実行
```

### 成功基準
- [ ] すべてのpytestテストがパス
- [ ] すべての受入条件が検証済み
- [ ] デッドコードが検出されないこと
- [ ] パフォーマンス目標達成（50ステップ < 150ms）

---

## 9. コンポーネント間整合性検証

### CI-1: バリデータ統合整合性
- **検証対象**: ComponentIntegrityValidator内の5つのサブバリデータ
- **検証方法**: E2Eテストで全バリデータが動作することを確認
- **確認項目**:
  - [ ] StepReferenceValidatorがステップ参照エラーを検出
  - [ ] TemplateSyntaxValidatorがテンプレートエラーを検出
  - [ ] CircularReferenceValidatorが循環参照を検出
  - [ ] エラーが正しく集約される

### CI-2: 既存ValidationPipelineとの統合
- **検証対象**: 既存9バリデータとComponentIntegrityValidatorの連携
- **検証方法**: ValidationPipeline全体を通したE2Eテスト
- **確認項目**:
  - [ ] 実行順序が正しい（既存 → ComponentIntegrity）
  - [ ] エラーが重複しない

---

## 10. 補足事項

### 注意点
- mySwiftAgentCoreはTypeScript/Node.jsプロジェクトのため、受入テストはPython pytestでHTTP APIを呼び出す形式
- Capability定義（google_search.yaml等）が存在しない場合、一部テストがスキップされる可能性あり

### 依存関係
- Issue #375: ワークフロー生成・実行のバリデーション強化（完了済み）
- Issue #380: Capability出力スキーマの正確な定義（完了済み）

### テストデータの準備
- google_search.yamlにresponseSchemaが定義されていることを確認
- テスト用の大規模ワークフロー（50ステップ）はテストコード内で動的生成

---

**備考**: 本計画はアーキテクチャレビューの改善項目（循環参照検出、エラーメッセージ改善、パフォーマンス最適化、デバッグモード）を含んでいます。
