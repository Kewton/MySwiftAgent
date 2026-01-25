# アーキテクチャレビュー: Issue #350

**レビュー対象**: `dev-reports/feature/issue/350/design-policy.md`
**レビュー日**: 2026-01-11
**レビュアー**: Claude (Senior Software Architect)

---

## 1. 設計原則の遵守確認

### SOLID原則チェック

| 原則 | 状態 | 評価 | コメント |
|------|------|------|---------|
| **S**ingle Responsibility | :white_check_mark: 準拠 | 良好 | Strategy毎に単一責任（GraphAI生成/TaskFlow生成） |
| **O**pen/Closed | :white_check_mark: 準拠 | 優秀 | Strategy Pattern採用で拡張に開いて修正に閉じている |
| **L**iskov Substitution | :white_check_mark: 準拠 | 良好 | `WorkflowGeneratorStrategy` Protocol準拠で置換可能 |
| **I**nterface Segregation | :white_check_mark: 準拠 | 良好 | 3メソッドのシンプルなインターフェース |
| **D**ependency Inversion | :white_check_mark: 準拠 | 良好 | Protocol（抽象）に依存、具象クラスに依存しない |

### その他の原則

| 原則 | 状態 | 評価 | コメント |
|------|------|------|---------|
| **KISS** | :white_check_mark: 準拠 | 良好 | Phase 4のみの変更で影響範囲を限定 |
| **YAGNI** | :white_check_mark: 準拠 | 良好 | 必要最小限の変更（エンジン切り替えのみ） |
| **DRY** | :white_check_mark: 準拠 | 良好 | 共通PromptBuilder + ルールファイル方式でコード重複回避 |

---

## 2. アーキテクチャ評価

### 構造的品質

| 評価項目 | スコア(1-5) | コメント |
|---------|------------|----------|
| **モジュール性** | 5 | Strategy Patternによる明確な分離、既存構造との整合性◎ |
| **結合度** | 4 | 低結合を維持、ただしPromptBuilder共有で若干の結合あり |
| **凝集度** | 5 | 各Strategyが独自の責務を持ち高凝集 |
| **拡張性** | 5 | 将来的なエンジン追加（例: Temporal, Prefect）が容易 |
| **保守性** | 4 | 既存コードのリファクタリング量が適度、テスト計画も充実 |

**構造的品質スコア: 4.6/5.0**

### パフォーマンス観点

| 項目 | 評価 | 詳細 |
|------|------|------|
| **レスポンスタイム予測** | 維持 | LLM呼び出し回数は変わらないため3-5分を維持 |
| **スループット評価** | 改善期待 | TaskFlow V2のシンプルな構造でリトライ減少が期待 |
| **リソース使用効率** | 同等 | JSONとYAMLで大差なし |
| **スケーラビリティ** | 同等 | 水平スケーリングへの影響なし |

---

## 3. セキュリティレビュー

### OWASP Top 10 チェック

| 脆弱性カテゴリ | 状態 | 対策状況 |
|--------------|------|---------|
| **A01: インジェクション** | :white_check_mark: 対策済 | Pydanticによる入力検証、LLM出力のスキーマ検証 |
| **A02: 認証の破綻** | N/A | 本機能は認証に関与しない |
| **A03: 機微データの露出** | :white_check_mark: 対策済 | `${secrets.KEY}`形式でmyVault経由、直接埋め込み禁止 |
| **A04: XXE** | N/A | JSON形式でXXEリスクなし |
| **A05: アクセス制御の不備** | N/A | 本機能はアクセス制御に関与しない |
| **A06: セキュリティ設定ミス** | :white_check_mark: 対策済 | デフォルトHTTPS強制、verify_ssl=True |
| **A07: XSS** | N/A | バックエンドAPI、フロントエンド出力なし |
| **A08: デシリアライゼーション** | :white_check_mark: 対策済 | Pydanticによる型安全なデシリアライズ |
| **A09: 既知の脆弱性** | :white_check_mark: 対策済 | 新規依存ライブラリ追加なし |
| **A10: ログ/モニタリング不足** | :white_check_mark: 対策済 | 既存Langfuse統合を継続 |

### TaskFlow V2 セキュリティ強化点

| 機能 | 評価 |
|------|------|
| HTTPS強制 | :white_check_mark: 設計に明記 |
| SSRF対策（プライベートIP遮断） | :white_check_mark: バリデーター設計に含む |
| パス走査保護 | :white_check_mark: `..`パターン拒否を明記 |

**セキュリティ評価: A (優秀)**

---

## 4. 既存システムとの整合性

### 統合ポイント

| 項目 | 状態 | 評価 |
|------|------|------|
| **API互換性** | :white_check_mark: 維持 | `engine`パラメータ追加のみ（後方互換） |
| **データモデル整合性** | :white_check_mark: 良好 | `WorkflowGenOutput`に`workflow_format`追加 |
| **認証/認可の一貫性** | :white_check_mark: 維持 | 変更なし |
| **ログ/監視の統合** | :white_check_mark: 維持 | Langfuse統合継続 |

### 技術スタックの適合性

| 項目 | 評価 | 詳細 |
|------|------|------|
| **既存技術との親和性** | 優秀 | Pydantic, LangChain, ValidationPipeline全て既存パターン |
| **チームスキルセット** | 適合 | 新技術導入なし、Python/Pydanticスキルで対応可能 |
| **運用負荷への影響** | 低 | 既存監視・運用体制をそのまま活用 |

### 現在の実装との差異（調査結果）

| 設計要素 | 設計方針書 | 現在の実装 | 整合性 |
|---------|-----------|-----------|-------|
| エンジン選択箇所 | Orchestrator層 | YamlGenerator層 | :warning: 要確認 |
| Schema構造 | Pydantic | Pydantic + to_yaml() | :white_check_mark: 整合 |
| PromptBuilder | 共通 + ルールファイル | assembler + rules/ + injector | :white_check_mark: 整合 |
| Validator | ValidationPipeline | ValidationPipeline統合済 | :white_check_mark: 整合 |

---

## 5. リスク評価

| リスク種別 | 内容 | 影響度 | 発生確率 | 対策優先度 |
|-----------|------|-------|---------|-----------|
| **技術的リスク** | LLM出力がTaskFlow形式に安定しない | 中 | 中 | 高: Few-shot充実 |
| **技術的リスク** | エンジン切り替えロジックの責務配置が不明確 | 低 | 中 | 中: 設計書明確化 |
| **運用リスク** | GraphAI/TaskFlow並存による保守コスト増 | 低 | 高 | 低: 長期的にGraphAI廃止検討 |
| **セキュリティリスク** | LLM生成URLのSSRF | 低 | 低 | 高: バリデーター実装済 |
| **ビジネスリスク** | 既存ワークフローの移行コスト | 低 | 中 | 中: 並存期間を設定 |

### リスクマトリクス

```
         影響度
    高    │ ①            │
          │              │
    中    │ ② ③         │
          │              │
    低    │ ④ ⑤         │
          └──────────────┘
            低   中   高
              発生確率

① LLM出力安定性 → Few-shot examples充実で対処
② エンジン切り替え責務 → 設計書明確化で対処
③ 保守コスト増 → 長期的にGraphAI廃止検討
④ SSRF → バリデーター実装済
⑤ 移行コスト → 並存期間設定
```

---

## 6. 改善提案

### 必須改善項目（Must Fix）

#### MF-1: エンジン選択責務の明確化

**問題**: 設計方針書ではOrchestratorでエンジン選択と記載されているが、現在の実装ではYamlGeneratorSubWorkflow層で制御されている。

**修正案**:
```python
# Option A: 現在の実装に合わせる（推奨）
# workflows/workflow_gen/workflow.py で Strategy 選択

class WorkflowGenWorkflow:
    def __init__(self, engine: str = "taskflow"):
        self.strategy = self._create_strategy(engine)

    def _create_strategy(self, engine: str) -> WorkflowGeneratorStrategy:
        if engine == "taskflow":
            return TaskFlowGeneratorStrategy()
        elif engine == "graphai":
            return GraphAIGeneratorStrategy()
        raise ValueError(f"Unknown engine: {engine}")
```

**設計方針書の修正箇所**:
- 「オーケストレーションレイヤー」の「エンジン選択ロジック追加」を「ワークフロー生成レイヤー」に移動
- `orchestrator.py`の変更範囲を「engine設定の受け渡しのみ」に修正

### 推奨改善項目（Should Fix）

#### SF-1: TaskFlowStep の discriminated union 改善

**問題**: `config`フィールドが`Union[ApiRestConfig, TransformConfig, CodeJsConfig]`で型の判別が困難。

**修正案**:
```python
class TaskFlowStep(BaseModel):
    id: str
    type: Literal["api_rest", "transform", "code_js"]
    config: dict  # 型はtypeに基づいて検証

    @model_validator(mode="after")
    def validate_config_by_type(self) -> "TaskFlowStep":
        config_models = {
            "api_rest": ApiRestConfig,
            "transform": TransformConfig,
            "code_js": CodeJsConfig,
        }
        model = config_models[self.type]
        model.model_validate(self.config)
        return self
```

#### SF-2: Few-shot examples の構造化

**問題**: Few-shot examplesが`graphai/`と`taskflow/`に分離される設計だが、パターン選択ロジックが不明。

**修正案**:
- `prompt_builder/few_shot/`に`selector.py`を追加
- パターンとTaskFlow構造のマッピングを明示化
- 例: `api_call_pattern.yaml` → TaskFlow `api_rest`ステップの例示

#### SF-3: テスト計画の詳細化

**問題**: テストファイル名は記載されているが、具体的なテストケースが不明。

**修正案**: 以下のテストケースを明記
```markdown
### test_taskflow_generator.py
- test_generate_simple_api_workflow: 単純なAPI呼び出しワークフロー生成
- test_generate_transform_workflow: データ変換ワークフロー生成
- test_generate_parallel_workflow: 並列実行ワークフロー生成
- test_generate_conditional_workflow: 条件分岐ワークフロー生成
- test_generate_with_secrets: シークレット参照を含むワークフロー生成
- test_validation_error_feedback: バリデーションエラー時のフィードバック
```

### 検討事項（Consider）

#### C-1: GraphAI廃止ロードマップ

**検討理由**: GraphAIとTaskFlow V2の並存は長期的には保守コストを増大させる。

**提案**:
1. Phase 1（現Issue）: TaskFlow V2をデフォルト化、GraphAIは`engine=graphai`で利用可能
2. Phase 2（6ヶ月後）: 新規ワークフローはTaskFlow V2のみ、既存GraphAIワークフローの移行ツール提供
3. Phase 3（12ヶ月後）: GraphAI生成機能を廃止（Deprecated警告後）

#### C-2: TaskFlow V2のcode_js制限

**検討理由**: `code_js`ノードはサンドボックス実行だが、任意JavaScriptのセキュリティリスクが残る。

**提案**:
- LLM生成時に`code_js`ノードの使用を制限（ホワイトリストされた関数のみ）
- または`code_js`は手動作成のみとし、LLM生成対象から除外

#### C-3: エラーメッセージの国際化

**検討理由**: バリデーションエラーが日本語/英語混在。

**提案**: 将来的にエラーコード体系を導入し、ローカライズ対応を検討

---

## 7. ベストプラクティスとの比較

### 業界標準との差異

| 標準パターン | 本設計での採用 | 評価 |
|------------|--------------|------|
| Strategy Pattern | :white_check_mark: 採用 | 適切な適用 |
| Factory Pattern | :white_check_mark: 採用予定 | Generator生成に使用 |
| Pipeline Pattern | :white_check_mark: 採用済 | ValidationPipeline |
| Builder Pattern | :white_check_mark: 採用済 | PromptBuilder |
| Repository Pattern | N/A | 本機能では不要 |

### 代替アーキテクチャ案

#### 代替案1: Plugin Architecture

**説明**: エンジンをプラグインとして動的ロード

**メリット**:
- 完全な疎結合
- サードパーティエンジン追加が容易
- ホットリロード可能

**デメリット**:
- 実装複雑度が高い
- 本Issueの要件に対してオーバーエンジニアリング
- YAGNI違反

**判定**: 不採用（Strategy Patternで十分）

#### 代替案2: Configuration-based Switching

**説明**: 設定ファイルでエンジンを切り替え（リクエスト単位ではなく）

**メリット**:
- API変更不要
- 運用が単純

**デメリット**:
- ユーザーがリクエスト単位で選択できない
- AB テストや段階移行が困難

**判定**: 不採用（本設計の方が柔軟性が高い）

#### 代替案3: 完全置き換え（GraphAI廃止）

**説明**: GraphAI生成を廃止し、TaskFlow V2のみに

**メリット**:
- 実装がシンプル
- 保守コストなし

**デメリット**:
- 後方互換性なし
- 既存ワークフローの即座の移行が必要

**判定**: 不採用（段階的移行が望ましい）

---

## 8. 総合評価

### レビューサマリ

| カテゴリ | スコア | 評価 |
|---------|-------|------|
| 設計原則遵守 | 5/5 | 優秀 |
| 構造的品質 | 4.6/5 | 良好 |
| セキュリティ | A | 優秀 |
| 既存システム整合性 | 4/5 | 良好（軽微な修正必要） |
| リスク管理 | 4/5 | 良好 |

**全体評価**: ⭐⭐⭐⭐☆（4.3/5.0）

### 強み

1. **SOLID原則への準拠**: Strategy Patternの適切な適用でOpen/Closed原則を満たす
2. **最小変更範囲**: Phase 4のみの変更でリスクを限定
3. **セキュリティ強化**: TaskFlow V2のセキュリティ機能を最大限活用
4. **後方互換性**: GraphAI機能を維持しつつ段階的移行を可能に
5. **既存パターンの活用**: 新技術導入なし、チーム学習コスト最小

### 弱み

1. **エンジン選択責務の曖昧さ**: 設計書と現在の実装で責務配置が異なる
2. **並存による複雑性**: 2つのエンジン対応で長期的保守コスト増
3. **テスト計画の詳細不足**: 具体的テストケースの記載が不十分

### 総評

本設計方針は、Issue #350の要件「ワークフロー生成エージェントV2の対象エンジン切り替え」を適切に満たす設計となっています。Strategy Patternの採用により、拡張性と保守性を確保しつつ、既存機能への影響を最小化しています。

セキュリティ面では、TaskFlow V2のHTTPS強制、SSRF対策、パス走査保護を活用し、GraphAIと比較して大幅な改善が見込めます。

軽微な修正として、エンジン選択責務の明確化（設計書の修正）を推奨します。これにより、実装時の混乱を防ぎ、コードレビューの効率化が期待できます。

### 承認判定

:white_check_mark: **承認（Approved）** - 2026-01-11 更新

**対応完了項目**:
- [x] **MF-1**: エンジン選択責務の明確化（設計方針書修正済）
- [x] **SF-1**: TaskFlowStep の discriminated union 改善（model_validator追加）
- [x] **SF-2**: Few-shot examples の構造化（selector.py設計追加）
- [x] **SF-3**: テスト計画の詳細化（60+テストケース追加）
- [x] **C-1**: GraphAI廃止ロードマップ追加
- [x] **C-2**: code_js LLM生成制限追加
- [x] **C-3**: エラーメッセージ国際化計画追加

### 次のステップ

1. :white_check_mark: **設計方針書の修正**: 全改善項目を反映済み
2. :arrow_right: **実装着手**: Phase 1（基盤整備）から開始可能
3. :arrow_right: **Issue分割**: 必要に応じてサブIssueを作成

---

**レビュー完了**: 2026-01-11
**承認更新**: 2026-01-11（全改善項目対応完了）
