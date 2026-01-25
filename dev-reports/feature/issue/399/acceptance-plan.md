# 受入テスト計画書

**Issue**: #399
**作成日**: 2026-01-25
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #399
- **タイトル**: Enhancement: ワークフロー生成時にAPI応答スキーマを考慮する仕組みの追加
- **プロジェクト**: mySwiftAgentCore

### 背景
- TaskFlowワークフロー生成時にAPIの応答形式（特に`result`ラッパー）を考慮せず、誤ったmappingパスが生成される問題
- 例: jsonoutput APIは`{ result: {...}, type: "jsonOutput" }`形式で応答するが、生成されたワークフローは`steps.step_id.subject`と誤ったパスを参照

### 参照ドキュメント
- Issue: #399
- 設計方針書: `dev-reports/feature/issue/399/design-policy.md`
- 作業計画書: `dev-reports/feature/issue/399/work-plan.md` （未作成）

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: N/A（実装未開始）
- 目標: 90%
- 判定: ⏳ 未評価

### テスト品質評価

※TDD実装完了後にレビューを実施すること。

| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | N/A | - |
| モック使用テスト数 | N/A | - |
| モック使用率 | N/A | - |
| 実API呼び出しテスト数 | N/A | - |

### TDD実装後の必須確認事項

以下のテストが実装されていることを確認：

1. **ResponsePatternResolver単体テスト**
   - [ ] YAML読み込み成功テスト
   - [ ] パターン解決テスト（wrapped/direct）
   - [ ] mappingヒント生成テスト
   - [ ] YAML読み込みエラー時のgraceful degradationテスト
   - [ ] 不正YAML検証（スキーマエラー）テスト
   - [ ] パターン未定義時の動作テスト

2. **PromptBuilder拡張テスト**
   - [ ] パターン情報がプロンプトに含まれるテスト
   - [ ] wrappedパターンの警告メッセージがプロンプトに含まれるテスト
   - [ ] ResponsePatternResolver注入テスト

---

## 3. 受入条件分析

### AC-1: response-patterns.yamlの作成
- **原文**: response-patterns.yamlが作成され、jsonoutput/google_search/gmail_sendのパターンが定義されている
- **分類**: 機能要件
- **テスト方法**: ファイル検証 + 内容検証
- **モック使用**: 不可
- **検証ポイント**:
  1. ファイルが`mySwiftAgentCore/config/response-patterns.yaml`に存在する
  2. `json_output_agent`パターンが`wrapped`で`wrapperField: result`を持つ
  3. `google_search`パターンが`direct`である
  4. `gmail_send`パターンが`direct`である
  5. YAML構文が正しい

> **注意**: API IDは既存のCapability定義（`json_output_agent.yaml`）と一致させる。設計方針書の`jsonoutput`は`json_output_agent`に読み替える。

### AC-2: ResponsePatternResolverの実装
- **原文**: ResponsePatternResolverが実装され、パターン解決機能が動作する
- **分類**: 機能要件
- **テスト方法**: 単体テスト + 結合テスト
- **モック使用**: 一部可（YAMLファイル読み込みのみ）
- **検証ポイント**:
  1. `resolvePattern('jsonoutput')`が`wrapped`パターンを返す
  2. `getMappingHint('jsonoutput')`が`steps.{step_id}.result.{field}`形式のヒントを返す
  3. 未定義APIに対して`undefined`を返す
  4. YAMLセキュアローダー（safeLoad）を使用している

### AC-3: PromptBuilder拡張
- **原文**: PromptBuilder.formatCapabilitiesEnhanced()がパターン情報を含むプロンプトを生成する
- **分類**: 機能要件
- **テスト方法**: 単体テスト + 結合テスト
- **モック使用**: 一部可（ResponsePatternResolverのモック可）
- **検証ポイント**:
  1. jsonoutput APIのプロンプトに「⚠️ Response Pattern: wrapped」が含まれる
  2. 正しいmappingパス例（`steps.{step_id}.result.{field}`）がプロンプトに含まれる
  3. 応答例がプロンプトに含まれる

### AC-4: 正しいmappingパス生成
- **原文**: jsonoutput APIを使用した新規ワークフローが正しいmappingパス（`steps.{id}.result.{field}`）を生成する
- **分類**: 機能要件（E2E）
- **テスト方法**: E2Eテスト（実LLM呼び出し）
- **モック使用**: 不可
- **検証ポイント**:
  1. LLMが生成したワークフローJSONのmappingパスが`steps.{id}.result.{field}`形式
  2. 生成されたワークフローが実行可能
  3. 実行結果が期待通り

### AC-5: 既存テスト維持
- **原文**: 既存のワークフロー生成テストが全てパスする
- **分類**: 品質要件
- **テスト方法**: 回帰テスト
- **モック使用**: 既存テストの方式に従う
- **検証ポイント**:
  1. 既存のPromptBuilder単体テストがパス
  2. 既存の結合テストがパス
  3. 破壊的変更がない

### AC-6: 品質要件
- **原文**: ResponsePatternResolverの単体テストカバレッジが90%以上、エラーハンドリング（graceful degradation）が実装されている、YAMLセキュアローダー（safeLoad）を使用している、パターン定義の検証機能が実装されている、適切なログ出力が実装されている、エッジケースのテストがある
- **分類**: 品質要件
- **テスト方法**: 単体テスト + コードレビュー
- **モック使用**: 可
- **検証ポイント**:
  1. カバレッジ90%以上
  2. YAML読み込みエラー時にログ出力してパターンなしで続行
  3. `js-yaml`の`safeLoad`または同等の安全なローダーを使用
  4. 不正パターン（pattern未定義、wrappedなのにwrapperField未定義）をエラー検出
  5. load完了、パターン解決、エラー時のログ出力
  6. エッジケーステスト存在

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: ResponsePatternResolverをサービス層に配置、PromptBuilderから注入して使用
- **検証方法**: コード構造確認
- **テスト項目**:
  1. `ResponsePatternResolver.ts`が`mySwiftAgentCore/src/taskflowGeneratorAgent/services/`または同等の場所に配置されている
  2. PromptBuilderがDI可能な構造になっている

### DP-2: データモデル整合性
- **設計方針**: ResponsePattern interfaceの定義
- **検証方法**: TypeScript型チェック
- **テスト項目**:
  1. `ResponsePattern` interfaceが定義されている
  2. `pattern: "wrapped" | "direct"`の型定義
  3. `wrapperField?: string`の型定義

### DP-3: キャッシング戦略
- **設計方針**: 起動時1回読み込み、loadedフラグで再読み込み防止
- **検証方法**: 単体テスト
- **テスト項目**:
  1. 2回目以降のload()呼び出しがスキップされる
  2. パターン情報がメモリに保持される

### DP-4: セキュリティ設計
- **設計方針**: YAMLセキュアローダー使用
- **検証方法**: コードレビュー + 単体テスト
- **テスト項目**:
  1. `yamlSafeLoad()`または`yaml.load(..., { schema: yaml.DEFAULT_SAFE_SCHEMA })`使用
  2. コード実行攻撃の防止

---

## 5. デッドコード検証計画

### F-1: response-patterns.yaml
- **ファイル**: `mySwiftAgentCore/config/response-patterns.yaml`
- **種別**: 設定ファイル
- **期待される呼び出し元**: ResponsePatternResolver
- **検証方法**:
  ```bash
  grep -rn "response-patterns" --include="*.ts" mySwiftAgentCore/
  ```
- **E2E確認**: ワークフロー生成時にパターン情報がプロンプトに含まれることを確認

### F-2: ResponsePatternResolver
- **ファイル**: `mySwiftAgentCore/src/taskflowGeneratorAgent/services/ResponsePatternResolver.ts`（予定）
- **種別**: class
- **期待される呼び出し元**: PromptBuilder
- **検証方法**:
  ```bash
  grep -rn "ResponsePatternResolver" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: ワークフロー生成APIが正常に動作し、パターン情報を含むプロンプトが生成されることを確認

### F-3: resolvePattern メソッド
- **ファイル**: ResponsePatternResolver.ts
- **種別**: method
- **期待される呼び出し元**: PromptBuilder.formatCapabilitiesEnhanced()
- **検証方法**:
  ```bash
  grep -rn "resolvePattern\|getMappingHint" --include="*.ts" mySwiftAgentCore/src/
  ```
- **E2E確認**: 生成されたプロンプトに「Response Pattern」や「⚠️」が含まれることを確認

---

## 6. テスト環境

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
| ANTHROPIC_API_KEY | myVault (default_project) |

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | ✅ (true) |
| MYVAULT_BASE_URL | MyVault URL | ✅ (http://localhost:8003) |
| MYVAULT_SERVICE_NAME | サービス名 | ✅ |
| MYVAULT_SERVICE_TOKEN | サービストークン | ✅ |

---

## 7. コンポーネント間整合性検証

### CI-1: パターン定義とCapability定義の整合性
- **検証対象**: response-patterns.yaml と capabilities/*.yaml
- **検証方法**:
  ```bash
  # response-patterns.yamlに定義されたAPIがcapabilityとして存在するか確認
  grep -l "id: jsonoutput\|id: json_output_agent" mySwiftAgentCore/config/capabilities/**/*.yaml
  ```
- **確認項目**:
  - [ ] jsonoutput/json_output_agentのIDが一致している
  - [ ] google_searchのIDが一致している
  - [ ] gmail_sendのIDが一致している

### CI-2: プロンプト内パターン情報の整合性
- **検証対象**: response-patterns.yaml と PromptBuilder出力
- **検証方法**: 単体テスト
- **確認項目**:
  - [ ] パターン情報がプロンプトに正しく含まれる
  - [ ] wrapperFieldが正しく表示される
  - [ ] mappingヒントが正しく表示される

### CI-3: 既存responseSchemaとの整合性
- **検証対象**: json_output_agent.yamlのresponseSchemaとresponse-patterns.yaml
- **検証方法**: 手動レビュー
- **確認項目**:
  - [ ] 既存のresponseSchemaと矛盾しない
  - [ ] 両方の情報がプロンプトに含まれる（重複なし）

---

## 8. サービス間データフロー検証

### DF-1: データフロー完全性
パターン情報がワークフロー生成まで正しく伝播されることを確認：

| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| response-patterns.yaml | パターン定義 | ResponsePatternResolver | ファイル読み込み | ⏳ |
| ResponsePatternResolver | パターン情報 | PromptBuilder | メソッド呼び出し | ⏳ |
| PromptBuilder | 拡張プロンプト | LLM | API呼び出し | ⏳ |

### DF-2: テスト項目必須化
以下のテスト項目を必ず含めること：

- [ ] **DF-TC-1**: response-patterns.yamlからパターンが正しく読み込まれることを検証
- [ ] **DF-TC-2**: パターン情報がプロンプトに含まれることを検証
- [ ] **DF-TC-3**: LLMが生成したワークフローが正しいmappingパスを持つことを検証

---

## 9. E2E統合テスト計画

### E2E-1: Job Generate API E2Eテスト（設計方針書記載）
- **テストファイル**: `mySwiftAgentCore/tests/acceptance/test_issue_399_acceptance.ts`
- **実行手順**:
  1. サービス起動（`./scripts/dev-hybrid.sh start --local-only`）
  2. ヘルスチェック確認
  3. Job Generate実行
  4. 生成されたワークフローのmappingパス検証
- **検証項目**:
  - [ ] jsonoutput APIを使用したタスクのmappingパスが`steps.{id}.result.{field}`形式
  - [ ] ワークフロー生成が成功する
  - [ ] 生成されたワークフローが実行可能

### E2E-2: 実LLM呼び出しテスト
- **目的**: モックではなく実際のLLMを呼び出してテスト
- **必須条件**:
  - 環境変数 `OPENAI_API_KEY` または `ANTHROPIC_API_KEY` が設定されている
- **検証項目**:
  - [ ] LLM応答が適切な形式である
  - [ ] プロンプトルールが正しく適用されている
  - [ ] mappingパスが正しい形式

### E2E-3: 実践的E2Eテスト（design-policy.md記載）
- **URL**: `http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/generate`
- **テスト手順**:
  1. Job Generateを実行
  2. Job Runを実行
     - キーワード: `大谷翔平の妻`
     - メール送信先: `alva-va-va-ro-recoba.2004.2.21@docomo.ne.jp`
  3. 結果確認
- **成功確認**:
  - [ ] 全てのタスクが成功ステータスで完了
  - [ ] jsonoutput APIタスクが`result`フィールド経由で正しい値を取得
  - [ ] メール送信が成功

---

## 10. テスト項目

### TC-001: response-patterns.yaml存在確認
- **テスト観点**: AC-1 パターン定義ファイルの存在
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: 静的検証
- **テスト方法**: ファイル確認
- **前提条件**:
  1. TDD実装が完了している
- **テスト手順**:
  1. ファイル存在確認
  2. YAML構文検証
  3. 必須フィールド確認
- **期待結果**:
  - ファイルが存在する
  - YAML構文エラーなし
  - version, patternsフィールドが存在
- **検証コマンド**:
  ```bash
  ls mySwiftAgentCore/config/response-patterns.yaml
  cat mySwiftAgentCore/config/response-patterns.yaml | python -c "import yaml,sys; yaml.safe_load(sys.stdin); print('OK')"
  ```
- **vitestメソッド**: `test_tc_001_response_patterns_yaml_exists`

### TC-002: json_output_agentパターン定義検証
- **テスト観点**: AC-1 json_output_agentのwrappedパターン定義
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. response-patterns.yamlが存在する
- **テスト手順**:
  1. YAMLを読み込む
  2. json_output_agentパターンを取得
  3. pattern="wrapped", wrapperField="result"を確認
- **期待結果**:
  - json_output_agent.pattern === "wrapped"
  - json_output_agent.wrapperField === "result"
- **vitestメソッド**: `test_tc_002_json_output_agent_pattern_definition`

### TC-003: ResponsePatternResolver.resolvePattern()テスト
- **テスト観点**: AC-2 パターン解決機能
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1, DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. ResponsePatternResolverが実装されている
- **テスト手順**:
  1. ResponsePatternResolverをインスタンス化
  2. load()を呼び出し
  3. resolvePattern('json_output_agent')を呼び出し
- **期待結果**:
  - パターンオブジェクトが返される
  - pattern === "wrapped"
  - wrapperField === "result"
- **vitestメソッド**: `test_tc_003_resolve_pattern`

### TC-003a: キャッシング動作テスト
- **テスト観点**: DP-3 load()の2回目以降スキップ
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. ResponsePatternResolverが実装されている
- **テスト手順**:
  1. ResponsePatternResolverをインスタンス化
  2. load()を呼び出し
  3. 再度load()を呼び出し
  4. ファイル読み込みが1回のみであることを確認（spyで検証）
- **期待結果**:
  - 2回目のload()でファイル読み込みが発生しない
  - loadedフラグがtrueになっている
  - パターン情報がメモリに保持されている
- **vitestメソッド**: `test_tc_003a_caching_behavior`

### TC-004: ResponsePatternResolver.getMappingHint()テスト
- **テスト観点**: AC-2 mappingヒント生成
- **関連する受入条件**: AC-2, AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. ResponsePatternResolverが実装されている
- **テスト手順**:
  1. ResponsePatternResolverをインスタンス化
  2. load()を呼び出し
  3. getMappingHint('json_output_agent')を呼び出し
- **期待結果**:
  - ヒント文字列に"result"が含まれる
  - ヒント文字列に"steps.{step_id}.result.{field}"形式が含まれる
- **vitestメソッド**: `test_tc_004_get_mapping_hint`

### TC-005: graceful degradationテスト
- **テスト観点**: AC-6 エラーハンドリング
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. ResponsePatternResolverが実装されている
- **テスト手順**:
  1. 存在しないYAMLパスでResponsePatternResolverを初期化
  2. load()を呼び出し
  3. エラーがスローされないことを確認
  4. resolvePattern()がundefinedを返すことを確認
- **期待結果**:
  - 例外がスローされない
  - resolvePattern()がundefinedを返す
  - ログにエラーが出力される
- **vitestメソッド**: `test_tc_005_graceful_degradation`

### TC-005a: パターン定義バリデーションテスト
- **テスト観点**: AC-6 validateConfig()の検証機能
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. ResponsePatternResolverが実装されている
- **テスト手順**:
  1. pattern未定義のYAMLでload()を呼び出し → エラー
  2. wrapped + wrapperField未定義のYAMLでload()を呼び出し → エラー
  3. pattern="invalid"（wrapped/direct以外）のYAMLでload()を呼び出し → エラー
  4. patternsフィールド未定義のYAMLでload()を呼び出し → エラー
- **期待結果**:
  - 各ケースでバリデーションエラーがログ出力される
  - graceful degradationによりクラッシュしない
  - resolvePattern()がundefinedを返す
- **テストデータ例**:
  ```yaml
  # Case 1: pattern未定義
  patterns:
    invalid_api:
      wrapperField: result

  # Case 2: wrapped + wrapperField未定義
  patterns:
    invalid_api:
      pattern: wrapped

  # Case 3: 不正なpattern値
  patterns:
    invalid_api:
      pattern: "unknown"
  ```
- **vitestメソッド**: `test_tc_005a_validate_config_errors`

### TC-006: YAMLセキュアローダーテスト
- **テスト観点**: AC-6 セキュリティ要件
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-4
- **テスト種別**: コードレビュー + 単体テスト
- **テスト方法**: 静的解析 + pytest
- **前提条件**:
  1. ResponsePatternResolverが実装されている
- **テスト手順**:
  1. ソースコードでyamlSafeLoadまたは同等の安全な方法を使用していることを確認
  2. 危険なYAML（コード実行を含む）でエラーになることを確認
- **期待結果**:
  - セキュアローダーを使用している
  - コード実行攻撃が防止される
- **検証コマンド**:
  ```bash
  grep -n "safeLoad\|DEFAULT_SAFE_SCHEMA\|SAFE_SCHEMA" mySwiftAgentCore/src/taskflowGeneratorAgent/**/*.ts
  ```
- **vitestメソッド**: `test_tc_006_secure_yaml_loader`

### TC-007: PromptBuilder拡張テスト
- **テスト観点**: AC-3 プロンプトへのパターン情報追加
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. ResponsePatternResolverが実装されている
  2. PromptBuilderが拡張されている
- **テスト手順**:
  1. json_output_agentを含むcapabilityリストでformatCapabilitiesEnhanced()を呼び出し
  2. 出力にパターン情報が含まれることを確認
- **期待結果**:
  - 出力に"Response Pattern: wrapped"が含まれる
  - 出力に"result"フィールドのヒントが含まれる
- **vitestメソッド**: `test_tc_007_prompt_builder_pattern_info`

### TC-008: E2E ワークフロー生成テスト
- **テスト観点**: AC-4 正しいmappingパス生成
- **関連する受入条件**: AC-4
- **関連する設計方針**: 全て
- **テスト種別**: E2E
- **テスト方法**: 実API呼び出し
- **前提条件**:
  1. 全サービスが起動している
  2. APIキーが設定されている
- **テスト手順**:
  1. json_output_agentを使用するタスクでワークフロー生成APIを呼び出し
  2. 生成されたワークフローJSONを取得
  3. mappingパスを検証
- **期待結果**:
  - mappingパスが`steps.{id}.result.{field}`形式
  - ワークフローが妥当な構造
- **curlコマンド**:
  ```bash
  # 方法1: myAgentDesk経由（設計方針書記載のE2Eフロー）
  # Job Generate
  curl -s -X POST "http://localhost:8000/projects/proj_mjbjua2z7y65wy/workbenches/wb_1766969315404_udrhx79/generate"

  # 方法2: mySwiftAgentCore直接呼び出し（単体E2Eテスト用）
  curl -s -X POST http://localhost:8006/api/v1/taskflow/generate \
    -H "Content-Type: application/json" \
    -d '{
      "task_id": "test_json_output",
      "name": "JSON Output Test",
      "description": "Test JSON output with result wrapper using json_output_agent",
      "interface": {
        "input": { "text": "string" },
        "output": { "subject": "string", "body": "string" }
      }
    }'
  ```
- **検証スクリプト**:
  ```bash
  # 生成されたワークフローのmappingパスを検証
  # 期待: steps.{id}.result.{field} 形式
  jq '.steps[] | select(.config.capability_id == "json_output_agent") | .output_mapping' generated_workflow.json
  ```
- **vitestメソッド**: `test_tc_008_e2e_workflow_generation`

### TC-009: 既存テスト回帰確認
- **テスト観点**: AC-5 後方互換性
- **関連する受入条件**: AC-5
- **関連する設計方針**: 制約条件
- **テスト種別**: 回帰テスト
- **テスト方法**: 既存テストスイート実行
- **前提条件**:
  1. 実装が完了している
- **テスト手順**:
  1. PromptBuilder単体テストを実行
  2. taskflowGeneratorAgent結合テストを実行
  3. 全テストがパスすることを確認
- **期待結果**:
  - 全既存テストがパス
  - 新規機能による既存機能の破壊なし
- **検証コマンド**:
  ```bash
  cd mySwiftAgentCore && npm test -- --grep "PromptBuilder"
  cd mySwiftAgentCore && npm test -- --grep "taskflowGeneratorAgent"
  ```
- **vitestメソッド**: N/A（既存テストスイートで実行）

### TC-010: デッドコード検証
- **テスト観点**: F-1〜F-3 実装コードが使用されていること
- **関連する受入条件**: 全て
- **関連する設計方針**: DP-1
- **テスト種別**: 静的検証
- **テスト方法**: grep + 実行確認
- **前提条件**:
  1. 実装が完了している
- **テスト手順**:
  1. ResponsePatternResolverの参照箇所を確認
  2. resolvePattern/getMappingHintの呼び出し箇所を確認
  3. response-patterns.yamlの参照箇所を確認
- **期待結果**:
  - ResponsePatternResolverがPromptBuilderから参照されている
  - 各メソッドが実際に呼び出されている
- **検証コマンド**:
  ```bash
  grep -rn "ResponsePatternResolver" --include="*.ts" mySwiftAgentCore/src/
  grep -rn "resolvePattern\|getMappingHint" --include="*.ts" mySwiftAgentCore/src/
  grep -rn "response-patterns" --include="*.ts" mySwiftAgentCore/
  ```
- **vitestメソッド**: `test_tc_010_no_dead_code`

### TC-011: ドキュメント要件検証
- **テスト観点**: 11.3 新規APIパターン追加手順のドキュメント
- **関連する受入条件**: 設計方針書 11.3 ドキュメント要件
- **関連する設計方針**: 全て
- **テスト種別**: 静的検証
- **テスト方法**: ドキュメント確認
- **前提条件**:
  1. 実装が完了している
- **テスト手順**:
  1. README.mdまたは専用ドキュメントにパターン追加手順が記載されているか確認
  2. 手順に以下が含まれているか確認:
     - response-patterns.yamlの編集方法
     - 必須フィールド（pattern, wrapperField等）の説明
     - wrapped/directパターンの違い
     - 追加後の検証方法
  3. 実際に手順に従って新規パターンを追加できるか検証
- **期待結果**:
  - ドキュメントが存在する
  - 手順が明確に記載されている
  - 手順に従って新規パターンを追加できる
- **検証コマンド**:
  ```bash
  # ドキュメント存在確認
  ls mySwiftAgentCore/README.md
  grep -n "response-patterns\|ResponsePattern" mySwiftAgentCore/README.md
  # または専用ドキュメント
  ls mySwiftAgentCore/docs/response-patterns.md
  ```
- **確認項目**:
  - [ ] パターン追加手順が記載されている
  - [ ] 必須フィールドの説明がある
  - [ ] サンプルコードがある
  - [ ] 検証方法が記載されている

---

## 11. テスト実行計画

### 実行順序
1. サービス起動確認（ヘルスチェック）
2. 静的検証（TC-001, TC-006, TC-010, TC-011）
3. 単体テスト実行（TC-002, TC-003, TC-003a, TC-004, TC-005, TC-005a, TC-007）
4. 回帰テスト実行（TC-009）
5. E2Eテスト実行（TC-008）
6. 実践的E2Eテスト（E2E-3）

### 成功基準
- [ ] すべての静的検証がパス（TC-001, TC-006, TC-010, TC-011）
- [ ] すべての単体テストがパス（TC-002〜TC-007、TC-003a、TC-005a含む）
- [ ] すべての回帰テストがパス（TC-009）
- [ ] E2Eテストで正しいmappingパスが生成される（TC-008）
- [ ] 実践的E2Eテストで全タスクが成功（E2E-3）
- [ ] デッドコードが検出されない
- [ ] ドキュメント要件が満たされている（TC-011）

### テストファイル配置
| テスト種別 | 配置場所 | 対応TC |
|-----------|---------|--------|
| 単体テスト（ResponsePatternResolver） | `mySwiftAgentCore/tests/unit/taskflowGeneratorAgent/services/ResponsePatternResolver.test.ts` | TC-002〜TC-006, TC-003a, TC-005a |
| 単体テスト（PromptBuilder拡張） | `mySwiftAgentCore/tests/unit/taskflowGeneratorAgent/prompts/PromptBuilder.test.ts`（追加） | TC-007 |
| 受入テスト | `mySwiftAgentCore/tests/acceptance/test_issue_399_acceptance.ts` | TC-008, E2E-1〜E2E-3 |
| 静的検証スクリプト | `mySwiftAgentCore/scripts/verify_issue_399.sh`（任意） | TC-001, TC-010, TC-011 |

---

## 12. 補足事項

### 注意点
1. **ID整合性（解決済み）**: response-patterns.yamlでは既存のCapability定義と一致させ、`json_output_agent`を使用する。設計方針書の`jsonoutput`は`json_output_agent`に読み替えること。
2. **TypeScript実装**: 本Issueの実装はTypeScriptで行うため、pytestではなくvitest/jestでのテストとなる
3. **E2Eテスト環境**: 実LLM呼び出しが必要なため、APIキーの設定が必須
4. **テストフレームワーク**: 単体テストはvitest、E2Eテストはvitest + 実APIで実行

### リスク
1. LLMの出力が非決定的なため、E2Eテストの結果にばらつきが生じる可能性がある
2. 新規APIが追加された場合、response-patterns.yamlの更新が必要

### 今後の改善候補
1. CI/CDでパターン未定義APIを警告する仕組み
2. Capability YAMLからresponse-patterns.yamlを自動生成する仕組み

---

## 改訂履歴

| 版 | 日付 | 作成者 | 内容 |
|----|------|--------|------|
| 1.0 | 2026-01-25 | acceptance-plan-agent | 初版作成 |
| 1.1 | 2026-01-25 | acceptance-plan-agent | レビュー結果反映: TC-003a（キャッシング）、TC-005a（バリデーション）、TC-011（ドキュメント要件）追加、ID整合性解決（json_output_agent統一）、TC-008エンドポイント修正 |
