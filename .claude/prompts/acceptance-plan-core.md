# 受入テスト計画 コアプロンプト

このプロンプトは、スラッシュコマンドとサブエージェントの両方から実行されます。

---

## 目的

Issue要件と設計方針に基づいて、**意味のある受入テスト計画**を立案します。

### 品質基準

| 基準 | 説明 |
|------|------|
| **ユーザー視点** | 実際のユーザー操作を想定したテスト |
| **E2E重視** | モックを最小限にし、実サービス連携を検証 |
| **デッドコード検出** | 実装された機能が実際に使用されていることを検証 |
| **設計方針準拠** | design-policy.md の設計判断が実装に反映されていることを検証 |

---

## 入力情報の取得

### スラッシュコマンドモードの場合

ユーザーから対話的に以下の情報を取得してください：

```bash
# Issue情報を取得
gh issue view {issue_number} --json number,title,body,labels
```

- Issue番号
- 機能概要（Feature Summary）
- 受入条件（Acceptance Criteria）
- 技術要件（Technical Requirements）

### サブエージェントモードの場合

コンテキストファイルから情報を取得してください：

```bash
CONTEXT_FILE="dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-{N}/acceptance-plan-context.json"
cat "$CONTEXT_FILE"
```

---

## 必須参照ドキュメント

以下のファイルを**必ず読み込んで**から計画を立案してください：

### 1. Issue情報
```bash
gh issue view {issue_number} --json number,title,body,labels,assignees
```

### 2. 設計方針書（design-policy.md）
```bash
cat dev-reports/feature/issue/{issue_number}/design-policy.md
```

**読み込む項目**:
- 現状調査サマリ
- アーキテクチャ設計
- 技術選定
- 設計パターン
- データモデル設計
- API設計
- セキュリティ設計
- テスト計画（記載がある場合）

### 3. 作業計画書（work-plan.md）（存在する場合）
```bash
cat dev-reports/feature/issue/{issue_number}/work-plan.md
```

### 4. TDD実装結果（存在する場合）
```bash
cat dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-{N}/tdd-result.json
```

### 5. 実装機能一覧（存在する場合）
```bash
cat dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-{N}/implemented-features.json
```

---

## 計画立案プロセス

### Step 1: 単体テスト結果レビュー

TDD実装結果から単体テストの状況を確認します。

```bash
# TDD結果を確認
cat dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-{N}/tdd-result.json | jq '{
  coverage: .coverage,
  unit_tests: .unit_tests,
  static_analysis: .static_analysis,
  files_modified: .files_modified
}'
```

**レビュー項目**:

| 項目 | 確認内容 | 判定基準 |
|------|---------|---------|
| カバレッジ | 単体テストカバレッジ | 90%以上 |
| テスト数 | 実装した機能に対するテスト数 | 各機能に最低1テスト |
| 静的解析 | Ruff/MyPyエラー | 0件 |
| モック使用率 | モック使用の割合 | 過剰でないこと |

**モック使用の妥当性チェック**:

```bash
# モック使用箇所を確認
grep -r "@patch\|Mock\|MagicMock" tests/unit/ | wc -l

# 実API呼び出しテストの有無を確認
grep -r "requests\.\|httpx\.\|aiohttp\." tests/unit/ | wc -l
```

**レビュー結果フォーマット**:

```markdown
## 単体テスト結果レビュー

### カバレッジ
- 現在: {coverage}%
- 目標: 90%
- 判定: ✅ PASS / ❌ FAIL

### テスト品質
- 総テスト数: {total_tests}
- モック使用テスト数: {mock_tests}
- モック使用率: {mock_rate}%
- 判定: ✅ 適切 / ⚠️ モック過剰

### モック過剰の兆候
- [ ] 外部API呼び出しをモックしている（適切）
- [ ] 内部関数をモックしている（要確認）
- [ ] データベースアクセスをモックしている（E2Eで検証必要）

### 単体テストでカバーされていない項目
1. [未カバー項目1]
2. [未カバー項目2]
```

---

### Step 2: 受入条件の分析

Issue本文から受入条件を抽出し、テスト項目に変換します。

**受入条件の分類**:

| 分類 | 説明 | テスト方法 |
|------|------|----------|
| **機能要件** | 「〜ができる」 | 実API呼び出し、E2Eテスト |
| **非機能要件** | 「〜秒以内に応答」 | パフォーマンステスト |
| **UI要件** | 「〜が表示される」 | Playwrightテスト |
| **セキュリティ要件** | 「〜が保護される」 | セキュリティテスト |

**分析フォーマット**:

```markdown
## 受入条件分析

### AC-1: [受入条件1の要約]
- **原文**: [Issue記載の原文]
- **分類**: 機能要件 / 非機能要件 / UI要件 / セキュリティ要件
- **テスト方法**: pytest / curl / Playwright
- **モック使用**: 不可 / 一部可（外部APIのみ）
- **検証ポイント**:
  1. [検証ポイント1]
  2. [検証ポイント2]

### AC-2: [受入条件2の要約]
...
```

---

### Step 3: 設計方針との整合性確認

design-policy.md の設計判断が実装に反映されているか確認するテスト項目を作成します。

**確認項目**:

| 設計方針セクション | 確認内容 |
|------------------|---------|
| アーキテクチャ設計 | レイヤー構成が正しいか |
| 技術選定 | 選定された技術が使用されているか |
| 設計パターン | 指定されたパターンが適用されているか |
| API設計 | APIエンドポイントが設計通りか |
| セキュリティ設計 | セキュリティ要件が満たされているか |

**設計方針検証テスト**:

```markdown
## 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: [design-policy.mdの記載内容]
- **検証方法**: コード構造確認 / APIテスト
- **テスト項目**:
  1. [具体的なテスト項目]

### DP-2: API設計整合性
- **設計方針**: [エンドポイント設計]
- **検証方法**: curl / pytest
- **テスト項目**:
  1. エンドポイント `POST /v1/xxx` が存在する
  2. リクエスト形式が設計通りである
  3. レスポンス形式が設計通りである
```

---

### Step 4: デッドコード検出計画

実装された機能が実際に使用されているか確認するテスト計画を作成します。

```bash
# implemented-features.json から機能一覧を取得
cat dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-{N}/implemented-features.json | jq '.implemented_features[]'
```

**各機能のデッドコード検証**:

```markdown
## デッドコード検証計画

### F-1: [機能名]
- **ファイル**: [file_path]
- **種別**: function / class / constant
- **期待される呼び出し元**: [expected_callers]
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -rn "[function_name]" --include="*.py" | grep -v "def [function_name]"
  ```
- **E2Eでの確認方法**: [APIを叩いて機能が動作することを確認]

### F-2: [機能名]
...
```

---

### Step 5: テスト環境・方法の定義

**テスト環境**:

```markdown
## テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| mySwiftAgentCore | http://localhost:8006 | GET /health |
| expertAgent | http://localhost:8004 | GET /health |
| myVault | http://localhost:8003 | GET /health |
| graphAiServer | http://localhost:8005 | GET /health |

### 起動コマンド（E2Eテスト用 - 必須）

**重要**: E2Eテストは以下の環境で実行すること。

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

これにより:
- mySwiftAgentCore, expertAgent: ローカル直接起動
- myVault: Dockerコンテナで起動（default_projectを使用）

### シークレット・設定情報

**E2Eテストで使用するシークレットは、コンテナ起動のmyVaultのdefault_projectから取得**します。

| 項目 | 取得元 |
|------|--------|
| OPENAI_API_KEY | myVault (default_project) |
| LLM_API_KEY | myVault (default_project) |
| ANTHROPIC_API_KEY | myVault (default_project) |
| その他APIキー | myVault (default_project) |

myVaultへのシークレット登録（事前設定が必要な場合）:
```bash
# myVaultにシークレットを登録
curl -X POST http://localhost:8003/api/v1/secrets \
  -H "Content-Type: application/json" \
  -d '{"project": "default_project", "key": "OPENAI_API_KEY", "value": "sk-xxx"}'
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | ✅ (true) |
| MYVAULT_BASE_URL | MyVault URL | ✅ (http://localhost:8003) |
| MYVAULT_SERVICE_NAME | サービス名 | ✅ |
| MYVAULT_SERVICE_TOKEN | サービストークン | ✅ |

### テストデータ
- [必要なテストデータの説明]
- [テストデータの準備方法]
```

**テスト方法**:

```markdown
## テスト方法

### 1. pytest受入テスト（自動）
- **ファイル**: `tests/acceptance/test_issue_{issue_number}_acceptance.py`
- **実行コマンド**: `uv run pytest tests/acceptance/test_issue_{issue_number}_acceptance.py -v`
- **前提条件**: サービス起動済み、環境変数設定済み

### 2. Playwrightテスト（自動）- myAgentDesk/commonUI対象時
- **ファイル**: `myAgentDesk/tests/e2e/test_issue_{issue_number}.spec.ts`
- **実行コマンド**: `cd myAgentDesk && npm test -- --run`
- **前提条件**: 開発サーバー起動済み

### 3. curl APIテスト（手動/自動）
- 各テストケースごとにcurlコマンドを記載
```

---

### Step 5.5: コンポーネント間整合性検証（Issue #359追加）

**論理的整合性の検証**:

```markdown
## コンポーネント間整合性検証

### CI-1: バリデータ整合性
- **検証対象**: 同一概念を検証する複数のバリデータ
- **検証方法**:
  ```bash
  # URL検証の整合性確認
  grep -n "validate_url\|http://\|https://" {target_files}
  ```
- **確認項目**:
  - [ ] すべてのバリデータが同じルールを適用している
  - [ ] localhost例外が一貫している
  - [ ] エラーメッセージが一貫している

### CI-2: プロンプトルール整合性
- **検証対象**: LLMプロンプト内のルール
- **検証方法**:
  ```bash
  # ルール間の矛盾を確認
  grep -n "HTTPS\|HTTP\|localhost" {prompt_files}
  ```
- **確認項目**:
  - [ ] セキュリティルールとAPIルールが矛盾していない
  - [ ] サンプルコードがルールに準拠している

### CI-3: テスト検証手法整合性
- **検証対象**: テストファイルの検証手法
- **検証方法**:
  - JSON出力にはJSON検証を使用
  - YAML出力にはYAML検証を使用
- **確認項目**:
  - [ ] テスト対象のフォーマットに適した検証手法が使用されている
```

### Step 5.6: E2E統合テスト計画（Issue #359追加）

**Job Generation機能のE2Eテスト**:

```markdown
## E2E統合テスト計画

### E2E-1: Job Generate API E2Eテスト
- **テストファイル**: `tests/acceptance/test_job_generate_api.py`
- **実行コマンド**:
  ```bash
  uv run pytest tests/acceptance/test_job_generate_api.py -v -s
  ```
- **検証項目**:
  - [ ] Job生成APIが正常に動作する
  - [ ] ステータスポーリングが正常に動作する
  - [ ] タスク分析フェーズが完了する
  - [ ] ワークフロー生成フェーズが完了する
  - [ ] 生成されたTaskFlow JSONが妥当である

### E2E-2: 実LLM呼び出しテスト
- **目的**: モックではなく実際のLLMを呼び出してテスト
- **必須条件**:
  - 環境変数 `OPENAI_API_KEY` が設定されている
  - 環境変数 `ANTHROPIC_API_KEY` が設定されている
- **検証項目**:
  - [ ] LLM応答が適切な形式である
  - [ ] プロンプトルールが正しく適用されている
```

---

### Step 6: テスト項目の作成

**テスト項目フォーマット**:

```markdown
## テスト項目

### TC-001: [テスト名]
- **テスト観点**: [何を検証するか]
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: E2E / 結合 / UI
- **テスト方法**: pytest / curl / Playwright
- **前提条件**:
  1. [前提条件1]
  2. [前提条件2]
- **テスト手順**:
  1. [手順1]
  2. [手順2]
- **期待結果**:
  - HTTPステータス: 200
  - レスポンス: [期待するレスポンス]
- **curlコマンド**:
  ```bash
  curl -s -X POST http://localhost:8104/v1/endpoint \
    -H "Content-Type: application/json" \
    -d '{"param": "value"}'
  ```
- **pytestメソッド**: `test_tc_001_xxx`

### TC-002: [テスト名]
...
```

---

## 禁止事項

以下のテスト項目は**禁止**です：

| 禁止事項 | 理由 | 代替方法 |
|---------|------|---------|
| 全面モックテスト | 実動作を確認できない | 実サービスを起動してE2Eテスト |
| ファイル存在確認のみ | 機能動作を確認できない | 実際にAPIを呼び出して検証 |
| 単体テスト結果の引用 | E2E確認にならない | 実環境で再度検証 |
| ヘルスチェックのみ | 機能を検証できない | 実際の機能をテスト |

---

## 出力フォーマット

### スラッシュコマンドモードの場合

ターミナルに計画を表示し、`acceptance-plan.md` を作成：

**ファイルパス**:
```
dev-reports/feature/issue/{issue_number}/acceptance-plan.md
```

### サブエージェントモードの場合

Writeツールで `acceptance-plan.md` を作成：

**ファイルパス**:
```
dev-reports/feature/issue/{issue_number}/acceptance-plan.md
```

---

## acceptance-plan.md テンプレート

```markdown
# 受入テスト計画書

**Issue**: #{issue_number}
**作成日**: {date}
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #{issue_number}
- **タイトル**: {issue_title}
- **プロジェクト**: {project_name}

### 参照ドキュメント
- Issue: #{issue_number}
- 設計方針書: `dev-reports/feature/issue/{issue_number}/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/{issue_number}/work-plan.md`

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: {coverage}%
- 目標: 90%
- 判定: ✅ PASS / ❌ FAIL

### テスト品質評価
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | {total} | - |
| モック使用テスト数 | {mock_count} | - |
| モック使用率 | {mock_rate}% | ⚠️/✅ |
| 実API呼び出しテスト数 | {real_api_count} | - |

### モック使用の妥当性
- [評価コメント]

### 単体テストでカバーされていない項目
1. [項目1]
2. [項目2]

---

## 3. 受入条件分析

### AC-1: {受入条件1}
- **原文**: {原文}
- **分類**: {分類}
- **テスト方法**: {方法}
- **検証ポイント**:
  1. {ポイント1}

### AC-2: {受入条件2}
...

---

## 4. 設計方針検証

### DP-1: {設計方針項目1}
- **設計方針**: {design-policy.mdの記載}
- **検証方法**: {方法}
- **テスト項目**:
  1. {項目1}

---

## 5. デッドコード検証計画

### F-1: {機能名}
- **ファイル**: {file_path}
- **種別**: {type}
- **検証方法**: {方法}
- **E2E確認**: {確認方法}

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| {service} | {url} | {health_check} |

### 起動コマンド
```bash
{起動コマンド}
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| {var} | {desc} | {required} |

---

## 7. テスト項目

### TC-001: {テスト名}
- **テスト観点**: {観点}
- **関連する受入条件**: AC-{n}
- **関連する設計方針**: DP-{n}
- **テスト種別**: {種別}
- **テスト方法**: {方法}
- **前提条件**:
  1. {前提1}
- **テスト手順**:
  1. {手順1}
- **期待結果**:
  - {結果1}
- **curlコマンド**:
  ```bash
  {curl_command}
  ```
- **pytestメソッド**: {method_name}

### TC-002: {テスト名}
...

---

## 8. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. pytest受入テスト実行
3. Playwrightテスト実行（該当時）
4. 追加curlテスト実行

### 成功基準
- [ ] すべてのpytestテストがパス
- [ ] すべてのPlaywrightテストがパス（該当時）
- [ ] すべての受入条件が検証済み
- [ ] デッドコードが検出されないこと

---

## 9. 補足事項

- [補足事項があれば記載]
```

---

## 完了条件

以下をすべて満たすこと：

- ✅ Issue情報を読み込み済み
- ✅ design-policy.md を読み込み済み
- ✅ 単体テスト結果をレビュー済み
- ✅ 受入条件を分析済み
- ✅ 設計方針との整合性確認項目を作成済み
- ✅ デッドコード検証計画を作成済み
- ✅ テスト環境・方法を定義済み
- ✅ テスト項目を作成済み
- ✅ acceptance-plan.md を出力済み
