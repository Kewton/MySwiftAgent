# 設計方針: Job Generator マルチモデルLLM対応

**作成日**: 2025-10-22
**ブランチ**: feature/issue/108
**担当**: Claude Code

---

## 📋 要求・要件

### ビジネス要求
ユーザーの要求: 「job-generatorに関し、claude系だけでなくgpt系とgemini系を利用可能にしてください。また、AIエージェントの各モデルについて環境変数から指定可能にし、.envにてコントロール可能にしてください。」

### 機能要件
1. **マルチプロバイダー対応**: Job Generatorで以下のLLMプロバイダーを利用可能にする
   - Claude (Anthropic) - 現在サポート済み
   - GPT (OpenAI) - 新規追加
   - Gemini (Google) - 新規追加

2. **環境変数での設定**: 各ノードで使用するLLMモデルを環境変数で指定可能にする
   - requirement_analysis_node
   - evaluator_node
   - interface_definition_node
   - validation_node

3. **.envファイルでの制御**: 開発者が.envファイルでモデルを簡単に変更できるようにする

### 非機能要件
- パフォーマンス: 現在のClaude実装と同等以上の応答速度
- セキュリティ: API KeysはMyVaultで管理（既存の仕組みを維持）
- 可用性: 各プロバイダーのAPI障害時にフォールバック機構は不要（明示的な設定のみ）
- 保守性: 新規LLMプロバイダーの追加が容易な設計

---

## 🏗️ アーキテクチャ設計

### システム構成

#### 現状の問題点
- 各ノードで`ChatAnthropic`をハードコードで直接インスタンス化
- モデル名 "claude-haiku-4-5" がハードコード
- プロバイダーの変更には全ノードのコード修正が必要

#### 提案する設計

```
┌─────────────────────────────────────────────────────┐
│          Environment Variables (.env)               │
│  JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL           │
│  JOB_GENERATOR_EVALUATOR_MODEL                      │
│  JOB_GENERATOR_INTERFACE_DEFINITION_MODEL           │
│  JOB_GENERATOR_VALIDATION_MODEL                     │
│  JOB_GENERATOR_MAX_TOKENS                           │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              LLM Factory Module                      │
│  create_llm(model_name, temperature, max_tokens)    │
│  ┌─────────────────────────────────────┐            │
│  │ Provider Detection                  │            │
│  │  - claude-* → ChatAnthropic         │            │
│  │  - gpt-* → ChatOpenAI               │            │
│  │  - gemini-* → ChatGoogleGenerativeAI│            │
│  └─────────────────────────────────────┘            │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│          Job Generator Nodes                        │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ requirement_   │  │ evaluator_     │            │
│  │ analysis_node  │  │ node           │            │
│  └────────────────┘  └────────────────┘            │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ interface_     │  │ validation_    │            │
│  │ definition_node│  │ node           │            │
│  └────────────────┘  └────────────────┘            │
└─────────────────────────────────────────────────────┘
```

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| Claude LLM | langchain-anthropic.ChatAnthropic | 現在使用中、実績あり |
| GPT LLM | langchain-openai.ChatOpenAI | LangChain公式サポート、実績多数 |
| Gemini LLM | langchain-google-genai.ChatGoogleGenerativeAI | LangChain公式サポート、高性能 |
| Factory Pattern | 関数ベースのファクトリー | シンプル、拡張しやすい |

### ディレクトリ構成

```
expertAgent/
├── aiagent/
│   └── langgraph/
│       └── jobTaskGeneratorAgents/
│           ├── nodes/
│           │   ├── requirement_analysis.py  # 修正対象
│           │   ├── evaluator.py            # 修正対象
│           │   ├── interface_definition.py # 修正対象
│           │   └── validation.py           # 修正対象
│           └── utils/
│               └── llm_factory.py          # 新規作成
├── .env                                    # 修正対象
└── .env.example                            # 修正対象
```

---

## 🔧 詳細設計

### 1. LLM Factory モジュール設計

**ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_factory.py`

**責務**:
- モデル名文字列からLLMプロバイダーを判定
- 適切なLLMクライアントをインスタンス化
- 共通パラメータ（temperature, max_tokens）の設定

**関数シグネチャ**:
```python
def create_llm(
    model_name: str,
    temperature: float = 0.0,
    max_tokens: int = 8192,
) -> BaseChatModel:
    """Create LLM instance based on model name.

    Args:
        model_name: Model name (e.g., "claude-haiku-4-5", "gpt-4o-mini", "gemini-2.5-flash")
        temperature: Temperature parameter (default: 0.0)
        max_tokens: Maximum tokens (default: 8192)

    Returns:
        LLM instance (ChatAnthropic, ChatOpenAI, or ChatGoogleGenerativeAI)

    Raises:
        ValueError: If model name is invalid or provider is not supported
    """
```

**プロバイダー判定ロジック**:
- `claude-*` または `haiku-*` または `sonnet-*` または `opus-*` → ChatAnthropic
- `gpt-*` → ChatOpenAI
- `gemini-*` → ChatGoogleGenerativeAI

### 2. 環境変数設計

#### .env ファイル追加項目

```bash
# ===== Job/Task Generator LLM設定 =====
# 各ノードで使用するモデルを個別に指定可能
# 対応プロバイダー: Claude (claude-*), GPT (gpt-*), Gemini (gemini-*)

# タスク分解ノード（ユーザー要求を実行可能なタスクに分解）
JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL=claude-haiku-4-5

# 評価ノード（タスク分解の品質を評価）
JOB_GENERATOR_EVALUATOR_MODEL=claude-haiku-4-5

# インターフェース定義ノード（タスクI/O用JSON Schema生成）
JOB_GENERATOR_INTERFACE_DEFINITION_MODEL=claude-haiku-4-5

# バリデーションノード（ワークフロー検証と修正提案）
JOB_GENERATOR_VALIDATION_MODEL=claude-haiku-4-5

# 最大トークン数（全ノード共通）
JOB_GENERATOR_MAX_TOKENS=32768
```

#### デフォルト値の設計方針

**原則**: 環境変数が未設定の場合、既存の "claude-haiku-4-5" をデフォルトとする

**理由**:
- 後方互換性の維持
- 既存環境での動作保証
- 段階的な移行を可能にする

### 3. ノード修正設計

#### 修正パターン（全4ノード共通）

**修正前**:
```python
from langchain_anthropic import ChatAnthropic

max_tokens = int(os.getenv("JOB_GENERATOR_MAX_TOKENS", "8192"))
model = ChatAnthropic(
    model="claude-haiku-4-5",  # ハードコード
    temperature=0.0,
    max_tokens=max_tokens,
)
```

**修正後**:
```python
from ..utils.llm_factory import create_llm

max_tokens = int(os.getenv("JOB_GENERATOR_MAX_TOKENS", "8192"))
model_name = os.getenv(
    "JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL",  # ノードごとに変更
    "claude-haiku-4-5"  # デフォルト値
)
model = create_llm(
    model_name=model_name,
    temperature=0.0,
    max_tokens=max_tokens,
)
```

#### 各ノードの環境変数名

| ノード | 環境変数名 | 用途 |
|-------|-----------|------|
| requirement_analysis.py | `JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL` | タスク分解 |
| evaluator.py | `JOB_GENERATOR_EVALUATOR_MODEL` | 品質評価 |
| interface_definition.py | `JOB_GENERATOR_INTERFACE_DEFINITION_MODEL` | JSON Schema生成 |
| validation.py | `JOB_GENERATOR_VALIDATION_MODEL` | ワークフロー検証 |

### 4. API Key管理

**重要**: API Keysは既存のMyVault統合を利用

- `ANTHROPIC_API_KEY` - Claude用（既存）
- `OPENAI_API_KEY` - GPT用（既存）
- `GOOGLE_API_KEY` - Gemini用（必要に応じてMyVaultに登録）

LangChainのLLMクライアントは環境変数から自動的にAPI Keyを読み込むため、LLM Factoryでの明示的な設定は不要。

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守
  - Single Responsibility: LLM Factory は LLM生成のみ、各ノードは既存の責務のみ
  - Open-Closed: 新規プロバイダー追加時はFactoryのみ修正、ノードは変更不要
  - Dependency Inversion: ノードはBaseChatModelに依存、具体的な実装に依存しない
- [x] **KISS原則**: 遵守
  - シンプルな関数ベースのFactory
  - 複雑な抽象化クラスは不使用
- [x] **YAGNI原則**: 遵守
  - フォールバック機構は実装しない（要求されていない）
  - キャッシュ機構は実装しない（必要性なし）
- [x] **DRY原則**: 遵守
  - LLM生成ロジックをFactoryに集約
  - 4つのノードで共通のFactory関数を使用

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠
  - ユーティリティモジュールをutilsディレクトリに配置
  - レイヤー分離を維持（LLM生成とビジネスロジックを分離）
- [x] 依存関係の方向性: 適切
  - ノード → LLM Factory → LLMクライアント（単方向）

### 設定管理ルール
- [x] **環境変数**: 遵守
  - LLMモデル選択はシステムパラメータのため環境変数で管理
  - `environment-variables.md` に準拠
- [x] **myVault**: 遵守
  - API KeysはMyVaultで管理（既存の仕組みを維持）
  - `myvault-integration.md` に準拠

### 品質担保方針
- [ ] **単体テストカバレッジ 90%以上**: 実装後に対応
  - LLM Factory の単体テスト作成予定
  - プロバイダー判定ロジックのテストケース
  - エラーハンドリングのテストケース
- [ ] **結合テストカバレッジ 50%以上**: 実装後に対応
  - 各ノードでの動作確認（E2Eテスト）
  - 各プロバイダーでの動作確認
- [ ] **Ruff linting エラーゼロ**: 実装後に確認
- [ ] **MyPy type checking エラーゼロ**: 実装後に確認

### CI/CD準拠
- [x] **PRラベル**: `feature` ラベルを付与予定（機能追加）
- [x] **コミットメッセージ**: 規約に準拠予定
- [ ] **pre-push-check-all.sh**: 実装後に実行予定

### 参照ドキュメント遵守
- [x] **CLAUDE.md**: 遵守
  - 作業前に必須ドキュメントを確認済み
  - dev-reports ディレクトリに設計ドキュメント作成済み
- [x] **GraphAI ワークフロー生成ルール**: 該当なし（本タスクはJob Generator内部の実装）

### 違反・要検討項目
なし

---

## 📝 設計上の決定事項

1. **Factory Pattern の採用理由**
   - 関数ベースのシンプルなFactoryパターンを採用
   - 複雑なクラス階層は不要と判断（YAGNI原則）
   - 拡張性とシンプルさのバランスを重視

2. **プロバイダー判定方法**
   - モデル名プレフィックスで判定（claude-*, gpt-*, gemini-*）
   - 明示的でわかりやすい
   - 将来的な新規プロバイダー追加も容易

3. **環境変数のデフォルト値**
   - 全ノードで "claude-haiku-4-5" をデフォルトに設定
   - 後方互換性を維持
   - 段階的な移行を可能にする

4. **API Key管理方針**
   - MyVault統合を継続利用
   - LangChainの標準的な環境変数読み込み機構を活用
   - セキュリティベストプラクティスに準拠

5. **各ノードで個別にモデルを指定可能にする理由**
   - タスク分解は高性能モデル、検証は軽量モデルなど、用途に応じた選択が可能
   - コスト最適化が可能
   - 将来的な柔軟性確保

6. **フォールバック機構を実装しない理由**
   - ユーザー要求に含まれていない（YAGNI原則）
   - 明示的な設定のみで十分
   - 予期しないモデル切り替えはデバッグを困難にする

---

## 🔍 リスク分析

### 技術的リスク

| リスク | 影響度 | 対策 |
|-------|-------|------|
| GPT/Gemini APIの応答形式がClaudeと異なる | 中 | LangChainが統一インターフェースを提供、structured outputも共通 |
| プロバイダー間の性能差 | 低 | ユーザーが明示的に選択するため、期待と異なる場合は設定変更可能 |
| API Key未設定時のエラー | 中 | LangChainの標準エラーメッセージを表示、ログに記録 |
| 新規依存関係の追加 | 低 | langchain-openai, langchain-google-genaiは安定版 |

### 運用リスク

| リスク | 影響度 | 対策 |
|-------|-------|------|
| 誤った環境変数設定 | 中 | .env.exampleに詳細なコメントを記載、デフォルト値を設定 |
| プロバイダー障害時の影響 | 低 | 明示的な設定のみ、フォールバックなし（意図的） |

---

## 📚 参考資料

- LangChain Documentation: https://python.langchain.com/docs/integrations/chat/
- ChatAnthropic: https://python.langchain.com/docs/integrations/chat/anthropic/
- ChatOpenAI: https://python.langchain.com/docs/integrations/chat/openai/
- ChatGoogleGenerativeAI: https://python.langchain.com/docs/integrations/chat/google_generative_ai/
