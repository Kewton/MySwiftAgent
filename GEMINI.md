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

Gemini CLIを使用してワークフロー生成を行う際は、**[GraphAI Workflow Generation Rules](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** を必ず参照してください。

詳細なシステムプロンプト、ユーザー指示の例、5フェーズの作業手順については、上記ドキュメントに記載されています。

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
curl -X POST http://127.0.0.1:8105/api/v1/myagent/llmwork/{your_workflow_name_without_extension} \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "ユーザー入力テキスト"
  }' ```

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

## 開発の進め方（5フェーズワークフロー）

GraphAI YMLワークフローの開発は、以下の5フェーズで進めます。各フェーズの詳細は **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** を参照してください。

### フェーズ1: 要件分析と設計合意 ✅

**目的**: ユーザーの要求を正確に理解し、実現可能性を評価

**実施内容**:
1. ユーザーからの要求を理解する
2. 必要な機能を整理（検索、Agent、LLM処理等）
3. 概算工数・技術的制約を確認
4. 作業計画を立案し、ユーザーに合意を得る

**成果物**: 要求定義書、作業計画

---

### フェーズ2: ワークフロー設計 📐

**目的**: データフローと処理構造を明確化

**実施内容**:
1. ワークフロー全体の流れを設計
   ```sh
   graphai -m <ワークフローファイル名>  # Mermaid図で視覚化
   ```
2. ノード間のインターフェース（入出力データ）を設計
3. 使用するAgentとモデルを選択（**[Agent選択指針](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#agent選択指針)** 参照）
4. エラー処理・並列処理の方針を決定

**チェックポイント**:
- [ ] すべてのノードの入出力が明確
- [ ] データ参照パス（`:node_name.field`）が正しい
- [ ] 並列処理に `concurrency` を設定済み

**成果物**: ワークフローYMLファイル（初版）、設計ドキュメント

---

### フェーズ3: テストモード検証 🧪

**目的**: LLM呼び出しなしで構造を検証（高速・低コスト）

**実施内容**:
1. 複数パターンのテストデータを用意（最低3パターン）
2. testモードで実行し、ノード間のデータ受け渡しを確認
   ```bash
   # expertAgent APIのtest_mode機能を使用
   curl -X POST http://127.0.0.1:8104/aiagent-api/v1/mylllm \
     -H "Content-Type: application/json" \
     -d '{"test_mode": true, "test_response": {...}}'
   ```
3. エラーが発生した場合は設計を見直し（**[よくあるエラーと対応](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#よくあるエラーと対応)** 参照）

**合格基準**:
- [ ] すべてのテストパターンで構造エラーが発生しない
- [ ] データフローが期待通り動作
- [ ] `undefined` や参照エラーが発生しない

**成果物**: テスト済みワークフローYML、テストデータ

---

### フェーズ4: 段階的本番実行 🚀

**目的**: ブロック毎に実際のLLM呼び出しで動作確認

**実施内容**:
1. ワークフローを2〜4つのブロックに分割
   - 例: ①入力処理 → ②検索・情報収集 → ③LLM生成 → ④出力整形
2. ブロック毎に本番モードで実行・検証
3. 各ブロックの出力品質を確認
4. エラー発生時は **[トラブルシューティング](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#動作確認とトラブルシューティング)** を参照

**検証ポイント**:
- [ ] 各ブロックの出力が期待通り
- [ ] LLMの応答品質が要求を満たす
- [ ] タイムアウト・エラーが発生しない
- [ ] `console.after: true` で重要ノードの出力をログ確認

**イテレーション改善**:
- 最大5回のイテレーションで品質を改善
- ルール更新が必要な場合は **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** を更新

**成果物**: 本番検証済みワークフローYML、実行ログ

---

### フェーズ5: 最終化とドキュメント整備 📝

**目的**: 本番運用可能な状態に整備

**実施内容**:
1. YMLヘッダーコメントを完成させる
   - Created, User Request, Test Results, Description, Notes
2. 最終動作確認（全体テスト）
3. パフォーマンス最適化
   - モデル選択の見直し（**[モデル選択指針](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#モデル選択指針)** 参照）
   - 不要なノードの削減
4. ドキュメント更新

**最終チェックリスト**: 下記「✅ チェックリスト」セクションを参照

**成果物**: 本番リリース用ワークフローYML、完全ドキュメント

---

### 📊 フェーズ進行の目安

| フェーズ | 所要時間 | 主要アウトプット |
|---------|---------|----------------|
| フェーズ1 | 10〜30分 | 要求定義、作業計画 |
| フェーズ2 | 30〜60分 | ワークフローYML初版 |
| フェーズ3 | 15〜30分 | テスト済みYML |
| フェーズ4 | 30〜90分 | 本番検証済みYML |
| フェーズ5 | 15〜30分 | リリース版YML |

**合計**: 約2〜4時間（複雑度により変動）

## 🤝 サポート

ワークフロー生成で問題が発生した場合:

1. **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** の該当セクションを確認
2. エラーログを確認（graphAiServer、expertAgent）
3. イテレーション改善フローに従って修正
4. 5回のイテレーションで解決しない場合は、チームに相談

---

## 📘 ドキュメント改善ポリシー

このドキュメント群は **Single Source of Truth (SSOT)** 原則に基づいて運用されています。

### 📂 ドキュメント構成

| ドキュメント | 役割 | 更新頻度 |
|-------------|------|---------|
| **GEMINI.md** (本書) | エントリーポイント、開発ワークフロー、チェックリスト | 低頻度 |
| **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** | 完全リファレンス、技術仕様、実装例 | 高頻度 |
| **[各Agent詳細ガイド](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#付録)** | Agent別の詳細仕様（付録A/B/C） | 中頻度 |

### 🔄 更新ルール

#### **新機能・新Agent追加時**

1. **GRAPHAI_WORKFLOW_GENERATION_RULES.md** に詳細を追加
   - 基本構造、実装例、エラーパターンを記載
   - Agent選択指針・モデル選択指針を更新
2. **GEMINI.md** のチェックリストを見直し（必要に応じて更新）
3. 参照リンクの整合性を確認

#### **エラーパターン・トラブルシューティング追加時**

1. **GRAPHAI_WORKFLOW_GENERATION_RULES.md** の「よくあるエラーと対応」セクションに追加
2. 診断手順・ルール更新基準を更新
3. **GEMINI.md** の「生成されたワークフローの動作確認」セクションを見直し

#### **開発プロセス改善時**

1. **GEMINI.md** の「開発の進め方（5フェーズワークフロー）」を更新
2. チェックリストを見直し
3. **GRAPHAI_WORKFLOW_GENERATION_RULES.md** の「LLMワークフロー作成手順」を同期

### ❌ 禁止事項

- **重複記述**: 同じ内容を複数のドキュメントに記載しない
- **不整合**: ドキュメント間で矛盾する情報を記載しない
- **古い情報の放置**: 更新時は必ず全ドキュメントの整合性を確認

### ✅ レビュー基準

新規PR・ドキュメント更新時は以下を確認:

- [ ] **SSOT原則**: 各情報が唯一の正しい場所に記載されているか
- [ ] **参照リンク**: すべてのリンクが正しく機能するか
- [ ] **整合性**: GEMINI.md と GRAPHAI_WORKFLOW_GENERATION_RULES.md の内容が矛盾していないか
- [ ] **例示の最新性**: 実装例がcurrent versionに対応しているか
- [ ] **チェックリストの網羅性**: 新機能に対応したチェック項目が追加されているか

### 🛠️ メンテナンス手順

**月次レビュー** (推奨):
1. エラーパターンの蓄積状況を確認
2. Agent・モデル選択指針の妥当性を検証
3. 参照リンクのリンク切れチェック
4. 実装例の動作確認

**四半期レビュー** (必須):
1. ドキュメント構成の見直し
2. 新規ベストプラクティスの追加
3. 非推奨機能の削除・警告追加
4. バージョン情報の更新

---

**最終更新日**: 2025-10-13

**バージョン**: 2.0.0
