# task_api_mapping 未使用問題 調査・対応方針レポート

**Issue**: #305 (関連調査)
**作成日**: 2025-12-24
**ステータス**: 対応方針検討中

---

## 1. 問題概要

v1.34 において、PDF ファイル読み取りタスクに「ファイル読み取りエージェント (File Reader Agent)」が推奨されない問題が報告された。

調査の結果、`expert_agent_capabilities.yaml` の `task_api_mapping` セクションがコード内で**一切使用されていない**ことが判明した。

---

## 2. 現状分析

### 2.1 YAML 定義（正常）

`expert_agent_capabilities.yaml` には以下が正しく定義されている：

#### AI Agent APIs セクション (lines 576-596)
```yaml
- name: "File Reader Agent"
  endpoint: "/v1/aiagent/utility/file_reader"
  method: "POST"
  description: "ファイル読み取りエージェント"
  use_cases:
    - "テキストファイル読み取り"
    - "PDFファイル読み取り"
    - "画像の読み取り・OCR"
    - "複数ファイルの一括処理"
```

#### task_api_mapping セクション (lines 800-811)
```yaml
- task_type: "ファイル読み取り"
  keywords:
    - "ファイル読み取り"
    - "PDF読み取り"
    - "テキスト抽出"
    - "OCR"
  recommended_api:
    api_name: "File Reader Agent"
    endpoint: "/v1/aiagent/utility/file_reader"
    method: "POST"
  reason: "テキスト・PDF・画像の読み取り対応"
```

### 2.2 コードでの使用状況（問題箇所）

| ファイル | 関数 | 使用セクション | `task_api_mapping` |
|----------|------|--------------|-------------------|
| `graphai_capabilities.py` | `_load_expert_agent_apis()` | `utility_apis`, `ai_agent_apis` | **❌ 未読込** |
| `task_breakdown.py` | `_build_expert_agent_capabilities()` | `utility_apis`, `ai_agent_apis` | **❌ 未使用** |
| `workflow_generation.py` | `create_workflow_generation_prompt()` | `utility_apis`, `ai_agent_apis` | **❌ 未使用** |

### 2.3 問題の原因

1. `task_api_mapping` は参照ドキュメントとして YAML に追加されたが、コードに統合されなかった
2. LLM プロンプトには API 一覧が渡されるが、「どのタスクにどの API を使うべきか」の明示的なガイダンスがない
3. LLM が独自判断で他の API（例: JSON Output Agent）を選択してしまう

---

## 3. 対応方針

### 方針 A: task_api_mapping をプロンプトに追加（推奨）

**概要**: LLM に渡すプロンプトに `task_api_mapping` の情報を追加し、タスク種別ごとの推奨 API を明示する。

**メリット**:
- 既存コード構造を大きく変更せずに対応可能
- LLM の API 選択精度が向上
- YAML 定義を活用できる

**デメリット**:
- プロンプトが長くなる（トークン消費増加）

**実装箇所**:
1. `task_breakdown.py` の `_build_expert_agent_capabilities()` に `task_api_mapping` セクションを追加
2. プロンプトに「タスク種別ごとの推奨 API」テーブルを含める

**変更例**:
```python
def _build_expert_agent_capabilities() -> str:
    config = _load_yaml_config("expert_agent_capabilities.yaml")
    lines = ["**expertAgent Direct API一覧**:", ""]

    # 既存: Utility APIs
    # 既存: AI Agent APIs

    # 追加: Task-to-API Mapping
    task_mappings = config.get("task_api_mapping", [])
    if task_mappings:
        lines.append("")
        lines.append("**タスク種別ごとの推奨API**:")
        lines.append("")
        lines.append("| タスク種別 | 推奨API | エンドポイント | 理由 |")
        lines.append("|-----------|---------|---------------|------|")
        for mapping in task_mappings:
            api = mapping.get("recommended_api", {})
            lines.append(
                f"| {mapping['task_type']} | {api.get('api_name', '')} | "
                f"`{api.get('endpoint', '')}` | {mapping.get('reason', '')} |"
            )

    return "\n".join(lines)
```

---

### 方針 B: プログラム的な API 自動選択

**概要**: タスク分解後に、タスク名・説明からキーワードマッチングで推奨 API を自動付与する。

**メリット**:
- LLM に依存しない確実な API 選択
- プロンプトサイズ増加なし

**デメリット**:
- キーワードマッチングの精度に限界
- 新規タスク種別への対応が手動になる

**実装箇所**:
1. `graphai_capabilities.py` に `task_api_mapping` ローダーを追加
2. タスク分解後の後処理で `recommended_apis` を自動補完

---

### 方針 C: Few-shot プロンプトの強化

**概要**: プロンプト内の例（Examples）に File Reader Agent を使用するケースを追加。

**メリット**:
- 最小限の変更で対応可能
- LLM の学習効果を利用

**デメリット**:
- 全てのタスク種別をカバーするのは困難
- 例が増えるとプロンプトが肥大化

**実装箇所**:
- `prompts/task_breakdown/default.yaml` に例を追加

---

## 4. 推奨対応

### 短期対応（推奨: 方針 A）

`_build_expert_agent_capabilities()` を修正し、`task_api_mapping` をプロンプトに含める。

**工数見積**: 2-3 時間
- コード修正: 1 時間
- テスト作成・実行: 1-2 時間

### 長期対応（オプション: 方針 B との併用）

キーワードマッチングによる自動補完を追加し、LLM の選択ミスをフォールバックでカバー。

**工数見積**: 4-6 時間
- キーワードマッチング実装: 2 時間
- 後処理ロジック追加: 2 時間
- テスト: 2 時間

---

## 5. 影響を受けるタスク種別

`task_api_mapping` が使用されていないため、以下の全マッピングが機能していない：

| タスク種別 | 推奨 API | 現状 |
|-----------|---------|------|
| 音声合成 | Text-to-Speech + Google Drive | ❌ 推奨されない可能性 |
| ファイルアップロード | Google Drive Upload | ❌ 推奨されない可能性 |
| メール送信 | Gmail送信 | ⚠️ 例示があるため動作 |
| メール検索 | Gmail検索 | ⚠️ 例示があるため動作 |
| Web検索 | Google検索 | ⚠️ 例示があるため動作 |
| **ファイル読み取り** | **File Reader Agent** | **❌ 推奨されない** |
| Wikipedia検索 | Wikipedia Agent | ❌ 推奨されない可能性 |

---

## 6. テスト計画

### ユニットテスト
- `_build_expert_agent_capabilities()` が `task_api_mapping` を含むことを確認
- 各タスク種別のマッピングが正しく出力されることを確認

### 統合テスト
- PDF ファイル読み取りタスクで File Reader Agent が推奨されることを確認
- 音声合成タスクで Text-to-Speech が推奨されることを確認

### 受入テスト
- v1.34 相当のシナリオで PDF 読み取りが正しく動作することを確認

---

## 7. 関連ファイル

| ファイルパス | 変更予定 |
|-------------|---------|
| `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/task_breakdown.py` | ✅ 修正必要 |
| `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/graphai_capabilities.py` | 🔶 方針Bの場合 |
| `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py` | 🔶 オプション |
| `expertAgent/tests/unit/test_task_breakdown.py` | ✅ テスト追加 |

---

## 8. 次のアクション

1. [ ] 対応方針の承認を得る
2. [ ] 方針 A の実装
3. [ ] ユニットテスト追加
4. [ ] 統合テストで動作確認
5. [ ] v1.34 シナリオで受入テスト

---

**作成者**: Claude Code
**レビュー待ち**: ユーザー確認
