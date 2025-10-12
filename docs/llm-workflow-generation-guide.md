# LLMワークフロー生成ガイド

このドキュメントは、LLM（大規模言語モデル）を使用してGraphAI YMLワークフローファイルを自動生成する際の方針と手順を提供します。

## 📋 概要

MySwiftAgentプロジェクトでは、自然言語の指示からGraphAI YMLワークフローファイルを自動生成する仕組みを採用しています。これにより、複雑なワークフロー定義を手動で記述する手間を大幅に削減し、開発効率を向上させます。

## 🎯 生成方針

### 基本方針

1. **ルール準拠**: [GRAPHAI_WORKFLOW_GENERATION_RULES.md](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) に記載された設計ルールに厳密に従う
2. **品質担保**: 生成されたワークフローは動作確認を経て、本番環境で使用可能な品質を保証
3. **イテレーション改善**: 最大5回のイテレーションで動作確認とエラー修正を実施
4. **ドキュメント化**: 生成されたYMLファイルには必ずヘッダーコメントを付与し、トレーサビリティを確保

### 対象LLM

MySwiftAgentでは以下のLLMを使用したワークフロー生成をサポートしています:

| LLM | 推奨度 | 特徴 | 使用ケース |
|-----|-------|------|-----------|
| **Gemini 2.5 Pro** | ⭐⭐⭐ | 最高精度、思考プロセス付き、100万トークンコンテキスト | 複雑なワークフロー、大規模な処理フロー |
| **Gemini 2.5 Flash** | ⭐⭐⭐ | 高速、コスト効率、バランス型 | 標準的なワークフロー、反復的な改善 |
| **Claude Sonnet 4.5** | ⭐⭐⭐ | コーディング世界最高、複雑なエージェント構築 | 高度なロジック、エージェント統合 |
| **Claude Opus 4.1** | ⭐⭐ | エージェントタスク特化、詳細な推論 | 実世界コーディング、複雑な推論タスク |
| **GPT-5** | ⭐⭐ | 27万トークン入力、コーディング・数学に優れる | 長文コンテキスト、数学的処理 |

**推奨**: Gemini 2.5シリーズ（Pro/Flash）を使用することで、コスト効率と品質のバランスが最適化されます。

## 🚀 Gemini CLI を使用したワークフロー生成

### セットアップ手順

#### 1. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
2. 「Create API Key」をクリックしてAPIキーを生成
3. 生成されたAPIキーをコピー

#### 2. 環境変数の設定

APIキーを環境変数として設定します:

```bash
# ~/.bashrc または ~/.zshrc に追加
export GOOGLE_API_KEY="your-api-key-here"

# 設定を反映
source ~/.bashrc  # または source ~/.zshrc
```

**セキュリティ注意事項**:
- APIキーはコミットしない（`.gitignore`に`*.env`を追加済み）
- 本番環境では環境変数またはシークレット管理サービスを使用
- APIキーは定期的にローテーション

#### 3. Gemini CLI のインストール

**方法A: Python SDK（推奨）**

```bash
# Python SDKをインストール
pip install google-generativeai

# または uv を使用
uv pip install google-generativeai
```

**方法B: Google Cloud CLI**

```bash
# Google Cloud CLIをインストール（未インストールの場合）
# macOS
brew install --cask google-cloud-sdk

# 認証設定
gcloud auth application-default login
```

#### 4. 動作確認

```bash
# Python SDKでの確認
python3 << 'EOF'
import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("Hello, Gemini!")
print(response.text)
EOF
```

成功すると、Geminiからの応答が表示されます。

### 基本的な使用方法

#### Python SDKを使用したワークフロー生成

```python
import google.generativeai as genai
import os

# API設定
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# モデル選択（推奨: gemini-2.5-flash または gemini-2.5-pro）
model = genai.GenerativeModel("gemini-2.5-flash")

# システムプロンプト
system_instruction = """
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
"""

# ユーザー要求
user_request = """
以下の要件でワークフローを作成してください:
1. ユーザーがトピックを入力
2. Google検索でトピックに関する情報を収集（3件）
3. explorerエージェントで情報を整理
4. gpt-oss:120bで詳細なレポートを生成
5. 結果を出力
"""

# ワークフロー生成
response = model.generate_content(
    system_instruction + "\n\n" + user_request
)

# 生成されたYMLファイルを保存
with open("./graphAiServer/config/graphai/llmwork/report_generation_20251012.yml", "w") as f:
    f.write(response.text)

print("✅ ワークフローファイルを生成しました")
```

### 対話型ワークフロー生成スクリプト

より実用的な対話型スクリプトの例:

```python
#!/usr/bin/env python3
"""
対話型GraphAI YMLワークフロー生成スクリプト
"""
import google.generativeai as genai
import os
from datetime import datetime

def generate_workflow():
    # API設定
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("=== GraphAI ワークフロー生成 ===\n")

    # ユーザー要求の入力
    print("ワークフローの要件を入力してください（複数行可、Ctrl+Dで終了）:")
    user_request = ""
    try:
        while True:
            line = input()
            user_request += line + "\n"
    except EOFError:
        pass

    # システムプロンプトの読み込み
    with open("./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md", "r") as f:
        rules = f.read()

    system_instruction = f"""
あなたはGraphAI YMLワークフローファイルを生成する専門エージェントです。

以下のルールドキュメントに厳密に従ってください:

{rules}

ユーザー要求に対して、完全なYMLファイルを生成してください。
ヘッダーコメント、version、nodes構造をすべて含めること。
"""

    # ワークフロー生成
    print("\n🔄 ワークフロー生成中...\n")
    response = model.generate_content(system_instruction + "\n\n" + user_request)

    # タイムスタンプ付きファイル名生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    purpose = input("\nワークフローの目的を簡潔に入力してください（ファイル名に使用）: ")
    filename = f"./graphAiServer/config/graphai/llmwork/{purpose}_{timestamp}.yml"

    # ファイル保存
    with open(filename, "w") as f:
        f.write(response.text)

    print(f"\n✅ ワークフローファイルを生成しました: {filename}")
    print("\n次のステップ:")
    print("1. ファイル内容を確認")
    print("2. graphAiServerで動作確認")
    print("3. エラーがあれば修正してイテレーション")

if __name__ == "__main__":
    generate_workflow()
```

**使用例**:

```bash
# スクリプトに実行権限を付与
chmod +x scripts/generate-workflow.py

# 実行
./scripts/generate-workflow.py
```

## 📝 ワークフロー生成の5フェーズ

詳細は [GRAPHAI_WORKFLOW_GENERATION_RULES.md - LLMワークフロー作成手順](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#llmワークフロー作成手順) を参照してください。

### フェーズ1: 要件分析と設計合意

- ユーザーの要求を正確に理解
- 処理フローの提示と合意形成
- 処理時間の目安を提示

### フェーズ2: 実現可能性評価

- 現在のexpertAgent機能で実現可能か評価
- 不足機能があればユーザーに提案
- 機能追加が必要な場合は実装後に続行

### フェーズ3: ワークフロー初期実装

- YMLファイルの初期実装
- ヘッダーコメントの記載
- 基本構造のチェックリスト確認

### フェーズ4: 動作確認と改善サイクル（最大5イテレーション）

```
イテレーション N (N = 1, 2, 3, 4, 5)
├─ ステップ1: graphAiServerで実行
├─ ステップ2: 結果判定（SUCCESS/FAILED）
├─ ステップ3: エラー原因調査
├─ ステップ4: ルール更新・YML修正
└─ ステップ5: Test Resultsヘッダー更新
```

5回のイテレーションで解決できない場合は、ユーザーにフィードバックを依頼します。

### フェーズ5: 最終化

- Test Resultsヘッダーの最終更新
- Notesセクションの追加（必要に応じて）
- 運用ドキュメントの更新

## 🔧 動作確認手順

### 1. サービス起動確認

```bash
# graphAiServerが起動していることを確認
curl http://127.0.0.1:8105/health

# expertAgentが起動していることを確認（4ワーカー推奨）
curl http://127.0.0.1:8104/health
```

### 2. ワークフロー実行

```bash
# 開発用エンドポイントで実行（想定）
curl -X POST http://127.0.0.1:8105/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_file": "llmwork/{your_workflow}.yml",
    "input": "ユーザー入力テキスト"
  }'
```

### 3. ログ確認

```bash
# graphAiServerログ
tail -f logs/graphaiserver.log

# expertAgentログ
tail -f logs/expertagent.log

# エラーのみ抽出
tail -n 100 logs/graphaiserver.log | grep -i error
tail -n 100 logs/expertagent.log | grep -i error
```

### 4. よくあるエラーと対応

| エラー | 原因 | 対応 |
|-------|------|------|
| `TypeError: fetch failed` | expertAgentへの接続失敗 | ポート番号確認（8104）、ワーカー数確認（`--workers 4`） |
| `undefined` が出力 | sourceノード参照エラー | `:source.text` → `:source` に修正 |
| `mapAgentでタイムアウト` | 並列処理過負荷 | `concurrency: 2` を追加 |
| `RuntimeWarning: coroutine was never awaited` | expertAgent側のawait漏れ | Pythonコードに `await` 追加 |

詳細なエラー回避パターンは [GRAPHAI_WORKFLOW_GENERATION_RULES.md - エラー回避パターン](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#エラー回避パターン) を参照してください。

## ✅ 生成品質チェックリスト

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
- [ ] 使用するエンドポイントが存在する（10種類のエンドポイントを確認）
- [ ] `model_name` パラメータが有効なモデル名

### モデル選択
- [ ] ローカルLLMを優先使用（gpt-oss:20b, gpt-oss:120b）
- [ ] タスクの複雑度に応じたモデルを選択
- [ ] コスト（ローカル vs クラウド）を考慮

### エラー処理
- [ ] タイムアウトが適切に設定されている（グローバル300秒）
- [ ] 重要なノードで `console.after: true` を設定
- [ ] 並列処理に `concurrency` パラメータを設定（軽量:4-8、中程度:2-3、重い:1-2）

### 命名規則
- [ ] ノード名が意味のある名前
- [ ] 小文字スネークケースを使用
- [ ] 適切な接尾辞（`_builder`, `_mapper`, `_search`, `_output` など）を使用

### ヘッダーコメント
- [ ] Created（作成日時）を記載
- [ ] User Request（ユーザー要求）を記載
- [ ] Test Results（動作確認履歴）を記載
- [ ] Description（概要）を記載
- [ ] Notes（注意事項）を記載（必要に応じて）

## 🔄 イテレーション改善のベストプラクティス

### エラー発生時の診断手順

1. **ログのタイムスタンプ確認**:
```bash
grep "node_name start" logs/graphaiserver.log
# リクエストが同時刻に集中していないか確認
```

2. **expertAgentのワーカー数確認**:
```bash
grep "Started server process" logs/expertagent.log | wc -l
# 1の場合は並列処理に対応できていない
```

3. **並列数確認**:
YMLファイルでmapAgentに `concurrency` パラメータがあるか確認

### ルール更新の判断基準

| 状況 | ルール更新の必要性 | 更新内容 |
|-----|----------------|---------|
| **新しいエラーパターン発見** | ✅ 必要 | 「エラー回避パターン」セクションに追記 |
| **新機能追加** | ✅ 必要 | 「expertAgent API統合」セクションに追記 |
| **既知のエラー** | ⭕ 不要 | YMLファイルのみ修正 |
| **ユーザー固有のエラー** | ⭕ 不要 | YMLファイルのNotesに記載 |

## 📚 参考ドキュメント

- 📄 **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** - ワークフロー生成の詳細ルール（必須）
- 📄 **[GEMINI.md](../GEMINI.md)** - Gemini CLI使用時の指針
- 📄 **[CLAUDE.md](../CLAUDE.md)** - Claude Code使用時の指針
- 🌐 **[Google AI Studio](https://aistudio.google.com/)** - Gemini API管理
- 🔧 **[GraphAI公式ドキュメント](https://github.com/receptron/graphai)** - GraphAIフレームワーク仕様
- 📖 **[expertAgent API仕様](../expertAgent/docs/)** - expertAgent統合ガイド

## 🤝 サポート

ワークフロー生成で問題が発生した場合:

1. **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** の該当セクションを確認
2. エラーログを確認（graphAiServer、expertAgent）
3. イテレーション改善フローに従って修正
4. 5回のイテレーションで解決しない場合は、チームに相談

## 📊 生成実績とベストプラクティス

### 成功事例

- ✅ **シンプルなLLM呼び出し**: 1イテレーションで完了
- ✅ **Google検索→レポート生成**: 2イテレーション（並列数調整）
- ✅ **ポッドキャスト台本生成（4章）**: 3イテレーション（concurrency設定、ワーカー数調整）

### 学習した教訓

1. **並列処理の規模を事前に見積もる**: 処理する配列の要素数とLLMモデルの種類を考慮
2. **concurrency値を必ず設定**: 軽量:4-8、中程度:2-3、重い:1-2
3. **expertAgentのワーカー数を調整**: `workers ≥ concurrency` を確保
4. **タイムアウトを確認**: グローバルタイムアウトが300秒に設定済みか確認

---

**最終更新日**: 2025-10-12

**バージョン**: 1.0.0
