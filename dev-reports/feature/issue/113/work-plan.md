# 作業計画: Langfuse Self-hosted導入によるLLM Observability基盤構築

**作成日**: 2025-11-02
**予定工数**: 8人日
**完了予定**: 2025-11-12

---

## 📚 参考ドキュメント

**必須参照** (該当する場合):
- [x] [設計方針](./design-policy.md) - 実装前に全文確認済み

**推奨参照**:
- [x] [アーキテクチャ概要](../../../docs/design/architecture-overview.md)
- [x] [環境変数管理](../../../docs/design/environment-variables.md)
- [x] [myVault連携](../../../docs/design/myvault-integration.md)

**外部ドキュメント**:
- [ ] [Langfuse Self-hosting Guide](https://langfuse.com/docs/deployment/self-host)
- [ ] [Langfuse Docker Deployment](https://langfuse.com/docs/deployment/docker)
- [ ] [LangChain Integration](https://langfuse.com/docs/integrations/langchain/tracing)

---

## 📊 Phase分解

実装は2つのPhaseに分けて段階的に進めます。

### Phase 1: Langfuse Self-hosted構築 + トレーシング実装 (5日)

**目標**: Langfuse Self-hosted環境構築 + expertAgentへの統合とトレーシング基盤の確立

#### Day 1: Langfuse Self-hosted環境構築 (1日目)

**作業内容**:
- [ ] **Docker Compose設定ファイル作成**
  - `langfuse/docker-compose.langfuse.yml` 作成
  - PostgreSQL設定（port 5433）
  - Langfuse Server設定（port 3000）
  - ネットワーク・ボリューム設定
  - healthcheck設定
- [ ] **環境変数ファイル作成**
  - `langfuse/.env.langfuse` 作成
  - シークレット生成（NEXTAUTH_SECRET, SALT）
  - データベース認証情報設定
- [ ] **Langfuse起動・初期化**
  - `docker-compose up -d` 実行
  - コンテナ起動確認
  - ログ確認（エラーがないこと）
  - データベースマイグレーション確認

**成果物**:
- `langfuse/docker-compose.langfuse.yml`
- `langfuse/.env.langfuse`
- Langfuseコンテナが起動中

**確認項目**:
- [ ] PostgreSQLコンテナが正常起動（`docker ps`）
- [ ] Langfuse Serverコンテナが正常起動（`docker ps`）
- [ ] ヘルスチェックがhealthy状態
- [ ] Langfuse Web UIにアクセス可能（http://localhost:3000）

---

#### Day 2: Langfuse初期セットアップ + myVault統合 (1日目)

**作業内容**:
- [ ] **Langfuse Web UI初期セットアップ**
  - 管理者アカウント作成
  - プロジェクト作成（expertAgent-traces）
  - APIキー生成（SECRET_KEY, PUBLIC_KEY）
  - APIキーの動作確認（curlでテスト）
- [ ] **myVaultへのシークレット登録**
  - LANGFUSE_SECRET_KEY登録
  - LANGFUSE_PUBLIC_KEY登録
  - myVault APIで取得テスト
- [ ] **expertAgent環境変数設定**
  - `.env.example` 更新（LANGFUSE_HOST等）
  - `core/config.py` 更新（Settings追加）

**成果物**:
- Langfuseプロジェクト作成完了
- myVaultにAPIキー登録完了
- `core/config.py` 更新

**確認項目**:
- [ ] Langfuse Web UIでプロジェクトが表示される
- [ ] APIキーが生成されている
- [ ] myVaultからAPIキーを取得できる
- [ ] `core/config.py` でLangfuse設定が読み込まれる

---

#### Day 3: LangfuseService実装 (1日目)

**作業内容**:
- [ ] **LangfuseService実装**
  - `app/services/langfuse_service.py` 作成
  - シングルトンクラス実装
  - Langfuse Client初期化（Self-hosted対応）
  - `get_callback_handler()` 実装
  - `score_trace()` 実装
  - `flush()` 実装
- [ ] **接続テスト**
  - Langfuse Clientの初期化確認
  - expertAgent → Langfuse間の通信テスト
  - トレース送信テスト（手動）

**成果物**:
- `app/services/langfuse_service.py`

**確認項目**:
- [ ] LangfuseServiceがシングルトンで動作
- [ ] Langfuse Clientが正常に初期化される
- [ ] expertAgent → Langfuse間の通信が成功
- [ ] テストトレースがLangfuse Web UIに表示される

---

#### Day 4: expertAgentへのトレーシング統合 (1日目)

**作業内容**:
- [ ] **ai_agent_service.py更新**
  - `langfuse_service.get_callback_handler()` 呼び出し追加
  - `execute_sample_agent()` にCallbackHandler統合
  - `execute_utility_agent()` にCallbackHandler統合
  - `execute_myllm()` にトレーシング追加
- [ ] **chat_endpoints.py更新**
  - `requirement_definition()` にトレーシング追加
  - ストリーミングAPIのManual Tracing実装
- [ ] **job_generator_endpoints.py更新**
  - `generate_job_and_tasks()` にトレーシング追加
- [ ] **standardAiAgent.py更新**
  - `trace_id` フィールド追加
  - レスポンススキーマにtrace_id追加

**成果物**:
- `app/services/ai_agent_service.py` 更新
- `app/api/v1/chat_endpoints.py` 更新
- `app/api/v1/job_generator_endpoints.py` 更新
- `app/schemas/standardAiAgent.py` 更新

**確認項目**:
- [ ] LangGraph Agent API（sample, utility）のトレースが記録される
- [ ] mylllm APIのトレースが記録される
- [ ] chat APIのトレースが記録される
- [ ] job_generator APIのトレースが記録される
- [ ] API応答にtrace_idが含まれる
- [ ] Langfuse Web UIでトレース詳細が確認可能

---

#### Day 5: Phase 1テスト作成 (1日目)

**作業内容**:
- [ ] **単体テスト作成**
  - `tests/unit/test_langfuse_service.py` 作成
    - `test_initialize_client()` - Client初期化テスト
    - `test_get_callback_handler()` - CallbackHandler取得テスト
    - `test_score_trace()` - スコア送信テスト
    - `test_flush()` - フラッシュテスト
    - `test_disabled_langfuse()` - 無効化時のテスト
- [ ] **結合テスト作成（Phase 1範囲）**
  - `tests/integration/test_tracing.py` 作成
    - `test_agent_tracing()` - エージェントトレーシングテスト
    - `test_trace_id_in_response()` - trace_id返却テスト
- [ ] **カバレッジ確認**
  - `uv run pytest --cov=app --cov=core`
  - カバレッジレポート確認
  - 90%未満の場合、追加テスト作成

**成果物**:
- `tests/unit/test_langfuse_service.py`
- `tests/integration/test_tracing.py`
- カバレッジレポート（90%以上）

**確認項目**:
- [ ] 単体テストカバレッジ90%以上
- [ ] 全テストが合格
- [ ] Ruff lintingエラーゼロ
- [ ] MyPy type checkingエラーゼロ

---

### Phase 2: Observability API実装 (3日)

**目標**: トレースデータ取得・フィードバック送信APIを構築

#### Day 6: TraceService + スキーマ実装 (1日目)

**作業内容**:
- [ ] **TraceService実装**
  - `app/services/trace_service.py` 作成
  - `get_traces()` - トレース一覧取得
  - `get_trace()` - トレース詳細取得
  - `generate_trace_url()` - Langfuse UIへのURL生成（Self-hosted対応）
- [ ] **Observabilityスキーマ実装**
  - `app/schemas/observability.py` 作成
  - `TraceListResponse` - トレース一覧レスポンス
  - `TraceDetailResponse` - トレース詳細レスポンス
  - `TraceURLResponse` - URL生成レスポンス
  - `FeedbackRequest` - フィードバック送信リクエスト
  - `FeedbackResponse` - フィードバック送信レスポンス
- [ ] **接続テスト**
  - Langfuse API呼び出しテスト
  - トレース取得テスト

**成果物**:
- `app/services/trace_service.py`
- `app/schemas/observability.py`

**確認項目**:
- [ ] TraceServiceがトレース一覧を取得できる
- [ ] TraceServiceがトレース詳細を取得できる
- [ ] generate_trace_url()がSelf-hosted URLを生成する
- [ ] スキーマが正しくバリデーションされる

---

#### Day 7: Observability API実装 (1日目)

**作業内容**:
- [ ] **Observability API実装**
  - `app/api/v1/observability_endpoints.py` 作成
  - `GET /v1/observability/traces` - トレース一覧取得
  - `GET /v1/observability/traces/{trace_id}` - トレース詳細取得
  - `GET /v1/observability/traces/{trace_id}/url` - URL生成
  - `POST /v1/observability/feedback` - フィードバック送信
  - `GET /v1/observability/feedback/{trace_id}` - フィードバック取得
- [ ] **app/main.py更新**
  - Observability APIルーター追加
- [ ] **Swagger UI確認**
  - 全エンドポイントが表示されることを確認
  - Try it outで動作確認

**成果物**:
- `app/api/v1/observability_endpoints.py`
- `app/main.py` 更新

**確認項目**:
- [ ] GET /v1/observability/tracesが正常動作
- [ ] GET /v1/observability/traces/{trace_id}が正常動作
- [ ] GET /v1/observability/traces/{trace_id}/urlが正常動作
- [ ] POST /v1/observability/feedbackが正常動作
- [ ] Swagger UIで全APIが確認可能

---

#### Day 8: Phase 2テスト + ドキュメント作成 (1日目)

**作業内容**:
- [ ] **単体テスト作成**
  - `tests/unit/test_trace_service.py` 作成
    - `test_get_traces()` - トレース一覧取得テスト
    - `test_get_trace()` - トレース詳細取得テスト
    - `test_generate_trace_url()` - URL生成テスト
- [ ] **結合テスト作成**
  - `tests/integration/test_observability_api.py` 作成
    - `test_get_traces_endpoint()` - トレース一覧APIテスト
    - `test_get_trace_detail_endpoint()` - トレース詳細APIテスト
    - `test_get_trace_url_endpoint()` - URL生成APIテスト
    - `test_submit_feedback_endpoint()` - フィードバック送信APIテスト
- [ ] **カバレッジ確認**
  - Phase 2の結合テストカバレッジ確認（50%以上）
- [ ] **ドキュメント作成**
  - `docs/langfuse-self-hosting-setup.md` 作成
    - Self-hostingセットアップ手順
    - トラブルシューティング
- [ ] **最終確認**
  - `./scripts/pre-push-check-all.sh` 実行
  - 全品質チェックに合格

**成果物**:
- `tests/unit/test_trace_service.py`
- `tests/integration/test_observability_api.py`
- `docs/langfuse-self-hosting-setup.md`
- カバレッジレポート（結合テスト50%以上）

**確認項目**:
- [ ] 単体テストカバレッジ90%以上
- [ ] 結合テストカバレッジ50%以上
- [ ] 全テストが合格
- [ ] Ruff lintingエラーゼロ
- [ ] MyPy type checkingエラーゼロ
- [ ] pre-push-check-all.sh合格

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守
  - Single Responsibility: LangfuseService（トレーシング）、TraceService（データ取得）で責務分離
  - Open-Closed: CallbackHandler方式で拡張性確保
  - Liskov Substitution: BaseService継承構造を維持
  - Interface Segregation: 最小限のインターフェース提供
  - Dependency Inversion: サービス層抽象化
- [x] **KISS原則**: 遵守
  - Langfuse公式SDKを使用し、独自実装を最小化
  - Self-hosted環境もDocker Composeでシンプルに構築
- [x] **YAGNI原則**: 遵守
  - Phase 1ではトレーシング基盤のみ実装
  - Dashboard機能は将来のissueで実装
- [x] **DRY原則**: 遵守
  - LangfuseServiceでCallbackHandler生成を一元管理
  - TraceServiceでLangfuse API呼び出しを一元管理

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: 準拠
  - レイヤー分離を維持（Service → Core）
  - 既存のAPI構造を変更せず、Observabilityを追加
- [x] **依存関係の方向性**: 正常
  - API → Service → Core の単方向依存

### 設定管理ルール
- [x] **環境変数**: 遵守（`./docs/design/environment-variables.md` 準拠）
  - `LANGFUSE_HOST`, `LANGFUSE_ENABLED` → .env
  - `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY` → myVault
- [x] **myVault**: 遵守（`./docs/design/myvault-integration.md` 準拠）
  - APIキーはmyVaultで暗号化管理

### 品質担保方針
- [x] **単体テストカバレッジ目標**: 90%以上
  - LangfuseService: 95%目標（モック使用）
  - TraceService: 92%目標
- [x] **結合テストカバレッジ目標**: 50%以上
  - Observability API: 60%目標
  - トレーシング統合: 55%目標
- [x] **Ruff linting**: エラーゼロ目標
- [x] **MyPy type checking**: エラーゼロ目標

### CI/CD準拠
- [x] **PRラベル**: `feature` ラベルを付与予定（minor版数アップ）
- [x] **コミットメッセージ**: Conventional Commits準拠
  - `feat(observability): add Langfuse self-hosted integration`
  - `feat(infrastructure): add Langfuse Docker Compose setup`
- [x] **pre-push-check-all.sh**: 全Phase完了後に実行予定

### 参照ドキュメント遵守
- [x] **新プロジェクト追加時**: N/A（既存プロジェクトへの機能追加）
- [x] **GraphAI ワークフロー開発時**: N/A（本タスクは該当しない）
- [x] **アーキテクチャ概要**: `./docs/design/architecture-overview.md` 参照済み
- [x] **環境変数管理**: `./docs/design/environment-variables.md` 参照済み
- [x] **myVault連携**: `./docs/design/myvault-integration.md` 参照済み

### 違反・要検討項目

なし

---

## 📅 スケジュール

| Phase | Day | 作業内容 | 開始予定 | 完了予定 | 状態 |
|-------|-----|---------|---------|---------|------|
| Phase 1 | Day 1 | Langfuse Self-hosted環境構築 | 11/03 | 11/03 | 予定 |
| Phase 1 | Day 2 | Langfuse初期セットアップ + myVault統合 | 11/04 | 11/04 | 予定 |
| Phase 1 | Day 3 | LangfuseService実装 | 11/05 | 11/05 | 予定 |
| Phase 1 | Day 4 | expertAgentへのトレーシング統合 | 11/06 | 11/06 | 予定 |
| Phase 1 | Day 5 | Phase 1テスト作成 | 11/07 | 11/07 | 予定 |
| Phase 2 | Day 6 | TraceService + スキーマ実装 | 11/08 | 11/08 | 予定 |
| Phase 2 | Day 7 | Observability API実装 | 11/09 | 11/09 | 予定 |
| Phase 2 | Day 8 | Phase 2テスト + ドキュメント作成 | 11/10 | 11/10 | 予定 |

**バッファ日**: 11/11-11/12（予備日）

---

## 🎯 マイルストーン

### Milestone 1: Phase 1完了（11/07）
- ✅ Langfuse Self-hosted環境が稼働
- ✅ expertAgentの全LLM APIでトレーシングが動作
- ✅ Langfuse Web UIでトレース詳細が確認可能
- ✅ API応答にtrace_idが含まれる
- ✅ 単体テストカバレッジ90%以上

### Milestone 2: Phase 2完了（11/10）
- ✅ expertAgent APIからトレースデータ取得が可能
- ✅ expertAgent APIからフィードバック送信が可能
- ✅ Langfuse UIへのリンク生成が可能（Self-hosted URL）
- ✅ 結合テストカバレッジ50%以上

### Final Milestone: Issue #113完了（11/10）
- ✅ Langfuse Self-hosted環境が安定稼働
- ✅ expertAgentでLLM Observability基盤が稼働
- ✅ Observability APIでトレースデータ取得・フィードバック送信が可能
- ✅ 開発者がcurlやPostmanでObservability APIを利用できる
- ✅ 将来のダッシュボード実装のためのAPI基盤が整っている
- ✅ 品質基準（カバレッジ90%/50%、Linting/Type checkエラーゼロ）達成
- ✅ Self-hostingセットアップガイドが完備

---

## 🚨 リスク管理

### リスク1: Langfuse Self-hosted環境構築の遅延

**リスク内容**: Docker Compose設定の複雑さ、ネットワーク問題等で環境構築に想定以上の時間がかかる

**影響度**: 高（Phase 1全体に影響）

**対策**:
- Day 1の午前中に公式ドキュメント熟読
- 公式のDocker Composeサンプルをベースにカスタマイズ
- 問題発生時は公式GitHubのIssueを確認

**緩和策**:
- バッファ日（11/11-11/12）で吸収

---

### リスク2: Langfuse APIの理解不足

**リスク内容**: Langfuse Python SDKのAPI仕様が不明確で、実装に時間がかかる

**影響度**: 中（Day 3-4に影響）

**対策**:
- Day 2で公式ドキュメント・サンプルコード確認
- 簡単なトレース送信スクリプトで事前検証

**緩和策**:
- Day 5のテスト作成をDay 4に前倒し可能

---

### リスク3: テストカバレッジ目標未達

**リスク内容**: 単体テストカバレッジ90%、結合テストカバレッジ50%に達しない

**影響度**: 中（品質基準に影響）

**対策**:
- Day 5, Day 8でカバレッジレポート確認
- 未カバー箇所を特定してテスト追加

**緩和策**:
- バッファ日（11/11-11/12）でテスト追加

---

## 📝 進捗報告方針

- **毎日の終了時**: phase-{N}-progress.md を作成（実装内容・課題・決定事項を記録）
- **Phase完了時**: 制約条件チェックを実施
- **Issue完了時**: final-report.md を作成（納品物・品質指標・目標達成度を記録）

---

## 🔍 品質チェックポイント

### Day 5 (Phase 1完了時)
- [ ] Langfuse Self-hosted環境が正常稼働
- [ ] expertAgent → Langfuse間の通信が安定
- [ ] 全LLM APIでトレーシングが動作
- [ ] 単体テストカバレッジ90%以上
- [ ] Ruff linting / MyPy type checkingエラーゼロ

### Day 8 (Phase 2完了時)
- [ ] Observability API全エンドポイントが動作
- [ ] 結合テストカバレッジ50%以上
- [ ] Swagger UIで全APIが確認可能
- [ ] pre-push-check-all.sh合格

### Issue完了時
- [ ] Self-hostingセットアップガイドが完備
- [ ] トレースデータがPostgreSQLに永続化
- [ ] Langfuse Web UIで全機能が利用可能
- [ ] 開発者がcurl/PostmanでObservability API利用可能

---

## 📚 参考資料

### 外部ドキュメント
- [Langfuse Self-hosting Guide](https://langfuse.com/docs/deployment/self-host)
- [Langfuse Docker Deployment](https://langfuse.com/docs/deployment/docker)
- [LangChain Integration](https://langfuse.com/docs/integrations/langchain/tracing)
- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)

### プロジェクト内ドキュメント
- [設計方針](./design-policy.md)
- [アーキテクチャ概要](../../../docs/design/architecture-overview.md)
- [環境変数管理](../../../docs/design/environment-variables.md)
- [myVault連携](../../../docs/design/myvault-integration.md)
- [開発ガイドライン](../../../DEVELOPMENT_GUIDE.md)
