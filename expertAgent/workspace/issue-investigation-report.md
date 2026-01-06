# Issue 調査レポート: JSON.stringify 問題と関連 Issue の実装状況

**作成日**: 2026-01-02
**調査対象**: Issue #321, #322, #325, #331, #333, #338

---

## 1. エグゼクティブサマリー

### 発見された重大な問題

| 問題 | 深刻度 | 影響範囲 | 状態 |
|-----|--------|---------|------|
| `${JSON.stringify()}` 構文が未サポート | **Critical** | 全ワークフロー生成 | 未修正 |
| Object→String 変換方法の欠如 | **High** | LLM API 呼び出し | 設計未定 |
| Issue #333 の TYPE_VALIDATION_RULES 誤記 | **Critical** | 生成プロンプト | 未修正 |

### Issue 実装状況一覧

| Issue | タイトル | 状態 | 問題有無 |
|-------|---------|------|---------|
| #321 | パラメータ抽出機能 | ✅ 完了 | 問題なし |
| #322 | body_template 検証機能 | ✅ 完了 | 一部制限あり |
| #325 | Job Generator 実行信頼性向上 | 🔶 一部完了 | 子Issue残存 |
| #331 | graphAiServer job_params 対応 | ✅ 完了 | 問題なし |
| #333 | API型・フィールド名検証 | ❌ バグあり | **誤った指示** |
| #338 | インターフェース契約強制 | ✅ 完了 | 問題なし |

---

## 2. 根本原因の詳細分析

### 2.1 問題の発生メカニズム

```
┌────────────────────────────────────────────────────────────────┐
│  Issue #333 で追加された TYPE_VALIDATION_RULES                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ### stringTemplateAgent Type Conversion Pattern          │ │
│  │ template: "${JSON.stringify(data)}"  ← 誤った指示        │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↓
                    LLM がこの指示に従う
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  生成されたワークフロー YAML                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ build_summary_prompt:                                    │ │
│  │   agent: stringTemplateAgent                             │ │
│  │   params:                                                │ │
│  │     template: |-                                         │ │
│  │       検索結果:                                           │ │
│  │       ${JSON.stringify(search_results, null, 2)}         │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↓
                    GraphAI が実行
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  stringTemplateAgent の実際の動作                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ template.replace("${" + key + "}", namedInputs[key])     │ │
│  │                                                          │ │
│  │ → 単純な文字列置換のみ                                    │ │
│  │ → JavaScript 関数は評価されない                           │ │
│  │ → "${JSON.stringify(...)}" はそのまま残る                │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↓
                         結果
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  LLM に渡されるプロンプト                                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 検索結果:                                                 │ │
│  │ ${JSON.stringify(search_results, null, 2)}               │ │
│  │                                                          │ │
│  │ ← search_results の内容ではなくリテラル文字列             │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 GraphAI stringTemplateAgent の実際の仕様

**ソースコード**: `@graphai/vanilla/lib/string_agents/string_template_agent.js`

```javascript
const stringTemplateAgent = async ({ params, namedInputs }) => {
    if (params.template === undefined) {
        if (namedInputs.text) {
            return namedInputs.text;
        }
        console.warn("warning: stringTemplateAgent no template");
    }
    return Object.keys(namedInputs).reduce((template, key) => {
        return processTemplate(template, "${" + key + "}", namedInputs[key]);
    }, params.template);
};

const processTemplate = (template, match, input) => {
    if (typeof template === "string") {
        if (template === match) {
            return input;  // テンプレート全体がプレースホルダーの場合、型を保持
        }
        return template.replace(match, input);  // 単純な文字列置換
    }
    // ... 配列・オブジェクト処理
};
```

**サポートされる機能**:
- `${variable}` - シンプルな変数展開
- テンプレート全体が `${key}` の場合、入力値の型を保持

**サポートされない機能**:
- `${JSON.stringify(data)}` - JavaScript 関数
- `${data.field}` - ネストアクセス
- その他の JavaScript 式

### 2.3 Object 型を String 型に変換する正しい方法

現在の GraphAI には Object→String 変換の標準的な方法が**存在しない**。

**可能なワークアラウンド**:

| 方法 | 実現可能性 | 課題 |
|-----|-----------|------|
| テンプレート全体を `${data}` にする | ✅ | オブジェクトは `[object Object]` になる |
| カスタム `jsonStringifyAgent` を作成 | ⚠️ | GraphAI 拡張が必要 |
| expertAgent API で変換 | ⚠️ | 追加の API 呼び出しが必要 |
| ワークフロー設計で回避 | ✅ | LLM に渡すデータ構造を変更 |

---

## 3. 各 Issue の詳細分析

### 3.1 Issue #321: パラメータ抽出機能

**状態**: ✅ 正常に実装

**実装箇所**:
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/requirement_analysis.py:194-209`
- `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/job_registration.py:19-40`

**検証結果**:
```python
# requirement_analysis.py
job_body_parameters = [param.model_dump() for param in response.job_body_parameters]
if job_body_parameters:
    logger.info(
        "Extracted %d job body parameters: %s",
        len(job_body_parameters),
        [p["name"] for p in job_body_parameters],
    )

# job_registration.py
def _build_job_body(job_body_parameters: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not job_body_parameters:
        return None
    body = {}
    for param in job_body_parameters:
        name = param.get("name")
        value = param.get("value")
        if name and value is not None:
            body[name] = value
    return body if body else None
```

**問題点**: なし

---

### 3.2 Issue #322: body_template 検証機能

**状態**: ✅ 実装済み（一部制限あり）

**実装箇所**:
- `jobqueue/app/api/v1/task_masters.py:86-87`
- `jobqueue/app/services/template_validator.py`

**検証結果**:
```python
# task_masters.py
if master_data.body_template is not None:
    template_validation = TemplateValidator.validate(master_data.body_template)
```

**制限事項**:
1. テンプレート構文の検証のみ（`{{job.body.field}}` 形式のチェック）
2. 参照先フィールドの存在確認は**行われない**
3. 検証結果は情報提供のみ（エラーでもブロックしない）

**改善提案**:
- Job body スキーマとの照合機能を追加
- 必須フィールドの null 検出時にエラーとする

---

### 3.3 Issue #325: Job Generator 実行信頼性向上

**状態**: 🔶 一部完了

**子 Issue 状況**:

| Issue | タイトル | 状態 | 備考 |
|-------|---------|------|------|
| #321 | パラメータ抽出 | ✅ 完了 | |
| #322 | body_template 検証 | ✅ 完了 | 制限あり |
| #323 | stringTemplateAgent ドキュメント | ⏸️ 保留 | |
| #324 | Worker ログ強化 | ⏸️ 保留 | |
| #331 | graphAiServer job_params 対応 | ✅ 完了 | |
| #333 | API 型・フィールド名検証 | ❌ バグあり | 本レポートの主題 |
| #335 | Gmail API スキーマ修正 | 🔴 未着手 | |
| #337 | Ready-to-Use Output 原則 | 🔴 未着手 | |

---

### 3.4 Issue #331: graphAiServer job_params 対応

**状態**: ✅ 正常に実装

**実装箇所**:
- `graphAiServer/src/app.ts:99, 129`
- `graphAiServer/src/services/graphai.ts:226-238`

**検証結果**:
```typescript
// app.ts
const { user_input, project, job_params } = req.body;
const result = await runGraphAI(user_input, model_name, project, job_params);

// graphai.ts
const mergedUserInput = typeof user_input === 'object'
    ? { ...(job_params || {}), ...(user_input as Record<string, unknown>) }
    : user_input;

const sourceData: SourceNodeData = {
    user_input: mergedUserInput,
    job_params: job_params || {},
};
graph.injectValue("source", sourceData);
```

**問題点**: なし

**改善点**:
- `user_input` と `job_params` のマージにより、後続タスクでも `:source.user_input.*` で静的パラメータにアクセス可能

---

### 3.5 Issue #333: API 型・フィールド名検証

**状態**: ❌ 重大なバグあり

**問題箇所**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py:46-63`

```python
TYPE_VALIDATION_RULES = """
## Important Type Validation Rules (Issue #333)
...
### stringTemplateAgent Type Conversion Pattern
When you need to convert Object type to String type:
```yaml
# Step 1: Convert Object to String using JSON.stringify
convert_to_string:
  agent: stringTemplateAgent
  inputs:
    data: :fetch_data  # Object type input
  params:
    template: "${JSON.stringify(data)}"  # ← ここが誤り！
```
"""
```

**問題の影響**:
1. LLM がこの指示に従って `${JSON.stringify(...)}` 構文を生成
2. GraphAI stringTemplateAgent は JavaScript 関数をサポートしていない
3. テンプレートが展開されずリテラル文字列として残る
4. 結果として LLM が意味のないデータを受け取る

**実装された検証機能自体は正常**:
- `workflow_schema_validator.py` の型チェック機能は正しく動作
- 問題は検証機能ではなく、生成指示にある

---

### 3.6 Issue #338: インターフェース契約強制

**状態**: ✅ 正常に実装

**実装箇所**:
- `jobqueue/app/core/worker.py:806-861` (`_extract_graphai_output`)
- `expertAgent/.../prompts/workflow_generation.py` (output ノード命名規約)

**検証結果**:
```python
def _extract_graphai_output(response_data: Any) -> Any:
    # GraphAI レスポンスから output ノードの result を抽出
    results = response_data.get("results", {})
    output_node = results.get("output")

    if output_node is None:
        logger.debug("No 'output' node found, returning full results")
        return results

    if isinstance(output_node, dict) and "result" in output_node:
        extracted = output_node["result"]
        return extracted

    return output_node
```

**問題点**: なし

---

## 4. 修正提案

### 4.1 緊急修正: TYPE_VALIDATION_RULES の修正

**ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py`

**修正前**:
```python
TYPE_VALIDATION_RULES = """
### stringTemplateAgent Type Conversion Pattern
When you need to convert Object type to String type:
```yaml
convert_to_string:
  agent: stringTemplateAgent
  inputs:
    data: :fetch_data
  params:
    template: "${JSON.stringify(data)}"
```
"""
```

**修正後**:
```python
TYPE_VALIDATION_RULES = """
### stringTemplateAgent 使用時の重要な制限

**stringTemplateAgent は JavaScript 関数をサポートしていません。**

❌ 使用禁止:
- `${JSON.stringify(data)}` - JavaScript 関数は動作しない
- `${data.field}` - ネストアクセスは動作しない

✅ 許可される構文:
- `${variable}` - シンプルな変数参照のみ

### Object 型データの取り扱い

Object 型データを LLM プロンプトに含める場合:

**方法1**: 個別フィールドを展開
```yaml
build_prompt:
  agent: stringTemplateAgent
  inputs:
    title: :search_result.title
    url: :search_result.url
    snippet: :search_result.snippet
  params:
    template: |-
      タイトル: ${title}
      URL: ${url}
      スニペット: ${snippet}
```

**方法2**: 配列データは mapAgent で処理
```yaml
process_results:
  agent: mapAgent
  inputs:
    rows: :search_results
  graph:
    nodes:
      format_item:
        agent: stringTemplateAgent
        inputs:
          item: :row
        params:
          template: "- ${item}"
        isResult: true
```

**方法3**: Object 全体を渡す（ただし [object Object] になる可能性あり）
テンプレート全体が `${data}` の場合のみ、型が保持される。
"""
```

### 4.2 中期対応: jsonStringifyAgent の追加検討

GraphAI に Object→String 変換用のカスタムエージェントを追加することを検討。

```typescript
// 提案: jsonStringifyAgent
const jsonStringifyAgent = async ({ namedInputs, params }) => {
    const data = namedInputs.data;
    const indent = params?.indent ?? 2;
    return JSON.stringify(data, null, indent);
};
```

### 4.3 長期対応: ワークフロー生成戦略の見直し

1. LLM API 呼び出しで複雑なデータ変換が必要な場合は、stringTemplateAgent ではなく fetchAgent + 専用 API を使用
2. タスクチェーンの設計で、各タスクの出力を次タスクが直接使用可能な形式にする（Issue #337）

---

## 5. 影響を受けるワークフロー

以下のワークフローが `${JSON.stringify(...)}` 問題の影響を受ける可能性がある:

| ワークフロー | 影響箇所 | 状態 |
|------------|---------|------|
| search_results_summary_generation.yml | build_summary_prompt | ❌ 影響あり |
| (今後生成される全ワークフロー) | stringTemplateAgent 使用箇所 | ⚠️ 潜在的影響 |

---

## 6. 推奨アクション

| 優先度 | アクション | 担当 | 期限 |
|--------|----------|------|------|
| 🔴 緊急 | TYPE_VALIDATION_RULES 修正 | 開発チーム | 即時 |
| 🔴 緊急 | 影響を受けるワークフローの再生成 | 開発チーム | 即時 |
| 🟡 中 | Issue #323 (stringTemplateAgent ドキュメント) 着手 | 開発チーム | 1週間以内 |
| 🟡 中 | jsonStringifyAgent の設計検討 | 開発チーム | 2週間以内 |
| 🟢 低 | Issue #337 (Ready-to-Use Output) 着手 | 開発チーム | 次スプリント |

---

## 7. 付録: stringTemplateAgent サンプルテスト結果

### テスト1: シンプルな変数展開

```yaml
inputs:
  message1: "hello"
  message2: "test"
params:
  template: "${message1}: ${message2}"
result: "hello: test"  # ✅ 正常動作
```

### テスト2: オブジェクト入力

```yaml
inputs:
  params: { text: "message" }
params:
  template: "${params}"  # テンプレート全体がプレースホルダー
result: { text: "message" }  # ✅ 型保持
```

### テスト3: オブジェクトの文字列埋め込み

```yaml
inputs:
  data: { key: "value" }
params:
  template: "Data: ${data}"
result: "Data: [object Object]"  # ❌ 問題あり
```

---

**レポート作成者**: Claude Code
**レビュー状態**: 未レビュー
