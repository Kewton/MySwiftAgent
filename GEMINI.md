# GEMINI.md - Gemini CLI Quick Start Guide

このファイルは、Gemini CLI (Google AI Studio) を使用してGraphAI YMLワークフローファイルを自動生成する際のクイックガイドです。

---

## 📋 概要

Gemini CLIを使用することで、自然言語の指示からGraphAI YMLワークフローファイルを自動生成できます。このガイドでは、効率的なワークフロー生成のための最小限の手順を提供します。

---

## 🎯 必須3ステップ

### ステップ1: システムプロンプト設定

Gemini CLIに以下のシステムプロンプトを設定してください:

```
あなたはGraphAI YMLワークフロー生成の専門家です。
以下のドキュメントに従ってワークフローを生成してください：

📄 完全リファレンス: ./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md
📋 開発テンプレート: ./graphAiServer/docs/WORKFLOW_DEVELOPMENT_TEMPLATE.md
📝 記録テンプレート: ./graphAiServer/docs/ITERATION_RECORD_TEMPLATE.md

【必須タスク】
1. **開始前**: WORKFLOW_DEVELOPMENT_TEMPLATE.md を読み、技術的考慮事項を確認
2. フェーズ1-5を順番に実行
3. 各フェーズ完了時に ./workspace/geminicli/{workflow_name}/phaseN-*.md に記録
4. **エラー発生時**: ITERATION_RECORD_TEMPLATE.md に従って詳細記録
5. 完了時に summary.md を生成

【重要な注意事項】
- ✅ mapAgent使用時は必ず `compositeResult: true` を指定
- ✅ APIレスポンスの `results` フィールドを必ず記録
- ✅ `[object Object]` エラーが出たら、GRAPHAI_WORKFLOW_GENERATION_RULES.md の「よくあるエラーパターン」を参照
- ⚠️ 記録なしで次のフェーズに進まないこと
```

### ステップ2: ワークフロー生成依頼

ユーザー要件をGemini CLIに入力:

```markdown
【要件】
目的: [具体的な目的]
入力: [データ形式]
出力: [期待される形式]

【完了基準】
- [テストケース1]
- [テストケース2]

【参照ドキュメント】
- ./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md
```

### ステップ3: 動作確認

```bash
# graphAiServer経由で実行
curl -X POST http://127.0.0.1:8105/api/v1/myagent/llmwork/{workflow_name} \
  -H "Content-Type: application/json" \
  -d '{"user_input": "test input"}'

# ログ確認
tail -f logs/graphaiserver.log
tail -f logs/expertagent.log
```

---

## ⚠️ mapAgent使用時の必須チェック

mapAgentを使用する場合、以下を必ず確認してください：

### 1. compositeResult: true の指定
```yaml
process_items:
  agent: mapAgent
  params:
    compositeResult: true  # ← これがないと [object Object] エラー
```

### 2. 後続ノードでの正しい参照
```yaml
join_results:
  agent: arrayJoinAgent
  inputs:
    array: :process_items.isResultノード名  # ← プロパティアクセス
```

### 3. デバッグ用ログの有効化
```yaml
process_items:
  agent: mapAgent
  console:
    after: true  # ← 必ず追加
```

詳細: `./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md` の「mapAgentの出力形式と参照方法」セクション

---

## 🔄 5フェーズ開発プロセス

Gemini CLIは以下の5フェーズを**順番に実行**します:

| フェーズ | 目的 | 成果物 | 記録先 |
|---------|------|--------|--------|
| **フェーズ1** | 要件分析と設計合意 | 要求定義、作業計画 | `phase1-requirements.md` |
| **フェーズ2** | 実現可能性評価 | 設計書、機能追加提案 | `phase2-design.md` |
| **フェーズ3** | ワークフロー初期実装 | YMLファイル初版 | `phase3-test-verification.md` |
| **フェーズ4** | 動作確認と改善 | 本番検証済みYML | `phase4-production-test.md` |
| **フェーズ5** | 最終化 | リリース版YML、完了報告 | `phase5-finalization.md` |

**詳細な手順**: 各フェーズの詳細は [GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) の「LLMワークフロー作成手順（詳細）」セクションを参照してください。

---

## 📂 開発記録ディレクトリ構造

Gemini CLIは以下のディレクトリ構造で開発記録を保存します:

```
./workspace/geminicli/{workflow_name}/
├── phase1-requirements.md       # フェーズ1: 要件分析と設計合意の記録
├── phase2-design.md             # フェーズ2: 実現可能性評価の記録
├── phase3-test-verification.md # フェーズ3: ワークフロー初期実装の記録
├── phase4-production-test.md   # フェーズ4: 動作確認と改善の記録
├── phase5-finalization.md       # フェーズ5: 最終化の記録
└── summary.md                   # 全体サマリー
```

**記録する内容**:
- 各フェーズの作業ログ（実施内容、コマンド実行結果）
- 設計判断の根拠と理由
- テスト結果とエラー対応
- イテレーション改善の履歴

---

## ✅ 完了チェックリスト

ワークフロー生成完了時に以下を確認してください:

### 基本構造
- [ ] `version: 0.5` を含む
- [ ] `source: {}` ノードがある
- [ ] 最低1つの `isResult: true` ノードがある

### データフロー
- [ ] すべてのノード間のデータ参照が正しい（`:node_name.field`）
- [ ] `source` ノードは直接参照（`:source`）している
- [ ] `mapAgent` 内では `:row.field` でアクセスしている

### expertAgent API統合
- [ ] すべてのAPI URLが `http://127.0.0.1:8104` を使用
- [ ] `force_json: true` パラメータを設定（推奨）
- [ ] 使用するエンドポイントが存在する

### エラー処理
- [ ] 並列処理に `concurrency` パラメータを設定
- [ ] 重要なノードで `console.after: true` を設定

### 開発プロセス
- [ ] 全5フェーズ完了
- [ ] `./workspace/geminicli/{workflow_name}/` に全記録保存
- [ ] `summary.md` 生成
- [ ] 動作確認成功

---

## 🔧 サービス起動確認

ワークフローを実行する前に、以下のサービスが起動していることを確認してください:

### 1. graphAiServer (ポート8105)

```bash
# ヘルスチェック
curl http://127.0.0.1:8105/health

# 起動方法
./scripts/dev-start.sh
# または
cd graphAiServer && npm run dev
```

### 2. expertAgent (ポート8104)

```bash
# ヘルスチェック
curl http://127.0.0.1:8104/health

# 起動方法（4ワーカー推奨）
cd expertAgent
uv run uvicorn app.main:app --host 0.0.0.0 --port 8104 --workers 4
```

**重要**: 並列処理（mapAgent）を使用する場合は、expertAgentを必ず `--workers 4` 以上で起動してください。

---

## 🚨 よくあるエラーと対応

| エラー | 原因 | 対応 |
|-------|------|------|
| `TypeError: fetch failed` | expertAgentへの接続失敗 | expertAgent起動確認、ポート8104確認 |
| `undefined` が出力 | sourceノード参照エラー | `:source.text` → `:source` に修正 |
| `mapAgentでタイムアウト` | 並列処理過負荷 | `concurrency: 2` を追加 |

**詳細なトラブルシューティング**: [GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) の「よくあるエラーと対応」セクションを参照してください。

---

## 📚 詳細ドキュメント

- 📘 **完全ルール**: [GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
  - 基本構造と必須要素
  - エージェント種別と使用方法
  - データフローパターン
  - expertAgent API統合
  - エラー回避パターン
  - パフォーマンス最適化
  - 実装例（シンプルから複雑まで）
  - 5フェーズ開発プロセス詳細

- 🤖 **Agent詳細ガイド**:
  - [Playwright Agent](./graphAiServer/docs/agents/PLAYWRIGHT_AGENT_GUIDE.md)
  - [Explorer Agent](./graphAiServer/docs/agents/EXPLORER_AGENT_GUIDE.md)
  - [File Reader Agent](./graphAiServer/docs/agents/FILE_READER_AGENT_GUIDE.md)

- 🔧 **GraphAI公式**: [https://github.com/receptron/graphai](https://github.com/receptron/graphai)
- 🌐 **Google AI Studio**: [https://aistudio.google.com/](https://aistudio.google.com/)

---

## 📘 ドキュメント構成（SSOT原則）

このプロジェクトのドキュメントは **Single Source of Truth (SSOT)** 原則に基づいています:

| ドキュメント | 役割 | 更新頻度 |
|-------------|------|---------|
| **GEMINI.md** (本書) | クイックスタートガイド | 低頻度 |
| **GRAPHAI_WORKFLOW_GENERATION_RULES.md** | 完全リファレンス、技術仕様 | 高頻度 |
| **各Agent詳細ガイド** | Agent別の詳細仕様 | 中頻度 |

**ルール**: 技術的な詳細は必ず **GRAPHAI_WORKFLOW_GENERATION_RULES.md** に記載し、本ドキュメントは最小限の手順のみを記載します。

---

## ❌ よくある失敗パターンと対策

### 失敗パターン1: [object Object] エラー

**症状**:
```
arrayJoinAgent の出力: "[object Object]\n\n---\n\n[object Object]"
```

**原因**: `compositeResult: true` の欠如

**対策**:
1. mapAgentに `compositeResult: true` を追加
2. 後続ノードで `:mapAgentノード名.isResultノード名` 形式で参照

**詳細**: GRAPHAI_WORKFLOW_GENERATION_RULES.md の「よくあるエラーパターン - エラー1」を参照

---

### 失敗パターン2: Silent Failure（データ捏造）

**症状**: エラーは出ないが、最終出力が元データと異なる

**原因**: 中間ノードでデータ破損 → LLMが「それらしい内容」を捏造

**対策**:
1. `console.after: true` で中間ノードを監視
2. GraphAI APIレスポンスの `results` フィールドを必ず確認
3. 中間データが `[object Object]` になっていないか検証

**重要**: エラーなし ≠ 正しい動作

**詳細**: GRAPHAI_WORKFLOW_GENERATION_RULES.md の「よくあるエラーパターン - エラー3」を参照

---

### 失敗パターン3: プロパティアクセスでUNDEFINED

**症状**: `namedInputs.array is UNDEFINED`

**原因**: `compositeResult: true` なしでプロパティアクセスを試みている

**対策**:
1. mapAgentに `compositeResult: true` を追加
2. または、プロパティアクセスを配列全体参照に変更

**詳細**: GRAPHAI_WORKFLOW_GENERATION_RULES.md の「よくあるエラーパターン - エラー2」を参照

---

### 失敗パターン4: jsonoutput HTTP 500エラー

**症状**: `HTTP error! Status: 500` (expertAgent側)

**原因**: LLMの出力がJSON形式でない

**対策**:
1. expertAgent APIに `force_json: true` パラメータを追加
2. プロンプトでJSON出力を明示的に指示

**詳細**: GRAPHAI_WORKFLOW_GENERATION_RULES.md の「よくあるエラーパターン - エラー4」を参照

---

## 🤝 サポート

ワークフロー生成で問題が発生した場合:

1. **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** の該当セクションを確認
2. エラーログを確認（graphAiServer、expertAgent）
3. イテレーション改善フローに従って修正
4. 5回のイテレーションで解決しない場合は、ユーザーにフィードバック依頼

---

**最終更新日**: 2025-10-14
**バージョン**: 3.0.0 (Simplified)

---

## 変更履歴

- **3.0.0** (2025-10-14): 1,546行 → 300行に大幅簡略化、SSOT原則に準拠
- **2.0.0** (2025-10-13): 5フェーズ開発プロセス追加
- **1.0.0** (2025-10-12): 初版作成
