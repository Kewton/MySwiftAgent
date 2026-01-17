# 受入テスト計画書

**Issue**: #373
**作成日**: 2026-01-17
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #373
- **タイトル**: feat(mySwiftAgentCore): ワークフロー生成でcapability_id使用とタスクIDディレクトリ構造対応
- **プロジェクト**: mySwiftAgentCore

### 参照ドキュメント
- Issue: #373
- 設計方針書: `dev-reports/feature/issue/373/design-policy.md`
- 関連Issue: #372（CapabilityExecutor実装）、#364（taskflowGeneratorAgent）、#370（ワークフロー永続化）

### 目的
1. ワークフロー生成時に `url` ではなく `capability_id` を使用し、Issue #372 の URL解決機能を活用
2. JSONファイルを `{project_id}/{task_id}/{workflow_name}.json` 構造で保存
3. loadAll() の性能劣化を防ぐキャッシュ機構の実装

---

## 2. 単体テスト結果レビュー（TDD前）

### 現状
- **カバレッジ**: TDD前のため測定なし
- **目標**: 90%以上

### 既存テストの確認

| テストファイル | 対象 | 変更予定 |
|---------------|------|---------|
| `WorkflowStorage.test.ts` | 永続化 | ✅ taskId対応追加、キャッシュテスト追加 |
| `WorkflowRegistrar.test.ts` | 登録 | ✅ taskId伝播テスト追加 |
| `BatchProcessor.test.ts` | バッチ処理 | ✅ taskId受け渡しテスト追加 |
| `PromptBuilder.test.ts` | プロンプト | ✅ capability_idルールテスト追加 |

### 追加すべきテスト項目
1. **キャッシュ機構テスト**（必須）
   - TTL期限切れテスト
   - キャッシュヒット/ミステスト
   - 無効化テスト（save/delete時）
   - 最大エントリ数超過時のLRU削除テスト
2. **taskId付きsave/loadテスト**
   - 新ディレクトリ構造への保存
   - タスクディレクトリの作成
3. **後方互換性テスト**
   - 旧構造のloadAll対応
   - 新旧混在時の動作

---

## 3. 受入条件分析

### AC-1: capability_id パラメータの使用
- **原文**: api_restステップでcapability参照時に`capability_id`を使用する
- **分類**: 機能要件
- **テスト方法**: E2E API呼び出し + 生成結果検証
- **モック使用**: 不可（実LLM呼び出し必須）
- **検証ポイント**:
  1. 生成されたJSONの `steps[].config.capability_id` が設定されている
  2. `steps[].config.url` がcapability参照時に使用されていない
  3. 生成されたワークフローがTaskFlowEngineで実行可能

### AC-2: プロンプトルールの更新
- **原文**: `taskflow-rules.ts`にcapability_idの使用方法を追加
- **分類**: 機能要件
- **テスト方法**: コード確認 + E2E生成テスト
- **モック使用**: 不可
- **検証ポイント**:
  1. `TASKFLOW_RULES` に capability_id の説明が含まれる
  2. capability_id と url の使い分けルールが記載されている
  3. 具体例が含まれている

### AC-3: タスクIDディレクトリ構造
- **原文**: ファイル保存パスを `{project_id}/{task_id}/{workflow_name}.json` に変更
- **分類**: 機能要件
- **テスト方法**: E2E API呼び出し + ファイルシステム確認
- **モック使用**: 不可
- **検証ポイント**:
  1. ワークフロー生成後に `generated/workflows/{project_id}/{task_id}/` ディレクトリが作成される
  2. JSONファイルがタスクIDディレクトリ内に保存される
  3. WorkflowStorage.save() にtaskIdパラメータが追加されている

### AC-4: 後方互換性
- **原文**: 既存の `{project_id}/{workflow_name}.json` 構造のワークフローも読み込み可能
- **分類**: 機能要件
- **テスト方法**: 既存ファイル読み込みテスト
- **モック使用**: 不可
- **検証ポイント**:
  1. 旧構造（平坦）のワークフローが loadAll() で読み込める
  2. 新構造（階層）と旧構造が混在しても正常動作
  3. マイグレーション不要

### AC-5: テスト・品質
- **原文**: 単体テストカバレッジ90%以上、統合テストでE2E動作確認
- **分類**: 非機能要件
- **テスト方法**: カバレッジレポート + E2Eテスト実行
- **検証ポイント**:
  1. 単体テストカバレッジ 90%以上
  2. E2Eテストで生成〜実行が正常動作

---

## 4. 設計方針検証

### DP-1: capability_id 優先アーキテクチャ
- **設計方針**: capability参照時はcapability_idを使用し、URLはCapabilityExecutorが解決
- **検証方法**: E2E生成テスト + JSONスキーマ検証
- **テスト項目**:
  1. 生成されたワークフローの api_rest ステップで capability_id が使用されている
  2. TaskFlowEngineが capability_id を正しく解決してAPI実行できる

### DP-2: Adapter Pattern for WorkflowStorage
- **設計方針**: save()メソッドのオーバーロードで後方互換性を維持
- **検証方法**: 単体テスト + E2Eテスト
- **テスト項目**:
  1. 旧形式 `save(projectId, workflowId, workflow)` が動作する
  2. 新形式 `save(projectId, taskId, workflowId, workflow)` が動作する

### DP-3: loadAll() キャッシュ機構
- **設計方針**: TTLベース・LRU風キャッシュで性能維持
- **検証方法**: 単体テスト + パフォーマンステスト
- **テスト項目**:
  1. キャッシュヒット時は1ms未満でレスポンス
  2. save/delete時にキャッシュが無効化される
  3. TTL期限切れ後に再読み込みされる

---

## 5. デッドコード検証計画

### F-1: capability_id ルール（taskflow-rules.ts）
- **ファイル**: `src/taskflowGeneratorAgent/prompts/templates/taskflow-rules.ts`
- **種別**: constant
- **期待される呼び出し元**: PromptBuilder
- **E2E確認**: ワークフロー生成API呼び出しで capability_id が生成される

### F-2: saveWithTaskId メソッド（WorkflowStorage）
- **ファイル**: `src/taskflowGeneratorAgent/storage/WorkflowStorage.ts`
- **種別**: method
- **期待される呼び出し元**: WorkflowRegistrar.register()
- **E2E確認**: バッチ生成API呼び出しでタスクIDディレクトリにファイル作成

### F-3: キャッシュ機構（WorkflowStorage）
- **ファイル**: `src/taskflowGeneratorAgent/storage/WorkflowStorage.ts`
- **種別**: private methods (getFromCache, setToCache, invalidateCache)
- **期待される呼び出し元**: loadAll(), save(), delete()
- **E2E確認**: 連続loadAll()呼び出しで2回目が高速化

### F-4: taskId伝播（WorkflowRegistrar → BatchProcessor）
- **ファイル**: `src/taskflowGeneratorAgent/generator/WorkflowRegistrar.ts`
- **種別**: parameter
- **期待される呼び出し元**: BatchProcessor
- **E2E確認**: バッチ生成APIでtaskIdが正しく伝播

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| myVault | http://localhost:8103 | GET /health |

### 起動コマンド
```bash
# 推奨: ハイブリッドモード（再起動含む）
./scripts/dev-hybrid.sh stop --local-only
./scripts/dev-hybrid.sh start --local-only
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| ANTHROPIC_API_KEY | Anthropic APIキー（MyVault経由） | ✅ |
| OPENAI_API_KEY | OpenAI APIキー（MyVault経由） | 推奨 |

### テストデータ
- MyVault の `default_project` に APIキーが登録済み
- E2Eテストスクリプト: `./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh`

---

## 7. テスト項目

### TC-001: サービス再起動後のヘルスチェック
- **テスト観点**: サービス再起動後の正常起動確認
- **関連する受入条件**: AC-5
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. `./scripts/dev-hybrid.sh stop --local-only` でサービス停止
  2. `./scripts/dev-hybrid.sh start --local-only` でサービス再起動
- **テスト手順**:
  1. mySwiftAgentCore のヘルスチェック
  2. Generator エンドポイントのヘルスチェック
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: `{"status": "healthy"}`
- **curlコマンド**:
  ```bash
  # mySwiftAgentCore ヘルスチェック
  curl -s http://localhost:8006/health | jq .

  # Generator ヘルスチェック
  curl -s http://localhost:8006/api/v1/generator/health | jq .
  ```
- **pytestメソッド**: `test_tc_001_service_health_after_restart`

### TC-002: E2Eテストスクリプトによるワークフロー生成
- **テスト観点**: 既存E2Eテストスクリプトでワークフロー生成が動作すること
- **関連する受入条件**: AC-1, AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: シェルスクリプト実行
- **前提条件**:
  1. サービス起動済み（TC-001完了後）
  2. MyVault に ANTHROPIC_API_KEY 設定済み
- **テスト手順**:
  1. E2Eテストスクリプトを実行
  2. 生成結果を確認
- **期待結果**:
  - Test 1, 2, 3 すべて PASS
  - ワークフローが生成される
- **実行コマンド**:
  ```bash
  ./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh
  ```
- **pytestメソッド**: `test_tc_002_e2e_script_workflow_generation`

### TC-003: capability_id 使用の検証
- **テスト観点**: 生成されたワークフローでcapability_idが使用されていること
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl + JSON検証
- **前提条件**:
  1. サービス起動済み
  2. MyVault に APIキー設定済み
- **テスト手順**:
  1. バッチ生成APIを呼び出し
  2. 生成されたJSONを取得
  3. api_rest ステップの config を確認
- **期待結果**:
  - api_rest ステップに `capability_id` が設定されている
  - `url` ではなく `capability_id` が使用されている
- **curlコマンド**:
  ```bash
  # ワークフロー生成（capability参照あり）
  curl -s -X POST http://localhost:8006/api/v1/generator/workflow/batch \
    -H "Content-Type: application/json" \
    -d '{
      "tasks": [{
        "task_id": "test_capability",
        "name": "Test Capability ID",
        "description": "Test that capability_id is used for API calls",
        "interface": {
          "input": {"query": "string"},
          "output": {"results": "array"}
        }
      }],
      "capabilities": [{
        "id": "google_search",
        "name": "Google Search",
        "description": "Web search",
        "category": "api",
        "status": "available"
      }],
      "project_id": "default_project"
    }' | jq '.workflows[].steps[] | select(.type == "api_rest") | .config'
  ```
- **pytestメソッド**: `test_tc_003_capability_id_in_generated_workflow`

### TC-004: タスクIDディレクトリ構造の検証
- **テスト観点**: JSONファイルがタスクIDディレクトリに保存されること
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: curl + ファイルシステム確認
- **前提条件**:
  1. サービス起動済み
  2. `generated/workflows/default_project/` ディレクトリの初期状態を確認
- **テスト手順**:
  1. バッチ生成APIを呼び出し（task_id指定）
  2. ファイルシステムでディレクトリ構造を確認
- **期待結果**:
  - `generated/workflows/default_project/{task_id}/` ディレクトリが作成される
  - ワークフローJSONがタスクIDディレクトリ内に保存される
- **確認コマンド**:
  ```bash
  # 生成後のディレクトリ構造確認
  tree generated/workflows/default_project/

  # または
  find generated/workflows/default_project/ -name "*.json" -type f
  ```
- **pytestメソッド**: `test_tc_004_task_id_directory_structure`

### TC-005: 後方互換性 - 旧構造ファイルの読み込み
- **テスト観点**: 既存の平坦構造ワークフローが読み込めること
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: ファイル準備 + API呼び出し
- **前提条件**:
  1. `generated/workflows/default_project/` に旧構造のJSONファイルが存在
- **テスト手順**:
  1. 旧構造のテストワークフローを配置
  2. loadAll相当のAPI（または直接確認）で読み込み
  3. 新旧両方のワークフローが取得できることを確認
- **期待結果**:
  - 旧構造（平坦）のワークフローが読み込める
  - 新構造（階層）のワークフローも読み込める
- **pytestメソッド**: `test_tc_005_backward_compatibility_load`

### TC-006: 生成されたワークフローの実行確認
- **テスト観点**: 生成されたワークフローがTaskFlowEngineで実行可能であること
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: curl（ワークフロー実行API）
- **前提条件**:
  1. TC-002またはTC-003でワークフローが生成済み
  2. graphAiServer または TaskFlowEngine が利用可能
- **テスト手順**:
  1. 生成されたワークフローを取得
  2. TaskFlowEngine APIで実行
  3. capability_id が正しく解決されてAPI呼び出しが行われることを確認
- **期待結果**:
  - ワークフローが正常に実行開始
  - capability_id からURLが解決される（Issue #372の機能）
- **curlコマンド**:
  ```bash
  # 生成されたワークフローを実行（graphAiServer経由）
  curl -s -X POST http://localhost:8005/api/v1/workflow/execute \
    -H "Content-Type: application/json" \
    -d '{
      "workflow_name": "{生成されたワークフロー名}",
      "project_id": "default_project",
      "input": {"query": "test query"}
    }'
  ```
- **pytestメソッド**: `test_tc_006_execute_generated_workflow`

### TC-007: キャッシュ機構の動作確認
- **テスト観点**: loadAll()のキャッシュが正常に動作すること
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト + パフォーマンステスト
- **テスト方法**: vitest + 時間計測
- **前提条件**:
  1. WorkflowStorageのキャッシュ機構が実装済み
- **テスト手順**:
  1. loadAll()を2回連続呼び出し
  2. 2回目の実行時間を計測
  3. キャッシュヒットを確認
- **期待結果**:
  - 2回目のloadAll()が1ms未満
  - キャッシュヒット率が正しく記録される
- **pytestメソッド**: `test_tc_007_cache_hit_performance`

### TC-008: キャッシュ無効化の検証
- **テスト観点**: save/delete時にキャッシュが無効化されること
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **テスト手順**:
  1. loadAll()でキャッシュを作成
  2. save()でワークフローを保存
  3. loadAll()で新しいワークフローが含まれていることを確認
- **期待結果**:
  - save後のloadAll()で新ワークフローが取得できる
  - delete後のloadAll()で削除されたワークフローが含まれない
- **pytestメソッド**: `test_tc_008_cache_invalidation`

---

## 8. テスト実行計画

### 実行順序
1. **サービス再起動**
   ```bash
   ./scripts/dev-hybrid.sh stop --local-only
   ./scripts/dev-hybrid.sh start --local-only
   ```

2. **ヘルスチェック確認**（TC-001）
   ```bash
   curl -s http://localhost:8006/health | jq .
   curl -s http://localhost:8006/api/v1/generator/health | jq .
   ```

3. **E2Eテストスクリプト実行**（TC-002）
   ```bash
   ./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh
   ```

4. **capability_id検証**（TC-003）
   - 生成されたJSONを確認

5. **ディレクトリ構造検証**（TC-004）
   ```bash
   tree generated/workflows/default_project/
   ```

6. **後方互換性確認**（TC-005）
   - 旧構造ファイルの読み込み確認

7. **ワークフロー実行確認**（TC-006）
   - 生成されたワークフローをTaskFlowEngineで実行

8. **pytest受入テスト実行**
   ```bash
   cd mySwiftAgentCore && npm test -- tests/acceptance/test_issue_373_acceptance.test.ts
   ```

### 成功基準
- [ ] TC-001: サービス再起動後ヘルスチェック成功
- [ ] TC-002: E2Eテストスクリプトが PASS
- [ ] TC-003: 生成ワークフローに capability_id が含まれる
- [ ] TC-004: タスクIDディレクトリが作成される
- [ ] TC-005: 旧構造ファイルが読み込める
- [ ] TC-006: 生成ワークフローがTaskFlowEngineで実行可能
- [ ] TC-007: キャッシュヒット時 < 1ms
- [ ] TC-008: save/delete後にキャッシュが無効化される
- [ ] 全受入条件が検証済み
- [ ] デッドコードが検出されないこと

---

## 9. 補足事項

### MyVault設定確認
```bash
# default_projectのシークレット一覧
curl -s http://localhost:8103/api/v1/projects/default_project/secrets | jq .
```

### 生成されたファイルの確認
```bash
# 最新の生成ワークフローを表示
cat generated/workflows/default_project/**/*.json | jq .
```

### トラブルシューティング
1. **LLMエラーが発生する場合**: MyVaultのAPIキー設定を確認
2. **ディレクトリが作成されない場合**: 書き込み権限を確認
3. **キャッシュが効かない場合**: WorkflowStorageのconfig設定を確認

### 関連コマンドまとめ
```bash
# サービス再起動
./scripts/dev-hybrid.sh stop --local-only
./scripts/dev-hybrid.sh start --local-only

# E2Eテスト実行
./mySwiftAgentCore/dev-reports/feature/issue/364/e2e-test-script.sh

# ディレクトリ構造確認
tree generated/workflows/

# ヘルスチェック
curl -s http://localhost:8006/health | jq .
```
