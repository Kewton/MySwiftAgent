# 設計方針: Marp レポート生成機能

**作成日**: 2025-10-21
**ブランチ**: feature/issue/97
**担当**: Claude Code

---

## 📋 要求・要件

### ビジネス要求

**ユーザーの要求**:
Job/Task Auto-Generation API の実行結果（特に `requirement_relaxation_suggestions`）を Marp プレゼンテーション形式で視覚化し、ユーザーに分かりやすく提示したい。

**想定シナリオ**:
1. ユーザーが要求を入力 → AI エージェントがタスク分割
2. ユーザーがレポート生成を指示
3. システムが Marp 形式のプレゼンテーションを返却
4. ユーザーが Marp CLI や Marp エディタでプレゼンテーションを表示・編集

### 機能要件

1. **Marp Markdown 生成**: Job/Task Generator の結果を Marp Markdown 形式に変換
2. **視覚的な構成**: タイトル、概要、提案詳細、まとめを含む構造化されたスライド
3. **API エンドポイント**: 既存の `/job-generator` エンドポイントの結果を受け取り、Marp を生成
4. **柔軟な入力**: JSON ファイルパス、job_id、直接 JSON データのいずれかを受け付け

### 非機能要件

- **パフォーマンス**: 1秒以内に Marp Markdown を生成
- **可読性**: Marp で表示した際に見やすいレイアウト
- **拡張性**: 将来的に他の形式（PDF、HTML）への変換も可能な設計

---

## 🏗️ アーキテクチャ設計

### システム構成

```
┌─────────────────────────────────────────────────────────────┐
│                        expertAgent                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │ POST /aiagent-api/v1/job-generator              │       │
│  │ - ユーザー要求から Job/Task を生成              │       │
│  │ - requirement_relaxation_suggestions を含む     │       │
│  └──────────────────────────────────────────────────┘       │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────┐       │
│  │ POST /aiagent-api/v1/marp-report                │ (NEW) │
│  │ - Job Generator の結果を Marp Markdown に変換  │       │
│  │ - スライド構成: タイトル、概要、提案、まとめ    │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### データフロー

```
1. ユーザー要求
   ↓
2. POST /job-generator → JobGeneratorResponse (JSON)
   {
     "status": "failed",
     "infeasible_tasks": [...],
     "requirement_relaxation_suggestions": [...]
   }
   ↓
3. POST /marp-report (JobGeneratorResponse を入力)
   ↓
4. Marp Markdown 生成
   ↓
5. レスポンス: Marp Markdown テキスト
```

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| **フレームワーク** | FastAPI | 既存の expertAgent と統一 |
| **テンプレートエンジン** | Jinja2 | Marp Markdown テンプレートの生成に適している |
| **バリデーション** | Pydantic | 入力の厳密な検証 |
| **Marp レンダリング** | ユーザー環境 | Marp CLI または Marp エディタで表示 (サーバー側では Markdown のみ生成) |

### ディレクトリ構成

```
expertAgent/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── job_generator_endpoints.py (既存)
│   │       └── marp_report_endpoints.py (NEW)
│   ├── schemas/
│   │   ├── job_generator.py (既存)
│   │   └── marp_report.py (NEW)
│   └── templates/
│       └── marp/
│           └── job_report.md.j2 (NEW)
└── tests/
    ├── unit/
    │   └── test_marp_report_endpoints.py (NEW)
    └── integration/
        └── test_marp_report_integration.py (NEW)
```

---

## 🎨 Marp スライド構成案

### スライド 1: タイトル

```markdown
---
marp: true
theme: default
paginate: true
---

# Job/Task 生成レポート

**ユーザー要求**: 企業名を入力すると、その企業の過去5年の売り上げとビジネスモデルの変化をまとめてメール送信する

**生成日時**: 2025-10-21 14:30:00
**ステータス**: failed (実現不可能タスクあり)

---
```

### スライド 2: 概要

```markdown
# 📊 実行結果サマリー

| 項目 | 値 |
|------|---|
| **ステータス** | failed |
| **実現不可能タスク数** | 3件 |
| **要求緩和提案数** | 10件 |
| **実行時間** | 72秒 |

---
```

### スライド 3-12: 各提案の詳細 (10件)

```markdown
# 提案 1: 企業の売上データ取得（一部手動処理）

## 📝 基本情報
- **元の要求**: 企業の売上データ取得
- **緩和後の要求**: 企業の売上データ取得（一部手動処理）
- **緩和タイプ**: intermediate_step_skip

## 🎯 評価
- **実現可能性**: high
- **推奨レベル**: strongly_recommended

---

# 提案 1: 詳細 (続き)

## ⚖️ トレードオフ
**犠牲になるもの**: 完全自動化が実現できず、一部手動での処理が必要となる。

**維持されるもの**: 企業の売上データを取得し、分析に活用することができる。

## 🔧 実装ガイド
**使用する機能**: geminiAgent, fetchAgent, stringTemplateAgent

**実装ステップ**:
1. ユーザーから企業名を受け取り、入力値の妥当性を確認する。
2. 外部データソースから、企業の過去2-3年分の売上データを取得する。
3. 取得したデータを手動でレビューし、必要に応じて追加情報を補完する。

---
```

### スライド 13: まとめ

```markdown
# 📈 まとめ

## Phase 11 の成果
- **提案生成数**: 1件 → **10件** (+900%改善)
- **LLM ベース**: Claude 3 Haiku による動的提案生成
- **コスト**: 約 $0.009/リクエスト (≈1円/回)

## 次のステップ
1. 提案から最適なものを選択
2. 要求を緩和して再度 Job 生成を実行
3. または、API 拡張を検討

---
```

---

## 🔧 API 設計

### エンドポイント仕様

**エンドポイント**: `POST /aiagent-api/v1/marp-report`

**リクエストスキーマ**:

```python
class MarpReportRequest(BaseModel):
    """Marp レポート生成リクエスト"""

    # 入力方法1: JobGeneratorResponse を直接渡す (推奨)
    job_result: JobGeneratorResponse | None = Field(
        default=None,
        description="Job Generator の実行結果 JSON"
    )

    # 入力方法2: JSON ファイルパスを指定
    json_file_path: str | None = Field(
        default=None,
        description="Job Generator 結果の JSON ファイルパス (例: /tmp/scenario1.json)"
    )

    # オプション
    theme: str = Field(
        default="default",
        description="Marp テーマ (default, gaia, uncover)",
        pattern="^(default|gaia|uncover)$"
    )
    include_implementation_steps: bool = Field(
        default=True,
        description="実装ステップを含めるかどうか"
    )
```

**レスポンススキーマ**:

```python
class MarpReportResponse(BaseModel):
    """Marp レポート生成レスポンス"""

    marp_markdown: str = Field(
        ...,
        description="生成された Marp Markdown テキスト"
    )

    slide_count: int = Field(
        ...,
        description="生成されたスライド数"
    )

    suggestions_count: int = Field(
        ...,
        description="含まれる提案数"
    )

    generation_time_ms: float = Field(
        ...,
        description="生成にかかった時間 (ミリ秒)"
    )
```

### エラーハンドリング

| エラーケース | HTTP ステータス | エラーメッセージ |
|-------------|----------------|-----------------|
| 入力が両方 None | 400 Bad Request | "Either job_result or json_file_path must be provided" |
| JSON ファイルが存在しない | 404 Not Found | "JSON file not found: {path}" |
| JSON パースエラー | 400 Bad Request | "Invalid JSON format" |
| テンプレートエラー | 500 Internal Server Error | "Failed to generate Marp report" |

---

## 🎯 実装方針

### Phase 1: 基盤実装 (60分)

1. **Pydantic スキーマ作成** (`app/schemas/marp_report.py`)
   - `MarpReportRequest`
   - `MarpReportResponse`

2. **Jinja2 テンプレート作成** (`app/templates/marp/job_report.md.j2`)
   - タイトルスライド
   - 概要スライド
   - 提案詳細スライド (ループ)
   - まとめスライド

3. **API エンドポイント実装** (`app/api/v1/marp_report_endpoints.py`)
   - リクエスト受付
   - JSON ファイル読み込み (json_file_path の場合)
   - Jinja2 テンプレートレンダリング
   - レスポンス返却

### Phase 2: テスト作成 (45分)

1. **単体テスト** (`tests/unit/test_marp_report_endpoints.py`)
   - リクエストバリデーション
   - JSON ファイル読み込み
   - Marp Markdown 生成

2. **結合テスト** (`tests/integration/test_marp_report_integration.py`)
   - `/marp-report` エンドポイント呼び出し
   - Scenario 1 の結果で実際に Marp 生成

### Phase 3: 検証・調整 (30分)

1. **Scenario 1 で実際に Marp 生成**
2. **Marp CLI でプレビュー確認**
3. **スライドレイアウトの調整**

### Phase 4: ドキュメント作成 (15分)

1. **API ドキュメント更新**
2. **README への使用例追加**

**総所要時間**: 約 2.5 時間

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守 / 単一責任の原則 (Marp 生成のみ)
- [x] **KISS原則**: 遵守 / シンプルな Jinja2 テンプレート使用
- [x] **YAGNI原則**: 遵守 / 必要最小限の機能のみ (Markdown 生成のみ、PDF変換は不要)
- [x] **DRY原則**: 遵守 / テンプレートの再利用

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠 / expertAgent のレイヤー分離を維持
- [x] 依存関係の方向性: API → Schemas → Templates

### 設定管理ルール
- [x] 環境変数: 不要 (Marp 生成に環境変数は使用しない)
- [x] myVault: 不要 (ユーザー API キーは使用しない)

### 品質担保方針
- [x] 単体テストカバレッジ: **目標90%以上**
- [x] 結合テストカバレッジ: **目標50%以上**
- [x] Ruff linting: エラーゼロ
- [x] MyPy type checking: エラーゼロ

### CI/CD準拠
- [x] PRラベル: `feature` ラベルを付与予定
- [x] コミットメッセージ: 規約に準拠
- [x] pre-push-check-all.sh: 実行予定

### 参照ドキュメント遵守
- [x] 新プロジェクト追加時: 該当なし (既存プロジェクト expertAgent への追加)
- [x] GraphAI ワークフロー開発時: 該当なし

### 違反・要検討項目
なし

---

## 📝 設計上の決定事項

### 決定事項 1: サーバー側では Markdown のみ生成

**理由**:
- Marp CLI や Marp エディタはユーザー環境で実行可能
- サーバー側で PDF/HTML 変換すると依存関係が増える
- Markdown であればユーザーが自由に編集・カスタマイズ可能

**代替案**:
- サーバー側で PDF 変換 → 却下 (依存関係増加、複雑度増加)
- HTML 変換のみ提供 → 却下 (ユーザーが編集できない)

### 決定事項 2: expertAgent に追加 (新サービスは作らない)

**理由**:
- Job/Task Generator の結果を直接変換する軽量な機能
- expertAgent と密結合している方が自然
- 将来的に Report Generator サービスに移行可能

**代替案**:
- 専用の Report Generator サービス → 却下 (現時点ではオーバーエンジニアリング)

### 決定事項 3: Jinja2 テンプレートエンジンを使用

**理由**:
- Python 標準的なテンプレートエンジン
- Marp Markdown の構造化に適している
- 既存の FastAPI プロジェクトとの親和性が高い

**代替案**:
- 文字列連結 → 却下 (保守性が低い)
- 別のテンプレートエンジン (Mako, Cheetah) → 却下 (学習コスト増)

### 決定事項 4: テーマは3種類のみサポート

**理由**:
- Marp 公式テーマ (default, gaia, uncover) で十分
- カスタムテーマはユーザー環境で追加可能

**代替案**:
- カスタムテーマのアップロード機能 → 却下 (セキュリティリスク、複雑度増加)

---

## 🔄 将来的な拡張案

### Phase 5 候補: PDF エクスポート機能 (優先度: 低)

**目的**: サーバー側で Marp Markdown → PDF 変換を提供

**実装方法**:
- Marp CLI をサーバーにインストール
- `marp --pdf` コマンドで PDF 生成
- バイナリレスポンスとして返却

**課題**:
- Docker イメージサイズ増加
- Chromium 依存関係の追加
- 実行時間の増加 (10-30秒)

### Phase 6 候補: カスタムテンプレート機能 (優先度: 中)

**目的**: ユーザーが独自のスライドテンプレートを定義可能に

**実装方法**:
- `POST /marp-report` にテンプレート文字列を含める
- Jinja2 でカスタムテンプレートをレンダリング

**課題**:
- セキュリティリスク (テンプレートインジェクション)
- バリデーションの複雑化

---

## 📚 参考資料

- [Marp 公式ドキュメント](https://marp.app/)
- [Marp CLI](https://github.com/marp-team/marp-cli)
- [Jinja2 ドキュメント](https://jinja.palletsprojects.com/)
- [FastAPI テンプレート](https://fastapi.tiangolo.com/advanced/templates/)
