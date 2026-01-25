# 要件定義書: ３層構造の組み換え (Issue #316)

## 現状調査サマリ

### 対象プロジェクト
- **プロジェクト名**: MySwiftAgent (インフラストラクチャ/Docker構成)
- **関連モジュール**:
  - `docker-compose.platform.yml`
  - `docker-compose.agent.yml`
  - `docker-compose.frontend.yml`
  - `scripts/dev-hybrid.sh`
  - `docs/arch/service-dependencies.md`

### 現在のDocker Compose層構造

| 層 | ファイル | 含まれるサービス |
|---|----------|-----------------|
| **Platform** | `docker-compose.platform.yml` | valkey, **jobqueue**, **myscheduler**, myvault, langfuse-* |
| **Agent** | `docker-compose.agent.yml` | expertagent, graphaiserver |
| **Frontend** | `docker-compose.frontend.yml` | commonui, myagentdesk |

### 変更後のDocker Compose層構造

| 層 | ファイル | 含まれるサービス |
|---|----------|-----------------|
| **Platform** | `docker-compose.platform.yml` | valkey, myvault, langfuse-* |
| **Agent** | `docker-compose.agent.yml` | **jobqueue**, **myscheduler**, expertagent, graphaiserver |
| **Frontend** | `docker-compose.frontend.yml` | commonui, myagentdesk |

### 使用されている設計パターン
- **外部ネットワーク共有**: 全層で `myswiftagent-network` を共有
- **層間依存**: `depends_on` と `service_healthy` 条件による起動順序制御
- **ヘルスチェック**: 各サービスに `/health` エンドポイント実装

### 参照したドキュメント
- `docs/arch/service-dependencies.md`: サービス依存関係マトリクス
- `docs/design/architecture-overview.md`: アーキテクチャ概要
- `scripts/dev-hybrid.sh`: ハイブリッド開発環境スクリプト

### 制約事項
- 全サービスは同一外部ネットワーク（`myswiftagent-network`）を使用
- `dev-hybrid.sh` はPlatform=Docker、Agent=ローカルの構成に依存
- myschedulerはjobqueueに依存（`service_healthy` 条件）

---

## ユーザーストーリー

```
As a 開発者/運用者
I want to スケジューラ（myscheduler）とジョブ管理（jobqueue）をAgent層に配置する
So that サービス間のネットワーク接続問題を解消し、より安定したサービス間通信を実現できる
```

---

## 受入条件（Acceptance Criteria）

### AC1: Docker Compose層構造の変更
- **Given**: 現在のdocker-compose.platform.ymlにjobqueueとmyschedulerが含まれている
- **When**: 層構造の組み換えを実施する
- **Then**: jobqueueとmyschedulerがdocker-compose.agent.ymlに移動し、docker-compose.platform.ymlから削除されている

### AC2: サービス間依存関係の維持
- **Given**: myschedulerはjobqueueに依存している
- **When**: Agent層内で両サービスが起動される
- **Then**: myschedulerはjobqueueの`service_healthy`条件を満たしてから起動する

### AC3: Platform層からAgent層への依存関係
- **Given**: Agent層のexpertagent/graphaiserverはmyvaultに依存している
- **When**: 全サービスを起動する
- **Then**: Platform層（myvault, valkey, langfuse）が先に起動し、Agent層（jobqueue, myscheduler, expertagent, graphaiserver）が後から起動する

### AC4: ネットワーク接続の正常動作
- **Given**: 全サービスが`myswiftagent-network`に接続している
- **When**: expertagentからjobqueueへAPI呼び出しを行う
- **Then**: `http://jobqueue:8000`で正常に通信できる

### AC5: ヘルスチェックの正常動作
- **Given**: 全サービスがヘルスチェック設定を持つ
- **When**: `docker compose up -d`で全サービスを起動する
- **Then**: 全サービスが`healthy`状態になる

### AC6: dev-hybrid.shの互換性維持
- **Given**: dev-hybrid.shはPlatform=Docker、Agent=ローカルで動作する
- **When**: 層構造変更後にdev-hybrid.shを実行する
- **Then**: jobqueueとmyschedulerがローカルプロセスとして起動し、他サービスと正常に通信できる

### AC7: Makefile更新
- **Given**: Makefileに`dev-platform`、`dev-agent`、`dev-frontend`ターゲットがある
- **When**: 層構造変更後に各ターゲットを実行する
- **Then**: 新しい層構造に従ってサービスが起動する

### AC8: ドキュメント更新
- **Given**: `docs/arch/service-dependencies.md`に現在の層構造が記載されている
- **When**: 層構造変更を完了する
- **Then**: ドキュメントが新しい層構造を反映している

---

## 機能要件

### 必須機能（Must Have）

| ID | 要件 | 詳細 |
|----|------|------|
| F1 | docker-compose.platform.yml からjobqueue/myscheduler削除 | サービス定義とdepends_on設定を削除 |
| F2 | docker-compose.agent.yml にjobqueue/myscheduler追加 | 既存の設定をコピーし、適切なdepends_on設定を追加 |
| F3 | Platform→Agent間の依存関係設定 | Agent層サービスがPlatform層の健全性を確認してから起動 |
| F4 | dev-hybrid.sh の更新 | Platform層起動時にjobqueue/myschedulerを含めない、Agent層でローカル起動に含める |
| F5 | Makefile の更新 | `dev-platform`と`dev-agent`のターゲット定義を更新 |

### あると良い機能（Nice to Have）

| ID | 要件 | 詳細 |
|----|------|------|
| N1 | 起動順序の最適化 | jobqueue → myscheduler → expertagent/graphaiserverの順序を明示化 |
| N2 | ヘルスチェックタイムアウトの調整 | 層間依存による起動遅延を考慮した設定 |
| N3 | ログ出力の統一 | 新層構造に対応したログ管理 |

### 将来的な拡張（Future Enhancement）

| ID | 要件 | 詳細 |
|----|------|------|
| E1 | サービスディスカバリ導入 | 動的なサービス検出機構の導入検討 |
| E2 | リトライ戦略の強化 | 指数バックオフの導入 |

---

## 非機能要件

### パフォーマンス要件
- 層構造変更後も起動時間は現行と同等（全サービス起動: 2分以内）
- サービス間通信のレイテンシは変更前後で同等

### セキュリティ要件
- 認証トークン（`X-API-Token`, `X-Service`, `X-Token`）の設定は変更なし
- ネットワーク分離は維持（外部ネットワーク経由の通信）

### ユーザビリティ要件
- 既存の起動コマンド（`make dev-all`, `docker compose up -d`）の互換性維持
- エラーメッセージの明確化（層構造に関する問題のデバッグ支援）

### 互換性要件
- 既存のAPI呼び出しパターン（URL構造）は変更なし
- 環境変数設定は変更なし（`JOBQUEUE_API_URL`等）

---

## 技術的制約

### 使用する技術スタック
- **Docker Compose**: v2.x（includeディレクティブ使用）
- **ネットワーク**: 外部ネットワーク（`myswiftagent-network`）
- **シェルスクリプト**: bash

### 既存システムとの連携
- jobqueue → myscheduler 依存関係は維持
- expertagent → jobqueue, myvault 依存関係は維持
- graphaiserver → myvault, jobqueue, myscheduler 依存関係は維持

### データ形式・API仕様
- 変更なし（既存のREST API仕様を維持）

---

## リスクと対策

### 技術的リスク

| リスク | 影響度 | 発生可能性 | 対策 |
|--------|-------|-----------|------|
| 起動順序の問題 | 高 | 中 | depends_onの`service_healthy`条件を厳密に設定 |
| ネットワーク接続エラー | 高 | 低 | ヘルスチェックの待機時間を十分に確保 |
| dev-hybrid.sh の互換性問題 | 中 | 中 | 変更前後のテストを実施 |
| ドキュメントとの乖離 | 低 | 高 | 変更完了後に即座にドキュメント更新 |

### ビジネスリスク

| リスク | 影響度 | 発生可能性 | 対策 |
|--------|-------|-----------|------|
| 開発環境の一時的な不安定化 | 中 | 中 | 段階的な移行（jobqueue先行、myscheduler後続） |
| 既存の運用手順との乖離 | 低 | 中 | 変更内容の事前共有とドキュメント更新 |

---

## 実装タスク（概要）

1. **docker-compose.platform.yml の変更**
   - jobqueue サービス定義の削除
   - myscheduler サービス定義の削除

2. **docker-compose.agent.yml の変更**
   - jobqueue サービス定義の追加（先頭に配置）
   - myscheduler サービス定義の追加（jobqueue依存）
   - expertagent/graphaiserverのdepends_on更新（myvault + jobqueue）

3. **scripts/dev-hybrid.sh の更新**
   - Platform層起動関数からjobqueue/myscheduler削除
   - Agent層起動関数にjobqueue/myscheduler追加
   - 起動順序の調整

4. **Makefile の更新**
   - `dev-platform`ターゲットの更新
   - `dev-agent`ターゲットの更新

5. **ドキュメント更新**
   - `docs/arch/service-dependencies.md`
   - `docs/design/architecture-overview.md`

6. **テスト**
   - `docker compose up -d` での全サービス起動確認
   - `make dev-platform && make dev-agent` での層別起動確認
   - `./scripts/dev-hybrid.sh start` でのハイブリッド起動確認
   - サービス間通信の確認（expertagent → jobqueue）

---

## 参照ドキュメント

| ドキュメント | パス | 関連内容 |
|-------------|------|---------|
| サービス依存関係 | `docs/arch/service-dependencies.md` | 依存関係マトリクス、起動順序 |
| アーキテクチャ概要 | `docs/design/architecture-overview.md` | システム構成図、ネットワーク構成 |
| Docker Compose設定 | `docker-compose.yml`, `docker-compose.*.yml` | サービス定義 |
| ハイブリッド開発スクリプト | `scripts/dev-hybrid.sh` | 開発環境起動 |
| ローカル開発ガイド | `docs/ops/local-development.md` | 起動方法比較 |

---

**作成日**: 2025-12-28
**Issue**: [#316](https://github.com/kewton/MySwiftAgent/issues/316)
**ステータス**: ドラフト
