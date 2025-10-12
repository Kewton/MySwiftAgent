# GEMINI.md

このファイルは、Gemini CLI (Google AI Studio) を使用してGraphAI YMLワークフローファイルを自動生成する際の指針を提供します。

## 📋 概要

Gemini CLIを使用することで、自然言語の指示からGraphAI YMLワークフローファイルを自動生成できます。このドキュメントでは、Gemini CLIの設定方法と、効果的なワークフロー生成のためのガイドラインを提供します。

## 🎯 目的

- **自然言語からのワークフロー生成**: ユーザーの要求を自然言語で受け取り、GraphAI YMLファイルを自動生成
- **品質担保**: 生成されたワークフローが設計ルールに準拠し、動作確認済みであることを保証
- **効率化**: 手動でのYMLファイル作成にかかる時間を大幅に削減

## 📖 ワークフロー生成ルール

**重要**: ワークフロー生成の詳細なルールと設計指針は以下のドキュメントを参照してください:

📄 **[GraphAI Workflow Generation Rules](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)**

このドキュメントには以下の情報が含まれています:

- ✅ 基本構造と必須要素
- ✅ エージェント種別と使用方法
- ✅ データフローパターン
- ✅ expertAgent API統合
- ✅ エラー回避パターン
- ✅ パフォーマンス最適化
- ✅ 命名規則とデバッグ方法
- ✅ 実装例（シンプルから複雑まで）
- ✅ YMLヘッダーコメント規約
- ✅ LLMワークフロー作成手順（フェーズ1〜5）
- ✅ 動作確認方法

## 💬 Gemini CLI への指示方法

### システムプロンプト

Gemini CLIを使用してワークフロー生成を行う際は、以下のシステムプロンプトを設定してください:

```
あなたはGraphAI YMLワークフローファイルを生成する専門エージェントです。

# 必須参照ドキュメント
以下のドキュメントに記載されたルールと設計指針に厳密に従ってください:
- ./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md

# 作業手順
1. フェーズ1: 要件分析と設計合意
2. フェーズ2: 実現可能性評価
3. フェーズ3: ワークフロー初期実装
4. フェーズ4: 動作確認と改善サイクル（最大5イテレーション）
5. フェーズ5: 最終化

# 出力形式
- YMLファイルの完全な内容を出力
- ヘッダーコメントを必ず含める（Created, User Request, Test Results, Description, Notes）
- ファイル保存先: ./graphAiServer/config/graphai/llmwork/{purpose}_{timestamp}.yml

# 品質基準
- version: 0.5 を使用
- sourceノードは直接参照（:source）
- mapAgent使用時はconcurrencyを設定
- 重要ノードにconsole.after: trueを設定
- expertAgent APIのポート番号は8104
- ローカルLLM（gpt-oss:20b, gpt-oss:120b）を優先使用
```

### ユーザー指示の例

#### 例1: シンプルなLLM呼び出し

```
ユーザー入力を受け取り、gpt-oss:20bモデルで応答を生成するシンプルなワークフローを作成してください。
```

#### 例2: Google検索からレポート生成

```
以下の要件でワークフローを作成してください:
1. ユーザーがトピックを入力
2. Google検索でトピックに関する情報を収集（3件）
3. explorerエージェントで情報を整理
4. gpt-oss:120bで詳細なレポートを生成
5. 結果を出力
```

#### 例3: ポッドキャスト台本生成（複雑な並列処理）

```
以下の要件でポッドキャスト台本生成ワークフローを作成してください:

【要件】
- 対象: 39歳、男性
- トーン: 深掘り討論

【処理フロー】
1. ユーザーがキーワード入力
2. 事前調査（Google検索 → 情報収集）
3. アウトライン生成（4-6章構成）
4. 各章を並列で詳細調査・執筆（mapAgent使用）
5. 結果統合
6. 最終台本生成
7. 音声合成してGoogle Driveにアップロード

【注意事項】
- mapAgentはconcurrency: 2を設定
- expertAgentは4ワーカーで起動
- タイムアウトは300秒に設定済み
```

## 🔧 生成されたワークフローの動作確認

### 1. ファイル保存

生成されたYMLファイルを以下のディレクトリに保存:

```bash
./graphAiServer/config/graphai/llmwork/{purpose}_{timestamp}.yml
```

### 2. graphAiServer起動確認

```bash
# graphAiServerが起動していることを確認
curl http://127.0.0.1:8105/health

# expertAgentが起動していることを確認（4ワーカー推奨）
curl http://127.0.0.1:8104/health
```

### 3. ワークフロー実行

```bash
# 開発用エンドポイントで実行（想定）
curl -X POST http://127.0.0.1:8105/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_file": "llmwork/{your_workflow}.yml",
    "input": "ユーザー入力テキスト"
  }'
```

### 4. エラー発生時の対応

エラーが発生した場合は、以下のログを確認:

```bash
# graphAiServerログ
tail -n 100 logs/graphaiserver.log | grep -i error

# expertAgentログ
tail -n 100 logs/expertagent.log | grep -i error
```

**よくあるエラーと対応**:

| エラー | 原因 | 対応 |
|-------|------|------|
| `TypeError: fetch failed` | expertAgentへの接続失敗 | ポート番号確認（8104）、ワーカー数確認 |
| `undefined` が出力 | sourceノード参照エラー | `:source.text` → `:source` に修正 |
| `mapAgentでタイムアウト` | 並列処理過負荷 | `concurrency: 2` を追加 |

## 📝 ヘッダーコメント規約

生成されたYMLファイルには、必ず以下の形式のヘッダーコメントを含めてください:

```yaml
# =============================================================================
# GraphAI Workflow File
# =============================================================================
# Created: 2025-10-12 14:30:00
# User Request:
#   [ユーザーからの要求を簡潔に記述]
#
# Test Results:
#   - [2025-10-12 14:45] Status: SUCCESS - [動作確認の詳細]
#
# Description:
#   [ワークフローの目的と概要を簡潔に記述]
#
# Notes:
#   - [実装時の注意点や制約事項]
# =============================================================================

version: 0.5
nodes:
  # ワークフロー定義
```

詳細は [GRAPHAI_WORKFLOW_GENERATION_RULES.md - YMLファイルのヘッダーコメント規約](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#ymlファイルのヘッダーコメント規約) を参照してください。

## 🔄 イテレーション改善フロー

ワークフロー生成は最大5回のイテレーションで改善します:

```
イテレーション N (N = 1, 2, 3, 4, 5)
├─ ステップ1: graphAiServerで実行
├─ ステップ2: 結果判定
│   ├─ SUCCESS → 完了
│   └─ FAILED → ステップ3へ
├─ ステップ3: エラー原因調査
├─ ステップ4: ルール更新・YML修正
└─ ステップ5: Test Resultsヘッダー更新
```

5回のイテレーションで解決できない場合は、ユーザーにフィードバックを依頼します。

## ✅ チェックリスト

ワークフロー生成時に以下を確認してください:

### 基本構造
- [ ] `version: 0.5` を含む
- [ ] `nodes:` セクションがある
- [ ] `source: {}` ノードがある
- [ ] 最低1つの `isResult: true` ノードがある

### データフロー
- [ ] すべてのノード間のデータ参照が正しい（`:node_name.field`）
- [ ] `source` ノードは直接参照（`:source`）している
- [ ] `mapAgent` 内では `:row.field` でアクセスしている

### expertAgent API統合
- [ ] すべてのAPI URLが `http://127.0.0.1:8104` を使用
- [ ] 使用するエンドポイントが存在する
- [ ] `model_name` パラメータが有効なモデル名

### モデル選択
- [ ] ローカルLLMを優先使用（gpt-oss:20b, gpt-oss:120b）
- [ ] タスクの複雑度に応じたモデルを選択

### エラー処理
- [ ] タイムアウトが適切に設定されている
- [ ] 重要なノードで `console.after: true` を設定
- [ ] 並列処理に `concurrency` パラメータを設定

### 命名規則
- [ ] ノード名が意味のある名前
- [ ] 小文字スネークケースを使用
- [ ] 適切な接尾辞（`_builder`, `_mapper` など）を使用

## 📚 参考リンク

- 📄 **[GraphAI Workflow Generation Rules](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** - 必須参照ドキュメント
- 🌐 **[Google AI Studio](https://aistudio.google.com/)** - Gemini API管理
- 🔧 **[GraphAI公式ドキュメント](https://github.com/receptron/graphai)** - GraphAIフレームワーク仕様
- 📖 **[expertAgent API仕様](./expertAgent/docs/)** - expertAgent統合ガイド

## 🤝 サポート

ワークフロー生成で問題が発生した場合:

1. **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** の該当セクションを確認
2. エラーログを確認（graphAiServer、expertAgent）
3. イテレーション改善フローに従って修正
4. 5回のイテレーションで解決しない場合は、チームに相談

---

**最終更新日**: 2025-10-12

**バージョン**: 1.0.0
