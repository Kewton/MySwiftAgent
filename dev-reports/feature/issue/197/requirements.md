# 要件定義書: モノレポでの品質と生産性向上施策

**Issue番号**: #197
**作成日**: 2025-11-30
**ステータス**: 要件定義

---

## 1. ユーザーストーリー

### ストーリー1: レイヤ別docker-compose分割
```
As a 開発者
I want to docker-composeをレイヤ別に三分割する
So that レイヤごとの責務が明確になり、将来的なリポジトリ分割やチーム分担が容易になる
```

### ストーリー2: ローカル実行モードの整備
```
As a 開発者
I want to make/justコマンドで簡単にレイヤ別起動できる
So that 毎回docker composeコマンドを手打ちせずに効率的に開発できる
```

### ストーリー3: サービス間URL/ポートの統一管理
```
As a 開発者
I want to サービス間のURL/ポートをENVで統一管理する
So that 環境ごとの設定差異を減らし、k8sデプロイやリポジトリ分割時の移行を容易にする
```

---

## 2. 受入条件（Acceptance Criteria）

### 機能1: docker-compose三分割

| ID | Given | When | Then |
|---|---|---|---|
| AC1.1 | docker-compose.platform.ymlが存在する | `docker compose -f docker-compose.platform.yml up` を実行 | valkey, jobqueue, myscheduler, myvault, langfuse群が正常起動する |
| AC1.2 | docker-compose.agent.ymlが存在する | `docker compose -f docker-compose.agent.yml up` を実行 | expertagent, graphaiserverが正常起動する |
| AC1.3 | docker-compose.frontend.ymlが存在する | `docker compose -f docker-compose.frontend.yml up` を実行 | commonui, myagentdeskが正常起動する |
| AC1.4 | 3つのcomposeファイルが存在する | 統合起動コマンドを実行 | 3レイヤすべてが立ち上がり依存関係に問題がない |
| AC1.5 | README.mdを確認する | composeファイルの説明を探す | どのcomposeが何を起動するか記載されている |

### 機能2: ローカル実行モード

| ID | Given | When | Then |
|---|---|---|---|
| AC2.1 | Makefile/justfileが存在する | `make dev-platform` を実行 | 運用基盤レイヤがエラーなく起動する |
| AC2.2 | platform層が起動済み | `make dev-agent` を実行 | エージェント層がエラーなく起動する |
| AC2.3 | platform+agent層が起動済み | `make dev-frontend` を実行 | フロントエンド層がエラーなく起動する |
| AC2.4 | サービスが未起動 | `make dev-all` を実行 | 3レイヤすべてが一括起動する |
| AC2.5 | README.mdを確認する | コマンド説明を探す | 各コマンドの責務と使用例が記載されている |

### 機能3: サービス間URL/ポート統一管理

| ID | Given | When | Then |
|---|---|---|---|
| AC3.1 | .env.exampleが存在する | ファイルをコピーする | ローカル開発に必要なURL/ポート設定が揃う |
| AC3.2 | 各サービスのソースコード | URL設定箇所を確認する | ハードコーディングされたローカルURLが存在しない |
| AC3.3 | レイヤを個別に起動する | サービス間通信を行う | 問題なく通信できる |

---

## 3. 機能要件

### 3.1 必須機能（Must Have）

#### docker-compose分割

| 機能ID | 機能名 | 説明 | 優先度 |
|--------|--------|------|--------|
| F1.1 | docker-compose.platform.yml | 運用基盤層の定義ファイル作成 | P0 |
| F1.2 | docker-compose.agent.yml | AIエージェント層の定義ファイル作成 | P0 |
| F1.3 | docker-compose.frontend.yml | フロントエンド層の定義ファイル作成 | P0 |
| F1.4 | 共有ネットワーク設定 | `myswiftagent-net`を3つのcomposeで共有 | P0 |
| F1.5 | レイヤ構成ドキュメント | サービス⇔レイヤ対応表を作成 | P0 |

**サービス⇔レイヤ対応表（設計案）**

| レイヤ | docker-compose | サービス | ホストポート |
|--------|----------------|---------|-------------|
| **Platform** | platform.yml | valkey | 6381 |
| | | jobqueue | 8001 |
| | | myscheduler | 8002 |
| | | myvault | 8003 |
| | | langfuse-db | 5433 |
| | | langfuse-clickhouse | 8123, 9000 |
| | | langfuse-redis | 6380 |
| | | langfuse-minio | 9002, 9001 |
| | | langfuse-worker | 3030 |
| | | langfuse-server | 3001 |
| **Agent** | agent.yml | expertagent | 8004 |
| | | graphaiserver | 8005 |
| **Frontend** | frontend.yml | commonui | 8501 |
| | | myagentdesk | 5173 (dev) |

#### Makefile/justfile作成

| 機能ID | 機能名 | 説明 | 優先度 |
|--------|--------|------|--------|
| F2.1 | make dev-platform | platform層を起動 | P0 |
| F2.2 | make dev-agent | agent層を起動（platform前提） | P0 |
| F2.3 | make dev-frontend | frontend層を起動（platform+agent前提） | P0 |
| F2.4 | make dev-all | 全レイヤ一括起動 | P0 |
| F2.5 | make down | 全サービス停止 | P0 |
| F2.6 | make logs | 全サービスログ表示 | P1 |

#### ENV統一管理

| 機能ID | 機能名 | 説明 | 優先度 |
|--------|--------|------|--------|
| F3.1 | .env.example更新 | レイヤ別URL/ポート変数を追加 | P0 |
| F3.2 | ハードコーディング除去 | 全サービスのURL設定をENV参照に変更 | P0 |
| F3.3 | ENVドキュメント更新 | 主要ENV変数の説明をREADMEに追記 | P1 |

### 3.2 あると良い機能（Nice to Have）

| 機能ID | 機能名 | 説明 | 優先度 |
|--------|--------|------|--------|
| F4.1 | make status | 全サービスヘルスチェック | P2 |
| F4.2 | make rebuild-{layer} | レイヤ別再ビルド | P2 |
| F4.3 | docker-compose.override.yml | 開発者別オーバーライド対応 | P2 |
| F4.4 | VSCode Remote Containers対応 | devcontainer.json作成 | P3 |

### 3.3 将来的な拡張（Future Enhancement）

| 機能ID | 機能名 | 説明 |
|--------|--------|------|
| F5.1 | Kubernetes Helm Charts | k8s環境へのレイヤ別デプロイ |
| F5.2 | リポジトリ分割対応 | git submodule/マルチレポ構成への移行 |
| F5.3 | CI/CDパイプライン分割 | レイヤ別テスト・デプロイフロー |

---

## 4. 非機能要件

### 4.1 パフォーマンス要件

| 要件ID | カテゴリ | 要件 | 目標値 |
|--------|---------|------|--------|
| NF1.1 | 起動時間 | make dev-platform の起動完了 | 60秒以内 |
| NF1.2 | 起動時間 | make dev-all の全サービス起動完了 | 180秒以内 |
| NF1.3 | リソース | 全サービス起動時のメモリ使用量 | 8GB以内 |

### 4.2 保守性要件

| 要件ID | カテゴリ | 要件 |
|--------|---------|------|
| NF2.1 | 可読性 | 各docker-composeファイルにサービス説明コメント |
| NF2.2 | 一貫性 | 命名規則の統一（サービス名、ネットワーク名、ボリューム名） |
| NF2.3 | ドキュメント | READMEに「よく使う開発パターン」セクション追加 |

### 4.3 互換性要件

| 要件ID | カテゴリ | 要件 |
|--------|---------|------|
| NF3.1 | Docker | Docker Compose v2.20+対応 |
| NF3.2 | OS | macOS, Linux, Windows WSL2対応 |
| NF3.3 | 既存構成 | 現在のdocker-compose.ymlからの移行パス提供 |

---

## 5. 技術的制約

### 5.1 使用する技術スタック

| カテゴリ | 技術 | バージョン |
|---------|------|-----------|
| コンテナ | Docker Compose | v2.20+ |
| ビルドツール | GNU Make または just | Make 3.81+ / just 1.0+ |
| シェル | Bash | 4.0+ |

### 5.2 既存システムとの連携

| 連携先 | 内容 | 影響 |
|--------|------|------|
| 現行docker-compose.yml | 分割元ファイル | 機能統合・置き換え |
| scripts/unified-start.sh | 既存起動スクリプト | Makefileと共存/置き換え検討 |
| .env.docker | Docker用環境変数 | 継続使用 |
| CI/CD (GitHub Actions) | 自動テスト・デプロイ | compose参照パス更新が必要 |

### 5.3 設計判断が必要な項目

| 項目 | 選択肢 | 推奨 | 理由 |
|------|--------|------|------|
| ビルドツール | Make vs just | Make | OS標準、学習コスト低 |
| ネットワーク定義場所 | 各compose内 vs 別ファイル | 各compose内 (external: true) | 単体起動可能にするため |
| langfuse群の配置 | platform vs 別レイヤ | platform | 運用観点で一括管理 |
| myagentdesk | Dockerビルド vs ローカルdev | 両方対応 | 開発効率と本番一致 |

---

## 6. リスクと対策

### 6.1 技術的リスク

| リスクID | リスク内容 | 影響度 | 発生確率 | 対策 |
|----------|-----------|--------|----------|------|
| R1 | 依存関係の複雑化 | 中 | 中 | depends_onとhealthcheckの明示的設定 |
| R2 | ネットワーク分離による通信障害 | 高 | 低 | 共有ネットワーク(external)の使用 |
| R3 | 環境変数の設定漏れ | 中 | 中 | .env.exampleの完備と起動時バリデーション |
| R4 | CI/CDパイプラインの破損 | 高 | 中 | 段階的移行とテスト強化 |

### 6.2 ビジネスリスク

| リスクID | リスク内容 | 影響度 | 発生確率 | 対策 |
|----------|-----------|--------|----------|------|
| R5 | 開発者の学習コスト | 低 | 中 | 詳細なドキュメントとサンプル提供 |
| R6 | 移行期間中の開発停滞 | 中 | 低 | 既存構成との並行運用期間設定 |

---

## 7. 実装タスク（参考）

### Phase 1: docker-compose分割
- [ ] レイヤ構成図・対応表の作成
- [ ] docker-compose.platform.yml 作成
- [ ] docker-compose.agent.yml 作成
- [ ] docker-compose.frontend.yml 作成
- [ ] 共有ネットワーク設定
- [ ] 各composeの単体起動テスト

### Phase 2: Makefile作成
- [ ] Makefile作成（dev-platform, dev-agent, dev-frontend, dev-all, down）
- [ ] ヘルパーターゲット追加（logs, status）
- [ ] バックグラウンド/フォアグラウンド切り替え対応

### Phase 3: ENV統一管理
- [ ] .env.example更新
- [ ] 各サービスのハードコーディングURL調査・修正
- [ ] 動作確認（全パターン）

### Phase 4: ドキュメント
- [ ] README.md更新（レイヤ説明、コマンド一覧、開発パターン例）
- [ ] CI/CDの更新（必要に応じて）

---

## 8. 見積もり前提

**この要件定義書は実装の詳細見積もりには使用しません。**
具体的な作業時間やスケジュールは、別途作業計画書（work-plan.md）で策定してください。

---

## 9. 関連ドキュメント

| ドキュメント | パス | 内容 |
|-------------|------|------|
| サービス依存関係 | docs/arch/service-dependencies.md | 現状のサービス構成・通信フロー |
| 環境変数設計 | docs/design/environment-variables.md | ENV設計方針 |
| 品質基準 | docs/claude/04-quality-standards.md | テスト・静的解析要件 |
| デプロイガイド | docs/ops/deployment-guide.md | 現行デプロイ手順 |

---

**作成者**: Claude Code
**レビュー待ち**: Yes
