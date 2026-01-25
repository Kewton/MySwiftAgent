# 作業計画書: LLMモデル設定のmyVault管理とcommonUI設定画面

## Issue概要

```markdown
## Issue: feat: LLMモデル設定をmyVaultで管理しcommonUIから設定可能にする
**Issue番号**: #269
**サイズ**: M
**作業見積**: 26時間（約3.5日）
**優先度**: Medium
**依存Issue**: なし
```

---

## 詳細タスク分解

### 実装タスク（Phase 1）

#### Phase 1.1: myVault側（2時間）

- [ ] **Task 1.1.1**: モデル設定初期登録スクリプト作成
  - 所要時間: 1.5時間
  - 成果物: `scripts/init-model-settings.sh`
  - 依存: なし
  - 内容:
    - 8つのモデル設定をdefault_projectに登録
    - 冪等性確保（既存設定は上書きしない）

- [ ] **Task 1.1.2**: 初期値登録・確認
  - 所要時間: 0.5時間
  - 成果物: myVaultに8つのシークレット登録完了
  - 依存: Task 1.1.1

#### Phase 1.2: expertAgent側（8時間）

- [ ] **Task 1.2.1**: 共通ヘルパー関数追加
  - 所要時間: 1時間
  - 成果物: `expertAgent/core/secrets.py` に `get_model_config()` 追加
  - 依存: なし
  - 内容:
    ```python
    def get_model_config(key: str, default: str) -> str:
        """MyVault優先でモデル設定を取得"""
    ```

- [ ] **Task 1.2.2**: llm_invocation.py修正
  - 所要時間: 2時間
  - 成果物: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py`
  - 依存: Task 1.2.1
  - 内容:
    - 行177: `os.getenv()` → `get_model_config()` に変更
    - 6つのモデル設定が対象

- [ ] **Task 1.2.3**: llm_service.py修正
  - 所要時間: 1.5時間
  - 成果物: `expertAgent/app/services/conversation/llm_service.py`
  - 依存: Task 1.2.1
  - 内容:
    - 行77, 192: `os.getenv()` → `get_model_config()` に変更
    - `CHAT_CLARIFICATION_MODEL` が対象

- [ ] **Task 1.2.4**: candidate_generator.py修正
  - 所要時間: 0.5時間
  - 成果物: `expertAgent/app/services/conversation/candidate_generator.py`
  - 依存: Task 1.2.1
  - 内容:
    - 行112: `os.getenv()` → `get_model_config()` に変更
    - `CANDIDATE_GENERATION_MODEL` が対象

- [ ] **Task 1.2.5**: 静的解析・フォーマット
  - 所要時間: 1時間
  - 成果物: Ruff/MyPyエラーゼロ
  - 依存: Task 1.2.2, 1.2.3, 1.2.4
  - 内容:
    ```bash
    uv run ruff check expertAgent/ --fix
    uv run ruff format expertAgent/
    uv run mypy expertAgent/
    ```

- [ ] **Task 1.2.6**: expertAgent単体テスト追加
  - 所要時間: 2時間
  - 成果物: `expertAgent/tests/unit/test_model_config.py`
  - 依存: Task 1.2.1
  - カバレッジ目標: 90%
  - テストケース:
    - MyVault取得成功
    - MyVault取得失敗→環境変数フォールバック
    - 両方未設定→デフォルト値
    - キャッシュ動作確認

#### Phase 1.3: commonUI側（8時間）

- [ ] **Task 1.3.1**: available_models.yaml作成
  - 所要時間: 1時間
  - 成果物: `commonUI/config/available_models.yaml`
  - 依存: なし
  - 内容:
    - プロバイダ別モデル定義（Claude/GPT/Gemini）
    - 設定カテゴリ定義（Chat/Job Generator/Workflow）

- [ ] **Task 1.3.2**: モデル設定ローダー実装
  - 所要時間: 1.5時間
  - 成果物: `commonUI/core/model_settings.py`
  - 依存: Task 1.3.1
  - 内容:
    - YAMLファイル読み込み
    - モデル一覧取得
    - 設定カテゴリ取得

- [ ] **Task 1.3.3**: モデル設定タブUI実装
  - 所要時間: 3時間
  - 成果物: `commonUI/pages/3_🔐_MyVault.py` 修正
  - 依存: Task 1.3.2
  - 内容:
    - 「Model Settings」タブ追加
    - カテゴリ別Expander
    - ドロップダウン選択UI
    - 保存ボタン

- [ ] **Task 1.3.4**: 設定保存・キャッシュリロード連携
  - 所要時間: 1.5時間
  - 成果物: `commonUI/pages/3_🔐_MyVault.py` 修正
  - 依存: Task 1.3.3
  - 内容:
    - PATCH API呼び出し
    - expertAgent/graphAiServerキャッシュリロード
    - 成功/エラー通知

- [ ] **Task 1.3.5**: commonUI単体テスト追加
  - 所要時間: 1時間
  - 成果物: `commonUI/tests/test_model_settings.py`
  - 依存: Task 1.3.2
  - カバレッジ目標: 90%

### テストタスク（Phase 2: TDD - CI実行可能）

- [ ] **Task 2.1**: expertAgent結合テスト
  - 所要時間: 2時間
  - 成果物: `tests/integration/test_model_config_integration.py`
  - 依存: Phase 1.2完了
  - シナリオ:
    - myVault起動時のモデル設定取得
    - myVault停止時のフォールバック動作

- [ ] **Task 2.2**: commonUI結合テスト
  - 所要時間: 1.5時間
  - 成果物: `commonUI/tests/integration/test_myvault_model_settings.py`
  - 依存: Phase 1.3完了
  - シナリオ:
    - モデル設定一覧取得
    - モデル設定更新

- [ ] **Task 2.3**: 静的解析（全体）
  - 所要時間: 0.5時間
  - 成果物: Ruff/MyPyエラーゼロ
  - 依存: Task 2.1, 2.2

### 受入テストタスク（Phase 3: L3ローカル受入テスト）

- [ ] **Task 3.1**: L3受入テスト計画
  - 所要時間: 0.5時間
  - 成果物: 受入テストシナリオ（curlコマンド）
  - 依存: Phase 2完了

- [ ] **Task 3.2**: L3受入テスト実行
  - 所要時間: 1.5時間
  - 成果物: `tests/acceptance/test_issue_269_model_settings.sh`
  - 依存: Task 3.1
  - 内容:
    - サービス起動確認
    - myVaultモデル設定取得API
    - expertAgentでのモデル設定適用確認
    - キャッシュリロードAPI

### ドキュメントタスク（Phase 4）

- [ ] **Task 4.1**: README更新
  - 所要時間: 0.5時間
  - 成果物: `commonUI/README.md` 更新
  - 依存: Phase 3完了

- [ ] **Task 4.2**: PR作成
  - 所要時間: 0.5時間
  - 成果物: GitHub PR
  - 依存: Task 4.1

---

## タスク依存関係

```
Phase 1.1 (myVault)
├── Task 1.1.1 → Task 1.1.2
│
Phase 1.2 (expertAgent)
├── Task 1.2.1 (共通ヘルパー)
│   ├── Task 1.2.2 (llm_invocation.py)
│   ├── Task 1.2.3 (llm_service.py)
│   └── Task 1.2.4 (candidate_generator.py)
│       └── Task 1.2.5 (静的解析)
│           └── Task 1.2.6 (単体テスト)
│
Phase 1.3 (commonUI)
├── Task 1.3.1 (YAML) → Task 1.3.2 (ローダー)
│                           └── Task 1.3.3 (UI)
│                               └── Task 1.3.4 (保存)
│                                   └── Task 1.3.5 (テスト)
│
Phase 2 (結合テスト)
├── Task 2.1 (expertAgent) ─┐
├── Task 2.2 (commonUI) ────┼── Task 2.3 (静的解析)
│
Phase 3 (受入テスト)
├── Task 3.1 (計画) → Task 3.2 (実行)
│
Phase 4 (ドキュメント)
├── Task 4.1 (README) → Task 4.2 (PR)
```

---

## 作業スケジュール

### 日次計画

**Day 1 (8時間)**
| 時間 | タスク | 成果物 |
|------|--------|--------|
| 09:00-10:30 | Task 1.1.1 | init-model-settings.sh |
| 10:30-11:00 | Task 1.1.2 | myVault設定完了 |
| 11:00-12:00 | Task 1.2.1 | get_model_config() |
| 13:00-15:00 | Task 1.2.2 | llm_invocation.py修正 |
| 15:00-16:30 | Task 1.2.3 | llm_service.py修正 |
| 16:30-17:00 | Task 1.2.4 | candidate_generator.py修正 |

**Day 2 (8時間)**
| 時間 | タスク | 成果物 |
|------|--------|--------|
| 09:00-10:00 | Task 1.2.5 | 静的解析パス |
| 10:00-12:00 | Task 1.2.6 | expertAgent単体テスト |
| 13:00-14:00 | Task 1.3.1 | available_models.yaml |
| 14:00-15:30 | Task 1.3.2 | model_settings.py |
| 15:30-18:30 | Task 1.3.3 | モデル設定タブUI |

**Day 3 (8時間)**
| 時間 | タスク | 成果物 |
|------|--------|--------|
| 09:00-10:30 | Task 1.3.4 | 保存・リロード連携 |
| 10:30-11:30 | Task 1.3.5 | commonUI単体テスト |
| 11:30-13:30 | Task 2.1 | expertAgent結合テスト |
| 14:30-16:00 | Task 2.2 | commonUI結合テスト |
| 16:00-16:30 | Task 2.3 | 静的解析（全体） |
| 16:30-17:00 | Task 3.1 | L3受入テスト計画 |
| 17:00-18:30 | Task 3.2 | L3受入テスト実行 |

**Day 4 (2時間)**
| 時間 | タスク | 成果物 |
|------|--------|--------|
| 09:00-09:30 | Task 4.1 | README更新 |
| 09:30-10:00 | Task 4.2 | PR作成 |

**総作業時間**: 26時間（約3.5日）

---

## チェックポイント

| タイミング | 確認事項 | 対応 |
|-----------|---------|------|
| Task 1.1.2完了時 | myVault設定登録確認 | curlで8設定取得確認 |
| Task 1.2.5完了時 | 静的解析パス | エラー時は修正 |
| Phase 1完了時 | 単体テストカバレッジ90%達成 | 未達の場合追加テスト |
| Phase 2完了時 | 結合テストパス | 失敗時はデバッグ |
| Phase 3完了時 | L3受入テストパス | 失敗時は原因調査 |
| PR作成前 | pre-push-check-all.shパス | エラー時は修正 |

---

## リスクと対策

| リスク | 発生確率 | 影響 | 対策 |
|-------|---------|------|------|
| myVault接続エラー | 低 | 実装遅延2時間 | ローカルmyVault起動確認を先行 |
| キャッシュ不整合 | 中 | テスト遅延1時間 | リロードAPI呼び出し確認 |
| Streamlit UIバグ | 中 | 実装遅延1時間 | 既存タブ実装を参考 |
| 静的解析エラー | 低 | 実装遅延0.5時間 | 随時ruff/mypy実行 |

---

## 成果物チェックリスト

### コード

**myVault**
- [ ] `scripts/init-model-settings.sh`

**expertAgent**
- [ ] `core/secrets.py` (修正: `get_model_config()` 追加)
- [ ] `aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py` (修正)
- [ ] `app/services/conversation/llm_service.py` (修正)
- [ ] `app/services/conversation/candidate_generator.py` (修正)

**commonUI**
- [ ] `config/available_models.yaml` (新規)
- [ ] `core/model_settings.py` (新規)
- [ ] `pages/3_🔐_MyVault.py` (修正)

### テスト

- [ ] `expertAgent/tests/unit/test_model_config.py` (新規)
- [ ] `tests/integration/test_model_config_integration.py` (新規)
- [ ] `commonUI/tests/test_model_settings.py` (新規)
- [ ] `commonUI/tests/integration/test_myvault_model_settings.py` (新規)
- [ ] `tests/acceptance/test_issue_269_model_settings.sh` (新規)

### ドキュメント

- [ ] `commonUI/README.md` (更新)

---

## L3受入テスト計画（具体的なコマンド）

### Step 1: サービス起動確認

```bash
# サービス起動
make dev-all

# ヘルスチェック（必須）
curl -sf http://localhost:8003/health && echo "✅ myVault: healthy"
curl -sf http://localhost:8004/health && echo "✅ expertAgent: healthy"
curl -sf http://localhost:8501/healthz && echo "✅ commonUI: healthy"
```

### Step 2: myVaultモデル設定取得API

```bash
# モデル設定一覧確認（8件登録されていること）
curl -s http://localhost:8003/api/secrets?project=default_project \
  -H "X-Service: commonui" \
  -H "X-Token: ${MYVAULT_TOKEN_COMMONUI}" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Total secrets: {len(d)}')"

# 個別設定取得（CHAT_CLARIFICATION_MODEL）
curl -s http://localhost:8003/api/secrets/default_project/CHAT_CLARIFICATION_MODEL \
  -H "X-Service: commonui" \
  -H "X-Token: ${MYVAULT_TOKEN_COMMONUI}"

# 期待するレスポンス:
# {
#   "id": 1,
#   "project": "default_project",
#   "path": "CHAT_CLARIFICATION_MODEL",
#   "value": "gemini-2.0-flash",
#   ...
# }
```

### Step 3: モデル設定更新API

```bash
# 設定更新（CHAT_CLARIFICATION_MODELをclaude-haiku-4-5に変更）
curl -s -X PATCH http://localhost:8003/api/secrets/default_project/CHAT_CLARIFICATION_MODEL \
  -H "Content-Type: application/json" \
  -H "X-Service: commonui" \
  -H "X-Token: ${MYVAULT_TOKEN_COMMONUI}" \
  -d '{"value": "claude-haiku-4-5"}'

# 期待するレスポンス:
# {
#   "id": 1,
#   "project": "default_project",
#   "path": "CHAT_CLARIFICATION_MODEL",
#   "value": "claude-haiku-4-5",
#   "version": 2,
#   ...
# }
```

### Step 4: キャッシュリロードAPI

```bash
# expertAgentキャッシュリロード
curl -s -X POST http://localhost:8004/aiagent-api/v1/admin/reload-secrets \
  -H "X-Admin-Token: ${EXPERTAGENT_ADMIN_TOKEN}"

# 期待するレスポンス:
# {"status": "ok", "message": "Secrets cache reloaded"}

# graphAiServerキャッシュリロード（将来対応）
curl -s -X POST http://localhost:8005/api/v1/admin/reload-secrets \
  -H "X-Admin-Token: ${GRAPHAISERVER_ADMIN_TOKEN}"
```

### Step 5: expertAgentでのモデル設定適用確認

```bash
# 要件定義チャットAPIを呼び出し、使用モデルを確認
# （Langfuseでトレースを確認、またはログで確認）
curl -s -X POST http://localhost:8004/aiagent-api/v1/chat/requirement-definition \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-model-config",
    "user_message": "テスト",
    "context": {
      "previous_messages": [],
      "current_requirements": {}
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Response received: {\"messages\" in d}')"

# Langfuseでトレース確認
echo "Langfuse URL: http://localhost:3001"
echo "モデル名が 'claude-haiku-4-5' になっていることを確認"
```

### Step 6: 設定を元に戻す

```bash
# 設定を元に戻す（CHAT_CLARIFICATION_MODELをgemini-2.0-flashに）
curl -s -X PATCH http://localhost:8003/api/secrets/default_project/CHAT_CLARIFICATION_MODEL \
  -H "Content-Type: application/json" \
  -H "X-Service: commonui" \
  -H "X-Token: ${MYVAULT_TOKEN_COMMONUI}" \
  -d '{"value": "gemini-2.0-flash"}'

# キャッシュリロード
curl -s -X POST http://localhost:8004/aiagent-api/v1/admin/reload-secrets \
  -H "X-Admin-Token: ${EXPERTAGENT_ADMIN_TOKEN}"
```

### Step 7: エビデンス収集

```bash
# レスポンスをファイルに保存
curl -s http://localhost:8003/api/secrets?project=default_project \
  -H "X-Service: commonui" \
  -H "X-Token: ${MYVAULT_TOKEN_COMMONUI}" > /tmp/model_settings_list.json

# サービスログ確認
docker logs myswiftagent-expertagent 2>&1 | tail -50 | grep -E "(model|config|secret)" || echo "No relevant logs"

echo "✅ L3受入テスト完了"
```

---

## Definition of Done

Issue完了条件：
- [ ] すべてのタスク（Phase 1-4）が完了
- [ ] 単体テストカバレッジ90%以上（expertAgent, commonUI）
- [ ] 結合テストカバレッジ50%以上
- [ ] **L3受入テスト全パス**（実際のサービス起動・API呼び出し確認）
- [ ] 静的解析エラーゼロ（Ruff, MyPy）
- [ ] `./scripts/pre-push-check-all.sh` パス
- [ ] CI/CDグリーン
- [ ] コードレビュー承認
- [ ] ドキュメント更新完了

---

## 次のアクション

作業計画承認後：
1. **ブランチ作成**: `feature/issue/269`
2. **worktree作成**: `./scripts/worktree-create-from-issue.sh 269 feature`
3. **タスク実行**: 計画に従って実装
4. **進捗報告**: 必要に応じて `/progress-report` で定期報告

---

*作成日: 2025-12-11*
*Issue: #269*
*ステータス: 承認待ち*
