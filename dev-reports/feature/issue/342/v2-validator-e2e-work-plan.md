# Issue #342 V2バリデーター修正 E2E検証 作業計画書

## Issue概要

```markdown
## Issue: V2バリデーター修正のE2E検証
**Issue番号**: #342 (サブタスク)
**サイズ**: S
**作業見積**: 2.5時間
**優先度**: High
**依存Issue**: なし（バリデーター修正完了済み）
**対象プロジェクト**: expertAgent, myAgentDesk
**Playwright必須**: ✅ Yes（myAgentDesk UI検証）
```

## 背景

### 完了済み作業

| タスクID | 修正内容 | 対象ファイル | 状態 |
|---------|---------|-------------|------|
| MF-1 | graphAiServerとの仕様同期ドキュメント | `docs/design/graphai-env-vars.md` | ✅ |
| DC-1 | 環境変数許可リスト追加 | `agent_constraint_validator.py` | ✅ |
| DC-2 | V1互換パスパターン許可 | `source_path_rule_engine.py` | ✅ |

### 修正前の問題

V2で生成されたワークフロー（v1.86, v1.87）が以下のエラーで失敗：

```
Invalid URL: '${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search'
```

---

## デッドコード検証結果 ✅

### 検証方法

修正したコードが実際に使用されているかを確認：

```bash
# ALLOWED_ENV_VARS の使用箇所
grep -n "ALLOWED_ENV_VARS" expertAgent/aiagent/langgraph/jobGeneratorV2/
```

### 検証結果

| 追加コード | 使用箇所 | 状態 |
|-----------|---------|------|
| `ALLOWED_ENV_VARS` | `agent_constraint_validator.py:177, 180, 401, 408` | ✅ 使用中 |
| `validate_path()` V1互換ロジック | `source_path_rule_engine.py` 内で呼び出し | ✅ 使用中 |

### 統合確認

| バリデーター | 統合先 | 状態 |
|-------------|-------|------|
| `AgentConstraintValidator` | `validation_pipeline.py:84` | ✅ 統合済 |
| `SourcePathRuleEngine` | `validation_pipeline.py:83` | ✅ 統合済 |
| 両方 | `workflow_schema_validator.py:41-42` | ✅ 統合済 |

**結論**: デッドコードなし ✅

---

## 詳細タスク分解

### Phase 1: 静的検証（完了済み）

- [x] **Task 1.1**: 単体テスト実行
  - 成果物: 53 tests passed
  - 状態: ✅ 完了

- [x] **Task 1.2**: デッドコード検証
  - 成果物: 統合確認済み
  - 状態: ✅ 完了

### Phase 2: サービス起動・API検証

- [ ] **Task 2.1**: サービス起動（V2有効）
  - 所要時間: 10分
  - コマンド: `USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh`
  - 依存: なし

- [ ] **Task 2.2**: API経由V2ジョブ生成テスト
  - 所要時間: 20分
  - 成果物: ジョブ生成成功確認
  - 依存: Task 2.1

### Phase 3: UI経由の実践的受入テスト【必須】

- [ ] **Task 3.1**: Generate画面からのジョブ生成
  - 所要時間: 30分
  - URL: `http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/generate`
  - 成果物: UI操作によるジョブ生成成功
  - 依存: Task 2.1

- [ ] **Task 3.2**: Runs画面でのワークフロー実行確認
  - 所要時間: 30分
  - URL: `http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/runs`
  - 成果物: ワークフロー実行成功（Invalid URLエラーなし）
  - 依存: Task 3.1

### Phase 4: 受入テストファイル作成

- [ ] **Task 4.1**: pytest受入テスト作成
  - 所要時間: 20分
  - 成果物: `tests/acceptance/test_issue_342_v2_validator_acceptance.py`
  - 依存: Task 3.2

### Phase 5: コミット

- [ ] **Task 5.1**: 変更コミット
  - 所要時間: 15分
  - 成果物: Git commit
  - 依存: Task 4.1

---

## タスク依存関係

```
Phase 1 (完了)
    │
    ▼
Task 2.1 ─────▶ Task 2.2
(サービス起動)   (API検証)
    │
    ├─────────────────────┐
    ▼                     ▼
Task 3.1              Task 3.2
(Generate画面)        (Runs画面)
    │                     │
    └─────────┬───────────┘
              ▼
          Task 4.1
        (受入テスト)
              │
              ▼
          Task 5.1
          (コミット)
```

---

## L3受入テスト計画（具体的なコマンド）

### Step 1: サービス起動確認

```bash
# サービス起動（V2有効）
USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh

# ヘルスチェック
curl -sf http://localhost:8004/health && echo "✅ expertAgent: healthy"
curl -sf http://localhost:8005/health && echo "✅ graphAiServer: healthy"
curl -sf http://localhost:8003/health && echo "✅ myVault: healthy"
curl -sf http://localhost:8001/health && echo "✅ jobqueue: healthy"
curl -sf http://localhost:8000 && echo "✅ myAgentDesk: healthy"
```

### Step 2: UI経由のジョブ生成テスト【実践的テスト】

#### 2.1 Generate画面でのジョブ生成

1. **ブラウザで開く**:
   ```
   http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/generate
   ```

2. **ユーザー要件を入力**:
   ```
   Google検索でAI関連のニュースを取得して要約する
   ```

3. **「Generate」ボタンをクリック**

4. **確認ポイント**:
   - [ ] ジョブ生成が開始される（ローディング表示）
   - [ ] エラーメッセージが表示されない
   - [ ] 生成完了後、タスク一覧が表示される

#### 2.2 Runs画面でのワークフロー実行

1. **ブラウザで開く**:
   ```
   http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/runs
   ```

2. **生成されたジョブを選択して「Run」をクリック**

3. **確認ポイント**:
   - [ ] ワークフロー実行が開始される
   - [ ] **「Invalid URL」エラーが発生しない** ← 重要
   - [ ] 実行結果が表示される

### Step 3: API経由の検証（補助）

```bash
# プロジェクトID・ワークベンチID
PROJECT_ID="proj_mjbjua2z7y65wy"
WORKBENCH_ID="wb_1766969315404_udrhx79"

# ジョブ一覧取得
curl -s "http://localhost:8004/v1/jobs?project_id=$PROJECT_ID" | jq '.jobs[-1]'

# 最新ジョブのステータス確認
JOB_ID=$(curl -s "http://localhost:8004/v1/jobs?project_id=$PROJECT_ID" | jq -r '.jobs[-1].id')
curl -s "http://localhost:8004/v1/jobs/$JOB_ID/status" | jq '.'

# ワークフローYAML確認（環境変数が含まれているか）
curl -s "http://localhost:8004/v1/jobs/$JOB_ID" | jq '.workflow_yaml' -r | head -50
```

### Step 4: エラーログ確認

```bash
# expertAgentログ確認（Invalid URLエラーがないこと）
tail -100 expertAgent/logs/expertagent.log | grep -E "(ERROR|Invalid URL)" || echo "✅ No errors found"

# graphAiServerログ確認
docker logs myswiftagent-graphaiserver 2>&1 | tail -50 | grep -iE "(error|invalid)" || echo "✅ No errors found"
```

### Step 5: エビデンス収集

```bash
# 成功したジョブのワークフローYAMLを保存
curl -s "http://localhost:8004/v1/jobs/$JOB_ID" | jq '.workflow_yaml' -r > /tmp/v2_workflow_success.yaml

# 環境変数プレースホルダーの存在確認
grep '${EXPERTAGENT_BASE_URL}' /tmp/v2_workflow_success.yaml && echo "✅ Environment variable placeholder found"

# V1互換パスの存在確認
grep ':source\.' /tmp/v2_workflow_success.yaml && echo "✅ V1 compatible source path found"
```

---

## 成果物チェックリスト

### コード変更（完了済み）
- [x] `docs/design/graphai-env-vars.md`
- [x] `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/agent_constraint_validator.py`
- [x] `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/source_path_rule_engine.py`
- [x] `expertAgent/tests/unit/test_job_generator_v2/test_agent_constraint_validator.py`
- [x] `expertAgent/tests/unit/test_job_generator_v2/test_source_path_rule_engine.py`

### デッドコード検証
- [x] `ALLOWED_ENV_VARS` が実際に使用されている
- [x] バリデーターがパイプラインに統合されている

### E2E検証（UI経由）
- [ ] Generate画面でジョブ生成成功
- [ ] Runs画面でワークフロー実行成功
- [ ] 「Invalid URL」エラーが発生しない

### テスト
- [ ] `tests/acceptance/test_issue_342_v2_validator_acceptance.py`

---

## Definition of Done

Issue完了条件：
- [x] 単体テスト全パス（53件）
- [x] デッドコード検証完了（統合確認済み）
- [ ] **UI経由でジョブ生成成功（Generate画面）**
- [ ] **UI経由でワークフロー実行成功（Runs画面）**
- [ ] **「Invalid URL」エラーが発生しない**
- [ ] 受入テストファイル作成済み
- [ ] 変更がコミット済み

---

## リスクと対策

| リスク | 発生確率 | 影響 | 対策 |
|-------|---------|------|------|
| LLM APIキー未設定 | 中 | E2E実行不可 | .env確認 |
| myAgentDesk起動失敗 | 低 | UI検証不可 | `npm run dev`で個別起動 |
| ワークフロー生成タイムアウト | 中 | 検証遅延 | シンプルな要件使用 |
| 既存プロジェクト/ワークベンチ不存在 | 中 | UI検証不可 | 新規作成または別ID使用 |

---

## 次のアクション

1. **Task 2.1実行**: `USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh`
2. **Task 3.1実行**: Generate画面でジョブ生成
3. **Task 3.2実行**: Runs画面でワークフロー実行
4. **Task 4.1実行**: 受入テストファイル作成
5. **Task 5.1実行**: 変更をコミット

---

*作成日: 2026-01-09*
*Issue #342 V2バリデーター修正 E2E検証*
