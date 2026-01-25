# 設計方針書: LLMモデル設定のmyVault管理とcommonUI設定画面

## 現状調査サマリ

### 対象プロジェクト
- **expertAgent**: モデル設定の使用箇所（8箇所、6ファイル）
- **myVault**: シークレット管理API（既存機能を活用）
- **commonUI**: 設定管理UI（既存MyVault画面を拡張）

### 既存アーキテクチャパターン

| パターン | 使用箇所 | 目的 | 本実装での活用 |
|---------|---------|------|---------------|
| Singleton | `secrets_manager` | グローバルインスタンス | そのまま活用 |
| Factory | `create_llm_with_fallback()` | プロバイダ別LLM生成 | モデル名取得部分を修正 |
| Strategy | `HTTPClient` | サービス別認証方式 | そのまま活用 |
| Cache with TTL | `SecretsManager._cache` | パフォーマンス最適化 | キャッシュリロード連携 |

### 類似機能の設計

| 機能 | 設計概要 | 参考にする点 |
|------|---------|-------------|
| `secrets_manager.get_secret()` | MyVault優先→環境変数フォールバック | フォールバックパターン |
| `commonUI/pages/3_🔐_MyVault.py` | タブ構成、CRUD操作、キャッシュリロード | UI構成、API呼び出しパターン |
| `invoke_structured_llm()` | 統一的なLLM呼び出し（行177: `os.getenv()`） | 修正対象箇所 |

### モジュール間依存関係

```
┌─────────────────────────────────────────────────────────────────┐
│                         commonUI                                 │
│  pages/3_🔐_MyVault.py (モデル設定タブ追加)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ PATCH /api/secrets/{project}/{path}
                            │ POST /v1/admin/reload-secrets
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         myVault                                  │
│  /api/secrets (既存APIをそのまま使用)                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │ GET /api/secrets/{project}/{path}
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       expertAgent                                │
│  core/secrets.py → SecretsManager.get_secret()                  │
│  ↓                                                               │
│  aiagent/.../llm_invocation.py → invoke_structured_llm()        │
│  ↓                                                               │
│  各ノード (requirement_analysis, evaluator, etc.)               │
└─────────────────────────────────────────────────────────────────┘
```

### 既存API設計パターン

| 項目 | パターン |
|------|---------|
| エンドポイント命名規則 | `/api/secrets/{project}/{path}` (RESTful) |
| レスポンス形式 | `{"id":1,"project":"...","path":"...","value":"..."}` |
| エラーハンドリング | HTTPException (400, 401, 403, 404, 500) |
| 認証 | X-Service + X-Token ヘッダー |

### 設計上の制約
1. **後方互換性**: 環境変数フォールバックを維持
2. **キャッシュ**: TTL=300秒、手動リロード対応
3. **モデル制限**: Claude/GPT/Geminiのみ（Ollamaは将来対応）

---

## アーキテクチャ設計

### システム構成図

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              commonUI (Streamlit)                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  pages/3_🔐_MyVault.py                                           │   │
│  │  ├── Projects Tab (既存)                                         │   │
│  │  ├── Secrets Tab (既存)                                          │   │
│  │  ├── **Model Settings Tab** (新規)  ←─────────────────────────   │   │
│  │  │   └── ModelSettingsSection                                    │   │
│  │  │       ├── load_model_settings()                               │   │
│  │  │       ├── render_model_dropdown()                             │   │
│  │  │       └── save_model_setting()                                │   │
│  │  └── Cache Reload Tab (既存)                                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │    HTTPClient         │
                    │  (components/)        │
                    └───────────┬───────────┘
                                │ REST API
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────────────┐
│   myVault    │      │ expertAgent  │      │   graphAiServer      │
│   :8003      │      │   :8004      │      │      :8005           │
│              │      │              │      │                      │
│ /api/secrets │      │ /v1/admin/   │      │ /api/v1/admin/       │
│              │      │ reload-      │      │ reload-secrets       │
│              │      │ secrets      │      │                      │
└──────────────┘      └──────┬───────┘      └──────────────────────┘
                             │
                    ┌────────┴────────┐
                    │ SecretsManager  │
                    │ (core/secrets)  │
                    └────────┬────────┘
                             │ get_secret()
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│llm_invocation│    │ llm_service  │    │ candidate_   │
│    .py       │    │    .py       │    │ generator.py │
└──────────────┘    └──────────────┘    └──────────────┘
```

### レイヤー構成

| レイヤー | コンポーネント | 責務 |
|---------|---------------|------|
| **Presentation** | commonUI/pages/3_🔐_MyVault.py | モデル設定UIの表示・操作 |
| **Business Logic** | expertAgent/core/secrets.py | モデル設定取得ロジック |
| **Data Access** | myVault API | シークレットのCRUD |
| **Infrastructure** | myVault/data/myvault.db | 暗号化SQLiteストレージ |

---

## 技術選定

| カテゴリ | 選定技術 | 選定理由 | 既存との整合性 |
|---------|---------|---------|---------------|
| シークレット管理 | myVault API | 既存インフラ活用、監査証跡 | 完全互換 |
| UI | Streamlit Tab | 既存MyVault画面の拡張 | 完全互換 |
| 設定取得 | SecretsManager | 既存パターン活用 | 完全互換 |
| キャッシュ | TTL Cache + 手動リロード | 既存機構活用 | 完全互換 |

**新規技術導入なし** - 全て既存技術スタックを活用

---

## 設計パターン

### 採用パターン（全て既存パターンを踏襲）

| パターン | 適用箇所 | 理由 |
|---------|---------|------|
| **Singleton** | `secrets_manager` | グローバルインスタンスとして既存活用 |
| **Strategy** | HTTPClient認証 | サービス別認証方式の切り替え |
| **Cache-Aside** | SecretsManager._cache | TTL付きキャッシュで性能最適化 |
| **Fallback** | MyVault → 環境変数 | 可用性確保 |

### 新規パターン導入
**なし** - 既存パターンで全要件を満たせる

---

## データモデル設計

### myVaultシークレット構造

myVaultの既存スキーマをそのまま使用（新規テーブル追加なし）：

```
secrets テーブル（既存）
├── id: INTEGER PRIMARY KEY
├── project: TEXT NOT NULL
├── path: TEXT NOT NULL (モデル設定キー名)
├── value: TEXT NOT NULL (モデル名)
├── version: INTEGER DEFAULT 1
├── created_at: TIMESTAMP
├── updated_at: TIMESTAMP
└── UNIQUE(project, path)
```

### モデル設定のシークレット定義

| project | path | value (デフォルト) |
|---------|------|-------------------|
| default_project | CHAT_CLARIFICATION_MODEL | gemini-2.0-flash |
| default_project | CANDIDATE_GENERATION_MODEL | gemini-2.0-flash |
| default_project | REQUIREMENT_EXTRACTION_MODEL | gemini-2.0-flash |
| default_project | JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL | claude-haiku-4-5 |
| default_project | JOB_GENERATOR_EVALUATOR_MODEL | claude-haiku-4-5 |
| default_project | JOB_GENERATOR_INTERFACE_DEFINITION_MODEL | claude-haiku-4-5 |
| default_project | JOB_GENERATOR_VALIDATION_MODEL | claude-haiku-4-5 |
| default_project | WORKFLOW_GENERATOR_MODEL | gemini-2.0-flash-exp |

### 利用可能モデル定義（commonUI用）

**ファイル**: `commonUI/config/available_models.yaml`（新規作成）

```yaml
# LLMモデル設定で選択可能なモデル一覧
# プロバイダごとにグループ化

models:
  anthropic:
    display_name: "Anthropic (Claude)"
    models:
      - id: "claude-haiku-4-5"
        name: "Claude Haiku 4.5"
        description: "高速・低コスト"
      - id: "claude-sonnet-4-20250514"
        name: "Claude Sonnet 4"
        description: "バランス型"
      - id: "claude-opus-4-20250514"
        name: "Claude Opus 4"
        description: "高性能"

  openai:
    display_name: "OpenAI (GPT)"
    models:
      - id: "gpt-4o-mini"
        name: "GPT-4o Mini"
        description: "高速・低コスト"
      - id: "gpt-4o"
        name: "GPT-4o"
        description: "バランス型"
      - id: "gpt-4-turbo"
        name: "GPT-4 Turbo"
        description: "高性能"

  google:
    display_name: "Google (Gemini)"
    models:
      - id: "gemini-2.0-flash"
        name: "Gemini 2.0 Flash"
        description: "高速・低コスト"
      - id: "gemini-2.0-flash-exp"
        name: "Gemini 2.0 Flash (Experimental)"
        description: "実験版"
      - id: "gemini-2.5-flash"
        name: "Gemini 2.5 Flash"
        description: "最新Flash"
      - id: "gemini-2.5-pro"
        name: "Gemini 2.5 Pro"
        description: "高性能"

# モデル設定のカテゴリ定義
settings:
  chat:
    display_name: "チャット設定"
    settings:
      - key: "CHAT_CLARIFICATION_MODEL"
        name: "要件定義チャット"
        description: "ユーザーとの対話による要件明確化"
        default: "gemini-2.0-flash"
      - key: "CANDIDATE_GENERATION_MODEL"
        name: "候補生成"
        description: "要件候補の生成"
        default: "gemini-2.0-flash"
      - key: "REQUIREMENT_EXTRACTION_MODEL"
        name: "要件抽出"
        description: "会話からの要件抽出"
        default: "gemini-2.0-flash"

  job_generator:
    display_name: "Job Generator設定"
    settings:
      - key: "JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL"
        name: "要件分析"
        description: "タスク分解のための要件分析"
        default: "claude-haiku-4-5"
      - key: "JOB_GENERATOR_EVALUATOR_MODEL"
        name: "評価"
        description: "タスク分解の品質評価"
        default: "claude-haiku-4-5"
      - key: "JOB_GENERATOR_INTERFACE_DEFINITION_MODEL"
        name: "インターフェース定義"
        description: "タスクI/OのJSON Schema生成"
        default: "claude-haiku-4-5"
      - key: "JOB_GENERATOR_VALIDATION_MODEL"
        name: "バリデーション"
        description: "ワークフロー検証と修正提案"
        default: "claude-haiku-4-5"

  workflow:
    display_name: "ワークフロー設定"
    settings:
      - key: "WORKFLOW_GENERATOR_MODEL"
        name: "ワークフロー生成"
        description: "GraphAIワークフローYAML生成"
        default: "gemini-2.0-flash-exp"
```

---

## API設計

### 使用API（既存APIをそのまま使用）

| 操作 | メソッド | エンドポイント | 用途 |
|------|---------|---------------|------|
| 設定取得 | GET | `/api/secrets/{project}/{path}` | モデル設定値の取得 |
| 設定更新 | PATCH | `/api/secrets/{project}/{path}` | モデル設定値の更新 |
| 設定作成 | POST | `/api/secrets` | 初回登録 |
| キャッシュリロード | POST | `/v1/admin/reload-secrets` | expertAgent |
| キャッシュリロード | POST | `/api/v1/admin/reload-secrets` | graphAiServer |

### リクエスト/レスポンス形式（既存形式を踏襲）

**設定取得**:
```http
GET /api/secrets/default_project/CHAT_CLARIFICATION_MODEL
X-Service: commonui
X-Token: {service_token}

Response:
{
  "id": 1,
  "project": "default_project",
  "path": "CHAT_CLARIFICATION_MODEL",
  "value": "gemini-2.0-flash",
  "version": 1,
  "created_at": "2025-12-11T00:00:00Z",
  "updated_at": "2025-12-11T00:00:00Z"
}
```

**設定更新**:
```http
PATCH /api/secrets/default_project/CHAT_CLARIFICATION_MODEL
X-Service: commonui
X-Token: {service_token}
Content-Type: application/json

{
  "value": "claude-haiku-4-5"
}

Response:
{
  "id": 1,
  "project": "default_project",
  "path": "CHAT_CLARIFICATION_MODEL",
  "value": "claude-haiku-4-5",
  "version": 2,
  ...
}
```

### エラーハンドリング（既存パターン踏襲）

| ステータス | 条件 | レスポンス |
|-----------|------|-----------|
| 400 | 不正なリクエスト | `{"detail": "Invalid request"}` |
| 401 | 認証失敗 | `{"detail": "Invalid service token"}` |
| 403 | 権限不足 | `{"detail": "Permission denied"}` |
| 404 | 設定未登録 | `{"detail": "Secret not found"}` |
| 500 | サーバーエラー | `{"detail": "Internal server error"}` |

---

## セキュリティ設計

### 認証・認可（既存方式を踏襲）

| サービス | 権限 | 用途 |
|---------|------|------|
| commonui | read, write, list | モデル設定の表示・編集 |
| expertagent | read, list | モデル設定の取得 |
| graphaiserver | read, list | モデル設定の取得（将来対応） |

### 入力検証

**モデル名バリデーション**:
- ドロップダウン選択による入力制限
- 許可リスト（`available_models.yaml`）との照合
- 正規表現: `^[a-z0-9\-\.]+$`（英小文字、数字、ハイフン、ドット）

---

## パフォーマンス設計

### キャッシング戦略（既存機構を活用）

```python
# SecretsManager._cache 構造
{
    "default_project": {
        "CHAT_CLARIFICATION_MODEL": ("gemini-2.0-flash", 1702300800.0),
        "CANDIDATE_GENERATION_MODEL": ("gemini-2.0-flash", 1702300800.0),
        ...
    }
}
```

| パラメータ | 値 | 設定箇所 |
|-----------|-----|---------|
| Cache TTL | 300秒（5分） | `SECRETS_CACHE_TTL` |
| 手動リロード | `/v1/admin/reload-secrets` | 既存API |

### パフォーマンス目標

| 操作 | 目標 | 実現方法 |
|------|------|---------|
| 設定取得（キャッシュヒット） | < 10ms | インメモリキャッシュ |
| 設定取得（キャッシュミス） | < 100ms | myVault API呼び出し |
| 設定画面表示 | < 2秒 | 8設定を並列取得 |
| キャッシュリロード | < 5秒 | HTTP POST |

---

## 実装詳細設計

### Phase 2: expertAgent側の修正

**修正方針**: `os.getenv()` → `secrets_manager.get_secret()` へ変更

#### 修正箇所1: llm_invocation.py (統一インターフェース)

```python
# 変更前 (行177)
model_name = os.getenv(model_env_var, default_model)

# 変更後
from core.secrets import secrets_manager

def _get_model_name(model_env_var: str, default_model: str) -> str:
    """モデル名を取得（MyVault優先、環境変数フォールバック）"""
    try:
        return secrets_manager.get_secret(model_env_var)
    except ValueError:
        # MyVaultに未登録の場合は環境変数→デフォルト値
        return os.getenv(model_env_var, default_model)

# invoke_structured_llm内で使用
model_name = _get_model_name(model_env_var, default_model)
```

#### 修正箇所2: llm_service.py (直接os.getenv使用箇所)

```python
# 変更前 (行77, 192)
model_name = os.getenv("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")

# 変更後
from core.secrets import secrets_manager

def _get_chat_model() -> str:
    """チャットモデル名を取得"""
    try:
        return secrets_manager.get_secret("CHAT_CLARIFICATION_MODEL")
    except ValueError:
        return os.getenv("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")

# 使用箇所で呼び出し
model_name = _get_chat_model()
```

### Phase 3: commonUI側の実装

**方針**: 既存の `pages/3_🔐_MyVault.py` に「モデル設定」タブを追加

```python
# pages/3_🔐_MyVault.py への追加

def render_model_settings_tab():
    """モデル設定タブをレンダリング"""
    st.subheader("LLMモデル設定")

    # カテゴリごとに表示
    for category_key, category in MODEL_SETTINGS.items():
        with st.expander(category["display_name"], expanded=True):
            for setting in category["settings"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    current_value = load_setting(setting["key"])
                    display_value = current_value or f"(未設定: {setting['default']})"

                    # ドロップダウン選択
                    selected = st.selectbox(
                        setting["name"],
                        options=get_available_models(),
                        index=get_model_index(current_value),
                        key=f"model_{setting['key']}",
                        help=setting["description"]
                    )

                with col2:
                    if st.button("保存", key=f"save_{setting['key']}"):
                        save_setting(setting["key"], selected)
                        reload_caches()
                        st.success(f"{setting['name']}を更新しました")
                        st.rerun()

# タブ構成に追加
tab1, tab2, tab3, tab4 = st.tabs([
    "Projects",
    "Secrets",
    "Model Settings",  # 新規追加
    "Cache Reload"
])
```

---

## 設計判断とトレードオフ

### 判断1: 新規API vs 既存API活用

| 選択肢 | メリット | デメリット |
|--------|---------|-----------|
| **採用: 既存API活用** | 実装コスト削減、テスト済み | なし |
| 却下: 専用API新規作成 | 専用エンドポイント | 実装・テストコスト |

**判断理由**: myVaultの既存シークレットAPIで全要件を満たせるため、新規API作成は不要

### 判断2: 設定画面の配置

| 選択肢 | メリット | デメリット |
|--------|---------|-----------|
| **採用: MyVault画面にタブ追加** | 関連機能の集約、既存UI活用 | 画面が複雑化 |
| 却下: 独立ページ新規作成 | シンプルな画面 | ナビゲーション増加 |

**判断理由**: モデル設定はシークレット管理の一種であり、MyVault画面への統合が自然

### 判断3: モデル選択UI

| 選択肢 | メリット | デメリット |
|--------|---------|-----------|
| **採用: ドロップダウン選択** | 入力エラー防止、UX向上 | 新モデル追加時にYAML更新必要 |
| 却下: 自由入力テキストボックス | 柔軟性 | 入力エラーリスク |

**判断理由**: セキュリティと運用安定性を優先し、許可リストベースのドロップダウン選択を採用

### 判断4: キャッシュ更新方式

| 選択肢 | メリット | デメリット |
|--------|---------|-----------|
| **採用: 手動リロード** | 制御性、既存API活用 | 操作が必要 |
| 却下: TTL短縮 | 自動反映 | 性能低下 |
| 却下: WebSocket通知 | リアルタイム | 実装コスト高 |

**判断理由**: 設定変更頻度が低いため、手動リロードで十分。既存APIを活用

---

## 実装チェックリスト

### Phase 1: myVault側（2時間）
- [ ] 8つのモデル設定をdefault_projectに初期登録（スクリプト作成）
- [ ] 初期値の確認

### Phase 2: expertAgent側（8時間）
- [ ] `llm_invocation.py`: `_get_model_name()` ヘルパー関数追加
- [ ] `llm_invocation.py`: `invoke_structured_llm()`の修正
- [ ] `llm_service.py`: `_get_chat_model()` ヘルパー関数追加
- [ ] `llm_service.py`: 2箇所の`os.getenv()`を置換
- [ ] `candidate_generator.py`: 修正（invoke_structured_llm経由のため自動対応）
- [ ] 単体テスト追加（モック化）

### Phase 3: commonUI側（8時間）
- [ ] `config/available_models.yaml` 作成
- [ ] `pages/3_🔐_MyVault.py`: モデル設定タブ追加
- [ ] モデル設定の読み込み・保存機能
- [ ] キャッシュリロード連携
- [ ] 単体テスト追加

### Phase 4: テスト（6時間）
- [ ] expertAgent単体テスト（90%カバレッジ）
- [ ] commonUI単体テスト（90%カバレッジ）
- [ ] 結合テスト（50%カバレッジ）
- [ ] E2E受入テスト

### Phase 5: ドキュメント・PR（2時間）
- [ ] API_REFERENCE.md更新
- [ ] README更新
- [ ] PR作成

---

## 参照ドキュメント

- [myVault統合規約](../../../docs/design/myvault-integration.md)
- [expertAgent API Reference](../../../expertAgent/docs/API_REFERENCE.md)
- [commonUI README](../../../commonUI/README.md)
- [要件定義書](./requirements.md)

---

*作成日: 2025-12-11*
*Issue: #269*
*ステータス: 承認待ち*
