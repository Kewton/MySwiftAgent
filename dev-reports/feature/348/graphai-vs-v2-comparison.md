# GraphAI YAML vs V2 TaskFlow JSON 比較評価

## 概要

LLMによる自動生成の観点から、GraphAI YAMLフォーマットとV2 TaskFlow JSONフォーマットを比較評価する。

## フォーマット比較

### 1. 基本構造

| 項目 | GraphAI YAML | V2 TaskFlow JSON |
|------|-------------|------------------|
| フォーマット | YAML | JSON |
| ノード定義 | `nodes:` 以下にフラット | `steps:` 配列で順序明示 |
| 実行順序 | 依存関係から暗黙的に推論 | 配列順序で明示的 |
| 入出力スキーマ | なし | `input_schema`, `output_schema` で明示 |
| 変数参照 | `:node_name.field` | `${node_id.output.field}` |

### 2. サンプル比較（Hello World）

**GraphAI YAML:**
```yaml
version: 0.5
nodes:
  source: {}
  expert_hello:
    agent: fetchAgent
    inputs:
      url: http://localhost:8104/aiagent-api/v1
      method: GET
  output:
    agent: copyAgent
    inputs:
      text: :expert_hello
    isResult: true
```

**V2 TaskFlow JSON:**
```json
{
  "workflow_name": "tutorial_1_hello",
  "input_schema": {},
  "output_schema": { "message": "string" },
  "steps": [
    {
      "id": "fetch_hello",
      "type": "api_rest",
      "config": { "method": "GET", "url": "https://..." }
    },
    {
      "id": "format_output",
      "type": "transform",
      "config": { "mode": "template", "template": "Hello! {{title}}" },
      "params": { "title": "${fetch_hello.output.title}" }
    }
  ],
  "output": { "message": "${format_output.output.result}" }
}
```

## LLM自動生成の観点での評価

### GraphAI YAML の特徴

#### 利点
1. **簡潔な記法**: YAMLは人間が読みやすく、記述量が少ない
2. **暗黙的な依存解決**: `:node.field` で参照するだけで依存関係が自動推論される
3. **柔軟なAgent**: `copyAgent`, `stringTemplateAgent`, `mapAgent` など多様なエージェントが利用可能
4. **ネストされたグラフ**: `mapAgent` 内に `graph.nodes` でサブグラフを定義可能

#### 課題
1. **暗黙ルールが多い**: `source: {}`の意味、`:` プレフィックスの意味など
2. **Agent名の知識が必要**: `fetchAgent`, `copyAgent`, `stringTemplateAgent` など
3. **YAMLインデント**: LLMはYAMLのインデントミスを起こしやすい
4. **型情報なし**: 入出力の型が不明確
5. **isResult: true**: 最終出力の指定が分かりにくい

### V2 TaskFlow JSON の特徴

#### 利点
1. **明示的なスキーマ**: `input_schema`, `output_schema` で型が明確
2. **順序が明示的**: `steps` 配列で実行順序が明確
3. **型定義済み**: `type: "api_rest"`, `type: "transform"` など明確な型
4. **JSONフォーマット**: LLMはJSONの構文エラーを起こしにくい
5. **変数構文が明確**: `${node_id.output.field}` は自己説明的
6. **バリデーション容易**: JSONスキーマでバリデーション可能

#### 課題
1. **記述量が多い**: 同じ処理でもGraphAIより冗長
2. **並列処理の表現**: `type: "parallel"` ブロックが必要
3. **動的map処理なし**: GraphAIの `mapAgent` 相当機能がない
4. **テンプレート分離**: `config.template` と `params` が分離している

## 定量比較

| メトリクス | GraphAI YAML | V2 TaskFlow JSON |
|-----------|-------------|------------------|
| Hello World 行数 | 15行 | 38行 |
| 複雑ワークフロー (podcast) | ~480行 | 実装不可（mapAgent相当なし） |
| 必要な事前知識 | Agent名、暗黙ルール | stepタイプのみ |
| 構文エラー発生率 | 高（YAML indent） | 低（JSON構造） |
| スキーマバリデーション | 困難 | 容易 |

## LLM自動生成しやすさの評価

### 総合評価: **V2 TaskFlow JSON が優位**

#### 理由

1. **構文の堅牢性** (V2優位)
   - JSONはインデントに依存しないため、LLMの構文エラーが少ない
   - GraphAI YAMLはインデントミスで動作しなくなるリスクが高い

2. **明示性** (V2優位)
   - V2は全てが明示的（型、順序、入出力）
   - GraphAIは暗黙知が多く、LLMが誤解しやすい

3. **バリデーション** (V2優位)
   - V2はJSONスキーマで事前バリデーション可能
   - 生成後にエラーを検出・修正しやすい

4. **プロンプト設計** (V2優位)
   - V2はstepタイプを列挙するだけでルールが伝わる
   - GraphAIはAgent毎の仕様をプロンプトに含める必要あり

5. **記述量** (GraphAI優位)
   - 単純なワークフローはGraphAIの方が短い
   - ただしLLMにとって記述量は大きな障壁ではない

6. **複雑なワークフロー** (GraphAI優位)
   - `mapAgent` による動的並列処理はGraphAIのみ
   - ただしV2でも静的並列は `type: "parallel"` で可能

### 推奨アプローチ

| ユースケース | 推奨フォーマット |
|-------------|-----------------|
| LLM自動生成（単純〜中程度） | **V2 TaskFlow JSON** |
| LLM自動生成（複雑・動的並列） | GraphAI YAML（要追加学習） |
| 人間による手動記述 | GraphAI YAML |
| CI/CDパイプライン統合 | V2 TaskFlow JSON |

## 結論

**V2 TaskFlow JSONはLLMによる自動生成に適している。**

- 明示的なスキーマと構造により、LLMが正しいフォーマットを生成しやすい
- JSONの構文堅牢性により、生成エラーが少ない
- ただし、動的並列処理（mapAgent相当）が必要な場合はGraphAI YAMLが必要

### 改善提案

V2 TaskFlow JSONをさらにLLM生成向けに改善するには：

1. **mapステップの追加**: `type: "map"` で配列要素への並列処理をサポート
2. **条件分岐の追加**: `type: "conditional"` でif/else分岐をサポート
3. **Few-shotサンプル**: 代表的なパターンのサンプルを用意
