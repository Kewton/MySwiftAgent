# アーキテクチャレビュー: TaskMaster body_template 検証機能

**Issue**: #322
**レビュー日**: 2025-12-29
**レビュアー**: Claude Architect
**対象ドキュメント**: `dev-reports/feature/issue/322/design-policy.md`

---

## 1. 設計原則の遵守確認

### SOLID原則チェック

| 原則 | 状態 | 評価 |
|------|------|------|
| **S**ingle Responsibility | ✅ 準拠 | `TemplateValidator` はテンプレート検証に専念、`TemplateResolver` は解決に専念 |
| **O**pen/Closed | ✅ 準拠 | 既存の `TemplateResolver` を拡張（パラメータ追加）、既存機能は変更なし |
| **L**iskov Substitution | ✅ 該当なし | 継承関係なし |
| **I**nterface Segregation | ✅ 準拠 | `TemplateValidator.validate()` は単一の明確なインターフェース |
| **D**ependency Inversion | ✅ 準拠 | スキーマ（`TemplateValidationResult`）への依存で抽象化 |

### その他の原則

| 原則 | 状態 | 評価 |
|------|------|------|
| **KISS** | ✅ 準拠 | 単純な構文検証と警告出力、複雑なロジックなし |
| **YAGNI** | ⚠️ 要注意 | `strict` モードは現時点で未使用、将来のための設計 |
| **DRY** | ⚠️ 要改善 | 正規表現パターンが `TemplateResolver` と `TemplateValidator` で重複 |

---

## 2. アーキテクチャ評価

### 構造的品質

| 評価項目 | スコア | コメント |
|---------|--------|----------|
| モジュール性 | ⭐⭐⭐⭐⭐ (5/5) | 新規クラス `TemplateValidator` は独立性が高い |
| 結合度 | ⭐⭐⭐⭐☆ (4/5) | API層とサービス層の適切な分離 |
| 凝集度 | ⭐⭐⭐⭐⭐ (5/5) | 検証ロジックが `TemplateValidator` に集約 |
| 拡張性 | ⭐⭐⭐⭐⭐ (5/5) | スキーマオプション、strict モードで段階的拡張可能 |
| 保守性 | ⭐⭐⭐⭐☆ (4/5) | テストカバレッジ計画あり、パターン重複が懸念 |

**総合スコア**: ⭐⭐⭐⭐☆ (4.6/5)

### パフォーマンス観点

| 項目 | 評価 |
|-----|------|
| レスポンスタイム | ✅ 微増のみ（正規表現は事前コンパイル済み） |
| スループット | ✅ 影響なし（同期処理、非ブロッキング） |
| リソース使用効率 | ✅ 検証結果は一時的、永続化なし |
| スケーラビリティ | ✅ ステートレス設計、水平スケール可能 |

---

## 3. セキュリティレビュー

### OWASP Top 10 チェック

| 項目 | 状態 | 対策 |
|-----|------|------|
| インジェクション | ✅ 対策済 | 正規表現パターンで許可された構文のみ受け入れ |
| 認証の破綻 | ✅ 該当なし | 認証は既存機構に依存 |
| 機微データの露出 | ✅ 対策済 | テンプレート変数名のみログ出力、値は出力しない |
| XXE | ✅ 該当なし | XML処理なし |
| アクセス制御 | ✅ 既存機構に依存 | TaskMaster APIの既存認可に従う |
| セキュリティ設定ミス | ✅ 対策済 | デフォルトは警告モード（安全側） |
| XSS | ✅ 該当なし | APIのみ、フロントエンド処理なし |
| 安全でないデシリアライゼーション | ✅ 対策済 | Pydanticによる型安全なデシリアライゼーション |
| 既知の脆弱性 | ✅ N/A | 新規コード |
| ログとモニタリング | ✅ 強化 | 詳細なログコンテキスト追加 |

### 追加セキュリティ確認

| 項目 | 状態 | コメント |
|-----|------|---------|
| パス深度制限 | ✅ 対策済 | `MAX_PATH_DEPTH = 10` で制限 |
| 入力サイズ制限 | ⚠️ 未明記 | body_template のサイズ制限を検討すべき |
| DoS対策 | ⚠️ 要検討 | 大量の変数を含むテンプレートへの対策 |

---

## 4. 既存システムとの整合性

### 統合ポイント

| 項目 | 評価 | 詳細 |
|-----|------|------|
| API互換性 | ✅ 完全 | レスポンスにフィールド追加のみ（後方互換） |
| データモデル整合性 | ✅ 完全 | TaskMaster スキーマに追加フィールドのみ |
| 認証/認可の一貫性 | ✅ 完全 | 既存機構をそのまま使用 |
| ログ/監視の統合 | ✅ 完全 | 既存の logging モジュールを使用 |

### 技術スタックの適合性

| 項目 | 評価 |
|-----|------|
| 既存技術との親和性 | ✅ Pydantic, 正規表現, logging すべて既存使用 |
| チームのスキルセット | ✅ 既存パターンの踏襲で学習コスト最小 |
| 運用負荷への影響 | ✅ 最小（ログ増加のみ） |

### Issue #321 との連携

| 項目 | 評価 |
|-----|------|
| 依存関係 | ✅ 明確 | #321 完了後にスキーマ検証が強化される |
| 並行開発 | ✅ 可能 | #321 なしでも基本機能は動作 |
| インターフェース整合 | ✅ 設計済 | `job_body_schema` パラメータで連携 |

---

## 5. リスク評価

| リスク種別 | 内容 | 影響度 | 発生確率 | 対策優先度 |
|-----------|------|-------|---------|-----------|
| **技術的リスク** | 正規表現パターン重複による不整合 | 中 | 中 | 🔴 高 |
| **技術的リスク** | 大量変数テンプレートでの性能低下 | 低 | 低 | 🟢 低 |
| **運用リスク** | ログ量増加によるストレージ圧迫 | 低 | 低 | 🟢 低 |
| **セキュリティリスク** | 巨大テンプレートによるDoS | 中 | 低 | 🟡 中 |
| **ビジネスリスク** | 誤検出による開発者の混乱 | 低 | 中 | 🟡 中 |

---

## 6. 改善提案

### 必須改善項目（Must Fix）

#### 1. 正規表現パターンの共通化

**問題**: `TemplateResolver` と `TemplateValidator` で同じ正規表現パターンが重複定義されている。

**影響**: 一方を変更した際に不整合が発生するリスク。

**対策案**:

```python
# jobqueue/app/services/template_patterns.py (新規)

import re

class TemplatePatterns:
    """テンプレート変数の正規表現パターン（共通定義）."""

    TASK_VARIABLE = re.compile(
        r"\{\{tasks\[(\d+)\]\.(input_data|output_data)(\.[\w.]+)?\}\}"
    )
    JOB_VARIABLE = re.compile(
        r"\{\{job\.(body|input_data)(\.[\w.]+)?\}\}"
    )
    CURRENT_TASK_VARIABLE = re.compile(
        r"\{\{task\.(input_data)(\.[\w.]+)?\}\}"
    )
    ANY_VARIABLE = re.compile(
        r"\{\{(tasks\[\d+\]|job|task)\.(input_data|output_data|body)(\.[\w.]+)?\}\}"
    )
```

```python
# TemplateResolver, TemplateValidator での使用
from app.services.template_patterns import TemplatePatterns

class TemplateResolver:
    VARIABLE_PATTERN = TemplatePatterns.TASK_VARIABLE
    JOB_VARIABLE_PATTERN = TemplatePatterns.JOB_VARIABLE
    # ...
```

---

### 推奨改善項目（Should Fix）

#### 1. テンプレートサイズ制限の追加

**問題**: 巨大な body_template によるDoSリスクが未対策。

**対策案**:

```python
# TemplateValidator に追加

MAX_TEMPLATE_SIZE = 64 * 1024  # 64KB
MAX_VARIABLES_COUNT = 100

@classmethod
def validate(cls, body_template: dict[str, Any] | None, ...) -> TemplateValidationResult:
    if body_template is None:
        return TemplateValidationResult(is_valid=True)

    # サイズチェック
    template_str = json.dumps(body_template)
    if len(template_str) > cls.MAX_TEMPLATE_SIZE:
        return TemplateValidationResult(
            is_valid=False,
            warnings=[
                TemplateValidationWarning(
                    variable="",
                    message=f"Template size exceeds maximum ({cls.MAX_TEMPLATE_SIZE} bytes)",
                    severity="error",
                )
            ],
        )

    # ... 既存処理 ...

    # 変数数チェック
    if len(extracted_variables) > cls.MAX_VARIABLES_COUNT:
        warnings.append(
            TemplateValidationWarning(
                variable="",
                message=f"Too many template variables ({len(extracted_variables)} > {cls.MAX_VARIABLES_COUNT})",
                severity="error",
            )
        )
```

#### 2. 検証結果のキャッシュ検討

**問題**: 同じ body_template で繰り返し検証が発生する可能性。

**対策案**: 将来的に必要であれば、テンプレートハッシュをキーにした短期キャッシュを検討。現時点では優先度低。

---

### 検討事項（Consider）

#### 1. 検証レベルの設定可能化

**背景**: 現在は警告のみだが、プロジェクトによっては厳格な検証が必要かもしれない。

**提案**: 環境変数または設定ファイルで検証レベルを設定可能に。

```python
# config.py
TEMPLATE_VALIDATION_LEVEL = os.getenv("TEMPLATE_VALIDATION_LEVEL", "warn")
# "off" | "warn" | "strict"
```

**優先度**: 低（現時点では不要、将来要件として検討）

#### 2. CLI 検証ツール

**背景**: 開発時に body_template を事前検証したいケースがある。

**提案**: 将来的にCLIツールを提供。

```bash
# 将来的なCLI
jobqueue validate-template --file template.json --schema job_body_schema.json
```

**優先度**: 低（本Issue範囲外）

---

## 7. ベストプラクティスとの比較

### 業界標準との差異

| 項目 | 業界標準 | 本設計 | 評価 |
|-----|---------|--------|------|
| テンプレート検証 | 構文＋型チェック | 構文＋参照警告 | ✅ 適切（動的型のため） |
| エラーハンドリング | Fail-fast | Warn-and-continue | ✅ 後方互換性重視で適切 |
| ログ戦略 | 構造化ログ | 文字列ログ | ⚠️ 将来的に構造化を検討 |

### 代替アーキテクチャ案

#### 代替案1: JSON Schema ベースの検証

**説明**: body_template 自体を JSON Schema として定義し、jsonschema ライブラリで検証。

| 観点 | 評価 |
|-----|------|
| メリット | 標準的な検証フレームワーク、豊富なエコシステム |
| デメリット | テンプレート変数（`{{...}}`）の特殊構文に対応困難 |

**判定**: 不採用（テンプレート変数の特殊性に対応困難）

#### 代替案2: AST ベースの検証

**説明**: テンプレートを抽象構文木（AST）にパースして検証。

| 観点 | 評価 |
|-----|------|
| メリット | より正確な構文解析、複雑なルール対応 |
| デメリット | 実装コスト高、既存パターンとの乖離 |

**判定**: 不採用（KISS原則に反する、現要件では過剰）

**結論**: 正規表現ベースの現設計が最適。

---

## 8. 総合評価

### レビューサマリ

| 項目 | 評価 |
|-----|------|
| **全体評価** | ⭐⭐⭐⭐☆ (4/5) |
| **強み** | 後方互換性、段階的検証、Issue #321 との連携設計 |
| **弱み** | 正規表現パターンの重複、テンプレートサイズ制限なし |

### 詳細評価

| 観点 | スコア | コメント |
|-----|--------|---------|
| 設計原則準拠 | 4.5/5 | DRY違反（パターン重複）を除き良好 |
| アーキテクチャ品質 | 4.6/5 | モジュール性・拡張性が優秀 |
| セキュリティ | 4/5 | 基本対策済み、サイズ制限追加で完璧 |
| 既存システム統合 | 5/5 | 完全な後方互換性 |
| リスク管理 | 4/5 | 主要リスクは特定済み、対策可能 |

### 承認判定

**判定**: ✅ **承認（Approved）**

**対応完了**:
1. ✅ 正規表現パターンの共通化 - `TemplatePatterns` モジュール追加
2. ✅ テンプレートサイズ制限の追加 - `MAX_TEMPLATE_SIZE`, `MAX_VARIABLES_COUNT` 追加

---

## 9. 次のステップ

1. ~~**必須改善項目の反映**: 設計書に正規表現パターン共通化を追記~~ ✅ 完了
2. ~~**推奨改善項目の検討**: サイズ制限を設計書に追記~~ ✅ 完了
3. **作業計画書作成**: `/work-plan #322` で詳細タスク分解
4. **実装開始**: Phase 1（TemplatePatterns, TemplateValidator）から着手

---

## 付録: チェックリスト

### 設計品質チェック
- [x] SOLID原則に準拠している
- [x] 既存パターンとの整合性がある
- [x] 後方互換性が確保されている
- [x] テスト計画が含まれている
- [x] DRY原則に完全準拠（`TemplatePatterns` 共通モジュール追加済み）

### セキュリティチェック
- [x] 入力検証が実装されている
- [x] ログに機密情報が含まれない
- [x] DoS対策（サイズ制限）が実装されている（`MAX_TEMPLATE_SIZE`, `MAX_VARIABLES_COUNT`）

### 運用チェック
- [x] ログ出力が適切に設計されている
- [x] パフォーマンス影響が評価されている
- [x] エラーハンドリングが定義されている
