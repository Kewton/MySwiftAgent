# GraphAI 利用可能エージェント一覧

**最終更新**: 2025-10-16
**GraphAI バージョン**: 2.0.15
**@graphai/agents バージョン**: 2.0.14

このドキュメントは、MySwiftAgent環境で実際に利用可能なGraphAI Agentの完全リストです。

---

## 📋 利用可能Agent一覧

### **@graphai/agents パッケージ**

以下のAgentが `@graphai/agents` v2.0.14 から利用可能です：

#### 🤖 LLM Agents
| Agent名 | 用途 | API Key必要 |
|---------|------|-----------|
| `anthropicAgent` | Claude API直接呼び出し | ANTHROPIC_API_KEY |
| `geminiAgent` | Gemini API直接呼び出し | GOOGLE_API_KEY |
| `openAIAgent` | OpenAI GPT API直接呼び出し | OPENAI_API_KEY |
| `groqAgent` | Groq API直接呼び出し | GROQ_API_KEY |
| `replicateAgent` | Replicate API直接呼び出し | REPLICATE_API_KEY |

#### 📡 HTTP/Fetch Agents
| Agent名 | 用途 |
|---------|------|
| `fetchAgent` | 汎用HTTP APIクライアント（expertAgent呼び出しに使用） |
| `openAIFetchAgent` | OpenAI API専用fetchクライアント |
| `vanillaFetchAgent` | 軽量HTTPクライアント |

#### 🔄 データ変換 Agents
| Agent名 | 用途 |
|---------|------|
| `arrayJoinAgent` | 配列を文字列に結合 |
| `arrayFlatAgent` | 多次元配列をフラット化 |
| `arrayToObjectAgent` | 配列をオブジェクトに変換 |
| `arrayFindFirstExistsAgent` | 最初の存在する要素を取得 |
| `copy2ArrayAgent` | 値を配列にコピー |
| `copyAgent` | 値をコピー |
| `copyMessageAgent` | メッセージをコピー |
| `mergeObjectAgent` | オブジェクトをマージ |
| `mergeNodeIdAgent` | ノードIDをマージ |
| `propertyFilterAgent` | オブジェクトのプロパティをフィルタ |
| `popAgent` | 配列から末尾要素を取り出し |
| `pushAgent` | 配列に要素を追加 |
| `shiftAgent` | 配列から先頭要素を取り出し |

#### 📝 文字列処理 Agents
| Agent名 | 用途 |
|---------|------|
| `stringTemplateAgent` | テンプレート文字列生成 |
| `stringSplitterAgent` | 文字列を分割 |
| `stringCaseVariantsAgent` | 大文字/小文字変換 |
| `stringUpdateTextAgent` | 文字列の一部を更新 |
| `stringEmbeddingsAgent` | テキストの埋め込みベクトル生成 |
| `jsonParserAgent` | JSON文字列をパース |

#### 🧮 数値処理 Agents
| Agent名 | 用途 |
|---------|------|
| `totalAgent` | 数値の合計 |
| `countingAgent` | カウント処理 |
| `dotProductAgent` | ベクトルの内積計算 |
| `dataSumTemplateAgent` | データ集計テンプレート |
| `dataObjectMergeTemplateAgent` | データオブジェクトマージ |

#### 🔁 制御フロー Agents
| Agent名 | 用途 |
|---------|------|
| `mapAgent` | 配列の各要素に並列処理 |
| `nestedAgent` | ネストされたサブグラフ実行 |
| `compareAgent` | 値の比較 |
| `sortByValuesAgent` | 値でソート |

#### 🛠️ ユーティリティ Agents
| Agent名 | 用途 |
|---------|------|
| `echoAgent` | 入力をそのまま出力 |
| `consoleAgent` | コンソールログ出力 |
| `sleeperAgent` | 指定時間スリープ |
| `sleeperAgentDebug` | スリープ（デバッグ用） |
| `sleepAndMergeAgent` | スリープ後にマージ |
| `textInputAgent` | テキスト入力 |
| `lookupDictionaryAgent` | 辞書検索 |

#### 🌐 外部サービス Agents
| Agent名 | 用途 |
|---------|------|
| `wikipediaAgent` | Wikipedia検索 |
| `images2messageAgent` | 画像をメッセージに変換 |
| `openAIImageAgent` | OpenAI画像生成 |

#### 🐛 デバッグ/テスト Agents
| Agent名 | 用途 |
|---------|------|
| `streamMockAgent` | ストリーミングモック |

---

### **追加パッケージのAgents**

#### @graphai/token_bound_string_agent
| Agent名 | 用途 |
|---------|------|
| `tokenBoundStringsAgent` | トークン制限付き文字列処理 |

#### @graphai/vanilla_node_agents
| Agent名 | 用途 |
|---------|------|
| `fileReadAgent` | ファイル読み込み |
| `fileWriteAgent` | ファイル書き込み |
| `pathUtilsAgent` | パスユーティリティ |

---

## ❌ 存在しないAgent（使用禁止）

以下のAgentは **GraphAI v2.0系では削除または存在しません**：

| Agent名 | 削除理由/代替手段 |
|---------|----------------|
| `functionAgent` | v2.0で削除。カスタムロジックは`fetchAgent`でexpertAgent経由で実装 |
| `vanillaAgent` | 存在しない。`@graphai/vanilla`はユーティリティパッケージ |
| `jsonoutput` Agent | 存在しない。JSON出力は`fetchAgent` + expertAgent `/v1/llm/jsonoutput`を使用 |
| `explorerAgent` | GraphAI標準Agentではない。expertAgentのUtility API (`/v1/aiagent/utility/explorer`)を使用 |

---

## 📖 利用方法

### Agent一覧の確認方法（起動ログ）

GraphAiServerのログで利用可能Agentを確認できます：

```bash
docker compose logs graphaiserver | grep "Available agents:"
```

### ワークフロー内での使用例

```yaml
version: 0.5
nodes:
  source: {}

  # LLM Agentの使用例
  call_llm:
    agent: geminiAgent
    inputs:
      prompt: :source
    params:
      model: gemini-2.5-flash

  # fetchAgentでexpertAgent呼び出し
  call_expert:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/aiagent/utility/explorer
      method: POST
      body:
        user_input: :source
        model_name: gemini-2.5-flash

  # データ変換の例
  format_result:
    agent: stringTemplateAgent
    inputs:
      llm_output: :call_llm
    params:
      template: "結果: ${llm_output}"
    isResult: true
```

---

## 🔗 関連ドキュメント

- [GraphAI Workflow Generation Rules](./GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [expertAgent API Reference](./GRAPHAI_WORKFLOW_GENERATION_RULES.md#expertagent-api統合)
- [GraphAI公式ドキュメント](https://github.com/receptron/graphai)

---

**注意**: このリストは実際の`graphAiServer/src/services/graphai.ts`の実装に基づいています。新しいAgentパッケージを追加する場合は、同ファイルの`agents`オブジェクトを更新してください。
