# 要件定義書: Issue #191 - プロンプト管理API実装

## 現状調査サマリ

### 対象プロジェクト
- **プロジェクト名**: expertAgent
- **関連モジュール**:
  - `app/services/prompt_loader.py` - PromptLoaderサービス（既存・#177で実装済み）
  - `app/services/prompt_cache.py` - PromptCacheサービス（既存）
  - `app/api/v1/` - FastAPIルーター群
  - `app/schemas/` - Pydanticスキーマ群
  - `prompts/` - YAMLプロンプトファイル（7カテゴリ）

### 既存の類似機能
| 機能 | 場所 | パターン |
|------|------|----------|
| Job Generator API | `app/api/v1/job_generator_endpoints.py` | POST /job-generator, GET /jobs/{id}/status |
| Marp Report API | `app/api/v1/marp_report_endpoints.py` | POST /marp-report, GET /marp-report/{id} |
| Observability API | `app/api/v1/observability_endpoints.py` | GET /observability/traces, POST /observability/scores |

### 使用されている設計パターン
| パターン | 使用箇所 | 目的 |
|----------|----------|------|
| **Factory Pattern** | `PromptLoader.create_default()` | デフォルト設定でのインスタンス生成 |
| **Singleton Pattern** | `PromptCache.get_instance()` | キャッシュの共有インスタンス |
| **Dependency Injection** | `Depends(get_service)` | サービスの注入 |
| **Repository Pattern** | `PromptLoader` | YAMLファイルへのアクセス抽象化 |

### 参照したドキュメント
- `dev-reports/feature/issue/152/prompts-api-design.md` - 設計方針書
- `expertAgent/docs/API_REFERENCE.md` - API仕様書
- `myAgentDesk/src/lib/mlops/api/client.ts` - フロントエンドAPIクライアント
- `myAgentDesk/src/lib/mlops/types/index.ts` - TypeScript型定義

### 制約事項
1. **Phase 1は読み取り専用API**: GET /v1/prompts, GET /v1/prompts/{id} のみ実装
2. **既存PromptLoaderを活用**: 新規データアクセス層は不要
3. **フロントエンドとの互換性**: myAgentDeskの期待するレスポンス形式に準拠
4. **デモモードからの切り替え**: 404解消によりリアルAPIへ自動切り替え

---

## ユーザーストーリー

```
As a 管理者
I want to 要件定義エージェントのプロンプトをREST API経由で管理したい
So that MLOps UIからプロンプトの一覧表示・詳細閲覧ができ、改善サイクルを効率化できる
```

---

## 受入条件（Acceptance Criteria）

### AC-1: プロンプト一覧取得
- **Given**: expertAgentサーバーが起動している
- **When**: `GET /aiagent-api/v1/prompts` をリクエストする
- **Then**: 全プロンプトテンプレートの一覧がJSON形式で返却される（7件）

### AC-2: プロンプト詳細取得
- **Given**: `requirement_clarification` プロンプトが存在する
- **When**: `GET /aiagent-api/v1/prompts/requirement_clarification` をリクエストする
- **Then**: プロンプトの詳細（メタデータ、バージョン一覧、コンテンツ）が返却される

### AC-3: 存在しないプロンプトのエラーハンドリング
- **Given**: `nonexistent_prompt` は存在しない
- **When**: `GET /aiagent-api/v1/prompts/nonexistent_prompt` をリクエストする
- **Then**: HTTPステータス404と適切なエラーメッセージが返却される

### AC-4: フロントエンドUI動作確認
- **Given**: expertAgentのPrompts APIが稼働している
- **When**: myAgentDeskの `/mlops/prompts` ページにアクセスする
- **Then**: 「Not Found - Using demo mode」が表示されず、実際のプロンプト一覧が表示される

### AC-5: OpenAPI仕様準拠
- **Given**: Prompts APIエンドポイントが実装されている
- **When**: `/aiagent-api/docs` (Swagger UI) にアクセスする
- **Then**: Prompts APIのエンドポイントがドキュメント化されている

---

## 機能要件

### Must Have（必須機能）

| ID | 機能 | 説明 |
|----|------|------|
| F-1 | プロンプト一覧API | `GET /v1/prompts` - 全プロンプトテンプレート一覧を取得 |
| F-2 | プロンプト詳細API | `GET /v1/prompts/{prompt_id}` - 特定プロンプトの詳細を取得 |
| F-3 | Pydanticスキーマ | `PromptTemplate`, `PromptVersion`, `PromptListResponse` |
| F-4 | PromptManagementService | ビジネスロジック層（PromptLoaderのラッパー） |
| F-5 | エラーハンドリング | 404 (Not Found), 500 (Internal Error) の適切な処理 |
| F-6 | 単体テスト | カバレッジ90%以上 |

### Nice to Have（あると良い機能）

| ID | 機能 | 説明 |
|----|------|------|
| N-1 | カテゴリフィルタリング | `GET /v1/prompts?category=system` でフィルタ |
| N-2 | 検索機能 | `GET /v1/prompts?search=clarification` でプロンプト検索 |
| N-3 | ページネーション | `limit`, `offset` パラメータ対応 |

### Future Enhancement（将来の拡張）

| ID | 機能 | 説明 |
|----|------|------|
| FE-1 | バージョン作成API | `POST /v1/prompts/{id}/versions` |
| FE-2 | バージョン有効化API | `POST /v1/prompts/{id}/versions/{version_id}/activate` |
| FE-3 | プロンプト更新API | `PUT /v1/prompts/{id}` |

---

## 非機能要件

### パフォーマンス要件
| 項目 | 要件 |
|------|------|
| レスポンス時間 | 一覧API: < 100ms、詳細API: < 50ms |
| キャッシュ | PromptCacheによるインメモリキャッシュ活用 |
| 同時リクエスト | 100リクエスト/秒以上 |

### セキュリティ要件
| 項目 | 要件 |
|------|------|
| 認証 | Phase 1では認証なし（内部ネットワーク利用想定） |
| パストラバーサル防止 | prompt_idのバリデーション（英数字・アンダースコアのみ） |
| 入力検証 | Pydanticによる自動バリデーション |

### ユーザビリティ要件
| 項目 | 要件 |
|------|------|
| APIドキュメント | OpenAPI (Swagger UI) 自動生成 |
| エラーメッセージ | 日本語/英語の明確なエラーメッセージ |

### 互換性要件
| 項目 | 要件 |
|------|------|
| フロントエンド互換 | myAgentDeskの `PromptTemplate` 型定義に準拠 |
| 既存API統一 | expertAgentの既存APIパターンに準拠 |

---

## 技術的制約

### 使用技術スタック
| カテゴリ | 技術 | 理由 |
|----------|------|------|
| フレームワーク | FastAPI | 既存expertAgent基盤 |
| バリデーション | Pydantic v2 | 型安全なスキーマ定義 |
| データストレージ | YAML ファイル | #177で実装済み、Git管理可能 |
| キャッシュ | PromptCache（インメモリ） | 既存実装を再利用 |

### API仕様
```
Base URL: /aiagent-api/v1

GET /prompts
  Response: { items: PromptTemplate[], total: number }

GET /prompts/{prompt_id}
  Response: PromptTemplate
  Error 404: { detail: "Prompt not found: {prompt_id}" }
```

### レスポンススキーマ（フロントエンド期待形式）
```python
class PromptVersion(BaseModel):
    id: str                    # バージョンID（例: "default"）
    version: int               # バージョン番号
    content: str               # プロンプト本文
    description: str           # バージョン説明
    created_at: datetime       # 作成日時
    is_active: bool            # アクティブフラグ

class PromptTemplate(BaseModel):
    id: str                    # プロンプトID（ディレクトリ名）
    name: str                  # 表示名
    description: str           # プロンプト説明
    category: str              # カテゴリ
    current_version: int       # 現在のバージョン番号
    versions: list[PromptVersion]
    created_at: datetime
    updated_at: datetime
```

---

## リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| YAMLファイル読み込みエラー | 中 | 低 | PromptLoaderの既存エラーハンドリングを活用、ログ出力強化 |
| キャッシュ不整合 | 低 | 低 | ファイル変更時のキャッシュ無効化（file_watcher連携） |
| フロントエンド互換性問題 | 高 | 中 | TypeScript型定義と完全一致するスキーマ設計、E2Eテスト実施 |
| パフォーマンス劣化 | 中 | 低 | PromptCacheによるキャッシュ、レスポンス時間モニタリング |

---

## 実装計画

### Phase 1: 読み取り専用API（本Issue）

| ステップ | タスク | 成果物 |
|----------|--------|--------|
| 1 | Pydanticスキーマ定義 | `app/schemas/prompts.py` |
| 2 | PromptManagementService実装 | `app/services/prompt_management.py` |
| 3 | FastAPIルーター実装 | `app/api/v1/prompts_endpoints.py` |
| 4 | main.pyへのルーター登録 | `app/main.py` 更新 |
| 5 | 単体テスト作成 | `tests/unit/test_prompts_*.py` |
| 6 | 統合テスト作成 | `tests/integration/test_prompts_api.py` |

### 品質基準
- 単体テストカバレッジ: 90%以上
- 静的解析: Ruff/MyPyエラーゼロ
- OpenAPI仕様: 自動生成ドキュメント確認

---

## 依存関係

```mermaid
graph LR
    A["#177 PromptLoader"] --> B["#191 Prompts API"]
    B --> C["#170 Prompts UI"]
    A["#152 MLOps導入"]:::parent --> B

    classDef parent fill:#f9f,stroke:#333
```

| 種別 | Issue | 状態 |
|------|-------|------|
| 依存 | #177 プロンプトYAML化 | 完了 |
| 被依存 | #170 UI実装 | デモモードで待機中 |
| 親 | #152 MLOps導入 | 進行中 |

---

## 参照ドキュメント

| ドキュメント | 用途 |
|--------------|------|
| [prompts-api-design.md](../152/prompts-api-design.md) | 設計方針書 |
| [API_REFERENCE.md](../../../expertAgent/docs/API_REFERENCE.md) | expertAgent API仕様 |
| [myAgentDesk types/index.ts](../../../myAgentDesk/src/lib/mlops/types/index.ts) | フロントエンド型定義 |
| [myAgentDesk api/client.ts](../../../myAgentDesk/src/lib/mlops/api/client.ts) | フロントエンドAPIクライアント |

---

## 見積

**2日**（設計方針書記載通り）

---

*作成日: 2025-12-10*
*Issue: #191*
*親Issue: #152*
