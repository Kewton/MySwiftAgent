# 設計方針書: Issue #409 - 複数独立タスク存在時のデータフロー設計不備

## 1. 概要

### 1.1 問題の定義

複数の独立タスク（`dependencies=[]`）が存在する場合、2番目以降の独立タスクがユーザー入力を受け取れず、データが失われる問題を解決する。

### 1.2 影響範囲

- **expertAgent**: MasterManagerSubWorkflowのbody_template生成ロジック
- **Issue #408**: ユーザー入力フィールド名の整合性検証機能の完全性

### 1.3 設計方針の基本原則

1. **後方互換性の維持**: 既存のレガシー呼び出しを破壊しない
2. **段階的移行**: TaskFlowエンジンを優先し、GraphAIは将来対応
3. **エラー検出の強化**: 同名フィールド衝突時の型チェックとエラー/警告の使い分け
4. **最小限の変更**: YAGNIとKISS原則に従い、必要最小限の修正に留める
5. **早期エラー検出**: 型不一致は実行時エラーを防ぐため早期にValueErrorを発生

---

## 2. アーキテクチャ設計

### 2.1 システム構成図

```mermaid
graph TB
    subgraph "Job Generation Pipeline"
        A[User Input] --> B[Task Generation]
        B --> C[Interface Design]
        C --> D[Registration Phase]
        D --> E[Workflow Generation]
    end

    subgraph "Registration Phase (本Issue対象)"
        D1[MasterManagerSubWorkflow]
        D1 --> D2[_build_body_template]
        D1 --> D3[_get_user_input_schema]
        D2 --> D4[独立タスク判定]
        D3 --> D5[スキーママージ]
    end

    subgraph "Data Flow"
        F[job.body.user_input] --> G1[Task 1<br/>dependencies=[]]
        F --> G2[Task 2<br/>dependencies=[]]
        G1 --> H[Task 3<br/>dependencies=[1]]
        G2 --> H
    end
```

### 2.2 レイヤー構成

| レイヤー | 責務 | 本Issueでの変更 |
|---------|------|----------------|
| **Workflow Generation** | ワークフロー定義の生成 | 変更なし |
| **Registration** | マスター定義の登録 | body_template生成ロジックを修正 |
| **Interface Design** | インターフェース設計と検証 | 変更なし（Issue #408で実装済み） |
| **Task Generation** | タスクの生成 | 変更なし |

---

## 3. 技術選定

### 3.1 実装技術の選択

| カテゴリ | 選定技術 | 選定理由 | 既存との整合性 |
|---------|---------|---------|---------------|
| **判定ロジック** | 条件分岐の拡張 | シンプルで理解しやすい | 既存の`if order == 0`パターンを拡張 |
| **スキーママージ** | 辞書のマージ処理 | Python標準的な手法 | 既存のスキーマ処理と一致 |
| **ログ出力** | Python logging | 既存のログシステムを使用 | loggerインスタンスが既に存在 |
| **テストフレームワーク** | pytest | 既存のテストと統一 | 全プロジェクトで使用 |

### 3.2 拒否した代替案

| 代替案 | 拒否理由 |
|--------|---------|
| 新しい抽象化層の追加 | YAGNI原則違反、過剰設計 |
| 全タスクのbody_template再設計 | 影響範囲が大きすぎる |
| GraphAI同時対応 | スコープが広がりすぎる |

---

## 4. 設計パターン

### 4.1 既存パターンの活用

**テンプレートメソッドパターンの継続**
- `_build_body_template`メソッドの構造を維持
- 新しい条件分岐を既存の流れに統合

**ビルダーパターンの拡張**
- `_get_user_input_schema`でのスキーママージ処理
- 段階的なプロパティ構築

### 4.2 新規適用パターン

本Issueでは新しいデザインパターンの導入は行わない（KISS原則）。

---

## 5. データモデル設計

### 5.1 変更なし

既存のデータモデルに変更を加えない。以下の構造を維持：

```python
# TaskDefinition (変更なし)
class TaskDefinition:
    id: str
    name: str
    dependencies: list[str]  # 空リストが独立タスクを示す
    # ...

# InterfaceSchema (変更なし)
class InterfaceSchema:
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    # ...
```

---

## 6. API設計

### 6.1 内部API変更

#### _build_body_template メソッドの拡張

**変更前:**
```python
def _build_body_template(
    self,
    order: int,
    task: TaskDefinition | None = None,
    # ...
) -> dict[str, Any]:
    if order == 0:
        return {...}  # user_input使用
    # order > 0 は全て前タスク参照
```

**変更後:**
```python
def _build_body_template(
    self,
    order: int,
    task: TaskDefinition | None = None,
    # ...
) -> dict[str, Any]:
    if order == 0 or (task is not None and not task.dependencies):
        return {...}  # user_input使用
    # 依存関係があるタスクのみ前タスク参照
```

#### _get_user_input_schema メソッドの拡張

**変更前:**
```python
def _get_user_input_schema(
    self,
    sorted_tasks: list[TaskDefinition],
    interfaces: dict[str, InterfaceSchema],
) -> dict[str, Any] | None:
    # 最初のタスクのみ
```

**変更後:**
```python
def _get_user_input_schema(
    self,
    sorted_tasks: list[TaskDefinition],
    interfaces: dict[str, InterfaceSchema],
) -> dict[str, Any] | None:
    # 全独立タスクのスキーマをマージ
```

### 6.2 外部APIの変更なし

外部向けREST APIに変更はない。

---

## 7. セキュリティ設計

### 7.1 考慮事項

- **入力検証**: 既存のBodyTemplateValidatorによる検証を継続
- **インジェクション対策**: テンプレート文字列は固定形式のみ使用
- **ログ出力**: 機密情報がログに含まれないよう注意

### 7.2 脆弱性対策

本修正による新たなセキュリティリスクは想定されない。

---

## 8. パフォーマンス設計

### 8.1 計算量の考慮

- **スキーママージ**: O(n×m) where n=独立タスク数, m=フィールド数
- 実用上の問題なし（タスク数は通常10以下）

### 8.2 最適化

- 早期リターンによる不要な処理の回避
- 既存のキャッシング機構に変更なし

---

## 9. エラーハンドリング設計

### 9.1 同名フィールド衝突時の処理（AC-6, AC-7対応）

同名フィールドが複数の独立タスクで定義された場合、型の一致/不一致で処理を分岐する。

#### 9.1.1 型不一致の場合：ValueErrorを発生（AC-7）

```python
if field_name in merged_properties:
    existing_type = merged_properties[field_name].get("type")
    new_type = field_schema.get("type")
    if existing_type != new_type:
        raise ValueError(
            f"Field '{field_name}' has conflicting types: "
            f"'{existing_type}' vs '{new_type}' (task: {task.name})"
        )
```

**理由**: 型不一致は実行時エラーの原因となるため、早期に検出してエラーとする。

#### 9.1.2 型一致の場合：警告ログ出力（AC-6）

```python
if field_name in merged_properties:
    existing_type = merged_properties[field_name].get("type")
    new_type = field_schema.get("type")
    # 型一致でも警告ログ（両方の型情報を含む）
    logger.warning(
        "Field '%s' from task '%s' overrides previous definition. "
        "Existing type: %s, New type: %s",
        field_name, task.name, existing_type, new_type,
    )
```

**理由**: 同名フィールドは意図しない上書きの可能性があるため、警告ログで検知可能とする。両方の型情報を含めることで、問題の特定が容易になる。

### 9.2 エラー伝播

- 型不一致時は`ValueError`を発生させ、Job生成を中断
- 型一致時は警告ログを出力し、処理を継続（後勝ち）
- 既存のエラーハンドリングパターンを踏襲

---

## 10. 設計上の決定事項とトレードオフ

### 10.1 主要な設計決定

| 決定事項 | 理由 | トレードオフ |
|---------|------|-------------|
| **task=Noneの場合はレガシー動作** | 後方互換性の維持 | 条件分岐の複雑化 |
| **同名フィールド（型一致）は後勝ち+警告** | シンプルな実装+問題検知 | 予期しない上書きの可能性 |
| **同名フィールド（型不一致）はValueError** | 実行時エラーの早期検出 | Job生成の中断 |
| **GraphAI対応は別Issue** | スコープの明確化 | 一時的な機能差異 |
| **警告ログに両方の型情報を含める** | デバッグ容易性 | ログ量の増加 |

### 10.2 代替案との比較

| 代替案 | メリット | デメリット | 採用/不採用 |
|--------|---------|-----------|-------------|
| **同名フィールド（型不一致）でエラー** | 実行時エラーの早期検出 | Job生成の中断 | ✅ **採用（AC-7）** |
| **同名フィールド（型一致）で警告+後勝ち** | 処理継続+問題検知 | 予期しない上書きの可能性 | ✅ **採用（AC-6）** |
| **同名フィールドで常にエラー** | 明確なエラー | 既存ワークフローが動かなくなる | ❌ 破壊的変更 |
| **同名フィールドを配列化** | 全データ保持 | 複雑な実装、下流への影響大 | ❌ YAGNI違反 |
| **依存関係の自動追加** | ユーザー負担軽減 | タスク生成ロジックへの影響大 | ❌ スコープ外 |

### 10.3 将来の拡張性

1. **GraphAIエンジン対応**: 同じロジックを適用可能
2. **互換性チェック強化**: compatibility.pyの拡張で対応可能
3. **より高度なフィールドマッピング**: 必要に応じて別Issueで対応

---

## 11. テスト戦略

### 11.1 単体テスト

| テストケース | 概要 | 検証内容 |
|-------------|------|---------|
| **TC-007** | 独立タスク（task指定あり、dependencies=[]）の判定 | `{{job.body.user_input}}`が返されることを確認 |
| **TC-009** | スキーママージのロジック | 複数独立タスクのスキーマがマージされることを確認 |
| **TC-011** | 同名フィールド衝突（型一致）の警告ログ | 警告ログに両方の型情報が含まれることを確認 |
| **TC-012** | 同名フィールド衝突（型不一致）のエラー | `ValueError`が発生し、エラーメッセージに両方の型情報が含まれることを確認 |

### 11.2 結合テスト

| テストケース | 概要 | 検証内容 |
|-------------|------|---------|
| **TC-008** | 複数独立タスクの統合動作 | 両タスクが`{{job.body.user_input}}`を参照することを確認 |
| **TC-010** | Issue #408との統合 | 全ユーザー入力フィールドが検証対象となることを確認 |

### 11.3 受入テスト

| テストケース | 概要 | 検証内容 |
|-------------|------|---------|
| **E2E-001** | 実際のJob生成フロー | 2つの独立タスクが正しくユーザー入力を受け取ることを確認 |
| **E2E-002** | 型不一致エラーの検出 | 型不一致時にJob生成が適切に失敗することを確認 |
| **E2E-003** | 型一致時の警告ログ | 型一致時に警告ログが出力され、処理が継続することを確認 |

### 11.4 テストカバレッジ目標

- 単体テスト: 90%以上（CLAUDE.md準拠）
- 結合テスト: 50%以上（CLAUDE.md準拠）
- 新規追加コードのカバレッジ: 100%

---

## 12. 移行計画

### 12.1 段階的な適用

1. **Phase 1**: TaskFlowエンジンのみ対応（本Issue）
   - `_build_body_template`の修正
   - `_get_user_input_schema`の修正
   - 同名フィールド衝突の型チェック実装
2. **Phase 2**: テスト整備
   - TC-007〜TC-012の実装
   - E2E-001〜E2E-003の実装
3. **Phase 3**: ドキュメント整備（AC-8対応）
   - `expertAgent/docs/features/independent-task-dataflow.md`作成
4. **Phase 4**: GraphAIエンジン対応（将来Issue）
5. **Phase 5**: 互換性チェック強化（将来Issue）

### 12.2 ドキュメント作成計画（AC-8対応）

**作成ファイル**: `expertAgent/docs/features/independent-task-dataflow.md`

**内容**:
1. 独立タスクの定義（`dependencies=[]`）
2. データフロー仕様
   - 独立タスクは`{{job.body.user_input}}`を使用
   - 依存タスクは`{{tasks[n].output_data}}`を使用
3. 同名フィールドの扱い
   - 型一致: 警告ログ + 後勝ち
   - 型不一致: ValueError
4. 設計の理由とトレードオフ
5. トラブルシューティングガイド

### 12.3 リスク軽減策

- 既存テストの全パス確認
- task=Noneケースの動作維持確認
- TC-005はレガシー互換性テストとして維持（docstringに明記）
- ステージング環境での検証

---

## 13. 制約事項

### 13.1 技術的制約

- Python 3.11以上が必要（既存要件）
- expertAgentサービス内での修正に限定

### 13.2 ビジネス制約

- 既存のワークフローを破壊しない
- パフォーマンス劣化を起こさない

---

## 14. レビュー指摘事項の反映状況

### 14.1 必須改善項目（Must Fix）

| 項目 | 対応状況 | 反映箇所 |
|------|---------|---------|
| スキーママージ時のログ改善（AC-6） | ✅ 対応済み | セクション9.1.2 |
| 警告ログに両方の型情報を含める | ✅ 対応済み | セクション9.1.2 |
| 型不一致時のValueError発生（AC-7） | ✅ 対応済み | セクション9.1.1 |
| エラーメッセージに両方の型情報を含める | ✅ 対応済み | セクション9.1.1 |

### 14.2 推奨改善項目（Should Fix）

| 項目 | 対応状況 | 反映箇所 |
|------|---------|---------|
| テストケース充実化 | ✅ 対応済み | セクション11（TC-011, TC-012, E2E-002, E2E-003追加） |
| ドキュメント整備（AC-8） | ✅ 対応済み | セクション12.2 |
| テストカバレッジ目標の明記 | ✅ 対応済み | セクション11.4 |

### 14.3 検討事項（Consider）

| 項目 | 対応状況 | 備考 |
|------|---------|------|
| GraphAIパスへの同様の修正適用 | 📋 将来対応 | Phase 4として計画 |
| 互換性チェックの拡張 | 📋 将来対応 | Phase 5として計画 |
| モニタリング追加 | 📋 将来対応 | 別Issueで対応予定 |
| スキーマ衝突の自動解決機能 | 📋 将来検討 | namespace付け等 |

---

## 15. 参照ドキュメント

- [expertAgent API Reference](../../../expertAgent/docs/API_REFERENCE.md)
- [Issue #408実装](https://github.com/Kewton/MySwiftAgent/issues/408)
- [Issue #403実装](https://github.com/Kewton/MySwiftAgent/issues/403)
- [CLAUDE.md - 開発ガイドライン](../../../CLAUDE.md)

---

## 16. 承認

本設計方針は以下の原則に基づいて策定されました：

- ✅ **SOLID原則**: 単一責任、開放/閉鎖原則を遵守
- ✅ **KISS原則**: 最小限の変更で問題を解決
- ✅ **YAGNI原則**: 必要な機能のみを実装
- ✅ **DRY原則**: 既存のロジックを再利用

本設計により、複数独立タスクのデータフロー問題を後方互換性を保ちながら解決します。

### レビュー結果

- **レビュー日**: 2026-01-26
- **レビュー結果**: ✅ 承認（Approved）
- **必須改善項目**: 全て反映済み
- **推奨改善項目**: 全て反映済み