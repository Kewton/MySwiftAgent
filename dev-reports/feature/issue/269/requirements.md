# 要件定義書: LLMモデル設定のmyVault管理とcommonUI設定画面

## 現状調査サマリ

### 対象プロジェクト
- **expertAgent**: モデル設定の使用箇所（8箇所）
- **myVault**: シークレット管理API
- **commonUI**: 設定管理UI（Streamlit）

### 既存の類似機能

| 機能 | 場所 | 概要 |
|------|------|------|
| シークレット管理画面 | `commonUI/pages/3_🔐_MyVault.py` | プロジェクト/シークレットのCRUD、キャッシュリロード |
| SecretsManager | `expertAgent/core/secrets.py` | MyVault優先＋環境変数フォールバック |
| invoke_structured_llm | `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py` | 統一的なLLM呼び出しインターフェース |

### 使用されている設計パターン

| パターン | 使用箇所 | 目的 |
|---------|---------|------|
| Singleton | `secrets_manager` | グローバルインスタンス |
| Factory | `create_llm_with_fallback()` | プロバイダ別LLM生成 |
| Strategy | `HTTPClient` | サービス別認証方式 |
| Cache with TTL | `SecretsManager._cache` | パフォーマンス最適化 |

### モデル設定の現状

| 設定名 | デフォルト値 | 取得方法 | 使用箇所 |
|-------|-------------|----------|---------|
| `CHAT_CLARIFICATION_MODEL` | `gemini-2.0-flash` | `os.getenv()` | `llm_service.py:77,192` |
| `CANDIDATE_GENERATION_MODEL` | `gemini-2.0-flash` | `os.getenv()` | `candidate_generator.py:112` |
| `REQUIREMENT_EXTRACTION_MODEL` | `gemini-2.0-flash` | `invoke_structured_llm()` | `requirement_clarification.py:313` |
| `JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL` | `claude-haiku-4-5` | `invoke_structured_llm()` | `requirement_analysis.py:150` |
| `JOB_GENERATOR_EVALUATOR_MODEL` | `claude-haiku-4-5` | `invoke_structured_llm()` | `evaluator.py:100` |
| `JOB_GENERATOR_INTERFACE_DEFINITION_MODEL` | `claude-haiku-4-5` | `invoke_structured_llm()` | `interface_definition.py:155` |
| `JOB_GENERATOR_VALIDATION_MODEL` | `claude-haiku-4-5` | `invoke_structured_llm()` | `validation.py:113` |
| `WORKFLOW_GENERATOR_MODEL` | `gemini-2.0-flash-exp` | `invoke_structured_llm()` | `generator.py:119` |

### 参照したドキュメント
- `docs/design/myvault-integration.md` - MyVault統合規約
- `expertAgent/core/secrets.py` - SecretsManager実装
- `commonUI/pages/3_🔐_MyVault.py` - 既存のMyVault管理画面

### 制約事項
- キャッシュTTL（デフォルト300秒）による設定反映遅延の可能性
- 環境変数へのフォールバックは維持する必要あり
- 対応プロバイダ: Claude, GPT, Gemini（Ollamaは別途）

---

## ユーザーストーリー

```
As a システム管理者
I want to LLMモデル設定をcommonUIから動的に変更できる
So that サービス再起動なしでモデルを切り替え、コスト最適化や性能調整を迅速に行える
```

### 追加ユーザーストーリー

```
As a 開発者
I want to モデル設定がmyVaultで一元管理される
So that 環境ごとの設定差異を減らし、設定変更の監査証跡を残せる
```

---

## 受入条件（Acceptance Criteria）

### AC-1: myVaultでのモデル設定管理
- **Given**: myVaultが起動している
- **When**: 8つのモデル設定がmyVaultに登録されている
- **Then**: expertAgentがmyVaultからモデル設定を取得できる

### AC-2: 環境変数フォールバック
- **Given**: myVaultが利用不可、または設定が未登録
- **When**: モデル設定を取得しようとする
- **Then**: 環境変数またはconfig.pyのデフォルト値にフォールバックする

### AC-3: commonUIからの設定変更
- **Given**: commonUIのモデル設定画面を開く
- **When**: モデル設定をドロップダウンから選択して保存
- **Then**: myVaultに設定が保存され、成功メッセージが表示される

### AC-4: サービス再起動なしの反映
- **Given**: モデル設定を変更した
- **When**: キャッシュリロードを実行する
- **Then**: expertAgentが新しいモデル設定を使用する

### AC-5: 利用可能モデル一覧の表示
- **Given**: commonUIのモデル設定画面を開く
- **When**: モデル選択ドロップダウンをクリック
- **Then**: 利用可能なモデル一覧（Claude/GPT/Gemini）が表示される

---

## 機能要件

### Must Have（必須機能）

| ID | 機能 | 説明 |
|----|------|------|
| F-1 | myVaultシークレット定義 | 8つのモデル設定用シークレットキーを定義 |
| F-2 | SecretsManager経由の取得 | `secrets_manager.get_secret()`でモデル設定を取得 |
| F-3 | commonUI設定画面 | モデル設定管理タブをMyVault画面に追加 |
| F-4 | プルダウン選択UI | 利用可能モデル一覧からの選択 |
| F-5 | キャッシュリロード | 設定変更後の即時反映機能 |
| F-6 | デフォルト値表示 | 現在の設定値と未設定時のデフォルト値を表示 |

### Nice to Have（あると良い機能）

| ID | 機能 | 説明 |
|----|------|------|
| N-1 | モデル検証 | 選択されたモデルが利用可能か事前検証 |
| N-2 | 使用量表示 | 各モデルの使用回数・コスト概算表示 |
| N-3 | 一括設定 | 全モデル設定を一括で変更 |

### Future Enhancement（将来的な拡張）

| ID | 機能 | 説明 |
|----|------|------|
| FE-1 | モデル自動切替 | コスト上限到達時の自動フォールバック |
| FE-2 | A/Bテスト | モデル比較のためのA/Bテスト機能 |
| FE-3 | カスタムモデル登録 | Ollamaや新規プロバイダの追加 |

---

## 非機能要件

### パフォーマンス要件
| 要件 | 基準 |
|------|------|
| 設定取得レスポンス | < 100ms（キャッシュヒット時 < 10ms） |
| 設定画面表示 | < 2秒 |
| キャッシュリロード | < 5秒 |

### セキュリティ要件
| 要件 | 基準 |
|------|------|
| 認証 | X-Service/X-Token ヘッダーによるサービス認証 |
| 権限 | commonUIにwrite権限、expertAgentにread権限 |
| 監査 | 設定変更履歴をmyVaultで記録 |

### 可用性要件
| 要件 | 基準 |
|------|------|
| フォールバック | myVault障害時は環境変数にフォールバック |
| エラーハンドリング | 設定取得失敗時もサービス継続 |

### 互換性要件
| 要件 | 基準 |
|------|------|
| 後方互換性 | 既存の環境変数設定を引き続きサポート |
| 移行 | 段階的移行が可能（myVault優先、環境変数フォールバック） |

---

## 技術的制約

### 使用する技術スタック

| レイヤー | 技術 | バージョン |
|---------|------|----------|
| expertAgent | FastAPI + Pydantic | 現行バージョン |
| myVault | FastAPI + SQLite | 現行バージョン |
| commonUI | Streamlit | 現行バージョン |

### 既存システムとの連携

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  commonUI    │ ──── │   myVault    │ ──── │ expertAgent  │
│  (設定変更)   │ POST │  (保存)      │ GET  │  (取得)      │
└──────────────┘      └──────────────┘      └──────────────┘
        │                                          │
        └──────────── キャッシュリロード ────────────┘
```

### データ形式

**myVaultシークレット構造**:
```json
{
  "project": "default_project",
  "path": "CHAT_CLARIFICATION_MODEL",
  "value": "gemini-2.0-flash"
}
```

**利用可能モデル定義（commonUI用）**:
```yaml
# commonUI/config/available_models.yaml
models:
  claude:
    - claude-haiku-4-5
    - claude-sonnet-4-20250514
    - claude-opus-4-20250514
  openai:
    - gpt-4o-mini
    - gpt-4o
    - gpt-4-turbo
  google:
    - gemini-2.0-flash
    - gemini-2.0-flash-exp
    - gemini-2.5-flash
    - gemini-2.5-pro
```

---

## リスクと対策

| リスク | 確率 | 影響 | 対策 |
|--------|------|------|------|
| myVault障害時のサービス停止 | 低 | 高 | 環境変数フォールバック維持、キャッシュTTL延長 |
| 設定変更の反映遅延 | 中 | 中 | キャッシュリロードAPIの提供、TTL調整 |
| 不正なモデル名の設定 | 中 | 中 | ドロップダウン選択による入力制限、バリデーション |
| 既存設定との互換性問題 | 低 | 中 | 段階的移行、デュアルサポート期間 |

---

## 対象モデル設定一覧

| # | 設定名 | デフォルト値 | 用途 | カテゴリ |
|---|-------|-------------|------|---------|
| 1 | `CHAT_CLARIFICATION_MODEL` | `gemini-2.0-flash` | 要件定義チャット | Chat |
| 2 | `CANDIDATE_GENERATION_MODEL` | `gemini-2.0-flash` | 候補生成 | Chat |
| 3 | `REQUIREMENT_EXTRACTION_MODEL` | `gemini-2.0-flash` | 要件抽出 | Chat |
| 4 | `JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL` | `claude-haiku-4-5` | 要件分析 | Job Generator |
| 5 | `JOB_GENERATOR_EVALUATOR_MODEL` | `claude-haiku-4-5` | 評価 | Job Generator |
| 6 | `JOB_GENERATOR_INTERFACE_DEFINITION_MODEL` | `claude-haiku-4-5` | インターフェース定義 | Job Generator |
| 7 | `JOB_GENERATOR_VALIDATION_MODEL` | `claude-haiku-4-5` | バリデーション | Job Generator |
| 8 | `WORKFLOW_GENERATOR_MODEL` | `gemini-2.0-flash-exp` | ワークフロー生成 | Workflow |

---

## 見積もり

| フェーズ | 作業内容 | 見積時間 |
|---------|---------|---------|
| Phase 1 | myVault側（シークレット定義、デフォルト値） | 2時間 |
| Phase 2 | expertAgent側（SecretsManager統合、8ファイル修正） | 8時間 |
| Phase 3 | commonUI側（設定画面、モデル一覧、キャッシュリロード） | 8時間 |
| Phase 4 | テスト（単体90%、統合50%） | 6時間 |
| Phase 5 | ドキュメント・PR | 2時間 |
| **合計** | | **26時間（約3.5日）** |

---

## 参照ドキュメント

- [myVault統合規約](../../../docs/design/myvault-integration.md)
- [expertAgent API Reference](../../../expertAgent/docs/API_REFERENCE.md)
- [commonUI README](../../../commonUI/README.md)

---

*作成日: 2025-12-11*
*Issue: #269*
*ステータス: 承認待ち*
