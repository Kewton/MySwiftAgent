# V2 タスクチェーン 根本原因分析レポート

**作成日**: 2026-01-09
**関連Issue**: #342
**分析対象**: Job Generator V2 タスクチェーン実行エラー

---

## 1. エグゼクティブサマリー

Job Generator V2で生成されたタスクチェーンにおいて、複数のHTTP 422エラーが発生。
調査の結果、**5つの根本原因**と**3つの共通パターン**を特定した。

| 根本原因 | 影響範囲 | 重要度 |
|---------|---------|-------|
| body_template二重ネスト問題 | Task 0（最初のタスク） | 🔴 Critical |
| 出力ノード命名不整合 | Task 0→1間のデータ受け渡し | 🔴 Critical |
| sourceパス参照不整合 | 全タスク | 🟡 High |
| recipientフィールド欠落 | Task 2（メール送信） | 🟡 High |
| Interface変換の不完全性 | 全タスク | 🟡 High |

---

## 2. 問題の全体像

### 2.1 タスクチェーン構成

```
Job Master: jm_01KEH9NMY2WHPPSBFV9W5D2R3V
├── Task 0: Google検索 (tm_01KEH9NMX4QXABSWVDP6989650)
├── Task 1: 検索結果の要約 (tm_01KEH9NMXGDTH720AMYP1RG3J5)
└── Task 2: メール送信 (tm_01KEH9NMXSBJYCDR27KJ3FD7KC)
```

### 2.2 発生したエラー

| Task | エラー | 状態 |
|------|-------|------|
| Task 0 | HTTP 422 (num>3) | ✅ 修正済み |
| Task 0 | HTTP 422 (body_template) | ✅ 修正済み |
| Task 1 | データ未取得 | ⚠️ 原因特定済み |
| Task 2 | HTTP 422 (recipient欠落) | ⚠️ 原因特定済み |

---

## 3. 根本原因の詳細分析

### 3.1 根本原因1: body_template二重ネスト問題

**発生箇所**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py:338-358`

**コード**:
```python
def _build_body_template(self, order: int) -> dict[str, Any]:
    if order == 0:
        # First task uses job.body
        return {
            "user_input": "{{job.body}}",  # ← 問題: job.body全体を代入
            "job_params": "{{job.body}}",
        }
    else:
        # Subsequent tasks use previous task's output
        return {
            "user_input": f"{{{{tasks[{order - 1}].output_data}}}}",
            "job_params": "{{job.body}}",
        }
```

**問題の流れ**:
```
1. Job body: {"user_input": {"query": "..."}, "model_name": "..."}
2. body_template適用後:
   {"user_input": {"user_input": {"query": "..."}, "model_name": "..."}}
3. graphAiServer source injection:
   source.user_input = {"user_input": {"query": "..."}, ...}
4. ワークフロー参照: :source.user_input.query → undefined
```

**正しい動作**:
```python
"user_input": "{{job.body.user_input}}"  # user_input部分のみを渡す
```

**影響**: 全てのTask 0で発生する可能性

---

### 3.2 根本原因2: 出力ノード命名不整合

**発生箇所**: `jobqueue/app/core/worker.py:837-892`

**コード**:
```python
def _extract_graphai_output(response_data: Any) -> Any:
    # ...省略...
    results = response_data.get("results", {})

    output_node = results.get("output")  # ← "output"固定
    if output_node is None:
        # No output node, return full results
        logger.debug("[GRAPHAI_EXTRACT] No 'output' node found, returning full results")
        return results  # 全結果を返す
```

**問題の流れ**:
```
1. Task 0 ワークフロー: format_output (isResult: true) ← "output"ではない
2. GraphAI結果: {source: {...}, google_search: {...}, format_output: {...}}
3. 抽出関数: "output"ノードがないため全結果を返す
4. Task 1入力: format_output.search_resultsではなく、全体を受け取る
```

**YAML生成ルールとの矛盾**:
- GRAPHAI_WORKFLOW_GENERATION_RULES.md: `isResult: true`を持つノードは任意の名前可
- jobqueue worker: `output`という名前のみを抽出

**影響**: 出力ノード名が`output`以外の全ワークフロー

---

### 3.3 根本原因3: sourceパス参照不整合

**発生箇所**: ワークフローYAML生成（LLMによる生成）

**パターン比較**:

| タスク | ワークフローの参照パス | 実際のデータ構造 | 問題 |
|-------|---------------------|-----------------|------|
| Task 0 | :source.user_input.query | :source.user_input.query | ✅ 修正済み |
| Task 1 | :source.search_results | :source.user_input.google_search.search_results | ❌ パス不一致 |
| Task 2 | :source.recipient | 存在しない | ❌ フィールド欠落 |
| Task 2 | :source.subject | :source.user_input.email_subject | ❌ パス不一致 |
| Task 2 | :source.body | :source.user_input.email_body | ❌ パス不一致 |

**原因**:
- LLM生成時に`source`構造（`user_input`, `job_params`のネスト）を考慮していない
- タスクチェーン間のデータ変換ルールがLLMプロンプトに明記されていない

---

### 3.4 根本原因4: recipientフィールド欠落

**発生箇所**: データフロー設計（タスク分解時のパラメータ抽出）

**問題の流れ**:
```
1. Job説明: "メール送信先: newtons.boiled.clock@gmail.com"
2. Job body: {"user_input": {"query": "..."}}  ← recipientなし
3. Task 2（メール送信）ワークフロー: to: :source.recipient  ← 参照先なし
4. Gmail API: HTTP 422 (to is required)
```

**原因**:
- タスク分解時にrecipientをパラメータとして抽出していない
- 静的パラメータの伝達メカニズムが未設計

---

### 3.5 根本原因5: Interface変換の不完全性

**発生箇所**: `jobqueue/app/core/worker.py:_transform_to_interface()`

**期待される動作**:
```
Task 1 output_interface: {search_results: [...]}
Task 1 実際の出力: {source: {...}, google_search: {...}, format_output: {...}}
→ 変換後: {search_results: [...]}
```

**実際の動作**:
- `_extract_graphai_output()`が先に実行
- `output`ノードがないため全結果を返す
- `_transform_to_interface()`は`search_results`を探すが、トップレベルに存在しない

---

## 4. 共通パターンの特定

### パターン1: データ構造の暗黙の前提

| コンポーネント | 前提 | 実際 |
|--------------|------|-----|
| ワークフロー | :source.X | :source.user_input.X |
| jobqueue worker | output ノード | 任意のisResultノード |
| body_template | job.bodyは単純構造 | job.bodyはネスト構造 |

**原因**: コンポーネント間のデータ契約が明文化されていない

---

### パターン2: LLM生成とシステム制約の乖離

- LLMはワークフローを自由に生成
- システムは特定の構造（outputノード名、sourceパス）を期待
- LLM生成プロンプトにシステム制約が反映されていない

---

### パターン3: エラーの連鎖伝播

```
Task 0 出力構造問題
    → Task 1 データ取得失敗
    → Task 2 不完全なデータ
    → Task 3 必須フィールド欠落
```

**影響**: 1つの問題が後続タスク全てに波及

---

## 5. 技術的詳細

### 5.1 graphAiServer source injection

```javascript
// graphAiServer/src/services/graphai.ts
const sourceData: SourceNodeData = {
  user_input: mergedUserInput,  // ← 動的入力
  job_params: job_params || {}, // ← 静的パラメータ
};
graph.injectValue("source", sourceData);
```

**ワークフローからの参照**:
- `:source.user_input.*` - 前タスクからの入力
- `:source.job_params.*` - ジョブパラメータ（静的）

### 5.2 jobqueue template resolution

```python
# jobqueue/app/services/template_resolver.py
"{{job.body}}" → job.body全体
"{{job.body.user_input}}" → job.body["user_input"]のみ
"{{tasks[0].output_data}}" → tasks[0].output_data
```

### 5.3 タスク出力抽出フロー

```
GraphAI Response
    ↓
_extract_graphai_output() → "output"ノードを探す
    ↓
_transform_to_interface() → output_schemaに基づき変換
    ↓
task.output_data に保存
```

---

## 6. 修正方針

### 6.1 即時修正（ワークフロー個別修正）

| 対象 | 修正内容 |
|-----|---------|
| Task 0 ワークフロー | 出力ノード名を`output`に変更 |
| Task 1 ワークフロー | sourceパスを`:source.user_input.*`形式に修正 |
| Task 2 ワークフロー | sourceパス修正 + recipient参照先の設定 |
| Job Master body | recipientフィールドを追加 |

### 6.2 システム修正（根本対策）

| コンポーネント | 修正内容 | 優先度 |
|--------------|---------|-------|
| master_manager.py | `{{job.body}}`を`{{job.body.user_input}}`に変更 | 🔴 High |
| worker.py | isResult:trueノードを動的に検出 | 🔴 High |
| yaml_generator.py | 出力ノード名を`output`に統一 | 🟡 Medium |
| LLMプロンプト | source構造制約を追加 | 🟡 Medium |

### 6.3 設計改善（長期対策）

1. **データ契約の明文化**
   - graphAiServer ↔ jobqueue間のデータ形式を仕様化
   - タスク間インターフェースの厳密な定義

2. **検証機能の強化**
   - ワークフロー生成時のsourceパス検証
   - タスクチェーン実行前のデータフロー検証

3. **エラーハンドリング改善**
   - 各タスクでのデータ検証と早期エラー報告
   - より詳細なエラーメッセージ

---

## 7. 検証チェックリスト

### 修正後の確認項目

- [ ] Task 0: body_templateが`{{job.body.user_input}}`を使用
- [ ] Task 0 ワークフロー: 出力ノード名が`output`
- [ ] Task 1 ワークフロー: `:source.user_input.*`パスを使用
- [ ] Task 2 ワークフロー: `:source.user_input.*`パスを使用 + recipientが取得可能
- [ ] E2Eテスト: タスクチェーン全体が成功

### 回帰テスト項目

- [ ] 既存の単一タスクジョブが動作
- [ ] 他のタスクチェーンジョブが動作
- [ ] num パラメータ制限（≤3）が有効

---

## 8. 関連ファイル

| ファイル | 役割 |
|---------|-----|
| `expertAgent/.../master_manager.py` | body_template生成 |
| `expertAgent/.../yaml_generator.py` | ワークフローYAML生成 |
| `jobqueue/.../worker.py` | タスク実行・出力抽出 |
| `graphAiServer/.../graphai.ts` | source injection |
| `graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md` | 生成ルール |

---

## 9. 付録: 問題発生時のデバッグ手順

### A. タスク出力の確認
```bash
curl "http://localhost:8001/api/v1/jobs/{job_id}/tasks" | jq '.tasks[] | {order, status, output_data}'
```

### B. GraphAI直接呼び出しテスト
```bash
curl "http://localhost:8005/api/v1/myagent" -X POST \
  -H "Content-Type: application/json" \
  -d '{"user_input": {...}, "model_name": "..."}'
```

### C. ワークフローソースパス確認
```bash
cat graphAiServer/config/graphai/taskmaster/{task_master_id}/*.yml | grep ":source"
```

---

## 10. アーキテクチャレビュー対応状況

**レビュー日**: 2026-01-09
**レビュー結果**: 条件付き承認（Conditionally Approved）

### 10.1 指摘事項と対応

| 指摘事項 | 対応状況 | 成果物 |
|---------|---------|--------|
| データ契約の明文化 | ✅ 完了 | `docs/spec/taskchain-data-contract.md` |
| 回帰テスト計画の明確化 | ✅ 完了 | `v2-taskchain-regression-test-plan.md` |
| Phase 1完了条件の明確化 | ✅ 完了 | 対策案に追記 |

### 10.2 設計原則の遵守状況

| 原則 | 指摘 | 対応予定 |
|-----|------|---------|
| Open/Closed | 出力ノード名がハードコード | Phase 2でisResult動的検出を実装 |
| Single Responsibility | workerが複数責務を持つ | Phase 2で抽出と変換を分離 |
| DRY | sourceパス構造が分散 | データ契約ドキュメントで一元化 |

### 10.3 承認条件の充足状況

- [x] 必須改善項目の対策実施計画を作成
- [x] データ契約ドキュメントをPhase 1に含める
- [x] 回帰テスト計画を明確化

### 10.4 関連ドキュメント

- `docs/spec/taskchain-data-contract.md` - データ契約仕様書
- `v2-taskchain-regression-test-plan.md` - 回帰テスト計画
- `v2-taskchain-remediation-plan.md` - 対策案（更新済み）
