# アーキテクチャレビュー: Issue #321 Job Generator パラメータ抽出機能

**レビュー日**: 2025-12-29
**レビュー対象**: `dev-reports/feature/issue/321/design-policy.md`
**レビュアー**: Claude Code (Senior Software Architect)

---

## 1. 設計原則の遵守確認

### SOLID原則チェック

| 原則 | 状態 | 評価 | コメント |
|------|------|------|---------|
| **S**ingle Responsibility | ✅ 遵守 | 良好 | requirement_analysis_node は「要件分析」という単一責任を維持。パラメータ抽出も要件分析の一部として自然 |
| **O**pen/Closed | ✅ 遵守 | 良好 | 既存クラス（TaskBreakdownResponse）を拡張のみで修正。JobqueueClient も Optional パラメータ追加で後方互換 |
| **L**iskov Substitution | ✅ 該当なし | - | 継承関係なし |
| **I**nterface Segregation | ✅ 遵守 | 良好 | 新規インターフェース追加なし。既存APIの拡張のみ |
| **D**ependency Inversion | ✅ 遵守 | 良好 | JobqueueClient への依存は既存パターンを踏襲 |

### その他の原則

| 原則 | 状態 | 評価 | コメント |
|------|------|------|---------|
| **KISS** | ✅ 遵守 | 良好 | 既存ノードの拡張で実現。新規ノード追加を避けた判断は適切 |
| **YAGNI** | ✅ 遵守 | 良好 | 必要最小限のフィールド追加。過度な汎用化なし |
| **DRY** | ✅ 遵守 | 良好 | 既存の Pydantic パターン、State パターンを再利用 |

---

## 2. アーキテクチャ評価

### 構造的品質

| 評価項目 | スコア | コメント |
|---------|--------|----------|
| **モジュール性** | ⭐⭐⭐⭐⭐ (5/5) | 変更が5つのモジュールに適切に分散 |
| **結合度** | ⭐⭐⭐⭐☆ (4/5) | 既存の結合パターンを維持。State経由の疎結合 |
| **凝集度** | ⭐⭐⭐⭐⭐ (5/5) | 各ノードの責務が明確 |
| **拡張性** | ⭐⭐⭐⭐☆ (4/5) | パラメータ型の拡張は容易。ただし body_template との動的連携は将来課題 |
| **保守性** | ⭐⭐⭐⭐⭐ (5/5) | 既存パターン踏襲により保守性維持 |

### パフォーマンス観点

| 項目 | 評価 | コメント |
|------|------|---------|
| **レスポンスタイム** | 影響なし | 同一LLM呼び出しでパラメータ抽出を実施 |
| **スループット** | 影響なし | 追加API呼び出しなし |
| **リソース使用効率** | 微増 | State サイズが微増（パラメータ5件程度で数百バイト） |
| **スケーラビリティ** | 影響なし | 既存アーキテクチャを踏襲 |

---

## 3. セキュリティレビュー

### OWASP Top 10 チェック

| 脆弱性カテゴリ | 状態 | 対策状況 |
|---------------|------|---------|
| インジェクション | ⚠️ 要注意 | LLM出力をPydanticでバリデーション。ただし value フィールドが Any 型 |
| 認証の破綻 | ✅ 該当なし | 認証変更なし |
| 機微データの露出 | ⚠️ 要注意 | パスワード等の抽出防止はプロンプト依存 |
| XXE | ✅ 該当なし | XML処理なし |
| アクセス制御の不備 | ✅ 該当なし | アクセス制御変更なし |
| セキュリティ設定ミス | ✅ 該当なし | 設定変更なし |
| XSS | ✅ 該当なし | フロントエンド変更なし |
| 安全でないデシリアライゼーション | ✅ 対策済 | Pydantic による型チェック |
| 既知の脆弱性 | ✅ 該当なし | 新規ライブラリ追加なし |
| ログとモニタリング不足 | ⚠️ 要改善 | パラメータ抽出結果のログ出力は #324 で対応 |

### セキュリティ改善提案

| 優先度 | 提案 | 理由 |
|-------|------|------|
| 🔴 高 | `JobBodyParameter.value` の型を制限 | Any 型は任意コード実行のリスク |
| 🟡 中 | 機密パラメータ名のブラックリスト | password, api_key 等の抽出防止 |
| 🟢 低 | パラメータ値の長さ制限 | DoS防止 |

---

## 4. 既存システムとの整合性

### 統合ポイント

| 項目 | 状態 | コメント |
|------|------|---------|
| **API互換性** | ✅ 完全互換 | JobQueue API は既に body をサポート |
| **データモデル整合性** | ✅ 良好 | State拡張は TypedDict の正当な使用法 |
| **認証/認可の一貫性** | ✅ 変更なし | 既存認証フローを踏襲 |
| **ログ/監視の統合** | ⚠️ 未定義 | パラメータ抽出ログは #324 で対応予定 |

### 技術スタックの適合性

| 項目 | 評価 | コメント |
|------|------|---------|
| **既存技術との親和性** | ⭐⭐⭐⭐⭐ | Pydantic, TypedDict, httpx すべて既存技術 |
| **チームのスキルセット** | ⭐⭐⭐⭐⭐ | 新規技術習得不要 |
| **運用負荷への影響** | ⭐⭐⭐⭐⭐ | 運用変更なし |

---

## 5. リスク評価

| リスク種別 | 内容 | 影響度 | 発生確率 | 対策優先度 |
|-----------|------|--------|---------|-----------|
| **技術的** | LLMがパラメータを正しく抽出できない | 中 | 中 | 🟡 中 |
| **技術的** | body_template とパラメータ名の不整合 | 高 | 高 | 🔴 高 |
| **運用** | 抽出失敗時のデバッグ困難 | 中 | 中 | 🟡 中 |
| **セキュリティ** | 機密情報のログ出力 | 中 | 低 | 🟡 中 |
| **ビジネス** | 既存ワークフローの動作変更 | 低 | 低 | 🟢 低 |

### リスク対策

| リスク | 対策 | 担当Issue |
|-------|------|-----------|
| パラメータ抽出失敗 | Few-shot例をプロンプトに追加 | #321 |
| body_template との不整合 | 静的検証機能を追加 | #322 |
| デバッグ困難 | ログ強化 | #324 |
| 機密情報ログ出力 | パラメータ値のマスキング | #324 |

---

## 6. 改善提案

### 必須改善項目（Must Fix）

#### 6.1 requirement_analysis_node の戻り値に job_body_parameters を追加

**問題**: 設計書の `requirement_analysis_node` 変更案では、State への格納処理が明示されていない。

**現在のコード** (`requirement_analysis.py:194-200`):
```python
return {
    **state,
    "task_breakdown": [task.model_dump() for task in response.tasks],
    "overall_summary": response.overall_summary,
    "evaluator_stage": "after_task_breakdown",
    "retry_count": updated_retry,
}
```

**修正案**:
```python
return {
    **state,
    "task_breakdown": [task.model_dump() for task in response.tasks],
    "overall_summary": response.overall_summary,
    "job_body_parameters": [p.model_dump() for p in response.job_body_parameters],  # 追加
    "evaluator_stage": "after_task_breakdown",
    "retry_count": updated_retry,
}
```

#### 6.2 JobBodyParameter.value の型制限

**問題**: `value: Any` は任意のオブジェクトを許容し、セキュリティリスクがある。

**修正案**:
```python
class JobBodyParameter(BaseModel):
    value: str | int | float | bool | list[str] | dict[str, str] = Field(
        description="ユーザー要件から抽出した値（プリミティブ型または単純構造のみ）"
    )
```

### 推奨改善項目（Should Fix）

#### 6.3 パラメータ抽出の検証関数追加

**提案**: `_validate_task_breakdown_response` を拡張して `job_body_parameters` も検証

```python
def _validate_task_breakdown_response(
    response: TaskBreakdownResponse | None,
) -> TaskBreakdownResponse:
    # ... 既存の検証 ...

    # 新規: パラメータ検証
    if response.job_body_parameters:
        for param in response.job_body_parameters:
            if not param.name or not param.name.isidentifier():
                logger.warning(
                    "Invalid parameter name: %s (must be valid identifier)",
                    param.name
                )

    return response
```

#### 6.4 機密パラメータのブラックリスト

**提案**: プロンプトに加えて、コード側でも機密パラメータ名をフィルタリング

```python
SENSITIVE_PARAM_NAMES = {"password", "api_key", "secret", "token", "credential"}

def _filter_sensitive_params(params: list[JobBodyParameter]) -> list[JobBodyParameter]:
    filtered = []
    for p in params:
        if p.name.lower() in SENSITIVE_PARAM_NAMES:
            logger.warning("Filtered sensitive parameter: %s", p.name)
            continue
        filtered.append(p)
    return filtered
```

### 検討事項（Consider）

#### 6.5 パラメータスキーマの動的生成（将来）

**背景**: 現在の設計では `{{job.body}}` の構造は静的。将来的に、抽出したパラメータから JSON Schema を自動生成し、body_template と整合性を検証できる。

**検討理由**:
- #322 の body_template 検証と統合可能
- InterfaceMaster の input_schema と同様の仕組みで実装可能

**優先度**: 低（#322 完了後に検討）

#### 6.6 パラメータのデフォルト値サポート

**背景**: ユーザーが明示しないパラメータにデフォルト値を設定できると、ワークフローの柔軟性が向上。

**検討理由**:
- `source: "default"` はスキーマに存在するが、デフォルト値の定義方法が未定義
- TaskMaster の body_template にデフォルト値を埋め込む方式との整合性が必要

**優先度**: 低（ユーザーフィードバック後に検討）

---

## 7. ベストプラクティスとの比較

### 業界標準との差異

| 観点 | 業界標準 | 本設計 | 評価 |
|------|---------|-------|------|
| LLM出力の構造化 | Pydantic / JSON Schema | Pydantic | ✅ 標準的 |
| パラメータ抽出 | Named Entity Recognition / Slot Filling | LLM直接抽出 | ⚠️ 精度はLLM依存 |
| テンプレート変数解決 | Jinja2 / Mustache | 独自実装 (TemplateResolver) | ⚠️ 車輪の再発明だが既存資産 |
| 状態管理 | Redux-like / State Machine | TypedDict + LangGraph | ✅ 標準的 |

### 代替アーキテクチャ案

#### 代替案1: 専用パラメータ抽出ノードの追加

```
requirement_analysis_node → parameter_extraction_node → evaluator_node
```

**メリット**:
- 責務分離がより明確
- パラメータ抽出ロジックの独立テストが容易

**デメリット**:
- LLM呼び出し増加（レイテンシ +2-3秒）
- 文脈の分断（タスク分解とパラメータの整合性が取りにくい）

**評価**: 採用しない（設計書の判断を支持）

#### 代替案2: body_template の動的生成

```
パラメータ抽出 → body_template 自動生成 → TaskMaster 作成
```

**メリット**:
- パラメータ名と body_template の完全な整合性
- #322 の検証が不要に

**デメリット**:
- 既存 TaskMaster との互換性問題
- 複雑性の大幅増加
- ワークフロー再利用性の低下

**評価**: 採用しない（設計書の判断を支持）

---

## 8. 総合評価

### レビューサマリ

| 項目 | 評価 |
|------|------|
| **全体評価** | ⭐⭐⭐⭐☆ (4/5) |
| **設計原則** | 優秀 - SOLID, KISS, YAGNI, DRY すべて遵守 |
| **アーキテクチャ** | 良好 - 既存パターン踏襲、変更範囲最小化 |
| **セキュリティ** | 要改善 - value 型制限、機密パラメータ対策が必要 |
| **リスク管理** | 良好 - 関連Issueで対策予定 |

### 強み

1. **既存アーキテクチャとの高い整合性**: 新規パターン導入なし、学習コストゼロ
2. **最小限の変更範囲**: 8ファイルの軽微な修正で実現
3. **後方互換性**: 既存 JobMaster/TaskMaster に影響なし
4. **パフォーマンス影響なし**: 追加LLM呼び出しを回避した設計判断

### 弱み

1. **セキュリティ詳細が未定義**: value 型制限、機密情報フィルタリング
2. **body_template との整合性は #322 依存**: 本Issue単体では不整合を検出できない
3. **LLM依存のパラメータ抽出精度**: Few-shot 例の品質に依存

### 総評

本設計は **実用的かつ保守性の高いアプローチ** を採用しており、承認に値する。
ただし、セキュリティ面での改善（value 型制限）を実装時に追加することを推奨。
body_template との整合性問題は #322 で対応予定のため、本Issue の範囲としては妥当。

---

## 承認判定

### ✅ 承認（Approved）

**当初の条件付き承認からの変更**: 2025-12-29

すべての必須改善項目が設計書に反映されたため、**承認** に変更。

**対応済み項目**:

1. ✅ `JobBodyParameter.value` の型を `JobBodyValueType` に制限（プリミティブ型 | 単純構造のみ）
2. ✅ `requirement_analysis_node` の戻り値に `job_body_parameters` を明示的に追加
3. ✅ パラメータ名の検証関数を追加（`_validate_task_breakdown_response` 拡張）
4. ✅ 機密パラメータ名のブラックリスト（`validate_not_sensitive` バリデータ）

**次のステップ**:

1. ~~上記の必須改善項目を設計書に反映~~ ✅ 完了
2. 作業計画書 (`work-plan.md`) の作成
3. Phase 1 から実装開始

---

## 参照ドキュメント

| ドキュメント | 参照目的 |
|-------------|---------|
| `design-policy.md` | レビュー対象 |
| `requirement_analysis.py` | 既存実装確認 |
| `state.py` | 既存State構造確認 |
| `jobqueue_client.py` | 既存API確認 |
| `job_registration.py` | 既存ノード実装確認 |
