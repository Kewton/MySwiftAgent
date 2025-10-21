# Phase 11 作業計画: LLMベースの動的提案生成への移行

**作成日**: 2025-10-21
**予定工数**: 2時間15分
**完了予定**: 2025-10-21 (当日完了予定)

---

## 📚 参考ドキュメント

**必須参照**:
- [x] [Phase 11 設計方針](./phase-11-design-policy.md)
- [x] [Phase 10-D 修正レポート](./phase-10d-fix-report.md)
- [x] [戦略パターン分析](./strategy-pattern-analysis.md)

**推奨参照**:
- [x] [アーキテクチャ概要](../../docs/design/architecture-overview.md)
- [x] [環境変数管理](../../docs/design/environment-variables.md)
- [x] [myVault連携](../../docs/design/myvault-integration.md)

---

## 🎯 作業目標

### ビジネス要求
- **Phase 10-Dの課題解決**: Scenario 2で0件の提案生成を3件以上に改善
- **保守性向上**: ルールベース戦略の追加が不要（YAML更新のみで拡張可能）
- **拡張性向上**: LLMの創造性により多様な提案を生成

### 機能要件
- FR-1: ルールベース戦略（Strategy 1-4）を完全削除
- FR-2: LLMベースの動的提案生成を実装（Claude Haiku 4.5 + myVault統合）
- FR-3: Pydanticスキーマで提案品質を担保
- FR-4: Scenario 2で3件以上の提案生成
- FR-5: 既存のPhase 10-D機能を維持（Scenario 1, 3での正常動作）

### 非機能要件
- NFR-1: レスポンスタイム +40秒以内（Phase 10-D比）
- NFR-2: LLMコスト $0.02-0.08/タスク以内
- NFR-3: 提案品質の安定性 80%以上
- NFR-4: 全468単体テスト合格
- NFR-5: Ruff linting/MyPy type checking エラーゼロ

---

## 📊 Phase分解

### Phase 11-1: 既存戦略の削除とLLM実装 (60分)

**目的**: ルールベース戦略を削除し、LLMベースの実装を追加

**タスク**:
- [ ] `_generate_capability_based_relaxations()` 関数を削除（lines 469-632）
- [ ] `RequirementRelaxationSuggestion` Pydanticスキーマを追加
- [ ] `_call_anthropic_for_relaxation_suggestions()` 関数を実装（myVault統合）
- [ ] `_generate_llm_based_relaxation_suggestions()` 関数を実装
- [ ] `_generate_requirement_relaxation_suggestions()` を修正（LLM版を呼び出す）
- [ ] エラーハンドリング追加（JSON解析失敗、API呼び出し失敗）
- [ ] ログ追加（デバッグ・警告・エラー）

**変更ファイル**:
- `expertAgent/app/api/v1/job_generator_endpoints.py`
  - 削除: lines 469-632 (Strategy 1-4)
  - 追加: `RequirementRelaxationSuggestion` スキーマ（約40行）
  - 追加: `_call_anthropic_for_relaxation_suggestions()` （約50行）
  - 追加: `_generate_llm_based_relaxation_suggestions()` （約80行）

**検証**:
- [ ] Scenario 1でテスト実行
- [ ] 少なくとも1件の提案生成を確認
- [ ] LLMレスポンスのJSON形式が適合することを確認

**成果物**:
- LLMベースの緩和提案生成機能（完動）
- Scenario 1テスト結果（JSON出力）

---

### Phase 11-2: Scenario 2での検証とチューニング (45分)

**目的**: Scenario 2で3件以上の提案生成を達成

**タスク**:
- [ ] Scenario 2で実行
- [ ] 提案数が3件以上生成されることを確認
- [ ] プロンプトをチューニング（必要に応じて）
  - 緩和タイプの選択が適切か確認
  - 実装ステップの具体性を確認
  - 利用可能機能の活用度を確認
- [ ] Scenario 3でリグレッションテスト（0件が正常）
- [ ] レスポンスタイム測定（Phase 10-D + 40秒以内）

**検証条件**:
- [ ] Scenario 1: 1件以上の提案生成 ✅
- [ ] Scenario 2: 3件以上の提案生成 ✅
- [ ] Scenario 3: 0件の提案（正常動作） ✅
- [ ] レスポンスタイム: Phase 10-D + 40秒以内 ✅

**チューニング対象**（必要に応じて）:
- LLMプロンプトの改善（明確性・具体性）
- temperature パラメータ調整（0.7 → 0.5 など）
- max_tokens 調整（2048 → 3072 など）

**成果物**:
- Scenario 2テスト結果（3件以上の提案生成）
- Scenario 3リグレッションテスト結果
- レスポンスタイム測定結果

---

### Phase 11-3: 品質チェックとドキュメント作成 (30分)

**目的**: 品質基準を満たし、作業成果をドキュメント化

**品質チェック**:
- [ ] 全468 unit tests passed
- [ ] Ruff linting: エラーゼロ
- [ ] Ruff formatting: 適用済み
- [ ] MyPy type checking: エラーゼロ
- [ ] Scenario 1-3: 全テスト成功
- [ ] LLMコスト試算: タスクあたり $0.08 以下
- [ ] カバレッジ: 90%以上維持

**ドキュメント作成**:
- [ ] `phase-11-results.md`: 実装結果・テスト結果・性能評価
- [ ] コミットメッセージ: Conventional Commits形式で詳細な変更内容

**コミット・プッシュ**:
- [ ] Git add: 変更ファイルすべて
- [ ] Git commit: `feat(expertAgent): implement Phase 11 LLM-based relaxation suggestions`
- [ ] Git push: `feature/issue/97`

**成果物**:
- `phase-11-results.md`（実装報告書）
- Git commit（Phase 11完了）
- Git push（リモートリポジトリ反映）

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守予定
  - Single Responsibility: `_call_anthropic_for_relaxation_suggestions()` はLLM呼び出しのみ、`_generate_llm_based_relaxation_suggestions()` は提案生成のみ
  - Open-Closed: LLMプロンプトをYAML外部化すれば、コード変更なしで拡張可能
  - Dependency Inversion: myVaultClientに依存（インターフェース経由）
- [x] **KISS原則**: 遵守予定
  - 複雑なルールベース戦略を削除し、LLM単一実装に統一
- [x] **YAGNI原則**: 遵守予定
  - 現時点で必要な機能のみ実装（キャッシュ、並列処理は将来的検討）
- [x] **DRY原則**: 遵守予定
  - LLM呼び出しロジックを `_call_anthropic_for_relaxation_suggestions()` に集約

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠予定
  - expertAgent内のLangGraph拡張として実装
  - レイヤー分離を維持（API層 → ビジネスロジック層）
- [x] **依存関係の方向性**: 正しい
  - expertAgent → myVault（適切な依存方向）
  - expertAgent → Anthropic API（外部サービス依存）

### 設定管理ルール
- [x] **環境変数管理**: 遵守
  - `JOB_GENERATOR_MAX_TOKENS` など既存環境変数を活用
- [x] **myVault管理**: 遵守
  - `ANTHROPIC_API_KEY` をmyVaultから取得（環境変数非使用）

### 品質担保方針
- [x] **単体テストカバレッジ**: 90%以上維持予定
  - 既存468テストを全合格させる
  - 新規関数のユニットテストは追加しない（統合テストで検証）
- [x] **結合テストカバレッジ**: 50%以上維持予定
  - Scenario 1-3での実行で検証
- [x] **Ruff linting**: エラーゼロ予定
  - 実装後に `uv run ruff check .` で検証
- [x] **MyPy type checking**: エラーゼロ予定
  - 実装後に `uv run mypy .` で検証

### CI/CD準拠
- [x] **PRラベル**: `feature` ラベル付与予定（minor bump）
- [x] **コミットメッセージ**: Conventional Commits遵守予定
  - 形式: `feat(expertAgent): implement Phase 11 LLM-based relaxation suggestions`
- [x] **pre-push-check.sh**: 実行予定（Phase 11-3で実施）

### 参照ドキュメント遵守
- [x] **新プロジェクト追加時**: N/A（既存プロジェクトの改修）
- [x] **GraphAI ワークフロー開発時**: N/A（expertAgent APIエンドポイント改修）

### 違反・要検討項目
**なし**: すべての制約条件を遵守予定

---

## 📅 スケジュール

| Phase | 開始予定 | 完了予定 | 所要時間 | 状態 |
|-------|---------|---------|---------|------|
| **Phase 11-1** | 即時 | +60分 | 60分 | 予定 |
| **Phase 11-2** | +60分 | +105分 | 45分 | 予定 |
| **Phase 11-3** | +105分 | +135分 | 30分 | 予定 |
| **合計** | - | - | **2時間15分** | - |

---

## 🎯 成功基準

### 必須条件（Phase 11完了の定義）

1. **✅ Scenario 2で3件以上の提案生成**
   - 検証方法: Scenario 2テスト実行
   - 合格基準: `requirement_relaxation_suggestions` に3件以上
   - 期待結果: 6個の実現困難タスクに対して3-6件の提案

2. **✅ 全単体テスト合格**
   - 検証方法: `uv run pytest tests/unit/ -x`
   - 合格基準: 468テスト全合格

3. **✅ 品質チェック合格**
   - Ruff linting: エラーゼロ
   - MyPy type checking: エラーゼロ
   - Ruff formatting: 適用済み

4. **✅ レスポンスタイム基準**
   - 検証方法: Scenario 1-3の実行時間測定
   - 合格基準: Phase 10-D + 50秒以内（許容範囲）
   - 参考値: Phase 10-D（40-52秒） → Phase 11（60-80秒想定）

### 推奨条件

1. **🟡 LLMコスト最適化**
   - 検証方法: Anthropic API使用量モニタリング（myVault経由）
   - 目標: タスクあたり $0.05 以下
   - 許容: タスクあたり $0.08 以下

2. **🟡 提案品質の安定性**
   - 検証方法: 同一シナリオで3回実行（時間があれば）
   - 目標: 80%以上の確率で同等の提案

---

## ⚠️ リスクと対策

### リスク1: LLMレスポンスのJSON形式不適合

**リスク内容**:
- LLMが指定したJSON形式を返さない
- Pydantic検証エラーが頻発

**対策**:
- プロンプトで明確にJSON配列形式を指定（「他のテキストは含めないこと」を強調）
- Pydantic検証失敗時は空リストを返却（エラーログ記録）
- 最大3回のリトライロジック（Phase 12以降で検討）

**影響度**: 🟡 中（提案数が減少するが、システムはクラッシュしない）

---

### リスク2: レスポンスタイム増加

**リスク内容**:
- LLM呼び出しで20-40秒の遅延
- ユーザー体験の低下

**対策**:
- Claude Haiku 4.5（高速モデル）を使用
- タイムアウト設定（40秒）
- 実現困難タスクが多い場合（6個以上）は警告ログ
- 将来的に並列処理の検討（Phase 12以降）

**影響度**: 🟡 中（許容範囲内の遅延）

---

### リスク3: LLMコスト増加

**リスク内容**:
- 実現困難タスクが多いと大量のAPI呼び出し
- コスト増加

**対策**:
- Claude Haiku 4.5（コスト効率的なモデル）を使用
- 最大3件の提案に制限
- max_tokens: 2048 に制限
- myVault経由でAPIキー管理（使用量の一元管理）

**影響度**: 🟢 低（タスクあたり $0.02-0.08 で許容範囲）

---

### リスク4: 提案品質のばらつき

**リスク内容**:
- LLMの出力が不安定
- 同じタスクで異なる提案が生成される

**対策**:
- temperature: 0.7（やや低めで安定性重視）
- プロンプトに具体的な例を含める
- Pydantic検証で品質を担保
- 将来的にfew-shot examplesの追加（Phase 12以降）

**影響度**: 🟡 中（品質は許容範囲だが、改善余地あり）

---

## 💡 技術選定の根拠

### Claude Haiku 4.5を選択する理由

| 基準 | Claude Haiku 4.5 | Gemini 1.5 Flash | GPT-4o mini |
|------|-----------------|------------------|-------------|
| **既存ノードとの統一** | ✅ 他のノードと同じモデル | ⚠️ 異なるモデル | ⚠️ 異なるモデル |
| **myVault統合** | ✅ 統一されたAPIキー管理 | ⚠️ 別途環境変数管理 | ⚠️ 別途環境変数管理 |
| **速度** | ✅ 高速 | ✅ 高速 | 🟡 中速 |
| **品質** | ✅ 高（構造化出力に強い） | 🟡 中 | 🟡 中 |
| **コスト** | 🟡 中（$0.00025/1K input, $0.00125/1K output） | ✅ 最安 | 🟡 中 |

**結論**: Claude Haiku 4.5が最適（既存ノードとの統一・myVault統合・品質）

---

## 📝 備考

### Phase 11以降の改善案（Phase 12-14で検討）

1. **Few-shot Examples の追加**（Phase 12）
   - プロンプトに成功事例を含める
   - 提案品質の安定性向上

2. **並列処理の導入**（Phase 13）
   - 複数の実現困難タスクを並列でLLM呼び出し
   - レスポンスタイム短縮

3. **キャッシュ機構の導入**（Phase 14）
   - 同一タスクの提案をキャッシュ
   - LLMコスト削減

4. **A/Bテストの実施**（Phase 15）
   - Phase 10-D（ルールベース） vs Phase 11（LLMベース）
   - 提案品質の定量評価

---

## 📋 実装チェックリスト

### Phase 11-1: LLM実装

- [ ] `_generate_capability_based_relaxations()` を削除（lines 469-632）
- [ ] `RequirementRelaxationSuggestion` Pydanticスキーマを追加
- [ ] `_call_anthropic_for_relaxation_suggestions()` を実装（myVault統合）
- [ ] `_generate_llm_based_relaxation_suggestions()` を実装
- [ ] `_generate_requirement_relaxation_suggestions()` を修正（LLM版を呼び出す）
- [ ] エラーハンドリング追加（JSON解析失敗、API呼び出し失敗）
- [ ] ログ追加（デバッグ・警告・エラー）

### Phase 11-2: テスト・検証

- [ ] Scenario 1でテスト実行
- [ ] Scenario 2でテスト実行（3件以上の提案確認）
- [ ] Scenario 3でリグレッションテスト
- [ ] レスポンスタイム測定
- [ ] LLMコスト試算

### Phase 11-3: 品質チェック

- [ ] 単体テスト: 468テスト全合格
- [ ] Ruff linting: エラーゼロ
- [ ] Ruff formatting: 適用済み
- [ ] MyPy type checking: エラーゼロ
- [ ] カバレッジ: 90%以上維持

### Phase 11-4: ドキュメント

- [ ] `phase-11-results.md` 作成
- [ ] コミットメッセージ作成
- [ ] Git add, commit, push

---

**次のアクション**: Phase 11-1の実装開始 🚀
