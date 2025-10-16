# GraphAI ワークフロー開発テンプレート

**バージョン**: 1.0.0
**最終更新**: 2025-10-14
**対象**: Gemini CLI / Claude Code

このドキュメントは、GraphAI ワークフロー開発の標準テンプレートです。
新しいワークフローを開発する際は、このテンプレートに従ってください。

---

## 📋 ワークフロー開発依頼テンプレート

### 基本情報

```markdown
# ワークフロー開発依頼

## 基本情報
- **ワークフロー名**: [ワークフロー名（英数字、アンダースコア可）]
- **バージョン**: 1.0.0
- **作成日**: YYYY-MM-DD
- **目的**: [ワークフローの目的を1-2文で説明]

## 機能要件
- **入力**: [入力形式（JSON、文字列など）と具体例]
- **処理**: [実行する処理の概要]
- **出力**: [期待される出力形式と具体例]

## 完了基準
- [ ] [具体的な成功条件1]
- [ ] [具体的な成功条件2]
- [ ] [具体的な成功条件3]
```

### 技術的考慮事項チェックリスト

#### 並列処理を使用する場合
- [ ] **mapAgent使用時は `compositeResult: true` を必ず指定**
- [ ] 後続ノードでの参照: `:mapAgentノード名.isResultノード名`
- [ ] `concurrency` パラメータで並列数を制限（推奨: 2-3）

#### デバッグ準備
- [ ] 重要なノードに `console.after: true` を追加
- [ ] GraphAI APIレスポンスの `results` フィールドを記録する準備
- [ ] エラー発生時は ITERATION_RECORD_TEMPLATE.md に従って記録

#### エージェント選択
- [ ] **Explorer Agent**: html2markdown MCP使用（Webページからのテキスト抽出に最適）
- [ ] **Playwright Agent**: ブラウザ操作が必要な場合のみ使用
- [ ] **File Reader Agent**: PDF/画像/音声ファイル処理
- [ ] **Action Agent**: Gmail送信、カレンダー操作
- [ ] **mylllm Agent**: 汎用LLM処理
- [ ] **jsonoutput Agent**: 構造化JSON出力

#### モデル選択
- [ ] **gpt-oss:120b**: 複雑な推論、要約生成
- [ ] **gpt-oss:20b**: 通常の処理（デフォルト推奨）
- [ ] **gpt-4o-mini**: Agent統合時（Explorer/Playwright/File Reader/Action）
- [ ] **gemini-2.5-flash**: 大規模文書処理（100万トークン）

---

## 🎯 フェーズ別開発テンプレート

### フェーズ1: 要件分析と設計合意

#### 作成ファイル
`./workspace/geminicli/{workflow_name}/phase1-requirements.md`

#### テンプレート
```markdown
# フェーズ1: 要件分析と設計合意

## ユーザー要求の理解
[ユーザーからの依頼内容を記載]

## 処理フローの提案
1. [ステップ1の説明]
2. [ステップ2の説明]
3. [ステップ3の説明]
...

## 使用するエージェント
| ステップ | エージェント | モデル | 理由 |
|---------|-------------|-------|------|
| [ステップ1] | [エージェント名] | [モデル名] | [選定理由] |
| [ステップ2] | [エージェント名] | [モデル名] | [選定理由] |

## ファイル名の決定
- YMLファイル名: `{workflow_name}_YYYYMMDD.yml`
- 配置先: `./graphAiServer/config/graphai/llmwork/`

## ユーザー承認
- [ ] 処理フロー承認
- [ ] エージェント選定承認
- [ ] ファイル名承認
```

---

### フェーズ2: 実現可能性評価

#### 作成ファイル
`./workspace/geminicli/{workflow_name}/phase2-design.md`

#### テンプレート
```markdown
# フェーズ2: 実現可能性評価

## expertAgentの既存機能確認
- [ ] 必要なエージェントが利用可能
- [ ] 必要なMCPツールが利用可能
- [ ] 必要なモデルが利用可能

## 不足機能の確認
[不足している機能があれば記載]

## 技術的リスク
| リスク | 対策 | 優先度 |
|-------|------|-------|
| [リスク1] | [対策] | 高/中/低 |

## 設計の最終化
### データフロー
\`\`\`
source → [ノード1] → [ノード2] → ... → output
\`\`\`

### ノード構成
| ノード名 | エージェント | 入力 | 出力 | 備考 |
|---------|-------------|------|------|------|
| [ノード1] | [エージェント] | [入力] | [出力] | [備考] |

## ユーザー承認
- [ ] 設計承認
- [ ] リスク対策承認
```

---

### フェーズ3: テスト検証

#### 作成ファイル
`./workspace/geminicli/{workflow_name}/phase3-test-verification.md`

#### テンプレート
```markdown
# フェーズ3: テスト検証

## テストケース設計

### 正常系テスト
1. **テストケース1**
   - 入力: [具体的な入力]
   - 期待される出力: [具体的な出力]
   - 検証項目:
     - [ ] [検証項目1]
     - [ ] [検証項目2]

### 異常系テスト
1. **エラーケース1**
   - 入力: [エラーを発生させる入力]
   - 期待される動作: [エラーハンドリング]

## 検証方法
### APIレスポンス確認ポイント
- [ ] 全ノードが正常終了（`errors` が空）
- [ ] mapAgentノードの出力形式が正しい
- [ ] `[object Object]` エラーが発生していない
- [ ] LLMの出力が元データに基づいている（Silent Failure防止）

### console.after によるログ確認
- [ ] mapAgentノードのログ出力
- [ ] 重要なノードの中間データ
```

---

### フェーズ4: 動作確認と改善

#### 作成ファイル
`./workspace/geminicli/{workflow_name}/phase4-production-test.md`

#### テンプレート
各イテレーションは ITERATION_RECORD_TEMPLATE.md に従って記録してください。

```markdown
# フェーズ4: 動作確認と改善

## イテレーション1
[ITERATION_RECORD_TEMPLATE.md を参照]

## イテレーション2
[ITERATION_RECORD_TEMPLATE.md を参照]

## サマリー
- 総イテレーション回数: [N]回
- 主な問題: [発生した主な問題]
- 解決策: [採用した解決策]
```

---

### フェーズ5: 最終化

#### 作成ファイル
`./workspace/geminicli/{workflow_name}/phase5-finalization.md`

#### テンプレート
```markdown
# フェーズ5: 最終化

## 最終動作確認
- 実行日時: YYYY-MM-DD HH:MM
- 結果: SUCCESS / FAILED
- 処理時間: [実測値]秒

## 完了報告
- YMLファイル: `./graphAiServer/config/graphai/llmwork/{filename}.yml`
- 使用方法:
  \`\`\`bash
  curl -X POST http://127.0.0.1:8105/api/v1/myagent/llmwork/{filename} \\
    -H "Content-Type: application/json" \\
    -d '{"user_input": "..."}'
  \`\`\`

- 注意事項:
  - [運用上の注意事項]
  - [既知の制限事項]

## 結論
[ワークフローが要件を満たしているかの最終判断]
```

---

### summary.md（全フェーズ完了後）

#### 作成ファイル
`./workspace/geminicli/{workflow_name}/summary.md`

#### テンプレート
```markdown
# [ワークフロー名] 開発サマリー

## プロジェクト概要
- 開発期間: YYYY-MM-DD
- イテレーション回数: [N]回
- 最終ステータス: SUCCESS / FAILED

## 主要な設計判断
1. [設計判断1とその理由]
2. [設計判断2とその理由]
3. [設計判断3とその理由]

## 発生したエラーと対応
- **問題**: [発生した問題]
- **対応**: [採用した解決策]

## 最終成果物
- YMLファイル: [ファイルパス]
- ノード数: [N]個
- 処理時間: [実測値]秒

## 技術的ハイライト
### 成功した実装パターン
\`\`\`yaml
[重要な実装パターンのコード例]
\`\`\`

### 使用したエージェント
| エージェント | 用途 | モデル |
|-------------|------|--------|
| [エージェント1] | [用途] | [モデル] |

## 学んだ教訓
1. [教訓1]
2. [教訓2]
3. [教訓3]

## 今後の改善案
- [改善案1]
- [改善案2]
```

---

## ⚠️ 重要な注意事項

### mapAgent使用時の必須パターン

**必ず以下のパターンに従ってください**:

```yaml
process_items:
  agent: mapAgent
  console:
    after: true  # ← デバッグ用（必須）
  params:
    compositeResult: true  # ← 必須
    concurrency: 2  # ← 推奨
  inputs:
    rows: :previous_node.result
  graph:
    nodes:
      # サブグラフの処理...

      final_format:
        agent: stringTemplateAgent
        params:
          template: "Result: ${input}"
        isResult: true  # ← この名前が出力オブジェクトのキーになる

# 後続ノード
join_results:
  agent: arrayJoinAgent
  inputs:
    array: :process_items.final_format  # ← プロパティアクセス
```

### デバッグ時の必須確認事項

#### 1. GraphAI APIレスポンスの確認
```bash
curl -X POST http://localhost:8105/api/v1/myagent/test/workflow \
  -H "Content-Type: application/json" \
  -d '{"user_input": "..."}' \
  | jq '.' > response.json
```

**確認ポイント**:
- `results` フィールド全体
- mapAgentノードの出力形式: `{ "isResultノード名": [...] }`
- `[object Object]` が含まれていないか

#### 2. console.after によるログ確認
```yaml
重要なノード:
  console:
    after: true  # ← 必ず追加
```

#### 3. Silent Failure の検出
- 最終出力が元データに基づいているか
- LLMが破損データを補完していないか
- エラーがない = 正しい動作、ではない

---

## 📚 参考ドキュメント

### 必須参照
1. **GRAPHAI_WORKFLOW_GENERATION_RULES.md**
   - パス: `./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md`
   - 内容: GraphAI の完全リファレンス

2. **ITERATION_RECORD_TEMPLATE.md**
   - パス: `./graphAiServer/docs/ITERATION_RECORD_TEMPLATE.md`
   - 内容: イテレーション記録の標準フォーマット

### よくある質問
- **Q**: mapAgentで `[object Object]` エラーが出る
- **A**: `compositeResult: true` を追加し、`:mapAgentノード名.isResultノード名` で参照

- **Q**: arrayJoinAgentで `UNDEFINED` エラーが出る
- **A**: `compositeResult: true` が指定されているか確認

- **Q**: メールは届いたが内容が正しくない
- **A**: Silent Failure の可能性。APIレスポンスの `results` フィールドで中間データを確認

---

**最終更新**: 2025-10-14
**バージョン**: 1.0.0
