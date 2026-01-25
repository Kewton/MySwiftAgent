# 用語集

MySwiftAgentプロジェクトで使用される用語の定義です。

---

## アーキテクチャ

### Platform層
データベース、キュー、シークレット管理などの基盤サービス群。
- **含まれるサービス**: jobqueue, myVault, myscheduler, valkey

### Agent層
AIエージェントとワークフロー実行を担当するサービス群。
- **含まれるサービス**: expertAgent, graphAiServer, mySwiftAgentCore

### Frontend層
ユーザーインターフェースを提供するサービス群。
- **含まれるサービス**: myAgentDesk, commonUI

---

## サービス

### expertAgent
AIエージェント基盤。LangGraphを使用したワークフロー生成と実行を担当。

### graphAiServer
GraphAI OSSを使用したワークフロー実行エンジン。主にgraphAiServer独自のワークフローを実行。

### mySwiftAgentCore
TaskFlow形式のワークフロー実行エンジン。**推奨されるワークフロー実行基盤**。

### myAgentDesk
SvelteKitベースのWeb UI。ジョブ管理、ワークフロー実行、結果確認を提供。

### jobqueue
ジョブキュー管理サービス。ジョブの作成、実行、ステータス管理を担当。

### myVault
シークレット管理サービス。APIキーや認証情報を安全に保管・提供。

### myscheduler
ジョブスケジューリングサービス。定期実行ジョブの管理。

### valkey
Redis互換のインメモリデータストア。キャッシュとセッション管理に使用。

---

## ワークフロー

### TaskFlow
mySwiftAgentCoreで使用されるワークフロー定義形式。JSON形式で定義。

### GraphAI
graphAiServerで使用されるワークフロー定義形式。YAML形式で定義。

### Job
実行単位。ワークフローの1回の実行を表す。

### TaskMaster
ジョブの実行を管理するエンティティ。ジョブの状態遷移を制御。

### Step / Node
ワークフロー内の1つの処理単位。LLM呼び出し、API呼び出しなど。

---

## 開発プロセス

### Feature
大きな機能単位。複数のIssueに分割して実装。

### Issue
実装の最小単位。1日以内で完了可能なサイズを推奨。

### PM Auto-Dev
Issue開発を自動化するスラッシュコマンド。TDD→受入テスト→リファクタリング→進捗報告を自動実行。

### TDD (Test-Driven Development)
テスト駆動開発。テストを先に書き、テストが通るようにコードを実装する開発手法。

### 受入テスト
Issue の受入条件を検証するE2Eテスト。実際のサービスに対してAPI呼び出しを行う。

---

## テスト

### L1 単体テスト
個々の関数・クラスをテストする。モックを使用。CI環境で実行。

### L2 結合テスト
複数のコンポーネントの連携をテストする。CI環境で実行。

### L3 受入テスト
E2Eで機能全体をテストする。実APIキーが必要。ローカル環境で実行。

### カバレッジ
テストによってカバーされるコードの割合。単体テスト90%以上、結合テスト50%以上が基準。

---

## LLM関連

### LangGraph
LangChain上に構築されたグラフベースのエージェントフレームワーク。

### LangChain
LLMアプリケーション構築のためのフレームワーク。

### Langfuse
LLM Observabilityプラットフォーム。トレース、プロンプト管理、評価を提供。

### Prompt
LLMへの入力テキスト。システムプロンプト、ユーザープロンプトなど。

### Token
LLMが処理するテキストの最小単位。課金やコンテキスト制限の基準。

---

## インフラ

### Docker Compose
複数のDockerコンテナを定義・実行するツール。

### Valkey
Redis互換のオープンソースインメモリデータストア。

### SQLite
軽量なファイルベースのデータベース。開発環境で使用。

### uv
高速なPythonパッケージマネージャー。pip/poetry の代替。

---

## Git / GitHub

### worktree
1つのリポジトリで複数のブランチを同時にチェックアウトする機能。

### PR (Pull Request)
コード変更をマージするためのレビューリクエスト。

### CI/CD
継続的インテグレーション・継続的デリバリー。GitHub Actionsで実装。

---

## ドキュメント

### CLAUDE.md
Claude Code向けのプロジェクト指針ドキュメント。

### dev-reports
開発中の作業ドキュメントを配置するディレクトリ。

### /doc-register
作業ドキュメントを正式ドキュメントに昇格させるスラッシュコマンド。

---

## 関連ドキュメント

- [システム概要](../architecture/overview.md)
- [サービス間依存関係](../architecture/service-dependencies.md)
- [開発ワークフロー](../development/workflow.md)
