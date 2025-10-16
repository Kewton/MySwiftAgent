# イテレーション記録テンプレート

**バージョン**: 1.0.0
**最終更新**: 2025-10-14
**対象**: Gemini CLI / Claude Code

このドキュメントは、GraphAI ワークフロー開発における各イテレーションの記録フォーマットです。
デバッグ効率を最大化し、エラーの再発を防止するために使用します。

---

## 📋 イテレーション記録フォーマット

### イテレーション N

#### 実行情報
- **実行日時**: YYYY-MM-DD HH:MM:SS
- **YMLバージョン**: vX.Y.Z
- **実行コマンド**:
  ```bash
  curl -X POST http://127.0.0.1:8105/api/v1/myagent/llmwork/{filename} \
    -H "Content-Type: application/json" \
    -d '{"user_input": "..."}'
  ```

#### テスト入力
```json
{
  "user_input": "[具体的な入力内容]"
}
```

---

#### 📊 GraphAI APIレスポンス分析

##### ✅ 成功したノード
| ノード名 | 実際の出力 | 期待値との比較 |
|---------|-----------|--------------|
| `node1` | `[出力内容]` | ✅ 期待通り |
| `node2` | `[出力内容]` | ✅ 期待通り |

##### ❌ 失敗したノード
| ノード名 | 期待値 | 実際の出力 | 差分 |
|---------|-------|-----------|------|
| `problem_node` | `["string1", "string2"]` | `[object Object]` | 型不一致 |

##### 🔍 中間ノードの詳細分析

**ノード名**: `mapAgent_node`

**APIレスポンスの `results` フィールド**:
```json
{
  "mapAgent_node": [
    {
      "node1": "...",
      "node2": "..."
    }
  ]
}
```

**期待していた出力形式**:
```json
{
  "mapAgent_node": {
    "isResultNodeName": ["...", "..."]
  }
}
```

**差分の原因**:
- `compositeResult: true` が指定されていない
- サブグラフに `isResult: true` が複数ある

---

#### 🐛 エラー診断

##### エラーの種類
- [ ] `[object Object]` エラー
- [ ] `UNDEFINED` エラー
- [ ] Silent Failure（データ捏造）
- [ ] HTTP 500 エラー
- [ ] その他: [具体的なエラー]

##### 根本原因
[エラーが発生した理由を記載]

例:
- mapAgentに `compositeResult: true` が未指定
- 後続ノードで `:mapAgentノード名.isResultノード名` 参照が必要なのに `:mapAgentノード名` で参照
- LLMに破損データ（`[object Object]`）が渡され、Hallucination が発生

##### 影響範囲
| ノード名 | 影響度 | 説明 |
|---------|-------|------|
| `node1` | 🔴 Critical | 完全に失敗 |
| `node2` | 🟡 Medium | データ破損 |
| `node3` | 🟢 Low | 後続処理で吸収可能 |

---

#### 🔧 適用した修正

##### 修正内容
**修正箇所**: [ファイル名:行番号]

**Before**:
```yaml
process_items:
  agent: mapAgent
  inputs:
    rows: :previous_node
  graph:
    nodes:
      format_result:
        agent: stringTemplateAgent
        isResult: true
```

**After**:
```yaml
process_items:
  agent: mapAgent
  console:
    after: true  # ← デバッグ用に追加
  params:
    compositeResult: true  # ← 追加
  inputs:
    rows: :previous_node
  graph:
    nodes:
      format_result:
        agent: stringTemplateAgent
        isResult: true

# 後続ノードも修正
next_node:
  agent: arrayJoinAgent
  inputs:
    array: :process_items.format_result  # ← プロパティアクセスに変更
```

##### 修正の理由
[なぜこの修正が必要だったのか]

例:
- mapAgentのデフォルト動作では、サブグラフの全ノード出力をオブジェクト配列として返す
- `compositeResult: true` により、`isResult: true` のノードのみを抽出して `{ "ノード名": [...] }` 形式で返す
- これにより後続ノードで配列を正しく参照できる

---

#### ✅ 検証結果

##### 修正後の動作確認

**APIレスポンス**:
```json
{
  "results": {
    "process_items": {
      "format_result": ["string1", "string2", "string3"]
    },
    "next_node": "string1\nstring2\nstring3"
  },
  "errors": {}
}
```

**検証項目**:
- [x] mapAgentの出力形式が `{ "isResultノード名": [...] }` になっている
- [x] 後続ノードで配列を正しく参照できている
- [x] `[object Object]` エラーが解消されている
- [x] 最終出力が期待通りの内容になっている
- [x] エラーフィールドが空である

##### 残存する問題
- [問題があれば記載、なければ「なし」]

---

#### 📝 学んだ教訓

##### 技術的な学び
1. [学び1]
2. [学び2]

例:
1. mapAgentで配列を返したい場合は必ず `compositeResult: true` を指定する
2. サブグラフ内の複数ノードに `isResult: true` があると、最初の1つのみが出力される
3. APIレスポンスの `results` フィールドを見ることで、中間ノードの出力を正確に把握できる

##### デバッグ手法
1. [手法1]
2. [手法2]

例:
1. まず APIレスポンスの `results` フィールド全体を確認
2. 問題のノードに `console.after: true` を追加してログ出力
3. 期待値と実際の値を JSON形式で比較

##### 予防策
1. [予防策1]
2. [予防策2]

例:
1. mapAgent使用時は必ず `compositeResult: true` をチェックリストに追加
2. 重要なノードには最初から `console.after: true` を設定
3. YMLファイルにコメントで出力形式を明記

---

#### ⏱️ 所要時間
- **修正時間**: [N]分
- **検証時間**: [N]分
- **合計**: [N]分

---

## 🎯 デバッグチェックリスト

### 初期確認（必須）
- [ ] GraphAI APIレスポンスの `results` フィールドを保存した
- [ ] `errors` フィールドが空か確認した
- [ ] 問題のノードを特定した

### mapAgent使用時
- [ ] `compositeResult: true` が指定されているか
- [ ] サブグラフに `isResult: true` が1つだけあるか
- [ ] 後続ノードで `:mapAgentノード名.isResultノード名` 形式で参照しているか
- [ ] `console.after: true` でログ出力を有効化したか

### arrayJoinAgent使用時
- [ ] 入力が文字列配列になっているか（`["str1", "str2"]`）
- [ ] オブジェクト配列（`[{...}, {...}]`）を渡していないか
- [ ] `[object Object]` エラーが出ていないか

### LLMエージェント使用時
- [ ] 入力データが破損していないか（Silent Failure防止）
- [ ] プロンプトで期待する出力形式を明示しているか
- [ ] 出力が元データに基づいているか検証したか

### 最終確認
- [ ] 全ノードが正常終了したか（`errors` が空）
- [ ] 最終出力が期待通りの形式か
- [ ] 最終出力が元データに基づいているか
- [ ] 処理時間が許容範囲内か

---

## 📊 イテレーションサマリー（複数回実行時）

### 統計情報
| イテレーション | ステータス | 主なエラー | 修正内容 | 所要時間 |
|--------------|-----------|-----------|---------|---------|
| 1 | ❌ FAILED | `[object Object]` | JSON parsing試行 | 15分 |
| 2 | ❌ FAILED | `UNDEFINED` | Property抽出試行 | 20分 |
| 3 | ✅ SUCCESS | なし | `compositeResult: true` 追加 | 10分 |

### 累積学習
1. [イテレーション全体を通じて得られた知見]
2. [効果的だったデバッグ手法]
3. [次回のワークフロー開発に活かせる教訓]

---

## 🔗 関連ドキュメント

- **開発テンプレート**: `./graphAiServer/docs/WORKFLOW_DEVELOPMENT_TEMPLATE.md`
- **GraphAIルール**: `./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md`
- **YMLファイル**: `./graphAiServer/config/graphai/llmwork/{workflow_name}.yml`

---

## ⚙️ APIレスポンス記録方法

### レスポンス保存コマンド
```bash
curl -X POST http://127.0.0.1:8105/api/v1/myagent/llmwork/{filename} \
  -H "Content-Type: application/json" \
  -d '{"user_input": "..."}' \
  | jq '.' > ./workspace/geminicli/{workflow_name}/iteration-{N}-response.json
```

### 重要フィールドの抽出
```bash
# resultsフィールドのみ抽出
jq '.results' iteration-{N}-response.json

# 特定ノードの出力のみ抽出
jq '.results.node_name' iteration-{N}-response.json

# errorsフィールドのみ抽出
jq '.errors' iteration-{N}-response.json
```

### 差分比較
```bash
# 期待値ファイルとの比較
diff <(jq -S '.results.node_name' expected.json) \
     <(jq -S '.results.node_name' iteration-{N}-response.json)
```

---

**最終更新**: 2025-10-14
**バージョン**: 1.0.0
