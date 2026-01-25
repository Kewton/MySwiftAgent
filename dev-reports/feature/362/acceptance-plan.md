# 受入テスト計画書

**Issue**: #362
**作成日**: 2025-01-15
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #362
- **タイトル**: feat(mySwiftAgentCore): 新規TypeScriptプロジェクトの作成
- **プロジェクト**: mySwiftAgentCore（新規）
- **種別**: 新規プロジェクト作成（基盤構築）

### 参照ドキュメント
- Issue: #362
- 設計方針書: `dev-reports/feature/issue/362/design-policy.md`
- サービス依存関係: `docs/arch/service-dependencies.md`

### テスト対象範囲
本Issueは新規TypeScriptプロジェクトの**プロジェクト構造・基盤構築**が対象であり、以下の子Issueで個別機能が実装される：

| 子Issue | コンポーネント | 概要 |
|---------|--------------|------|
| #363 | taskflowEngine | TaskFlow実行エンジン |
| #364 | taskflowGeneratorAgent | ワークフロー生成エージェント |
| #365 | capabilityManagement | Capability一元管理システム |

本計画書では **Issue #362（プロジェクト構造・基盤）** の受入テストに焦点を当てる。

---

## 2. 単体テスト結果レビュー

### 状況
新規プロジェクト作成のため、実装前の段階でありTDD結果は存在しない。

### 単体テスト計画

プロジェクト構造確立後に以下のテストが必要：

| テストカテゴリ | ファイル | カバレッジ目標 |
|--------------|---------|---------------|
| Shared Components | `tests/unit/shared/` | 90%+ |
| API Layer | `tests/unit/api/` | 90%+ |
| Configuration | `tests/unit/config/` | 90%+ |

### 受入テスト前提条件
- [ ] Vitestテスト環境が設定されている
- [ ] `npm test` または `bun test` でテストが実行できる
- [ ] 単体テストカバレッジ90%以上

---

## 3. 受入条件分析

### AC-1: プロジェクト構造が作成されている
- **原文**: プロジェクト構造が作成されている
- **分類**: 機能要件
- **テスト方法**: ファイルシステム確認 + コード解析
- **検証ポイント**:
  1. `mySwiftAgentCore/` ディレクトリが存在する
  2. 設計方針書のディレクトリ構造に準拠している
  3. 以下のディレクトリが存在する：
     - `src/taskflowEngine/`
     - `src/taskflowGeneratorAgent/`
     - `src/capabilityManagement/`
     - `src/shared/`
     - `tests/`
     - `config/`

### AC-2: package.json, tsconfig.jsonが設定されている
- **原文**: package.json, tsconfig.jsonが設定されている
- **分類**: 機能要件
- **テスト方法**: ファイル内容検証 + npm/bun実行
- **検証ポイント**:
  1. `package.json` が有効なJSONである
  2. 必要な依存関係が含まれている（Hono, Zod, Vitest等）
  3. `tsconfig.json` が有効である
  4. TypeScriptコンパイルが成功する

### AC-3: ESLint, Prettierが設定されている
- **原文**: ESLint, Prettierが設定されている
- **分類**: 機能要件
- **テスト方法**: Lint/Format実行
- **検証ポイント**:
  1. `.eslintrc.*` または `eslint.config.*` が存在する
  2. `.prettierrc.*` が存在する
  3. `npm run lint` が成功する
  4. `npm run format` が成功する

### AC-4: 基本的なAPIエンドポイントが動作する
- **原文**: 基本的なAPIエンドポイントが動作する
- **分類**: 機能要件
- **テスト方法**: E2E API呼び出し（curl/pytest）
- **モック使用**: 不可
- **検証ポイント**:
  1. サービスが起動する
  2. ルートエンドポイントにアクセスできる
  3. 404エラーが適切に返される

### AC-5: ヘルスチェックエンドポイント /health が動作する
- **原文**: ヘルスチェックエンドポイント `/health` が動作する
- **分類**: 機能要件
- **テスト方法**: E2E API呼び出し（curl）
- **モック使用**: 不可
- **検証ポイント**:
  1. `GET /health` が200を返す
  2. レスポンスに `status: "ok"` が含まれる
  3. レスポンスにサービス名・バージョンが含まれる

### AC-6: Langfuseトレースが記録される
- **原文**: Langfuseトレースが記録される
- **分類**: 非機能要件
- **テスト方法**: E2E + Langfuse UI確認
- **モック使用**: 一部可（Langfuse接続不可時）
- **検証ポイント**:
  1. Langfuseクライアントが初期化される
  2. API呼び出し時にトレースが送信される
  3. Langfuse UIでトレースが確認できる

### AC-7: docker-compose.core.ymlが作成されている
- **原文**: docker-compose.core.ymlが作成されている
- **分類**: 機能要件
- **テスト方法**: Docker Compose検証
- **検証ポイント**:
  1. `docker-compose.core.yml` が存在する
  2. `docker compose -f docker-compose.core.yml config` が成功する
  3. サービス定義が正しい

### AC-8: docker-compose.ymlにincludeされている
- **原文**: docker-compose.ymlにincludeされている
- **分類**: 機能要件
- **テスト方法**: Docker Compose検証
- **検証ポイント**:
  1. `docker-compose.yml` に `docker-compose.core.yml` がincludeされている
  2. `docker compose config` で全体構成が確認できる

### AC-9: make dev-coreでサービスが起動する
- **原文**: `make dev-core` でサービスが起動する
- **分類**: 機能要件
- **テスト方法**: Makefile実行 + ヘルスチェック
- **検証ポイント**:
  1. `make dev-core` が成功する
  2. ヘルスチェックが通る
  3. ログにエラーがない

### AC-10: make dev-allに組み込まれている
- **原文**: `make dev-all` に組み込まれている
- **分類**: 機能要件
- **テスト方法**: Makefile確認 + 実行
- **検証ポイント**:
  1. Makefileに `dev-all` ターゲットがCoreを含む
  2. `make dev-all` でCoreサービスが起動する

### AC-11: dev-hybrid.shでローカル起動できる
- **原文**: dev-hybrid.shでローカル起動できる
- **分類**: 機能要件
- **テスト方法**: スクリプト実行
- **検証ポイント**:
  1. `./scripts/dev-hybrid.sh` でmySwiftAgentCoreが起動する
  2. 環境変数が正しく設定される
  3. ヘルスチェックが通る

### AC-12: health-check.shでヘルスチェックできる
- **原文**: health-check.shでヘルスチェックできる
- **分類**: 機能要件
- **テスト方法**: スクリプト実行
- **検証ポイント**:
  1. `./scripts/health-check.sh` でmySwiftAgentCoreのステータスが表示される
  2. 起動中・停止中の状態が正しく判定される

### AC-13: .env.exampleに環境変数が追加されている
- **原文**: .env.exampleに環境変数が追加されている
- **分類**: 機能要件
- **テスト方法**: ファイル内容確認
- **検証ポイント**:
  1. `.env.example` にmySwiftAgentCore関連の変数が存在する
  2. design-policy.md Section 8.3の環境変数がすべて含まれる

### AC-14: GitHub Actionsワークフローが設定されている
- **原文**: GitHub Actionsワークフローが設定されている
- **分類**: 機能要件
- **テスト方法**: YAMLファイル確認 + ローカル実行（act）
- **検証ポイント**:
  1. `.github/workflows/` に該当ワークフローが存在する
  2. ワークフロー構文が有効である

### AC-15: Dockerイメージがビルドできる
- **原文**: Dockerイメージがビルドできる
- **分類**: 機能要件
- **テスト方法**: Docker build実行
- **検証ポイント**:
  1. `docker build -t myswiftagentcore:test ./mySwiftAgentCore` が成功する
  2. イメージサイズが妥当である（< 500MB）

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: 3.1 システム構成図に示されたレイヤー構成
- **検証方法**: コード構造確認
- **テスト項目**:
  1. API層（Hono Router）が存在する
  2. Core Services層（TFE, TFG, CM）のディレクトリが存在する
  3. Shared Components層が存在する

### DP-2: 技術選定整合性
- **設計方針**: 4.1 選定技術（TypeScript, Bun/Node.js, Hono, Zod, Vitest）
- **検証方法**: package.json確認 + 実行テスト
- **テスト項目**:
  1. TypeScript 5.x が使用されている
  2. Hono が依存関係に含まれている
  3. Zod が依存関係に含まれている
  4. Vitest が devDependencies に含まれている
  5. Bun または Node.js で起動できる

### DP-3: Context Manager責務分割整合性
- **設計方針**: 3.4 Context Manager責務分割設計
- **検証方法**: コード構造確認
- **テスト項目**:
  1. `src/shared/context/ExecutionContext.ts` が存在する
  2. `src/shared/context/VariableResolver.ts` が存在する
  3. `src/shared/context/SecretManager.ts` が存在する
  4. `src/shared/context/ValidationCoordinator.ts` が存在する

### DP-4: セキュリティ設計整合性
- **設計方針**: 8.3 デフォルトセキュリティ設定
- **検証方法**: コード確認 + 起動時チェック
- **テスト項目**:
  1. 起動時にセキュリティ設定検証が実行される
  2. 必須環境変数が欠落した場合にエラー終了する
  3. SECURITY_DEFAULTS 定数が実装されている

### DP-5: 部分成功モデル整合性
- **設計方針**: 6.3 部分成功モデル（実行結果の詳細定義）
- **検証方法**: 型定義確認
- **テスト項目**:
  1. `WorkflowExecutionResult` 型が定義されている
  2. `status` が `'success' | 'partial_success' | 'failed'` である
  3. `StepError` 型が定義されている
  4. `RecoveryAction` 型が定義されている

### DP-6: API設計整合性
- **設計方針**: 7.1 エンドポイント設計
- **検証方法**: API呼び出しテスト
- **テスト項目**:
  1. `/api/v2/workflows/*` パスが存在する（スタブでも可）
  2. `/api/v1/generator/*` パスが存在する（スタブでも可）
  3. `/api/v1/capabilities/*` パスが存在する（スタブでも可）
  4. エラーレスポンス形式が設計通りである

---

## 5. デッドコード検証計画

### 概要
Issue #362は新規プロジェクト作成であり、既存コードの移植は子Issueで行われる。本Issueではデッドコード検証の対象は限定的。

### F-1: Shared Components使用確認
- **ファイル**: `src/shared/**/*.ts`
- **種別**: module
- **期待される呼び出し元**: `src/taskflowEngine/`, `src/taskflowGeneratorAgent/`, `src/capabilityManagement/`
- **検証方法**:
  ```bash
  # 各shared moduleがCore Servicesから参照されているか確認
  grep -rn "from.*shared" src/taskflowEngine/ src/taskflowGeneratorAgent/ src/capabilityManagement/
  ```
- **E2Eでの確認方法**: API呼び出し時にトレースが記録されることで、Tracer.tsが使用されていることを確認

### F-2: Context Manager統合確認
- **ファイル**: `src/shared/context/ExecutionContext.ts`
- **種別**: class
- **期待される呼び出し元**: `WorkflowExecutor`, `WorkflowGenerator`
- **検証方法**:
  ```bash
  grep -rn "ExecutionContext" src/ --include="*.ts" | grep -v "ExecutionContext.ts"
  ```
- **E2Eでの確認方法**: ワークフロー実行時に変数解決が機能することを確認（子Issue #363で検証）

### F-3: Zodスキーマ使用確認
- **ファイル**: `src/shared/validation/schemas.ts`
- **種別**: constants
- **期待される呼び出し元**: バリデーター、API層
- **検証方法**:
  ```bash
  grep -rn "schemas" src/ --include="*.ts" | grep -v "schemas.ts"
  ```
- **E2Eでの確認方法**: 不正なリクエストを送信し、バリデーションエラーが返ることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック | 必須 |
|---------|-----|--------------|------|
| mySwiftAgentCore | http://localhost:8006 | GET /health | ✅ |
| Langfuse | http://localhost:3001 | GET /api/public/health | ❌（トレース検証時） |
| myVault | http://localhost:8003 | GET /health | ❌（シークレット検証時） |

### 起動コマンド

#### ローカル開発（推奨）
```bash
# mySwiftAgentCoreのみ起動
cd mySwiftAgentCore
bun run dev
# または
npm run dev
```

#### ハイブリッドモード
```bash
# Platform=Docker, Core=ローカル
./scripts/dev-hybrid.sh
```

#### Docker全環境
```bash
make dev-core
# または
docker compose -f docker-compose.core.yml up -d
```

### 環境変数
| 変数名 | 説明 | 必須 | デフォルト |
|--------|------|------|----------|
| NODE_ENV | 実行環境 | ❌ | development |
| PORT | サービスポート | ❌ | 8006 |
| API_TOKEN | サービス間認証トークン | ✅ | なし |
| ADMIN_TOKEN | 管理API認証トークン | ✅ | なし |
| MYVAULT_SERVICE_TOKEN | MyVault連携トークン | ✅ | なし |
| LANGFUSE_PUBLIC_KEY | Langfuse公開キー | ❌ | なし |
| LANGFUSE_SECRET_KEY | Langfuse秘密キー | ❌ | なし |

### テストデータ
- 特別なテストデータは不要
- 環境変数の設定で動作確認可能

---

## 7. テスト項目

### TC-001: プロジェクトディレクトリ構造確認
- **テスト観点**: プロジェクト構造が設計通りに作成されているか
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 構造検証
- **テスト方法**: Bash + tree/ls
- **前提条件**:
  1. `mySwiftAgentCore/` ディレクトリが存在する
- **テスト手順**:
  1. ディレクトリ構造を確認する
  2. 必須ディレクトリの存在を確認する
- **期待結果**:
  - 以下のディレクトリが存在する：
    - `src/taskflowEngine/`
    - `src/taskflowGeneratorAgent/`
    - `src/capabilityManagement/`
    - `src/shared/`
    - `tests/`
    - `config/`
- **コマンド**:
  ```bash
  ls -la mySwiftAgentCore/
  ls -la mySwiftAgentCore/src/
  ```
- **pytestメソッド**: `test_tc_001_project_structure`

### TC-002: package.json検証
- **テスト観点**: package.jsonが有効で必要な依存関係を含むか
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 構造検証
- **テスト方法**: jq + npm
- **前提条件**:
  1. `mySwiftAgentCore/package.json` が存在する
- **テスト手順**:
  1. package.jsonをパースする
  2. 依存関係を確認する
  3. npm install を実行する
- **期待結果**:
  - dependencies に `hono`, `zod` が含まれる
  - devDependencies に `vitest`, `typescript` が含まれる
  - `npm install` が成功する
- **コマンド**:
  ```bash
  cat mySwiftAgentCore/package.json | jq '.dependencies | keys'
  cat mySwiftAgentCore/package.json | jq '.devDependencies | keys'
  cd mySwiftAgentCore && npm install
  ```
- **pytestメソッド**: `test_tc_002_package_json`

### TC-003: TypeScriptコンパイル検証
- **テスト観点**: TypeScriptが正常にコンパイルできるか
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: ビルド検証
- **テスト方法**: npm run build
- **前提条件**:
  1. 依存関係がインストール済み
- **テスト手順**:
  1. `npm run build` を実行する
  2. 出力ディレクトリを確認する
- **期待結果**:
  - ビルドが成功する
  - `dist/` ディレクトリが作成される
  - エラーがない
- **コマンド**:
  ```bash
  cd mySwiftAgentCore && npm run build
  ls -la mySwiftAgentCore/dist/
  ```
- **pytestメソッド**: `test_tc_003_typescript_compile`

### TC-004: ESLint実行
- **テスト観点**: ESLintが設定されており、コードが基準を満たすか
- **関連する受入条件**: AC-3
- **関連する設計方針**: -
- **テスト種別**: 静的解析
- **テスト方法**: npm run lint
- **前提条件**:
  1. 依存関係がインストール済み
- **テスト手順**:
  1. ESLint設定ファイルの存在確認
  2. `npm run lint` を実行する
- **期待結果**:
  - ESLint設定ファイルが存在する
  - Lintが成功する（エラー0件）
- **コマンド**:
  ```bash
  ls mySwiftAgentCore/eslint.config.* || ls mySwiftAgentCore/.eslintrc.*
  cd mySwiftAgentCore && npm run lint
  ```
- **pytestメソッド**: `test_tc_004_eslint`

### TC-005: Prettier実行
- **テスト観点**: Prettierが設定されており、フォーマットが統一されているか
- **関連する受入条件**: AC-3
- **関連する設計方針**: -
- **テスト種別**: 静的解析
- **テスト方法**: npm run format:check
- **前提条件**:
  1. 依存関係がインストール済み
- **テスト手順**:
  1. Prettier設定ファイルの存在確認
  2. `npm run format:check` を実行する
- **期待結果**:
  - `.prettierrc` または類似の設定ファイルが存在する
  - フォーマットチェックが成功する
- **コマンド**:
  ```bash
  ls mySwiftAgentCore/.prettierrc*
  cd mySwiftAgentCore && npm run format:check
  ```
- **pytestメソッド**: `test_tc_005_prettier`

### TC-006: サービス起動確認
- **テスト観点**: サービスが起動するか
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: npm run dev + curl
- **前提条件**:
  1. 依存関係がインストール済み
  2. 必須環境変数が設定済み
- **テスト手順**:
  1. 環境変数を設定する
  2. サービスを起動する
  3. ヘルスチェックを実行する
- **期待結果**:
  - サービスが起動する
  - ログにエラーがない
- **コマンド**:
  ```bash
  # 環境変数設定
  export API_TOKEN="test_token_32_characters_long__"
  export ADMIN_TOKEN="admin_token_32_characters_long_"
  export MYVAULT_SERVICE_TOKEN="vault_token_here"

  # 起動（バックグラウンド）
  cd mySwiftAgentCore && npm run dev &
  sleep 5

  # 確認
  curl -s http://localhost:8006/health
  ```
- **pytestメソッド**: `test_tc_006_service_startup`

### TC-007: ヘルスチェックエンドポイント
- **テスト観点**: `/health` エンドポイントが正しく動作するか
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-6
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. サービスが起動済み
- **テスト手順**:
  1. `GET /health` を呼び出す
  2. レスポンスを確認する
- **期待結果**:
  - HTTPステータス: 200
  - レスポンスに `status: "ok"` が含まれる
  - レスポンスにサービス名とバージョンが含まれる
- **curlコマンド**:
  ```bash
  curl -s -X GET http://localhost:8006/health | jq
  ```
- **期待レスポンス**:
  ```json
  {
    "status": "ok",
    "service": "mySwiftAgentCore",
    "version": "0.1.0",
    "timestamp": "2025-01-15T..."
  }
  ```
- **pytestメソッド**: `test_tc_007_health_endpoint`

### TC-008: 404エラーレスポンス
- **テスト観点**: 存在しないエンドポイントへのアクセスで適切なエラーが返るか
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-6
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. サービスが起動済み
- **テスト手順**:
  1. 存在しないパスにアクセスする
  2. エラーレスポンスを確認する
- **期待結果**:
  - HTTPステータス: 404
  - エラーレスポンス形式が設計通り
- **curlコマンド**:
  ```bash
  curl -s -w "\nHTTP_CODE:%{http_code}" -X GET http://localhost:8006/nonexistent
  ```
- **pytestメソッド**: `test_tc_008_404_error`

### TC-009: docker-compose.core.yml検証
- **テスト観点**: Docker Compose設定が有効か
- **関連する受入条件**: AC-7
- **関連する設計方針**: -
- **テスト種別**: 構造検証
- **テスト方法**: docker compose config
- **前提条件**:
  1. `docker-compose.core.yml` が存在する
- **テスト手順**:
  1. ファイルの存在確認
  2. 構文検証
- **期待結果**:
  - ファイルが存在する
  - 構文が有効である
  - `myswiftagentcore` サービスが定義されている
- **コマンド**:
  ```bash
  docker compose -f docker-compose.core.yml config
  ```
- **pytestメソッド**: `test_tc_009_docker_compose_core`

### TC-010: docker-compose.yml統合確認
- **テスト観点**: メインのdocker-compose.ymlにCoreが含まれるか
- **関連する受入条件**: AC-8
- **関連する設計方針**: -
- **テスト種別**: 構造検証
- **テスト方法**: grep + docker compose config
- **前提条件**:
  1. `docker-compose.yml` が存在する
- **テスト手順**:
  1. includeを確認する
  2. 全体構成を確認する
- **期待結果**:
  - `docker-compose.core.yml` がincludeされている
- **コマンド**:
  ```bash
  grep "docker-compose.core.yml" docker-compose.yml
  docker compose config --services | grep -i core
  ```
- **pytestメソッド**: `test_tc_010_docker_compose_include`

### TC-011: Dockerイメージビルド
- **テスト観点**: Dockerイメージが正常にビルドできるか
- **関連する受入条件**: AC-15
- **関連する設計方針**: -
- **テスト種別**: ビルド検証
- **テスト方法**: docker build
- **前提条件**:
  1. Dockerfileが存在する
- **テスト手順**:
  1. イメージをビルドする
  2. イメージサイズを確認する
- **期待結果**:
  - ビルドが成功する
  - イメージサイズが500MB未満
- **コマンド**:
  ```bash
  docker build -t myswiftagentcore:test ./mySwiftAgentCore
  docker images myswiftagentcore:test --format "{{.Size}}"
  ```
- **pytestメソッド**: `test_tc_011_docker_build`

### TC-012: make dev-core実行
- **テスト観点**: Makefileターゲットでサービスが起動するか
- **関連する受入条件**: AC-9
- **関連する設計方針**: -
- **テスト種別**: E2E
- **テスト方法**: make + curl
- **前提条件**:
  1. Makefileが更新済み
  2. docker-compose.core.ymlが存在する
- **テスト手順**:
  1. `make dev-core` を実行する
  2. ヘルスチェックを実行する
  3. `make down-core` で停止する
- **期待結果**:
  - サービスが起動する
  - ヘルスチェックが通る
- **コマンド**:
  ```bash
  make dev-core
  sleep 10
  curl -s http://localhost:8006/health
  make down-core
  ```
- **pytestメソッド**: `test_tc_012_make_dev_core`

### TC-013: .env.example確認
- **テスト観点**: 環境変数テンプレートが完備されているか
- **関連する受入条件**: AC-13
- **関連する設計方針**: DP-4
- **テスト種別**: 構造検証
- **テスト方法**: grep
- **前提条件**:
  1. `.env.example` が存在する
- **テスト手順**:
  1. 必須環境変数がすべて含まれているか確認する
- **期待結果**:
  - 以下の変数が含まれる：
    - `MYSWIFTAGENTCORE_PORT`
    - `API_TOKEN`
    - `ADMIN_TOKEN`
    - `MYVAULT_SERVICE_TOKEN`
    - `LANGFUSE_PUBLIC_KEY`
    - `LANGFUSE_SECRET_KEY`
- **コマンド**:
  ```bash
  grep -E "MYSWIFTAGENTCORE|API_TOKEN|ADMIN_TOKEN|MYVAULT_SERVICE_TOKEN|LANGFUSE" .env.example
  ```
- **pytestメソッド**: `test_tc_013_env_example`

### TC-014: GitHub Actions確認
- **テスト観点**: CI/CDワークフローが設定されているか
- **関連する受入条件**: AC-14
- **関連する設計方針**: -
- **テスト種別**: 構造検証
- **テスト方法**: ファイル確認 + YAML検証
- **前提条件**:
  1. `.github/workflows/` ディレクトリが存在する
- **テスト手順**:
  1. mySwiftAgentCore用のワークフローを確認する
  2. YAML構文を検証する
- **期待結果**:
  - mySwiftAgentCore関連のワークフローが存在する
  - 構文が有効である
- **コマンド**:
  ```bash
  ls .github/workflows/ | grep -i core
  # または全ワークフローを確認
  cat .github/workflows/*.yml | grep -A5 "mySwiftAgentCore\|myswiftagentcore"
  ```
- **pytestメソッド**: `test_tc_014_github_actions`

### TC-015: APIスタブエンドポイント確認
- **テスト観点**: 設計されたAPIパスがスタブとして存在するか
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-6
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. サービスが起動済み
- **テスト手順**:
  1. 各APIパスにアクセスする
  2. 501 Not Implemented または適切なレスポンスを確認する
- **期待結果**:
  - パスが存在する（404ではない）
  - スタブ実装またはエラーレスポンスが返る
- **curlコマンド**:
  ```bash
  # TaskFlow Engine
  curl -s -w "\nHTTP:%{http_code}" http://localhost:8006/api/v2/workflows/health

  # TaskFlow Generator
  curl -s -w "\nHTTP:%{http_code}" http://localhost:8006/api/v1/generator/health

  # Capability Management
  curl -s -w "\nHTTP:%{http_code}" http://localhost:8006/api/v1/capabilities/health
  ```
- **pytestメソッド**: `test_tc_015_api_stub_endpoints`

### TC-016: セキュリティ設定検証（起動時チェック）
- **テスト観点**: 起動時にセキュリティ設定が検証されるか
- **関連する受入条件**: -
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: 起動ログ確認
- **前提条件**:
  1. ソースコードが実装済み
- **テスト手順**:
  1. 必須環境変数を設定せずに起動する
  2. エラーメッセージを確認する
  3. 必須環境変数を設定して起動する
  4. 起動成功を確認する
- **期待結果**:
  - 必須環境変数なしで起動するとエラー終了する
  - エラーメッセージに具体的な変数名が含まれる
- **コマンド**:
  ```bash
  # 必須変数なしで起動（エラーになるはず）
  cd mySwiftAgentCore && unset API_TOKEN && npm run dev 2>&1 | head -20

  # 必須変数ありで起動
  export API_TOKEN="test_token_32_characters_long__"
  export ADMIN_TOKEN="admin_token_32_characters_long_"
  export MYVAULT_SERVICE_TOKEN="vault_token_here"
  cd mySwiftAgentCore && npm run dev &
  ```
- **pytestメソッド**: `test_tc_016_security_validation`

### TC-017: Context Manager型定義確認
- **テスト観点**: 設計方針の型定義がコードに存在するか
- **関連する受入条件**: -
- **関連する設計方針**: DP-3, DP-5
- **テスト種別**: 構造検証
- **テスト方法**: grep + TypeScriptコンパイル
- **前提条件**:
  1. `src/shared/` ディレクトリが実装済み
- **テスト手順**:
  1. 型定義ファイルの存在確認
  2. インターフェース定義の確認
- **期待結果**:
  - `IExecutionContext` インターフェースが存在する
  - `IVariableResolver` インターフェースが存在する
  - `ISecretManager` インターフェースが存在する
  - `WorkflowExecutionResult` 型が存在する
- **コマンド**:
  ```bash
  grep -rn "interface IExecutionContext" mySwiftAgentCore/src/
  grep -rn "interface IVariableResolver" mySwiftAgentCore/src/
  grep -rn "interface ISecretManager" mySwiftAgentCore/src/
  grep -rn "WorkflowExecutionResult" mySwiftAgentCore/src/
  ```
- **pytestメソッド**: `test_tc_017_type_definitions`

---

## 8. テスト実行計画

### 実行順序
1. **構造検証フェーズ**
   - TC-001: プロジェクトディレクトリ構造確認
   - TC-002: package.json検証
   - TC-003: TypeScriptコンパイル検証
   - TC-004: ESLint実行
   - TC-005: Prettier実行
   - TC-017: Context Manager型定義確認

2. **E2Eサービス起動フェーズ**
   - TC-006: サービス起動確認
   - TC-007: ヘルスチェックエンドポイント
   - TC-008: 404エラーレスポンス
   - TC-015: APIスタブエンドポイント確認
   - TC-016: セキュリティ設定検証

3. **Docker/インフラフェーズ**
   - TC-009: docker-compose.core.yml検証
   - TC-010: docker-compose.yml統合確認
   - TC-011: Dockerイメージビルド
   - TC-012: make dev-core実行
   - TC-013: .env.example確認
   - TC-014: GitHub Actions確認

### 成功基準
- [ ] すべての構造検証テストがパス（TC-001〜TC-005, TC-017）
- [ ] すべてのE2Eテストがパス（TC-006〜TC-008, TC-015〜TC-016）
- [ ] すべてのインフラテストがパス（TC-009〜TC-014）
- [ ] TypeScriptコンパイルエラーが0件
- [ ] ESLintエラーが0件
- [ ] Dockerイメージが正常にビルドできる

### テストファイル
```
mySwiftAgentCore/tests/acceptance/test_issue_362_acceptance.py
```

または手動実行の場合は本計画書のcurlコマンドを順次実行。

---

## 9. 補足事項

### 子Issueとの関係
本Issue #362は**プロジェクト基盤**の構築であり、実際の機能は以下の子Issueで実装される：
- **#363**: TaskFlow Engine - ワークフロー実行機能の受入テストは#363で実施
- **#364**: TaskFlow Generator - ワークフロー生成機能の受入テストは#364で実施
- **#365**: Capability Management - Capability管理機能の受入テストは#365で実施

### Langfuseトレース検証について
Langfuse連携（AC-6）の完全な検証は、実際のAPIが実装される子Issue（#363, #364）で実施する。本Issueでは以下を確認：
- Langfuseクライアントの初期化コードが存在する
- 環境変数が設定されている場合、起動時エラーがない

### dev-hybrid.sh / health-check.sh について
これらのスクリプト更新（AC-11, AC-12）はプロジェクト基盤に含まれるが、完全な動作確認はサービスが起動可能になった後に実施する。

---

作成日: 2025-01-15
作成者: acceptance-plan-agent
バージョン: 1.0.0
