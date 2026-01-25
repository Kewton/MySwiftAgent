# Marpレポート スライド構造説明書

**作成日**: 2025-10-21
**対象**: Job/Task Auto-Generation Marp Report
**実装ブランチ**: feature/issue/97

---

## 📋 目的

このMarpレポートは、**Job/Task Auto-Generation API** (`/v1/job-generator`) の実行結果を、視覚的に分かりやすいプレゼンテーションスライドとして出力するものです。

ユーザーからの要求（自然言語）に対して、以下の情報を提供します：

- ✅ **成功ケース**: 生成されたタスク一覧とジョブマスターへの登録状況
- ❌ **失敗ケース**: 実現不可能なタスクと、それに対する要求緩和提案（10件の詳細提案）

---

## 🎯 ユーザーからの拡張要求（Phase 11で実装）

このMarpレポート機能は、以下の4つの拡張要件に基づいて実装されました：

### 1. **成功・失敗の両方でタスクリストを表示**
   - **要求**: 成功ケースでもタスク一覧を表示してほしい
   - **実装**: すべてのケースでタスクリストスライドを追加

### 2. **失敗ケースでタスクと対策提案を紐付ける**
   - **要求**: どのタスクに対してどの緩和提案が有効かを明示してほしい
   - **実装**: タスク名と提案の `original_requirement` をマッチングし、各タスクに最大2件の対策提案を表示

### 3. **提案タイトルを日本語化**
   - **要求**: 技術的な英語用語（`data_source_substitution`等）ではなく、分かりやすい日本語ラベルで表示してほしい
   - **実装**: 7種類の緩和タイプに対して日本語ラベルを付与（詳細は後述）

### 4. **タスク表示数を5件/スライドに変更**
   - **要求**: 当初3件/スライドで実装したが、5件/スライドに増やしてほしい
   - **実装**: スライドページネーションロジックを `5件/スライド` に変更

---

## 📊 スライド構造の全体像

### **成功ケース** (4スライド)

| スライド番号 | タイトル | 内容 | データソース |
|------------|---------|------|------------|
| 1 | タイトル | ユーザー要求、実行日時、ステータス | `status`, `error_message`, `timestamp` |
| 2 | 実行結果サマリー | ステータス、実現不可能タスク数、要求緩和提案数 | `infeasible_tasks`, `requirement_relaxation_suggestions` |
| 3 | 生成されたタスク一覧 (1/1) | タスク名、説明、優先度（最大5件） | `task_breakdown[].task_name`, `.description`, `.priority` |
| 4 | まとめ | 次のステップ、Job ID | `job_id` |

**総スライド数計算式**: `3 + ceil(tasks_count / 5) + 0`
（成功ケースは提案なしのため `+0`）

---

### **失敗ケース** (36スライド)

| スライド番号 | タイトル | 内容 | データソース |
|------------|---------|------|------------|
| 1 | タイトル | ユーザー要求、実行日時、ステータス | `status`, `error_message`, `timestamp` |
| 2 | 実行結果サマリー | ⚠️実現不可能タスク検出の警告 | `infeasible_tasks`, `requirement_relaxation_suggestions` |
| 3-5 | 📋 生成されたタスク一覧 (1/3, 2/3, 3/3) | 各タスクに対し：<br>- タスク名、説明、優先度<br>- 💡対策提案（最大2件、日本語ラベル付き） | `task_breakdown[]`, `task_suggestions_map` |
| 6-35 | 💡 提案 1-10（各3スライド） | 各提案につき：<br>- **1枚目**: 元の要求、緩和後の要求<br>- **2枚目**: 実現可能性、犠牲/維持するもの<br>- **3枚目**: 実装ガイド、使用機能、ステップ | `requirement_relaxation_suggestions[]` |
| 36 | 📝 まとめ | Phase 11の成果、次のステップ | - |

**総スライド数計算式**: `3 + ceil(11 / 5) + (10 × 3) = 36`
（タスク11件 → 3スライド、提案10件 → 30スライド）

---

## 🔍 詳細スライド構成

### **スライド1: タイトル**

**表示内容**:
```markdown
# Job/Task 生成レポート

## ユーザー要求
{元の要求または成功メッセージ}

---

**実行日時**: {YYYY-MM-DD HH:MM:SS UTC}
**ステータス**: `{success/failed}`
```

**データソース**:
- `job_result["error_message"]` から抽出（失敗ケース）
- デフォルト値: "Job/Task 生成が正常に完了しました" （成功ケース）
- `timestamp`: レポート生成日時（UTC）

**変更点**:
- ユーザー要求をタイトル行ではなく、見出し付き本文として表示
- ステータスをコードブロック形式 (`) で強調表示

---

### **スライド2: 実行結果サマリー**

**表示内容**:
```markdown
# 📊 実行結果サマリー

| 項目 | 結果 |
|------|------|
| ステータス | **{success/failed}** |
| 実現不可能タスク | {N}件 |
| 要求緩和提案 | {N}件 |
```

**失敗ケースのみ**:
```markdown
**⚠️ 実現不可能なタスクが検出されました**

要求緩和提案を参考に、要求を見直してください。
```

**データソース**:
- `infeasible_tasks`: 実現不可能タスク配列の長さ
- `requirement_relaxation_suggestions`: 提案配列の長さ

---

### **スライド3以降: タスク一覧**

#### **表示ロジック**:
- **5件/スライド** で分割（フォントサイズ 0.8em で表示）
- タスク総数 `N` の場合、`ceil(N / 5)` スライド生成
- 失敗ケースでは警告メッセージ「⚠️ 注意: 実現不可能なタスクが含まれている可能性があります」を表示

#### **各タスクの表示内容**:

**すべてのケース共通**:
```markdown
<!-- _class: task-list -->
# 📋 生成されたタスク一覧 (1/N)

{% if status == 'failed' %}
**⚠️ 注意**: 実現不可能なタスクが含まれている可能性があります
{% endif %}

## {N}. {task_name}

<div class="task-detail">

**タスクID**: `{task_id}`
**説明**: {description}
**優先度**: {priority}
**期待される成果物**: {expected_output[:200]}...
**依存タスク**: {dependencies (カンマ区切り)}

</div>
```

**失敗ケースのみ追加**:
```markdown
💡 **対策提案**: {マッチする提案数}件
  - {relaxation_type_ja}: {relaxed_requirement[:50]}...
  - {relaxation_type_ja}: {relaxed_requirement[:50]}...
```
（最大2件まで表示）

**データソース**:
- `task_breakdown[].name` または `task_breakdown[].task_name`: タスク名
- `task_breakdown[].task_id`: タスクID
- `task_breakdown[].description`: タスク説明
- `task_breakdown[].priority`: 優先度
- `task_breakdown[].expected_output`: 期待される成果物（最大200文字）
- `task_breakdown[].dependencies`: 依存タスク配列
- `task_suggestions_map[task_name]`: タスクに紐づく提案配列

**マッチングロジック**:
```python
# Support both 'name' and 'task_name' field names
task_name = task.get("name") or task.get("task_name", "")
# タスク名が提案の original_requirement に含まれる場合にマッチ
if task_name and task_name in suggestion["original_requirement"]:
    matched = True
```

**CSSスタイル**:
```css
section.task-list {
  font-size: 0.8em;
}
section.task-list h2 {
  font-size: 1.2em;
  margin-bottom: 0.3em;
}
section.task-list .task-detail {
  line-height: 1.4;
}
```

---

### **スライド（失敗ケースのみ）: 要求緩和提案詳細**

各提案につき **3スライド** で構成：

#### **提案スライド1枚目**:
```markdown
# 💡 提案 {N}: {relaxation_type_ja}

## 元の要求
{original_requirement}

## 緩和後の要求
{relaxed_requirement}
```

#### **提案スライド2枚目**:
```markdown
# 💡 提案 {N} (続き)

## 実現可能性
**{feasibility_after_relaxation}** (推奨レベル: **{recommendation_level}**)

## 犠牲にするもの
{what_is_sacrificed}

## 維持されるもの
{what_is_preserved}
```

#### **提案スライド3枚目**:
```markdown
# 💡 提案 {N} (実装ガイド)

## 実装時の注意点
{implementation_note}

## 使用する機能
- {capability_1}
- {capability_2}
...

## 実装ステップ
{implementation_steps[]}
```

**データソース**: `requirement_relaxation_suggestions[]`

---

### **最終スライド: まとめ**

**失敗ケース**:
```markdown
# 📝 まとめ

## Phase 11 の成果
- **{N}件** の詳細な要求緩和提案を生成
- LLM (Claude 3 Haiku) による高品質な提案
- 実装ステップまで含む実用的なガイダンス

## 次のステップ
1. 提案を検討し、最適な緩和案を選択
2. 緩和した要求で再度 Job Generator を実行
3. ジョブマスターへの登録を完了
```

**成功ケース**:
```markdown
# 📝 まとめ

## 次のステップ
- ジョブマスターへの登録が完了しています
- Job ID: {job_id}
```

---

## 🌐 日本語ラベル対応表

### **relaxation_type → relaxation_type_ja マッピング**

| 英語キー (relaxation_type) | 日本語ラベル (relaxation_type_ja) |
|---------------------------|--------------------------------|
| `data_source_substitution` | データソース代替案 |
| `intermediate_step_skip` | 中間処理の簡略化 |
| `output_format_change` | 出力形式の変更 |
| `scope_reduction` | 対象範囲の縮小 |
| `automation_level_reduction` | 自動化レベルの調整 |
| `phased_implementation` | 段階的実装 |
| `requirement_relaxation` | 要求仕様の緩和 |

**実装箇所**: `app/api/v1/marp_report_endpoints.py:24-32`

**使用例**:
- 提案タイトル: `# 💡 提案 1: データソース代替案`
- タスク内対策提案: `- 中間処理の簡略化: 売上データ分析において...`

---

## 📦 データフロー図

```
Job Generator API (/v1/job-generator)
  ↓
job_result JSON
  ├── status: "success" / "failed"
  ├── task_breakdown: [...]  ← タスクリストスライドに使用
  ├── infeasible_tasks: [...]
  ├── requirement_relaxation_suggestions: [...]  ← 提案詳細スライドに使用
  └── job_id: "..."
  ↓
Marp Report API (/v1/marp-report)
  ↓
_extract_template_data()
  ├── tasks ← task_breakdown から抽出
  ├── task_suggestions_map ← タスク名と提案をマッチング
  ├── relaxation_type_ja ← 各提案に日本語ラベル追加
  └── tasks_count ← スライド数計算用
  ↓
Jinja2 Template (job_report.md.j2)
  ├── タスクリストスライド: {% for task in tasks %}
  ├── 提案詳細スライド: {% for suggestion in suggestions %}
  └── スライド数計算: 3 + ceil(tasks/5) + (suggestions*3)
  ↓
Marp Markdown (.md)
  ↓
Marpツール
  ↓
プレゼンテーションスライド (HTML/PDF/PPTX)
```

---

## 🔍 実装の詳細

### **タスク-提案マッチングロジック**

**関数**: `_group_suggestions_by_task(suggestions, tasks)`
**場所**: `app/api/v1/marp_report_endpoints.py:47-71`

```python
for task in tasks:
    task_name = task.get("task_name", "")
    # タスク名が original_requirement に含まれる場合にマッチ
    matching_suggestions = [
        s for s in suggestions
        if task_name and task_name in s.get("original_requirement", "")
    ]
    task_suggestions_map[task_name] = matching_suggestions
```

**例**:
- タスク名: "企業名入力受付"
- 提案の original_requirement: "企業名入力受付において、入力形式をメール送信から..."
- → **マッチング成功** → タスクスライドに対策提案として表示

---

### **スライド数計算ロジック**

**関数**: `_count_slides(suggestions_count, include_implementation_steps, tasks_count)`
**場所**: `app/api/v1/marp_report_endpoints.py:167-193`

```python
import math

task_slides = math.ceil(tasks_count / 5) if tasks_count > 0 else 0
suggestion_slides = suggestions_count * 3

return 3 + task_slides + suggestion_slides
```

**例**:
- タスク11件 → `ceil(11 / 5) = 3` スライド
- 提案10件 → `10 × 3 = 30` スライド
- 合計 → `3 + 3 + 30 = 36` スライド

---

## 📂 関連ファイル

| ファイルパス | 役割 |
|------------|------|
| `app/api/v1/marp_report_endpoints.py` | APIエンドポイント、データ抽出ロジック、日本語ラベル定義 |
| `app/templates/marp/job_report.md.j2` | Jinja2テンプレート、スライドレイアウト定義 |
| `app/schemas/marp_report.py` | リクエスト/レスポンススキーマ定義 |
| `/tmp/scenario1_phase11_model_fix_result.json` | 失敗ケースのテストデータ（11タスク、10提案） |
| `/tmp/success_case_marp_enhanced.md` | 成功ケースの生成結果（4スライド） |
| `dev-reports/feature/issue/97/marp/failed-case.md` | 失敗ケースの生成結果（36スライド） |

---

## 🚀 使用方法

### **API呼び出し例**

```bash
# 失敗ケースのレポート生成
curl -X POST http://localhost:8104/aiagent-api/v1/marp-report \
  -H "Content-Type: application/json" \
  -d '{
    "json_file_path": "/tmp/scenario1_phase11_model_fix_result.json",
    "theme": "default",
    "include_implementation_steps": true
  }'

# 成功ケースのレポート生成
curl -X POST http://localhost:8104/aiagent-api/v1/marp-report \
  -H "Content-Type: application/json" \
  -d '{
    "job_result": {...},
    "theme": "gaia",
    "include_implementation_steps": false
  }'
```

### **レスポンス例**

```json
{
  "marp_markdown": "---\nmarp: true\n...",
  "slide_count": 36,
  "suggestions_count": 10,
  "generation_time_ms": 4.48
}
```

---

## 📝 ユーザーからの元の要求との対応

| ユーザー要求 | 実装箇所 | スライド表示 |
|------------|---------|------------|
| **成功・失敗の両方でタスク表示** | `job_report.md.j2:37-62` | スライド3以降（5件/スライド） |
| **タスクと対策提案の紐付け** | `_group_suggestions_by_task()` | タスクスライド内に💡対策提案を表示 |
| **提案タイトルの日本語化** | `RELAXATION_TYPE_LABELS_JA` | `relaxation_type_ja` フィールド使用 |
| **5件/スライドに変更** | `_count_slides()`, テンプレート | `{% if loop.index0 % 5 == 0 %}` |

---

## 🔧 今後の改善案

1. **タスク名の欠落問題**:
   - 現状: テストデータに `task_name` フィールドが含まれていない
   - 対策: Job Generator側で `task_name` を必須フィールドとして強制

2. **マッチング精度の向上**:
   - 現状: 単純な部分文字列マッチング
   - 対策: 類似度スコアリング、LLMベースのセマンティックマッチング

3. **テーマのカスタマイズ**:
   - 現状: `default`, `gaia`, `uncover` の3種類
   - 対策: プロジェクト固有のカスタムテーマ追加

---

**🤖 Generated with Claude Code**
**Document Type**: Marp Report Slide Structure Documentation
**Generated at**: 2025-10-21 13:40 UTC
