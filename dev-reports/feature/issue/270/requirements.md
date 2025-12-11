# 要件定義書: expert_agent_capabilities.yaml スキーマ拡張 (Issue #270)

## 現状調査サマリ

### 対象プロジェクト
- **プロジェクト名**: expertAgent
- **関連モジュール**:
  - `aiagent/langgraph/jobTaskGeneratorAgents/utils/graphai_capabilities.py`
  - `aiagent/langgraph/jobTaskGeneratorAgents/prompts/task_breakdown.py`
  - `aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py`
  - `aiagent/langgraph/jobTaskGeneratorAgents/nodes/schema_enrichment.py`

### 既存の類似機能
- **graphai_capabilities.yaml**: GraphAIエージェント定義（スキーマなし）
- **OpenAPIスキーマコレクター**: `core/openapi_schema_collector.py`（実行時にAPIからスキーマ取得）
- **output_schema定義**: `text_to_speech_drive`のみ部分的にスキーマ定義あり（lines 95-119）

### 使用されている設計パターン
- **YAML設定ファイル + Pythonローダー**: `graphai_capabilities.py`がYAMLを読み込み、データクラスに変換
- **マークダウンフォーマット**: LLMプロンプトへの埋め込み時にマークダウンテーブル形式に変換
- **OpenAPI仕様活用**: 実行時にexpertAgent APIからOpenAPI仕様を取得してスキーマ補完

### 参照したドキュメント
| ドキュメント | 関連内容 |
|-------------|---------|
| `expertAgent/docs/API_REFERENCE.md` | 全APIのリクエスト/レスポンス仕様 |
| `docs/spec/job-generation-workflow.md` | LangGraphワークフロー設計、7段階処理フロー |
| `expert_agent_capabilities.yaml` | 現在のAPI定義構造（概要のみ） |

### 制約事項
- `interface_definition`ノードは現在 `expert_agent_capabilities.yaml` を参照していない
- `schema_enrichment`ノードはOpenAPI仕様に依存（サービス起動が必要）
- 既存のプロンプトテンプレートとの互換性維持が必要

---

## ユーザーストーリー

### プライマリストーリー
```
As a ジョブ生成APIのユーザー
I want to LLMがAPIスキーマを正確に把握した状態でインターフェースを定義してほしい
So that schema_enrichment段階での補正を最小化し、初回生成精度を向上できる
```

### セカンダリストーリー
```
As a システム運用者
I want to expertAgentが起動していなくてもスキーマ情報が利用可能であってほしい
So that OpenAPI依存によるエラーや遅延を回避できる
```

---

## 受入条件（Acceptance Criteria）

### AC1: スキーマ定義の追加
- **Given**: `expert_agent_capabilities.yaml`ファイルが存在する
- **When**: 主要API（10件以上）にリクエスト/レスポンススキーマを追加する
- **Then**: 各APIの`request_schema`と`response_schema`がJSON Schema形式で定義されている

### AC2: プロンプトへのスキーマ情報埋め込み
- **Given**: スキーマ定義が追加された`expert_agent_capabilities.yaml`
- **When**: `task_breakdown.py`の`_build_expert_agent_capabilities()`が実行される
- **Then**: LLMプロンプトにスキーマ情報が含まれる

### AC3: インターフェース定義精度の向上
- **Given**: スキーマ情報がプロンプトに含まれている
- **When**: `interface_definition`ノードがスキーマを生成する
- **Then**: パラメータ名、型、必須/任意の正確性が向上する（手動検証）

### AC4: 既存ワークフローの互換性維持
- **Given**: スキーマ拡張後の`expert_agent_capabilities.yaml`
- **When**: 既存のジョブ生成ワークフローを実行する
- **Then**: エラーなく正常に動作する

### AC5: テストカバレッジ
- **Given**: スキーマ拡張の実装が完了
- **When**: 単体テストを実行する
- **Then**: カバレッジ90%以上を維持

---

## 機能要件

### 必須機能（Must Have）

| ID | 要件 | 詳細 |
|----|-----|------|
| FR-01 | Gmail API スキーマ追加 | `/v1/utility/gmail/search`, `/v1/utility/gmail/send` |
| FR-02 | Google Drive API スキーマ追加 | `/v1/utility/drive/upload`, `/v1/utility/drive/upload_from_url` |
| FR-03 | TTS API スキーマ追加 | `/v1/utility/text_to_speech`, `/v1/utility/text_to_speech_drive` |
| FR-04 | Google Search API スキーマ追加 | `/v1/utility/google_search`, `/v1/utility/google_search_overview` |
| FR-05 | AI Agent API スキーマ追加 | `/v1/aiagent/utility/jsonoutput`, `/v1/mylllm` |
| FR-06 | プロンプトビルダー更新 | `_build_expert_agent_capabilities()`でスキーマを含める |
| FR-07 | YAML構造拡張 | `request_schema`, `response_schema`フィールド追加 |

### あると良い機能（Nice to Have）

| ID | 要件 | 詳細 |
|----|-----|------|
| FR-08 | interface_definitionプロンプト更新 | スキーマ情報を直接参照するよう修正 |
| FR-09 | スキーマバリデーション | YAML読み込み時のスキーマ整合性チェック |
| FR-10 | HTTPメソッド追加 | 各APIに`method`フィールド追加 |

### 将来的な拡張（Future Enhancement）

| ID | 要件 | 詳細 |
|----|-----|------|
| FR-11 | OpenAPI仕様との自動同期 | スクリプトでOpenAPIからYAML生成 |
| FR-12 | schema_enrichmentのフォールバック | OpenAPI取得失敗時にYAMLスキーマを使用 |

---

## 非機能要件

### パフォーマンス要件
| ID | 要件 | 基準 |
|----|-----|------|
| NFR-01 | YAML読み込み時間 | 100ms以内 |
| NFR-02 | プロンプト生成時間 | 現行比10%以内の増加 |

### セキュリティ要件
| ID | 要件 | 基準 |
|----|-----|------|
| NFR-03 | 機密情報排除 | スキーマにAPIキー等の機密情報を含めない |

### 互換性要件
| ID | 要件 | 基準 |
|----|-----|------|
| NFR-04 | 後方互換性 | 既存のYAML構造を破壊しない |
| NFR-05 | プロンプト互換性 | 既存のLLMプロンプトテンプレートとの互換性維持 |

### 品質要件
| ID | 要件 | 基準 |
|----|-----|------|
| NFR-06 | 単体テストカバレッジ | 90%以上 |
| NFR-07 | 静的解析 | Ruff/MyPyエラーゼロ |

---

## 技術的制約

### 使用技術スタック
- **Python 3.12+**: 既存スタックとの整合性
- **PyYAML**: YAML読み込み（既存利用）
- **Pydantic**: スキーマバリデーション（任意）

### 既存システムとの連携
| 連携先 | 連携方法 | 注意点 |
|--------|---------|--------|
| `graphai_capabilities.py` | `_load_yaml_config()`関数を共用 | 既存インターフェース維持 |
| `task_breakdown.py` | `_build_expert_agent_capabilities()`を拡張 | マークダウン出力形式の変更 |
| `interface_definition.py` | プロンプトテンプレート更新（Nice to Have） | 段階的実装可能 |

### データ形式・API仕様
- **YAML構造**: JSON Schema形式でスキーマを定義
- **プロパティ定義**: `type`, `description`, `required`, `default`をサポート

---

## リスクと対策

### 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| LLMプロンプトのトークン数増加 | 中 | 高 | 必要最小限のスキーマ情報に絞る、要約版を生成 |
| YAML構造変更による既存処理破壊 | 高 | 低 | 後方互換性を維持、オプショナルフィールドとして追加 |
| スキーマ定義の陳腐化 | 中 | 中 | API変更時のメンテナンス手順を文書化 |

### ビジネスリスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|------|
| 開発工数の増大 | 中 | 中 | Phase分割で段階的実装、優先度の高いAPIから着手 |

---

## 実装フェーズ提案

### Phase 1: スキーマ定義（2-3時間）
- [ ] Gmail API（search, send）のスキーマ追加
- [ ] Google Drive API（upload, upload_from_url）のスキーマ追加
- [ ] TTS API（text_to_speech, text_to_speech_drive）のスキーマ追加
- [ ] Google Search APIのスキーマ追加
- [ ] AI Agent API（jsonoutput, mylllm）のスキーマ追加

### Phase 2: プロンプト更新（1-2時間）
- [ ] `_build_expert_agent_capabilities()`更新
- [ ] スキーマ情報のマークダウン出力形式設計
- [ ] トークン数最適化

### Phase 3: テスト・検証（1-2時間）
- [ ] 単体テスト追加
- [ ] E2Eテスト（ジョブ生成成功率比較）
- [ ] 静的解析確認

---

## 参照ドキュメント

| ドキュメント | パス |
|-------------|------|
| API Reference | `expertAgent/docs/API_REFERENCE.md` |
| Job Generation Workflow | `docs/spec/job-generation-workflow.md` |
| 現在のCapabilities YAML | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/config/expert_agent_capabilities.yaml` |
| Schema Enrichment Node | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/schema_enrichment.py` |
| Interface Definition Prompt | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py` |

---

## 付録: スキーマ定義サンプル

```yaml
- name: "Gmail検索"
  endpoint: "/v1/utility/gmail/search"
  method: "POST"
  description: "Gmail検索（高速・AIフレンドリー）"
  use_cases:
    - "キーワード検索"
    - "日付範囲指定"
  request_schema:
    query:
      type: string
      description: "Gmail検索クエリ（例: 'from:example@gmail.com subject:重要'）"
      required: true
    max_results:
      type: integer
      description: "取得する最大メール数"
      default: 10
    date_after:
      type: string
      description: "この日付以降のメールを検索（YYYY-MM-DD形式）"
    date_before:
      type: string
      description: "この日付以前のメールを検索（YYYY-MM-DD形式）"
    unread_only:
      type: boolean
      description: "未読メールのみを検索"
      default: false
    has_attachment:
      type: boolean
      description: "添付ファイル付きメールのみを検索"
      default: false
  response_schema:
    messages:
      type: array
      description: "検索結果のメール一覧"
      items:
        type: object
        properties:
          id:
            type: string
          subject:
            type: string
          from:
            type: string
          date:
            type: string
          snippet:
            type: string
    result_count:
      type: integer
      description: "検索結果の件数"
```

---

**作成日**: 2025-12-11
**Issue**: #270
**ステータス**: 要件定義完了
