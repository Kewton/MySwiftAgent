# アーキテクチャレビュー: Issue #270 expert_agent_capabilities.yaml スキーマ拡張

**レビュー日**: 2025-12-11
**レビュアー**: Claude Code (Architecture Review)
**対象ドキュメント**:
- `dev-reports/feature/issue/270/requirements.md`
- `dev-reports/feature/issue/270/design-policy.md`

---

## 1. 設計原則の遵守確認

### SOLID原則チェック

| 原則 | 評価 | コメント |
|-----|------|---------|
| **S** Single Responsibility | ✅ 準拠 | 各モジュールが明確な単一責任を持つ（YAML読み込み、プロンプト生成、スキーマ変換） |
| **O** Open/Closed | ✅ 準拠 | Dataclassにオプショナルフィールドを追加する設計で、既存コードの修正を最小化 |
| **L** Liskov Substitution | ✅ 準拠 | 継承構造なし、影響なし |
| **I** Interface Segregation | ✅ 準拠 | インターフェースが適切に分離されている（設定、データアクセス、プロンプト生成） |
| **D** Dependency Inversion | ⚠️ 注意 | YAML設定に直接依存。抽象化レイヤーの追加を検討可能 |

### その他の原則

| 原則 | 評価 | コメント |
|-----|------|---------|
| **KISS** | ✅ 準拠 | 既存パターンを踏襲したシンプルな設計 |
| **YAGNI** | ✅ 準拠 | 必要最小限の機能に絞られている（FR-11, FR-12を将来拡張として分離） |
| **DRY** | ⚠️ 注意 | `output_schema`と`response_schema`の二重定義が一時的に発生する可能性 |

---

## 2. アーキテクチャ評価

### 構造的品質

| 評価項目 | スコア | コメント |
|---------|--------|---------|
| **モジュール性** | ⭐⭐⭐⭐☆ (4/5) | レイヤー分離が明確。プロンプト生成レイヤーの責務がやや広い |
| **結合度** | ⭐⭐⭐⭐⭐ (5/5) | 疎結合を維持。YAMLファイル経由で設定を分離 |
| **凝集度** | ⭐⭐⭐⭐☆ (4/5) | 各モジュールの機能凝集度は高い |
| **拡張性** | ⭐⭐⭐⭐⭐ (5/5) | オプショナルフィールド追加で高い拡張性を確保 |
| **保守性** | ⭐⭐⭐⭐☆ (4/5) | スキーマ定義のメンテナンス負荷は中程度（FR-11で改善予定） |

### パフォーマンス観点

| 項目 | 評価 | 詳細 |
|-----|------|------|
| **レスポンスタイム予測** | ✅ 良好 | YAML読み込みは起動時のみ、モジュールレベルキャッシング |
| **スループット評価** | ✅ 良好 | LLMリクエスト数に変更なし |
| **リソース使用効率** | ⚠️ 注意 | トークン消費量+10%〜+100%（許容範囲内だが監視推奨） |
| **スケーラビリティ** | ✅ 良好 | ステートレス設計、スケールに影響なし |

---

## 3. セキュリティレビュー

### OWASP Top 10 チェック

| 項目 | 評価 | コメント |
|-----|------|---------|
| インジェクション対策 | ✅ | `yaml.safe_load()`使用、信頼できるソースのみ |
| 認証の破綻対策 | N/A | 認証機能なし |
| 機微データの露出対策 | ✅ | スキーマにAPIキー等を含めない方針明記 |
| XXE対策 | ✅ | YAML使用、XMLではない |
| アクセス制御の不備対策 | N/A | 内部設定ファイル |
| セキュリティ設定ミス対策 | ✅ | デフォルト値の明示 |
| XSS対策 | N/A | Web出力なし |
| 安全でないデシリアライゼーション対策 | ✅ | `safe_load()`使用 |
| 既知の脆弱性対策 | ✅ | 標準ライブラリ（PyYAML）使用 |
| ログとモニタリング不足対策 | ⚠️ | スキーマ変換エラー時のログ出力を検討 |

### セキュリティ総合評価
**リスクレベル: 低**

スキーマ定義は設計時に定義される静的データであり、実行時の外部入力を受け付けないため、セキュリティリスクは最小限。

---

## 4. 既存システムとの整合性

### 統合ポイント

| 項目 | 評価 | 詳細 |
|-----|------|------|
| **API互換性** | ✅ | 外部API変更なし |
| **データモデル整合性** | ✅ | 既存`output_schema`形式を踏襲 |
| **認証/認可の一貫性** | N/A | 影響なし |
| **ログ/監視の統合** | ⚠️ | スキーマ関連のログ出力追加を推奨 |

### 技術スタックの適合性

| 項目 | 評価 | 詳細 |
|-----|------|------|
| **既存技術との親和性** | ⭐⭐⭐⭐⭐ (5/5) | Python, PyYAML, Pydantic（既存スタック） |
| **チームのスキルセット** | ⭐⭐⭐⭐⭐ (5/5) | 既存パターンの拡張で学習コスト最小 |
| **運用負荷への影響** | ⭐⭐⭐⭐☆ (4/5) | スキーマメンテナンスの継続的作業が必要 |

---

## 5. リスク評価

| リスク種別 | 内容 | 影響度 | 発生確率 | 対策優先度 |
|-----------|------|-------|---------|-----------|
| **技術的リスク** | トークン消費量増加によるLLMコスト増 | 中 | 高 | 中（監視で対応） |
| **技術的リスク** | スキーマ定義とAPI実装の乖離 | 中 | 中 | 高（FR-11で解消） |
| **運用リスク** | API変更時のスキーマ更新忘れ | 中 | 中 | 高（CI/CDチェック推奨） |
| **セキュリティリスク** | 機密情報の誤混入 | 高 | 低 | 高（レビュープロセス） |
| **ビジネスリスク** | 開発工数超過 | 低 | 低 | 低（Phase分割済み） |

---

## 6. 改善提案

### 必須改善項目（Must Fix）

**なし** - 設計は適切で、重大な問題は見つかりませんでした。

### 推奨改善項目（Should Fix）

#### SF-01: `output_schema` → `response_schema` マイグレーション戦略の明確化

**問題**: 既存の`output_schema`（text_to_speech_drive）と新規の`response_schema`の共存期間が不明確

**提案**:
```python
# graphai_capabilities.py に追加
def _normalize_schema(api: dict) -> dict:
    """Normalize output_schema to response_schema for backwards compatibility."""
    if "output_schema" in api and "response_schema" not in api:
        api["response_schema"] = api.pop("output_schema")
    return api
```

**理由**: 後方互換性を維持しつつ、段階的にマイグレーションを進められる

---

#### SF-02: スキーマバリデーションの追加

**問題**: YAML読み込み時のスキーマ整合性チェックがNice to Have（FR-09）に分類されている

**提案**: Phase 2（Dataclass更新）で簡易バリデーションを追加
```python
def _validate_schema(schema: dict) -> bool:
    """Validate schema structure."""
    valid_types = {"string", "integer", "number", "boolean", "array", "object"}
    for field_name, field_spec in schema.items():
        if "type" not in field_spec:
            logger.warning(f"Schema field '{field_name}' missing 'type'")
            return False
        if field_spec["type"] not in valid_types:
            logger.warning(f"Invalid type '{field_spec['type']}' for field '{field_name}'")
            return False
    return True
```

**理由**: 不正なスキーマ定義を早期に検出し、LLMへの不正入力を防止

---

#### SF-03: トークン消費量のモニタリング追加

**問題**: interface_definitionフェーズでトークン消費が+100%増加する可能性

**提案**: Langfuseを活用したトークン消費量の監視
```python
# interface_schema.py に追加
@langfuse.observe()
def build_interface_prompt_with_schema():
    prompt = _build_schema_reference()
    langfuse.trace(metadata={"prompt_tokens": len(prompt) // 4})  # 概算
    return prompt
```

**理由**: コスト増加の実態を把握し、必要に応じて最適化を検討

---

### 検討事項（Consider）

#### C-01: スキーマ自動生成スクリプトの早期実装

**現状**: FR-11（OpenAPI仕様との自動同期）は将来拡張として分類

**提案**: 手動メンテナンスの負荷が高い場合、優先度を上げて実装を検討

```bash
# 例: scripts/sync_api_schemas.py
python -c "
from app.main import app
import yaml

openapi = app.openapi()
# OpenAPI spec → expert_agent_capabilities.yaml 形式に変換
"
```

---

#### C-02: スキーマのバージョニング

**現状**: スキーマにバージョン情報なし

**提案**: 将来的にスキーマ進化を管理するためのバージョンフィールド追加
```yaml
schema_version: "1.0.0"
utility_apis:
  - name: "Gmail検索"
    # ...
```

---

#### C-03: 単体テストにおけるスナップショットテスト導入

**現状**: 単体テスト追加が計画されている

**提案**: スキーマ変換結果のスナップショットテストを追加
```python
def test_convert_to_json_schema_snapshot():
    result = convert_to_json_schema(GMAIL_SEARCH_SCHEMA)
    assert result == snapshot  # pytest-snapshot等を使用
```

---

## 7. ベストプラクティスとの比較

### 業界標準との差異

| 項目 | 業界標準 | 本設計 | 評価 |
|-----|---------|-------|------|
| スキーマ形式 | JSON Schema / OpenAPI | 独自YAML形式 | ⚠️ 非標準だが変換ユーティリティで対応 |
| 設定管理 | 環境変数 / Secret Manager | YAMLファイル | ✅ 静的設定に適切 |
| キャッシング | Redis / Memcached | モジュールレベル変数 | ✅ 単一プロセスに適切 |

### 代替アーキテクチャ案

#### 代替案1: JSON Schema完全準拠

**説明**: expert_agent_capabilities.yamlをJSON Schema完全準拠形式に変更

| 項目 | 内容 |
|-----|------|
| **メリット** | 標準形式、ツール互換性（ajv等でバリデーション可能）、OpenAPIとの親和性 |
| **デメリット** | YAML肥大化（+200%程度）、既存形式からのマイグレーションコスト |
| **判定** | ❌ 不採用（現時点では過剰） |

#### 代替案2: OpenAPI仕様の直接参照

**説明**: YAMLにスキーマを埋め込まず、実行時にOpenAPI仕様を参照

| 項目 | 内容 |
|-----|------|
| **メリット** | Single Source of Truth、自動同期 |
| **デメリット** | サービス起動必須（セカンダリストーリーに反する）、ネットワーク依存 |
| **判定** | ❌ 不採用（要件に反する） |

#### 代替案3: ハイブリッドアプローチ（推奨された設計）

**説明**: YAMLにスキーマを埋め込みつつ、OpenAPIからの自動生成スクリプトを提供

| 項目 | 内容 |
|-----|------|
| **メリット** | オフライン利用可能、メンテナンス自動化可能、段階的移行 |
| **デメリット** | 同期の手動トリガーが必要 |
| **判定** | ✅ 採用済み（FR-11として計画） |

---

## 8. 総合評価

### レビューサマリ

| 項目 | 評価 |
|-----|------|
| **全体評価** | ⭐⭐⭐⭐☆ (4/5) |
| **強み** | 既存パターン踏襲による低リスク、後方互換性確保、明確なPhase分割 |
| **弱み** | スキーマメンテナンス負荷、トークン消費増加の可能性 |

### 総評

本設計は、既存アーキテクチャとの整合性を維持しながら、LLMのインターフェース定義精度を向上させる実用的なアプローチです。

**特に評価できる点**:
1. **後方互換性の確保**: オプショナルフィールドによる段階的拡張
2. **トークン効率の考慮**: task_breakdownでは概要のみ、interface_definitionで詳細を提供
3. **明確な優先度付け**: Must Have / Nice to Have / Future の適切な分類
4. **リスク認識**: トークン増加、スキーマ陳腐化等のリスクと対策が明記

**改善が望まれる点**:
1. `output_schema` → `response_schema` のマイグレーション戦略
2. スキーマバリデーションの早期実装
3. トークン消費量のモニタリング体制

---

### 承認判定

| 判定 | 結果 |
|-----|------|
| ✅ **条件付き承認（Conditionally Approved）** | SF-01（マイグレーション戦略）の対応を推奨 |

### 承認条件

1. **必須**: `output_schema` → `response_schema` の共存・移行方針を設計書に追記
2. **推奨**: Phase 2にスキーマバリデーション（簡易版）を追加
3. **推奨**: トークン消費量の監視計画を策定

---

### 次のステップ

1. ✅ 設計書への承認条件反映
2. ⬜ Phase 1: YAML構造拡張の実装開始
3. ⬜ Phase 2: Dataclass更新（マイグレーションユーティリティ含む）
4. ⬜ Phase 3: プロンプト更新
5. ⬜ Phase 4: テスト・検証

---

**レビュー完了日**: 2025-12-11
**次回レビュー**: 実装完了後のコードレビュー時
