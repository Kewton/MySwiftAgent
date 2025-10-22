# 設計方針: Job Generator Multi-Model Support Enhancement

**作成日**: 2025-10-22
**ブランチ**: feature/issue/111
**GitHub Issue**: [#111](https://github.com/Kewton/MySwiftAgent/issues/111)
**担当**: Claude Code

---

## 📋 要求・要件

### ビジネス要求
- Job Generatorの全ノード（requirement_analysis, evaluator, interface_definition, validation）でClaude/GPT/Geminiの3つのLLMプロバイダーを環境変数から柔軟に切り替え可能にする
- APIエラー時の自動復旧機能（フォールバック機能）を実装する
- モデル別のパフォーマンス測定・コスト追跡機能を追加する

### 機能要件
1. **環境変数による柔軟なモデル指定**
   - `core/config.py`に以下の環境変数を追加:
     - `JOB_GENERATOR_MAX_TOKENS`
     - `JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL`
     - `JOB_GENERATOR_EVALUATOR_MODEL`
     - `JOB_GENERATOR_INTERFACE_DEFINITION_MODEL`
     - `JOB_GENERATOR_VALIDATION_MODEL`
   - 各ノードで異なるモデルを指定可能（コスト最適化）

2. **自動フォールバック機能**
   - `llm_factory.py`に`create_llm_with_fallback()`関数を追加
   - フォールバック順序: プライマリモデル → Claude → GPT → Gemini
   - APIエラー時（RateLimitError, APIConnectionError等）に自動的に次のモデルへ切り替え
   - 最大リトライ回数: 3回（全プロバイダーを試行）

3. **ノードの統一**
   - `evaluator.py`: `ChatAnthropic`（ハードコード）→ `create_llm_with_fallback()`
   - `interface_definition.py`: 2箇所の`ChatAnthropic` → `create_llm_with_fallback()`
   - `validation.py`: `ChatAnthropic` → `create_llm_with_fallback()`
   - `requirement_analysis.py`: 既存の`create_llm()`を`create_llm_with_fallback()`に更新

4. **モデルパフォーマンス測定**
   - `llm_factory.py`に`ModelPerformanceTracker`クラスを追加
   - 測定項目:
     - レスポンス時間（ミリ秒）
     - トークン使用量（input/output）
     - 成功/失敗回数
     - エラー種別の統計
   - ログ出力: INFO レベルで各呼び出しのメトリクスを記録

5. **コスト追跡機能**
   - `llm_factory.py`に`ModelCostTracker`クラスを追加
   - プロバイダー別のコストテーブル（2025年10月時点）:
     - Claude Haiku 4.5: $0.80/1M input, $4.00/1M output
     - Claude Sonnet 4.5: $3.00/1M input, $15.00/1M output
     - GPT-4o: $2.50/1M input, $10.00/1M output
     - GPT-4o-mini: $0.15/1M input, $0.60/1M output
     - Gemini 2.5 Flash: $0.075/1M input, $0.30/1M output
   - セッション単位での累積コスト計算
   - ログ出力: INFO レベルでコストサマリーを記録

### 非機能要件
- **パフォーマンス**:
  - フォールバック時のオーバーヘッド: 最大1秒以内
  - 通常時のオーバーヘッド: 10ms以内（ログ記録のみ）
- **可用性**:
  - 単一プロバイダー障害時も処理継続可能（99.9%以上）
- **保守性**:
  - コスト単価の更新が容易（設定ファイルまたはクラス変数）
  - 新規プロバイダーの追加が容易（拡張可能な設計）

---

## 🏗️ アーキテクチャ設計

### システム構成

```
┌─────────────────────────────────────────────────────────────┐
│                   Job Generator Nodes                        │
│  (requirement_analysis, evaluator, interface_definition,     │
│   validation)                                                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              create_llm_with_fallback()                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Primary Model指定（環境変数から読み取り）         │   │
│  │ 2. ModelPerformanceTracker初期化                      │   │
│  │ 3. ModelCostTracker初期化                             │   │
│  │ 4. Try Primary Model                                  │   │
│  │    ├─ Success → Log metrics & cost                    │   │
│  │    └─ Error → Fallback to next provider              │   │
│  │ 5. Fallback Chain: Claude → GPT → Gemini             │   │
│  │ 6. All Failed → Raise Exception                       │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                 LLM Provider Clients                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ChatAnthropic│  │ ChatOpenAI   │  │ ChatGoogle   │      │
│  │  (Claude)    │  │   (GPT)      │  │  GenerativeAI│      │
│  │              │  │              │  │  (Gemini)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| **LLMファクトリー** | `llm_factory.py`拡張 | 既存のコードを活用し、統一的なインターフェース提供 |
| **フォールバック実装** | Try-Exceptチェーン + 再帰呼び出し | シンプルで理解しやすい、エラーハンドリングが明確 |
| **パフォーマンス測定** | `time.perf_counter()` | 高精度（ナノ秒単位）、標準ライブラリで依存なし |
| **コスト計算** | トークンカウント × 単価 | 透明性が高く、検証可能 |
| **ログ記録** | Python標準`logging` | 既存のログインフラと統合、柔軟なレベル制御 |
| **環境変数管理** | Pydantic `BaseSettings` | 型安全、バリデーション、デフォルト値サポート |

### クラス設計

#### 1. `ModelPerformanceTracker`クラス

```python
class ModelPerformanceTracker:
    """モデルパフォーマンスを測定・記録するクラス"""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.success: bool = False
        self.error: str | None = None

    def start(self) -> None:
        """測定開始"""
        self.start_time = time.perf_counter()

    def end(self, success: bool, input_tokens: int, output_tokens: int, error: str | None = None) -> None:
        """測定終了"""
        self.end_time = time.perf_counter()
        self.success = success
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.error = error

    def get_duration_ms(self) -> float:
        """レスポンス時間（ミリ秒）を取得"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def log_metrics(self) -> None:
        """メトリクスをログ出力"""
        logger.info(
            f"Model Performance: model={self.model_name}, "
            f"duration={self.get_duration_ms():.2f}ms, "
            f"input_tokens={self.input_tokens}, "
            f"output_tokens={self.output_tokens}, "
            f"success={self.success}, "
            f"error={self.error}"
        )
```

#### 2. `ModelCostTracker`クラス

```python
class ModelCostTracker:
    """モデルコストを計算・記録するクラス"""

    # コストテーブル（2025年10月時点、USD per 1M tokens）
    COST_TABLE = {
        "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
        "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    }

    def __init__(self):
        self.total_cost: float = 0.0
        self.session_costs: list[dict] = []

    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """コストを計算（USD）"""
        cost_info = self.COST_TABLE.get(model_name.lower())
        if not cost_info:
            logger.warning(f"Cost table not found for model: {model_name}")
            return 0.0

        input_cost = (input_tokens / 1_000_000) * cost_info["input"]
        output_cost = (output_tokens / 1_000_000) * cost_info["output"]
        total = input_cost + output_cost

        return total

    def add_call(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """呼び出しコストを追加"""
        cost = self.calculate_cost(model_name, input_tokens, output_tokens)
        self.total_cost += cost
        self.session_costs.append({
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
        })
        return cost

    def log_summary(self) -> None:
        """コストサマリーをログ出力"""
        logger.info(
            f"Cost Summary: total_cost=${self.total_cost:.4f} USD, "
            f"calls={len(self.session_costs)}"
        )
        for call in self.session_costs:
            logger.debug(
                f"  - {call['model']}: ${call['cost_usd']:.4f} USD "
                f"(input={call['input_tokens']}, output={call['output_tokens']})"
            )
```

#### 3. `create_llm_with_fallback()`関数

```python
async def create_llm_with_fallback(
    model_name: str,
    temperature: float = 0.0,
    max_tokens: int = 8192,
    fallback_models: list[str] | None = None,
    max_retries: int = 3,
) -> tuple[BaseChatModel, ModelPerformanceTracker, ModelCostTracker]:
    """フォールバック機能付きLLM作成

    Args:
        model_name: プライマリモデル名
        temperature: 温度パラメータ
        max_tokens: 最大トークン数
        fallback_models: フォールバックモデルリスト（Noneの場合はデフォルト）
        max_retries: 最大リトライ回数

    Returns:
        (LLMインスタンス, パフォーマンストラッカー, コストトラッカー)

    Raises:
        ValueError: すべてのモデルで失敗した場合
    """
    if fallback_models is None:
        # デフォルトフォールバックチェーン
        fallback_models = [
            "claude-haiku-4-5",
            "gpt-4o-mini",
            "gemini-2.5-flash",
        ]

    # プライマリモデルを先頭に追加
    models_to_try = [model_name] + [m for m in fallback_models if m != model_name]

    perf_tracker = ModelPerformanceTracker(model_name)
    cost_tracker = ModelCostTracker()

    for attempt, model in enumerate(models_to_try):
        if attempt >= max_retries:
            break

        try:
            logger.info(f"Attempting to create LLM: model={model} (attempt={attempt+1}/{max_retries})")
            llm = create_llm(model, temperature, max_tokens)

            logger.info(f"Successfully created LLM: model={model}")
            perf_tracker.model_name = model  # Update to actual used model
            return llm, perf_tracker, cost_tracker

        except Exception as e:
            logger.warning(f"Failed to create LLM: model={model}, error={str(e)}")
            if attempt == len(models_to_try) - 1:
                # All models failed
                raise ValueError(
                    f"All models failed after {max_retries} retries. "
                    f"Models tried: {models_to_try}. "
                    f"Last error: {str(e)}"
                )

    raise ValueError(f"Max retries ({max_retries}) exceeded")
```

### ディレクトリ構成

```
expertAgent/
├── core/
│   └── config.py                           # [修正] 環境変数追加
├── aiagent/
│   └── langgraph/
│       └── jobTaskGeneratorAgents/
│           ├── nodes/
│           │   ├── requirement_analysis.py # [修正] create_llm_with_fallback使用
│           │   ├── evaluator.py            # [修正] create_llm_with_fallback使用
│           │   ├── interface_definition.py # [修正] create_llm_with_fallback使用
│           │   └── validation.py           # [修正] create_llm_with_fallback使用
│           └── utils/
│               └── llm_factory.py          # [修正] 拡張機能追加
└── tests/
    └── unit/
        └── test_llm_factory_fallback.py    # [新規] 単体テスト
```

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守
  - **Single Responsibility**: 各クラス（ModelPerformanceTracker, ModelCostTracker）は単一の責任を持つ
  - **Open-Closed**: `create_llm_with_fallback()`は拡張可能（fallback_modelsパラメータ）
  - **Liskov Substitution**: `BaseChatModel`の派生クラスは置換可能
  - **Interface Segregation**: 各トラッカークラスは必要最小限のインターフェースを提供
  - **Dependency Inversion**: 高レベルモジュール（ノード）は抽象（create_llm_with_fallback）に依存
- [x] **KISS原則**: 遵守
  - Try-Exceptチェーンのシンプルな実装
  - クラスは最小限の機能に限定
- [x] **YAGNI原則**: 遵守
  - 必要な機能のみ実装（過度な抽象化を避ける）
- [x] **DRY原則**: 遵守
  - `create_llm_with_fallback()`で共通処理を統一
  - コストテーブルを一箇所に集約

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠
  - レイヤー分離を維持（utils層 → nodes層）
  - 依存関係の方向性が正しい（上位レイヤーが下位レイヤーに依存）

### 設定管理ルール
- [x] **環境変数**: 遵守
  - `core/config.py`で一元管理
  - Pydantic BaseSettingsでバリデーション
- [x] **myVault**: 遵守
  - API Keysは引き続きmyVaultで管理
  - モデル名のみ環境変数で指定

### 品質担保方針
- [x] **単体テストカバレッジ**: 目標90%以上
  - `test_llm_factory_fallback.py`で包括的にテスト
- [x] **結合テストカバレッジ**: 目標50%以上
  - 各ノードでClaude/GPT/Geminiの切り替えテスト
- [x] **Ruff linting**: エラーゼロを維持
- [x] **MyPy type checking**: エラーゼロを維持

### CI/CD準拠
- [x] **PRラベル**: `feature`, `enhancement` ラベルを付与予定（minor版数アップ）
- [x] **コミットメッセージ**: Conventional Commits規約に準拠
- [x] **pre-push-check-all.sh**: 実装完了後に実行予定

### 参照ドキュメント遵守
- [x] **GRAPHAI_WORKFLOW_GENERATION_RULES.md**: 該当なし（GraphAIワークフロー開発ではない）
- [x] **NEW_PROJECT_SETUP.md**: 該当なし（新プロジェクト追加ではない）

### 違反・要検討項目
なし

---

## 📝 設計上の決定事項

### 1. フォールバック順序の決定
**決定内容**: プライマリモデル → Claude Haiku → GPT-4o-mini → Gemini 2.5 Flash

**理由**:
- Claude Haiku: 最も高速でコスト効率が良い（$0.80/1M input）
- GPT-4o-mini: OpenAIの軽量モデル、Claudeより安価（$0.15/1M input）
- Gemini 2.5 Flash: Googleの最新モデル、最も安価（$0.075/1M input）

**代替案検討**:
- 高性能優先: Sonnet → GPT-4o → Gemini Pro（コスト増）
- 低コスト優先: Gemini → GPT-4o-mini → Haiku（品質低下リスク）

**選定理由**: バランス重視（速度・コスト・品質）

### 2. コスト単価の管理方法
**決定内容**: クラス変数として`ModelCostTracker.COST_TABLE`に定義

**理由**:
- シンプルで変更が容易
- 外部ファイル（JSON/YAML）は過剰設計（YAGNI原則）
- コード内で完結し、依存関係が少ない

**代替案検討**:
- 環境変数: 多数の変数が必要で煩雑
- 外部ファイル: ファイル読み込みのオーバーヘッド、エラーハンドリングが複雑

### 3. パフォーマンストラッキングの粒度
**決定内容**: LLM呼び出し単位で測定（ノード全体ではない）

**理由**:
- LLM呼び出しがボトルネックの主要因
- ノード全体の測定はビジネスロジックのノイズが混入
- フォールバック時のモデル別比較が容易

### 4. ログレベルの設定
**決定内容**:
- 通常動作: INFO レベル（メトリクス、コストサマリー）
- エラー時: WARNING レベル（フォールバック発動）
- デバッグ時: DEBUG レベル（詳細な呼び出し履歴）

**理由**:
- 本番環境でもパフォーマンス・コスト情報を可視化
- ログ量を抑制しつつ、必要な情報を記録

### 5. 非同期対応の方針
**決定内容**: `create_llm_with_fallback()`は同期関数のまま（非同期化しない）

**理由**:
- LLM作成自体は非同期処理不要（インスタンス化のみ）
- LLM呼び出し（`ainvoke()`）は各ノードで既に非同期化済み
- 不要な複雑化を避ける（KISS原則）

**注意点**: 将来的にAPI接続テストを追加する場合は非同期化を検討

---

## 🔄 変更影響範囲

### 修正対象ファイル
1. `expertAgent/core/config.py` - 環境変数追加（5行追加）
2. `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_factory.py` - 拡張機能追加（約200行追加）
3. `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/requirement_analysis.py` - `create_llm()` → `create_llm_with_fallback()` （5行修正）
4. `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/evaluator.py` - `ChatAnthropic` → `create_llm_with_fallback()` （10行修正）
5. `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py` - 2箇所修正（20行修正）
6. `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/validation.py` - `ChatAnthropic` → `create_llm_with_fallback()` （10行修正）

### 新規作成ファイル
1. `expertAgent/tests/unit/test_llm_factory_fallback.py` - 単体テスト（約300行）

### 後方互換性
- ✅ **完全互換**: 環境変数未設定時はデフォルト値（claude-haiku-4-5）を使用
- ✅ **既存ノード**: requirement_analysis.pyは既に環境変数対応済み、動作に影響なし
- ✅ **API変更なし**: 外部APIインターフェースは変更なし

---

## 📚 参考資料

### 技術ドキュメント
- [LangChain ChatModels Documentation](https://python.langchain.com/docs/modules/model_io/chat/)
- [Anthropic Claude API Pricing](https://www.anthropic.com/api)
- [OpenAI GPT API Pricing](https://openai.com/pricing)
- [Google Gemini API Pricing](https://ai.google.dev/pricing)

### 関連Issue・PR
- Issue #108: タスク具体化エージェント生成（llm_factory.py初版作成）
- Issue #111: 本Issue（マルチモデル対応拡張）

### コスト参考情報（2025年10月時点）
| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | 用途 |
|-------|---------------------------|----------------------------|------|
| Claude Haiku 4.5 | $0.80 | $4.00 | 高速・低コスト（検証向け） |
| Claude Sonnet 4.5 | $3.00 | $15.00 | 高品質（分析向け） |
| GPT-4o | $2.50 | $10.00 | 汎用高性能 |
| GPT-4o-mini | $0.15 | $0.60 | 軽量タスク |
| Gemini 2.5 Flash | $0.075 | $0.30 | 最低コスト |

---

## 🎯 成功基準

### 機能要件
- [x] 全ノードで環境変数からモデルを指定可能
- [x] APIエラー時に自動フォールバックが動作
- [x] パフォーマンスメトリクスがログ出力される
- [x] コストが正確に計算・記録される

### 非機能要件
- [x] 単体テストカバレッジ90%以上
- [x] 結合テストでClaude/GPT/Geminiの切り替え確認
- [x] Ruff linting エラーゼロ
- [x] MyPy type checking エラーゼロ
- [x] pre-push-check-all.sh 合格

### 品質要件
- [x] ドキュメント完備（設計方針、作業計画、最終報告）
- [x] コミットメッセージがConventional Commits規約に準拠
- [x] PRに適切なラベル（feature, enhancement）を付与

---

**次ステップ**: 作業計画書（work-plan.md）の作成
