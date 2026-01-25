# myAgentDesk以外の必要機能洗い出し

**Issue**: #120
**作成日**: 2025-01-30
**ブランチ**: feature/issue/120

---

## 📋 概要

myAgentDeskドメインエキスパート向けUI実装に必要な、他システムの追加・改修機能を洗い出します。

**レビューフィードバック反映**:
- ✅ 認証機能: 将来実装（Phase 1-5では不要）
- ✅ Marp Viewer: オプション1（Marp CLI + iframe）
- ✅ ワークフローエディタ: Svelte Flow
- ✅ 評価データ保存先: **新規テーブル作成**
- ✅ 版数管理: **Git-like方式**

---

## 🏗️ システム別必要機能一覧

### 1. expertAgent (Backend - FastAPI)

#### 既存機能（利用可能）

| API | エンドポイント | 用途 | 状態 |
|-----|-------------|------|------|
| Job Generator | `/aiagent-api/v1/job-generator` | ジョブ作成 | ✅ 既存 |
| Marp Report | `/aiagent-api/v1/marp-report` | スライド生成 | ✅ 既存 |

#### 必要な新規機能

##### 1.1 チャット対話API（ストリーミング対応）- Phase 1

**目的**: 自然言語でのジョブ要件定義を対話的に実施

**仕様**:
```python
# POST /aiagent-api/v1/chat/requirement-definition
# Content-Type: text/event-stream (SSE)

Request:
{
  "conversation_id": "uuid-string",  # 会話セッションID
  "user_message": "売上データを分析したい",
  "context": {
    "previous_messages": [...],  # 対話履歴
    "current_requirements": {}   # 現在明確化された要件
  }
}

Response (SSE):
data: {"type": "message", "content": "どのような形式の売上データですか？"}
data: {"type": "message", "content": "CSV、Excel、データベースなど..."}
data: {"type": "clarification", "field": "data_source", "question": "..."}
data: {"type": "requirement_update", "requirements": {...}}
data: {"type": "done"}
```

**実装場所**: `expertAgent/app/api/v1/chat_endpoints.py`

**依存関係**:
- LLM API（Gemini/Claude）のストリーミング対応
- 要件明確化プロンプトテンプレート（新規作成）
- 会話履歴管理（セッション管理）

**工数**: 6-8時間

---

##### 1.2 評価フィードバックAPI - Phase 3

**目的**: 人間の評価データを受け取り、タスク改善を実行

**仕様**:
```python
# POST /aiagent-api/v1/feedback/submit

Request:
{
  "job_id": "job_12345",
  "task_id": "task_001",
  "evaluation": "bad",  # "good" | "bad"
  "feedback_type": ["speed", "accuracy", "output_format"],
  "comment": "出力形式が期待と異なる",
  "timestamp": "2025-01-30T10:00:00Z"
}

Response:
{
  "feedback_id": "fb_12345",
  "improvement_triggered": true,
  "estimated_time": "2-3分"
}
```

**実装場所**: `expertAgent/app/api/v1/feedback_endpoints.py`

**依存関係**:
- jobqueue評価データテーブル（新規）
- タスク改善ロジック（新規LangGraphノード）

**工数**: 8-10時間

---

##### 1.3 タスク自動改善API - Phase 3

**目的**: 低評価タスクを自動で再生成・改善

**仕様**:
```python
# POST /aiagent-api/v1/tasks/improve

Request:
{
  "task_id": "task_001",
  "feedback_summary": {
    "bad_count": 5,
    "common_issues": ["速度が遅い", "出力形式不適切"],
    "recent_feedbacks": [...]
  }
}

Response:
{
  "improved_task_id": "task_001_v2",
  "changes": {
    "interface_schema": {...},
    "workflow_config": {...}
  },
  "improvement_summary": "出力形式を修正し、処理速度を改善"
}
```

**実装場所**: `expertAgent/aiagent/langgraph/taskImprovementAgents/`

**実装方針**:
- 新規LangGraphワークフロー作成
- 評価データ分析ノード
- タスク再生成ノード
- A/Bテスト機能（オプション）

**工数**: 12-16時間

---

### 2. graphAiServer (Backend - FastAPI)

#### 既存機能（確認が必要）

| 機能 | API候補 | 状態 |
|------|---------|------|
| Workflow実行 | `/graphai/execute` | ✅ 既存（推定） |
| Workflow一覧取得 | `/graphai/workflows` | ❓ 確認必要 |
| Workflow YAML取得 | `/graphai/workflows/{id}` | ❓ 確認必要 |

#### 必要な新規・改修機能

##### 2.1 Workflow CRUD API - Phase 4

**目的**: ワークフローエディタからの作成・更新・削除

**仕様**:
```python
# GET /graphai/v1/workflows
Response: [{"id": "wf_001", "name": "企業分析", "version": "1.0.0", ...}]

# GET /graphai/v1/workflows/{workflow_id}
Response: {"id": "wf_001", "yaml_content": "...", "metadata": {...}}

# POST /graphai/v1/workflows
Request: {"name": "新規ワークフロー", "yaml_content": "...", "description": "..."}
Response: {"id": "wf_new", "status": "created"}

# PUT /graphai/v1/workflows/{workflow_id}
Request: {"yaml_content": "...", "commit_message": "ノード追加"}
Response: {"version": "1.0.1", "status": "updated"}

# DELETE /graphai/v1/workflows/{workflow_id}
Response: {"status": "deleted"}
```

**実装場所**: `graphAiServer/app/api/v1/workflow_endpoints.py`

**工数**: 6-8時間

---

##### 2.2 Workflow バリデーションAPI - Phase 4

**目的**: ユーザー編集したワークフローの妥当性検証

**仕様**:
```python
# POST /graphai/v1/workflows/validate

Request:
{
  "yaml_content": "...",
  "strict_mode": true  # GRAPHAI_WORKFLOW_GENERATION_RULES.md 準拠チェック
}

Response:
{
  "is_valid": false,
  "errors": [
    {
      "type": "circular_dependency",
      "nodes": ["node1", "node3"],
      "message": "循環依存が検出されました"
    },
    {
      "type": "missing_parameter",
      "node": "node2",
      "parameter": "prompt",
      "message": "必須パラメータが不足しています"
    }
  ],
  "warnings": [
    {
      "type": "performance",
      "message": "ノード数が多すぎます（50ノード以上）"
    }
  ]
}
```

**バリデーション項目**:
- ✅ 循環依存の検出
- ✅ 必須パラメータのチェック
- ✅ GraphAI YAMLスキーマ準拠
- ✅ ノード数制限（推奨100ノード以内）
- ✅ GRAPHAI_WORKFLOW_GENERATION_RULES.md ルール適合

**実装場所**: `graphAiServer/app/services/workflow_validator.py`

**工数**: 8-10時間

---

##### 2.3 Workflow YAML ⇔ JSON 変換API - Phase 4

**目的**: フロントエンド（Svelte Flow）用のJSON形式と内部YAML形式の相互変換

**仕様**:
```python
# POST /graphai/v1/workflows/yaml-to-json
Request: {"yaml_content": "..."}
Response: {
  "nodes": [
    {"id": "node1", "type": "llm", "data": {...}, "position": {"x": 0, "y": 0}},
    ...
  ],
  "edges": [
    {"id": "edge1", "source": "node1", "target": "node2", "type": "default"},
    ...
  ]
}

# POST /graphai/v1/workflows/json-to-yaml
Request: {"nodes": [...], "edges": [...]}
Response: {"yaml_content": "..."}
```

**変換ルール**:
- GraphAI YAMLノード → Svelte Flowノード
- 依存関係（`:node_id`） → Svelte Flowエッジ
- ノード座標の保存・復元（metadata内）

**実装場所**: `graphAiServer/app/services/workflow_converter.py`

**工数**: 6-8時間

---

### 3. jobqueue (Backend - FastAPI)

#### 既存機能（利用可能）

| API | 用途 | 状態 |
|-----|------|------|
| Job/Task CRUD | ジョブ管理 | ✅ 既存 |
| Job実行履歴 | 実行状況確認 | ✅ 既存 |

#### 必要な新規機能

##### 3.1 評価データ管理API - Phase 3

**目的**: タスク実行結果への人間評価を保存・取得

**データベーススキーマ**:
```sql
-- 新規テーブル: task_evaluations
CREATE TABLE task_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id),
    task_id UUID NOT NULL REFERENCES tasks(id),
    evaluation VARCHAR(10) NOT NULL CHECK (evaluation IN ('good', 'bad')),
    feedback_types TEXT[],  -- ["speed", "accuracy", "output_format"]
    comment TEXT,
    evaluated_by VARCHAR(255),  -- 将来の認証機能用
    evaluated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_task_evaluations_task_id (task_id),
    INDEX idx_task_evaluations_evaluated_at (evaluated_at)
);

-- 評価統計ビュー
CREATE VIEW task_evaluation_stats AS
SELECT
    task_id,
    COUNT(*) as total_evaluations,
    SUM(CASE WHEN evaluation = 'good' THEN 1 ELSE 0 END) as good_count,
    SUM(CASE WHEN evaluation = 'bad' THEN 1 ELSE 0 END) as bad_count,
    ROUND(SUM(CASE WHEN evaluation = 'good' THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric * 100, 2) as good_rate
FROM task_evaluations
GROUP BY task_id;
```

**API仕様**:
```python
# POST /jobqueue/v1/evaluations
Request: {
  "job_id": "job_12345",
  "task_id": "task_001",
  "evaluation": "bad",
  "feedback_types": ["speed", "accuracy"],
  "comment": "処理が遅い"
}
Response: {"evaluation_id": "eval_001", "status": "saved"}

# GET /jobqueue/v1/evaluations/task/{task_id}
Response: {
  "task_id": "task_001",
  "evaluations": [...],
  "stats": {"total": 10, "good": 3, "bad": 7, "good_rate": 30.0}
}

# GET /jobqueue/v1/evaluations/task/{task_id}/summary
Response: {
  "common_issues": ["速度が遅い", "出力形式不適切"],
  "improvement_needed": true,
  "priority": "high"
}
```

**実装場所**:
- `jobqueue/app/models/task_evaluation.py`
- `jobqueue/app/schemas/evaluation.py`
- `jobqueue/app/api/v1/evaluation_endpoints.py`

**工数**: 8-10時間

---

##### 3.2 Git-like版数管理機能 - Phase 5

**目的**: タスク/ワークフロー定義の変更履歴をGit-likeに管理

**データベーススキーマ**:
```sql
-- 新規テーブル: version_commits
CREATE TABLE version_commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('task', 'workflow', 'job')),
    entity_id UUID NOT NULL,
    commit_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256ハッシュ
    parent_commit_hash VARCHAR(64),  -- 親コミット
    commit_message TEXT NOT NULL,
    author VARCHAR(255),  -- 将来の認証機能用
    committed_at TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_version_commits_entity (entity_type, entity_id),
    INDEX idx_version_commits_hash (commit_hash)
);

-- 新規テーブル: version_snapshots
CREATE TABLE version_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_hash VARCHAR(64) NOT NULL REFERENCES version_commits(commit_hash),
    content JSONB NOT NULL,  -- タスク/ワークフロー定義の完全なスナップショット
    content_hash VARCHAR(64) NOT NULL,  -- 内容のSHA-256ハッシュ
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_version_snapshots_commit (commit_hash),
    INDEX idx_version_snapshots_content_hash (content_hash)
);

-- 新規テーブル: version_tags
CREATE TABLE version_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    tag_name VARCHAR(100) NOT NULL,  -- "v1.0.0", "stable"
    commit_hash VARCHAR(64) NOT NULL REFERENCES version_commits(commit_hash),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (entity_type, entity_id, tag_name),
    INDEX idx_version_tags_entity (entity_type, entity_id)
);

-- 新規テーブル: version_branches (将来拡張用)
CREATE TABLE version_branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    branch_name VARCHAR(100) NOT NULL DEFAULT 'main',
    head_commit_hash VARCHAR(64) NOT NULL REFERENCES version_commits(commit_hash),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (entity_type, entity_id, branch_name)
);
```

**API仕様**:
```python
# コミット作成
# POST /jobqueue/v1/versions/commit
Request: {
  "entity_type": "task",
  "entity_id": "task_001",
  "content": {...},  # タスク定義全体
  "commit_message": "出力形式を修正",
  "parent_commit_hash": "abc123..."  # オプション、初回はnull
}
Response: {
  "commit_hash": "def456...",
  "commit_id": "commit_001",
  "status": "committed"
}

# コミット履歴取得
# GET /jobqueue/v1/versions/{entity_type}/{entity_id}/commits
Response: {
  "commits": [
    {
      "commit_hash": "def456...",
      "parent_commit_hash": "abc123...",
      "message": "出力形式を修正",
      "author": "user@example.com",
      "committed_at": "2025-01-30T10:00:00Z"
    },
    ...
  ]
}

# 特定バージョンの取得
# GET /jobqueue/v1/versions/snapshot/{commit_hash}
Response: {
  "commit_hash": "def456...",
  "content": {...},  # タスク定義スナップショット
  "commit_message": "出力形式を修正",
  "committed_at": "2025-01-30T10:00:00Z"
}

# Diff取得
# GET /jobqueue/v1/versions/diff?from={hash1}&to={hash2}
Response: {
  "from_commit": "abc123...",
  "to_commit": "def456...",
  "diff": {
    "added": [...],
    "modified": [...],
    "removed": [...]
  },
  "diff_text": "--- a/task.json\n+++ b/task.json\n..."
}

# タグ作成
# POST /jobqueue/v1/versions/tag
Request: {
  "entity_type": "task",
  "entity_id": "task_001",
  "tag_name": "v1.0.0",
  "commit_hash": "def456...",
  "description": "初回リリース"
}
Response: {"tag_id": "tag_001", "status": "created"}

# タグ一覧
# GET /jobqueue/v1/versions/{entity_type}/{entity_id}/tags
Response: {
  "tags": [
    {"tag_name": "v1.0.0", "commit_hash": "def456...", "created_at": "..."},
    ...
  ]
}

# ロールバック
# POST /jobqueue/v1/versions/rollback
Request: {
  "entity_type": "task",
  "entity_id": "task_001",
  "target_commit_hash": "abc123...",
  "commit_message": "Rollback to v1.0.0"
}
Response: {
  "new_commit_hash": "ghi789...",
  "status": "rolled_back"
}
```

**実装場所**:
- `jobqueue/app/models/version_commit.py`
- `jobqueue/app/models/version_snapshot.py`
- `jobqueue/app/models/version_tag.py`
- `jobqueue/app/schemas/version.py`
- `jobqueue/app/api/v1/version_endpoints.py`
- `jobqueue/app/services/version_control.py` (Git-likeロジック)

**実装機能**:
- ✅ コミット作成・履歴管理
- ✅ スナップショット保存
- ✅ タグ管理（v1.0.0形式）
- ✅ Diff生成（JSON diff）
- ✅ ロールバック
- ⏳ ブランチ管理（将来拡張）

**工数**: 16-20時間

---

### 4. myScheduler (Backend - FastAPI)

#### 既存機能（確認が必要）

| 機能 | API候補 | 状態 |
|------|---------|------|
| スケジュール登録 | `/scheduler/v1/schedules` | ❓ 確認必要 |
| スケジュール一覧 | `/scheduler/v1/schedules` | ❓ 確認必要 |
| 実行履歴 | `/scheduler/v1/executions` | ❓ 確認必要 |

#### 必要な新規・改修機能

##### 4.1 スケジュール管理API拡張 - Phase 2

**目的**: myAgentDeskからのスケジュール登録・管理

**必要なAPI**:
```python
# スケジュール登録
# POST /scheduler/v1/schedules
Request: {
  "job_id": "job_12345",
  "schedule_type": "cron",  # "cron" | "interval" | "one_time"
  "cron_expression": "0 9 * * MON-FRI",  # 平日9時
  "timezone": "Asia/Tokyo",
  "enabled": true,
  "metadata": {
    "created_by": "myAgentDesk",
    "job_name": "売上レポート生成"
  }
}
Response: {
  "schedule_id": "sch_001",
  "next_run_at": "2025-01-31T09:00:00+09:00",
  "status": "active"
}

# スケジュール一覧
# GET /scheduler/v1/schedules?job_id={job_id}
Response: {
  "schedules": [
    {
      "schedule_id": "sch_001",
      "job_id": "job_12345",
      "cron_expression": "0 9 * * MON-FRI",
      "next_run_at": "2025-01-31T09:00:00+09:00",
      "enabled": true,
      "created_at": "2025-01-30T10:00:00Z"
    },
    ...
  ]
}

# スケジュール更新
# PUT /scheduler/v1/schedules/{schedule_id}
Request: {
  "cron_expression": "0 10 * * MON-FRI",  # 10時に変更
  "enabled": true
}
Response: {
  "schedule_id": "sch_001",
  "next_run_at": "2025-01-31T10:00:00+09:00",
  "status": "updated"
}

# スケジュール削除
# DELETE /scheduler/v1/schedules/{schedule_id}
Response: {"status": "deleted"}

# 実行履歴
# GET /scheduler/v1/executions?schedule_id={schedule_id}&limit=10
Response: {
  "executions": [
    {
      "execution_id": "exec_001",
      "schedule_id": "sch_001",
      "executed_at": "2025-01-30T09:00:00+09:00",
      "status": "success",
      "duration_ms": 1234
    },
    ...
  ]
}
```

**確認事項**:
- mySchedulerに上記APIが既に存在するか確認
- 存在しない場合は新規実装が必要

**実装場所（新規の場合）**:
- `myScheduler/app/api/v1/schedule_endpoints.py`
- `myScheduler/app/services/schedule_service.py`

**工数**: 6-8時間（新規実装の場合）/ 2-4時間（既存API確認・修正のみの場合）

---

## 📊 実装優先度マトリクス

### Phase 1実装に必要（必須）

| システム | 機能 | 工数 | 優先度 |
|---------|------|------|--------|
| expertAgent | チャット対話API（ストリーミング） | 6-8h | 🔴 必須 |

**Phase 1合計工数**: 6-8時間

---

### Phase 2実装に必要（必須）

| システム | 機能 | 工数 | 優先度 |
|---------|------|------|--------|
| myScheduler | スケジュール管理API | 2-8h | 🔴 必須 |

**Phase 2合計工数**: 2-8時間

---

### Phase 3実装に必要（必須）

| システム | 機能 | 工数 | 優先度 |
|---------|------|------|--------|
| jobqueue | 評価データ管理API | 8-10h | 🔴 必須 |
| expertAgent | 評価フィードバックAPI | 8-10h | 🔴 必須 |
| expertAgent | タスク自動改善API | 12-16h | 🔴 必須 |

**Phase 3合計工数**: 28-36時間

---

### Phase 4実装に必要（必須）

| システム | 機能 | 工数 | 優先度 |
|---------|------|------|--------|
| graphAiServer | Workflow CRUD API | 6-8h | 🔴 必須 |
| graphAiServer | Workflow バリデーションAPI | 8-10h | 🔴 必須 |
| graphAiServer | YAML ⇔ JSON 変換API | 6-8h | 🔴 必須 |

**Phase 4合計工数**: 20-26時間

---

### Phase 5実装に必要（必須）

| システム | 機能 | 工数 | 優先度 |
|---------|------|------|--------|
| jobqueue | Git-like版数管理機能 | 16-20h | 🔴 必須 |

**Phase 5合計工数**: 16-20時間

---

## 🎯 全体工数サマリー

### システム別工数

| システム | 機能数 | 合計工数 |
|---------|--------|---------|
| **expertAgent** | 3機能 | 26-34時間 |
| **graphAiServer** | 3機能 | 20-26時間 |
| **jobqueue** | 2機能 | 24-30時間 |
| **myScheduler** | 1機能 | 2-8時間 |

### Phase別工数

| Phase | myAgentDesk工数 | 外部システム工数 | 合計工数 |
|-------|----------------|----------------|---------|
| Phase 1 | 8-10h | 6-8h | 14-18h |
| Phase 2 | 6-8h | 2-8h | 8-16h |
| Phase 3 | 6-8h | 28-36h | 34-44h |
| Phase 4 | 10-12h | 20-26h | 30-38h |
| Phase 5 | 6-8h | 16-20h | 22-28h |
| **合計** | **36-46h** | **72-98h** | **108-144h** |

---

## 🚨 リスクと対策

### リスク1: expertAgent改善ロジックの複雑さ

**リスク内容**: タスク自動改善（Phase 3）は新規LangGraphワークフローが必要で、工数が膨らむ可能性

**対策**:
1. **Phase 3を2段階に分割**:
   - Phase 3-1: 評価データ収集のみ（myAgentDesk + jobqueue）
   - Phase 3-2: 自動改善ロジック（expertAgent）
2. **MVPアプローチ**: 最初は単純な再生成のみ、段階的に高度化

---

### リスク2: graphAiServer既存APIの不明点

**リスク内容**: graphAiServerのCRUD APIが存在するか不明

**対策**:
1. **Phase 4開始前に既存API調査**
2. **既存APIがない場合**: graphAiServer側の実装を先行実施
3. **代替案**: 一時的にファイルシステムベースでワークフローを管理

---

### リスク3: jobqueue版数管理の実装コスト

**リスク内容**: Git-like版数管理は複雑で、工数が見積もりを超える可能性

**対策**:
1. **Phase 5を低優先度とする**: 他Phase完了後に着手
2. **外部ライブラリ検討**: PostgreSQLのtemporal table機能を活用
3. **MVPアプローチ**: 最初はコミット・スナップショットのみ、タグ・ブランチは将来実装

---

## 📋 確認事項チェックリスト

### myScheduler既存API確認

- [ ] **スケジュール登録API**: `POST /scheduler/v1/schedules` が存在するか
- [ ] **スケジュール一覧API**: `GET /scheduler/v1/schedules` が存在するか
- [ ] **実行履歴API**: `GET /scheduler/v1/executions` が存在するか
- [ ] **Cron式パース機能**: Cron式のバリデーションが実装されているか
- [ ] **タイムゾーン対応**: ジョブ実行時のタイムゾーン設定が可能か

### graphAiServer既存API確認

- [ ] **Workflow一覧取得**: `GET /graphai/workflows` が存在するか
- [ ] **Workflow取得**: `GET /graphai/workflows/{id}` が存在するか
- [ ] **Workflow作成**: `POST /graphai/workflows` が存在するか
- [ ] **Workflow更新**: `PUT /graphai/workflows/{id}` が存在するか
- [ ] **Workflow削除**: `DELETE /graphai/workflows/{id}` が存在するか
- [ ] **YAMLスキーマバリデーション**: GraphAI YAML検証機能が存在するか

---

## 🔄 実装推奨順序

### ステップ1: Phase 1実装前

1. ✅ expertAgent: チャット対話API実装（6-8h）
2. ✅ expertAgent: 要件明確化プロンプトテンプレート作成（2-4h）

**合計**: 8-12時間

---

### ステップ2: Phase 2実装前

1. ✅ myScheduler: 既存API調査（1-2h）
2. ✅ myScheduler: スケジュール管理API実装（必要な場合）（6-8h）

**合計**: 1-10時間

---

### ステップ3: Phase 3実装前

1. ✅ jobqueue: 評価データテーブル作成（2-3h）
2. ✅ jobqueue: 評価データ管理API実装（6-7h）
3. ✅ expertAgent: 評価フィードバックAPI実装（8-10h）
4. ✅ expertAgent: タスク自動改善LangGraphワークフロー実装（12-16h）

**合計**: 28-36時間

---

### ステップ4: Phase 4実装前

1. ✅ graphAiServer: 既存API調査（1-2h）
2. ✅ graphAiServer: Workflow CRUD API実装（6-8h）
3. ✅ graphAiServer: バリデーションAPI実装（8-10h）
4. ✅ graphAiServer: YAML ⇔ JSON変換API実装（6-8h）

**合計**: 21-28時間

---

### ステップ5: Phase 5実装前

1. ✅ jobqueue: 版数管理テーブル設計・作成（3-4h）
2. ✅ jobqueue: Git-likeロジック実装（10-12h）
3. ✅ jobqueue: 版数管理API実装（3-4h）

**合計**: 16-20時間

---

## 📚 参考資料

### expertAgent関連

- **既存API**: `expertAgent/app/api/v1/`
- **LangGraphワークフロー**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/`
- **プロンプトテンプレート**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/`

### graphAiServer関連

- **GRAPHAI_WORKFLOW_GENERATION_RULES.md**: ワークフロー設計ルール
- **既存ワークフロー**: `graphAiServer/config/graphai/`

### jobqueue関連

- **既存モデル**: `jobqueue/app/models/`
- **既存スキーマ**: `jobqueue/app/schemas/`
- **既存API**: `jobqueue/app/api/v1/`

### myScheduler関連

- **既存API**: `myScheduler/app/api/v1/` （要確認）

---

## 🔄 次のステップ

1. **外部依存機能洗い出しレビュー** ← 今ここ
2. **設計方針策定** (`design-policy.md` 作成)
3. **作業計画立案** (`work-plan.md` 作成)
4. **Phase 1実装開始**

---

**この洗い出しについてレビューをお願いします。追加・修正があればお知らせください。**
