# 受入テスト計画書

**Issue**: #410
**タイトル**: feat: user_input_schemaのエンドツーエンド伝播
**作成日**: 2026-01-26
**作成者**: Claude Code (acceptance-plan)

---

## 1. 概要

### 対象Issue
- **番号**: #410
- **タイトル**: feat: user_input_schemaのエンドツーエンド伝播
- **プロジェクト**: expertAgent, myAgentDesk, E2Eテスト（クロスレイヤー）

### 参照ドキュメント
- Issue: #410
- 設計方針書: `dev-reports/feature/issue/410/design-policy.md`
- 前提Issue: #409（複数独立タスク存在時のデータフロー修正）✅ 対応済み

### 機能概要
LLMが生成した`user_input_schema`（ユーザーが入力すべきフィールドの定義）をシステム全体で伝播・保存・表示できるようにする。これにより、ユーザーが正しいフィールド名で入力できるようになる。

---

## 2. 単体テスト結果レビュー

### 現状（TDD実装前）
本Issueはまだ実装されていないため、TDD結果は存在しない。
以下は、**実装後に達成すべき目標値**である。

### 目標カバレッジ
- 現在: N/A（未実装）
- 目標: 90%以上
- 判定: ⏳ 実装後に評価

### テスト品質目標
| 指標 | 目標値 | 判定 |
|------|--------|------|
| 総テスト数 | 各AC毎に最低1テスト | ⏳ |
| モック使用率 | 50%以下 | ⏳ |
| 実API呼び出しテスト | 受入テストで必須 | ⏳ |

### モック使用の妥当性基準
- ✅ 許可: 外部API呼び出し（LLM API等）
- ✅ 許可: 外部サービス（myVault、jobqueue）※ただし結合テストで実サービステスト必須
- ❌ 禁止: 内部関数のモック
- ❌ 禁止: データベースアクセスのモック（E2Eで検証必要）

---

## 3. 受入条件分析

### AC-1: expertAgent - JobGenerationResultにuser_input_schema追加
- **原文**:
  - `JobGenerationResult`クラスに`user_input_schema: dict[str, Any] | None`フィールドを追加
  - `_build_result()`で`analysis.user_input_schema`を設定
  - APIレスポンスに`user_input_schema`が含まれることを確認
- **分類**: 機能要件
- **テスト方法**: pytest（単体）+ curl（E2E）
- **モック使用**: 一部可（LLM APIのみ）
- **検証ポイント**:
  1. `JobGenerationResult`に`user_input_schema`フィールドが存在する
  2. `_build_result()`で`analysis.user_input_schema`が正しく設定される
  3. Job Generator API（`POST /api/v1/job-generator`）のレスポンスに`user_input_schema`が含まれる
  4. `user_input_schema`がJSON Schema形式である

### AC-2: myAgentDesk - JobVersionテーブルにカラム追加
- **原文**:
  - Drizzleスキーマに`userInputSchema: text('user_input_schema')`カラムを追加
  - マイグレーションを実行
  - Job生成完了時に`userInputSchema`を保存
- **分類**: 機能要件
- **テスト方法**: vitest（単体）+ Playwright（E2E）
- **モック使用**: 不可（DB操作は実DBでテスト）
- **検証ポイント**:
  1. `schema.ts`に`userInputSchema`カラムが定義されている
  2. マイグレーションが正常に完了する
  3. `UpdateGenerationResultInput`に`userInputSchema`フィールドが追加されている
  4. Job生成完了時に`userInputSchema`がDBに保存される
  5. 既存データ（userInputSchema=null）でもエラーにならない（後方互換性）

### AC-3: myAgentDesk - UIで入力フォームを動的生成
- **原文**:
  - `getFirstTaskInputSchema()`を`getUserInputSchema()`に置き換え
  - `userInputSchema`が存在する場合はそれを使用
  - フォールバックとして従来の`task_001.input_schema`を使用
- **分類**: UI要件
- **テスト方法**: vitest（単体）+ Playwright（E2E）
- **モック使用**: 不可（UI動作は実際にレンダリング確認）
- **検証ポイント**:
  1. `getUserInputSchema()`関数が実装されている
  2. `userInputSchema`が存在する場合、そのフィールドで入力フォームが生成される
  3. `userInputSchema`がnullの場合、`task_001.input_schema`にフォールバックする
  4. LLMが`email_address`を生成した場合、フォームに`email_address`入力欄が表示される

### AC-4: E2Eテスト - スキーマの動的取得
- **原文**:
  - E2Eテストでジョブ生成後に`userInputSchema`を取得
  - 取得したスキーマに基づいてテストデータを構築
  - ハードコードされたフィールド名を削除
- **分類**: 非機能要件（テスト品質）
- **テスト方法**: シェルスクリプト（E2E）
- **モック使用**: 不可
- **検証ポイント**:
  1. E2Eテストがスキーマを動的に取得している
  2. ハードコードされたフィールド名（`email`, `keyword`）が削除されている
  3. LLMが異なるフィールド名を生成してもテストが正常動作する

### AC-5: 単体テスト・結合テスト
- **原文**:
  - expertAgent: `user_input_schema`伝播のテスト追加
  - myAgentDesk: `userInputSchema`保存・取得のテスト追加
  - カバレッジ90%以上を維持
- **分類**: 非機能要件
- **テスト方法**: pytest/vitest
- **モック使用**: 適切に使用
- **検証ポイント**:
  1. expertAgentの単体テストカバレッジ90%以上
  2. myAgentDeskの単体テストカバレッジ90%以上
  3. 結合テストで実際のデータフローが検証されている

---

## 4. 設計方針検証

### DP-1: アーキテクチャ整合性
- **設計方針**: 各レイヤー境界で明示的な型変換を行う（Explicit Conversion at Boundaries パターン）
- **検証方法**: コード構造確認
- **テスト項目**:
  1. `JobAnalysisResponse.user_input_schema` → `JobGenerationResult.user_input_schema` 変換が存在する
  2. `JobGenerationResult.user_input_schema` → `JobGeneratorResponse.user_input_schema` 変換が存在する
  3. 各変換で型の不整合が発生しない

### DP-2: Graceful Degradation パターン
- **設計方針**: UI層でのフォールバック処理を実装
- **検証方法**: 単体テスト + E2Eテスト
- **テスト項目**:
  1. `userInputSchema`が存在する場合、それを使用する
  2. `userInputSchema`がnull/undefinedの場合、`getFirstTaskInputSchema()`にフォールバックする
  3. JSONパースエラー時も正常にフォールバックする

### DP-3: スキーマバリデーション
- **設計方針**: 多層防御（プロンプト、生成時バリデーション、フォールバック、Langfuseログ）
- **検証方法**: 単体テスト
- **テスト項目**:
  1. `UserInputSchemaValidator.validate()`が不正なスキーマを検出する
  2. 不正なスキーマの場合、フォールバックスキーマが使用される
  3. バリデーション失敗がログに記録される

### DP-4: 後方互換性
- **設計方針**: 新規フィールドはOptionalで、既存クライアントに影響しない
- **検証方法**: E2Eテスト
- **テスト項目**:
  1. 既存のJobVersionデータ（userInputSchema=null）が正常に読み込める
  2. APIレスポンスで`user_input_schema`がnullでもクライアントエラーにならない
  3. UIが`userInputSchema`なしでも正常動作する（フォールバック）

---

## 5. デッドコード検証計画

### F-1: JobGenerationResult.user_input_schema
- **ファイル**: `expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py`
- **種別**: フィールド追加
- **期待される呼び出し元**: `_build_result()`, `_convert_result()`
- **検証方法**:
  ```bash
  grep -rn "user_input_schema" expertAgent/ --include="*.py" | grep -v "test_" | grep -v "__pycache__"
  ```
- **E2E確認**: Job Generator APIを呼び出してレスポンスに`user_input_schema`が含まれることを確認

### F-2: JobGeneratorResponse.user_input_schema
- **ファイル**: `expertAgent/app/schemas/job_generator.py`
- **種別**: フィールド追加
- **期待される呼び出し元**: `_convert_result()`, APIエンドポイント
- **検証方法**:
  ```bash
  grep -rn "JobGeneratorResponse" expertAgent/ --include="*.py" | grep -v "test_"
  ```
- **E2E確認**: OpenAPI仕様（`/openapi.json`）に`user_input_schema`フィールドが含まれることを確認

### F-3: jobVersion.userInputSchema
- **ファイル**: `myAgentDesk/src/lib/server/db/schema.ts`
- **種別**: カラム追加
- **期待される呼び出し元**: `UpdateGenerationResultInput`, `status/+server.ts`
- **検証方法**:
  ```bash
  grep -rn "userInputSchema" myAgentDesk/src/ --include="*.ts" --include="*.svelte"
  ```
- **E2E確認**: DBにJob Versionを保存後、`userInputSchema`カラムにデータが格納されていることを確認

### F-4: getUserInputSchema()
- **ファイル**: `myAgentDesk/src/lib/utils/interface-schema.ts`
- **種別**: 関数追加
- **期待される呼び出し元**: `runs/+page.svelte`
- **検証方法**:
  ```bash
  grep -rn "getUserInputSchema" myAgentDesk/src/ --include="*.ts" --include="*.svelte"
  ```
- **E2E確認**: UIで入力フォームが`userInputSchema`に基づいて動的生成されることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック | 役割 |
|---------|-----|--------------|------|
| expertAgent | http://localhost:8004 | GET /health | Job Generator API |
| myAgentDesk | http://localhost:5173 | GET / | フロントエンドUI |
| myVault | http://localhost:8003 | GET /health | シークレット管理 |
| jobqueue | http://localhost:8001 | GET /health | ジョブキュー管理 |
| mySwiftAgentCore | http://localhost:8006 | GET /health | ワークフロー実行 |

### 起動コマンド

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動（推奨）
./scripts/dev-hybrid.sh start --local-only
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| MYVAULT_ENABLED | MyVault有効化フラグ | ✅ (true) |
| MYVAULT_BASE_URL | MyVault URL | ✅ (http://localhost:8003) |
| OPENAI_API_KEY | OpenAI APIキー（myVault経由） | ✅ |
| ANTHROPIC_API_KEY | Anthropic APIキー（myVault経由） | ✅ |

### テストデータ
- **ユーザー要件**: 「キーワードを入力してWeb検索を行い、結果をメールで送信する」
- **期待されるuser_input_schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "keyword": {"type": "string", "description": "検索キーワード"},
      "email_address": {"type": "string", "description": "送信先メールアドレス"}
    },
    "required": ["keyword", "email_address"]
  }
  ```

---

## 7. テスト項目

### TC-001: JobGenerationResultにuser_input_schemaフィールドが存在する
- **テスト観点**: データモデルの変更確認
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. expertAgentの実装が完了している
- **テスト手順**:
  1. `JobGenerationResult`をインスタンス化
  2. `user_input_schema`フィールドが存在することを確認
- **期待結果**:
  - `user_input_schema`フィールドが`dict | None`型で存在する
- **pytestメソッド**: `test_job_generation_result_has_user_input_schema_field`

### TC-002: _build_resultでuser_input_schemaが設定される
- **テスト観点**: データ伝播の確認
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. `JobAnalysisResponse`に`user_input_schema`が設定されている
- **テスト手順**:
  1. モックの`JobAnalysisResponse`を作成（`user_input_schema`付き）
  2. `_build_result()`を呼び出す
  3. 戻り値の`user_input_schema`を検証
- **期待結果**:
  - `JobGenerationResult.user_input_schema`に値が設定されている
- **pytestメソッド**: `test_build_result_sets_user_input_schema`

### TC-003: Job Generator APIレスポンスにuser_input_schemaが含まれる
- **テスト観点**: APIレスポンス形式の確認
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: curl
- **前提条件**:
  1. expertAgentが起動している
  2. 必要な環境変数が設定されている
- **テスト手順**:
  1. Job Generator APIを呼び出す
  2. レスポンスJSONを検証
  3. OpenAPI仕様（`/openapi.json`）を確認
- **期待結果**:
  - レスポンスに`user_input_schema`フィールドが存在する
  - `user_input_schema`がJSON Schema形式である
  - OpenAPI仕様に`user_input_schema`フィールドが定義されている
- **curlコマンド**:
  ```bash
  # APIレスポンス確認
  curl -s -X POST http://localhost:8004/api/v1/job-generator \
    -H "Content-Type: application/json" \
    -d '{
      "user_requirement": "キーワードを入力してWeb検索を行い、結果をメールで送信する"
    }' | jq '.user_input_schema'

  # OpenAPI仕様確認（改善提案#6対応）
  curl -s http://localhost:8004/openapi.json | \
    jq '.components.schemas.JobGeneratorResponse.properties.user_input_schema'
  ```
- **pytestメソッド**: `test_job_generator_api_returns_user_input_schema`

### TC-004: JobVersionテーブルにuserInputSchemaカラムが存在する
- **テスト観点**: DBスキーマの変更確認
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. マイグレーションが実行済み
- **テスト手順**:
  1. `schema.ts`のjobVersionテーブル定義を確認
  2. `userInputSchema`カラムが存在することを検証
- **期待結果**:
  - `userInputSchema: text('user_input_schema')`が定義されている
- **vitestメソッド**: `test_job_version_schema_has_user_input_schema_column`

### TC-005: Job生成完了時にuserInputSchemaがDBに保存される
- **テスト観点**: データ永続化の確認
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: E2E
- **テスト方法**: Playwright + SQL確認
- **前提条件**:
  1. myAgentDeskが起動している
  2. expertAgentが起動している
- **テスト手順**:
  1. UIからJob生成を実行
  2. 生成完了を待機
  3. DBのjob_versionテーブルを確認
- **期待結果**:
  - `user_input_schema`カラムにJSON文字列が保存されている
- **Playwrightテスト**: `test_job_generation_saves_user_input_schema.spec.ts`

### TC-006: getUserInputSchema関数が正しく動作する
- **テスト観点**: フォールバックロジックの確認
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. `getUserInputSchema()`関数が実装されている
- **テスト手順**:
  1. `userInputSchema`が存在する場合のテスト
  2. `userInputSchema`がnullの場合のフォールバックテスト
  3. JSONパースエラー時のフォールバックテスト
- **期待結果**:
  - 各ケースで期待通りのスキーマが返される
- **vitestメソッド**: `test_get_user_input_schema_with_valid_schema`, `test_get_user_input_schema_fallback`

### TC-007: UIで入力フォームがuserInputSchemaに基づいて動的生成される
- **テスト観点**: UI動作の確認
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: Playwright
- **前提条件**:
  1. Job Versionが生成済み（userInputSchema付き）
  2. myAgentDeskが起動している
- **テスト手順**:
  1. Runsページを開く
  2. Job Versionを選択
  3. 入力フォームのフィールドを確認
- **期待結果**:
  - `userInputSchema`で定義されたフィールドが表示される
  - LLMが`email_address`を生成した場合、`email_address`入力欄が表示される
- **Playwrightテスト**: `test_runs_page_dynamic_form.spec.ts`

### TC-008: E2Eテストがスキーマを動的に取得する
- **テスト観点**: E2Eテストの改善確認
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: シェルスクリプト
- **前提条件**:
  1. 全サービスが起動している
  2. E2Eテストスクリプトが更新されている
- **テスト手順**:
  1. `test_full_workflow_e2e.sh`を実行
  2. スキーマ取得ログを確認
  3. 動的ペイロード構築を確認
- **期待結果**:
  - スキーマを動的に取得している
  - ハードコードされたフィールド名がない
  - LLMが異なるフィールド名を生成しても成功する
- **期待されるログ出力**（改善提案#1対応）:
  ```
  📋 Fetching user input schema for job: <JOB_ID>
  🔧 Building user input payload from schema
    - Keyword field: keyword (or search_keyword, query等)
    - Email field: email_address (or email, recipient等)
  📤 User input payload: {"keyword": "...", "email_address": "..."}
  ```
- **検証ポイント詳細**:
  1. `📋 Fetching user input schema` ログが出力される
  2. `🔧 Building user input payload` ログにフィールド名が動的に表示される
  3. `📤 User input payload` のJSONキーがスキーマから取得したフィールド名である
  4. ハードコード `{"keyword": "...", "email": "..."}` が存在しない
- **実行コマンド**:
  ```bash
  ./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
    --keyword "テストキーワード" \
    --email "test@example.com"
  ```

### TC-009: 後方互換性の確認（userInputSchema=null）
- **テスト観点**: 既存データとの互換性確認
- **関連する受入条件**: AC-2, AC-3
- **関連する設計方針**: DP-2, DP-4
- **テスト種別**: E2E
- **テスト方法**: Playwright
- **前提条件**:
  1. 既存のJobVersionデータ（userInputSchema=null）が存在する
- **テスト手順**:
  1. 既存のJob Versionを選択
  2. Runsページを開く
  3. 入力フォームが表示されることを確認
- **期待結果**:
  - エラーなく入力フォームが表示される
  - `task_001.input_schema`に基づいたフォームが表示される（フォールバック）
- **Playwrightテスト**: `test_backward_compatibility.spec.ts`

### TC-010: スキーマバリデーション失敗時のフォールバック
- **テスト観点**: 多層防御の確認
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. `UserInputSchemaValidator`が実装されている
- **テスト手順**:
  1. 不正なスキーマ（type != "object"）でバリデーション実行
  2. フォールバックスキーマが使用されることを確認
- **期待結果**:
  - バリデーションエラーがログに記録される
  - フォールバックスキーマが返される
- **pytestメソッド**: `test_schema_validation_fallback`

### TC-011: LLM生成フィールド名の変動対応（改善提案#2対応）
- **テスト観点**: LLMが異なるフィールド名を生成した場合の動作確認
- **関連する受入条件**: AC-3, AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: Playwright + シェルスクリプト
- **前提条件**:
  1. 全サービスが起動している
  2. Job生成が完了している
- **テスト手順**:
  1. LLMが`email`を生成した場合のシナリオ
  2. LLMが`email_address`を生成した場合のシナリオ
  3. LLMが`recipient_email`を生成した場合のシナリオ
- **期待結果**:
  - いずれのフィールド名でもUIフォームが正しく表示される
  - E2Eテストがフィールド名を動的に検出して正しいペイロードを構築する
  - ワークフロー実行が成功する
- **検証パターン**:
  | LLM生成フィールド名 | 期待されるUI表示 | E2Eでの検出パターン |
  |-------------------|----------------|-------------------|
  | `email` | `email`入力欄 | `email\|mail\|recipient` |
  | `email_address` | `email_address`入力欄 | `email\|mail\|recipient` |
  | `recipient_email` | `recipient_email`入力欄 | `email\|mail\|recipient` |
  | `keyword` | `keyword`入力欄 | `keyword\|search\|query` |
  | `search_keyword` | `search_keyword`入力欄 | `keyword\|search\|query` |
- **Playwrightテスト**: `test_dynamic_field_name_variation.spec.ts`

### TC-012: DBマイグレーションロールバック検証（改善提案#4対応）
- **テスト観点**: マイグレーション失敗時のロールバック動作確認
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-4
- **テスト種別**: 手動検証
- **テスト方法**: シェルスクリプト + SQL確認
- **前提条件**:
  1. マイグレーション適用前のDBバックアップが存在する
  2. マイグレーションが適用済み
- **テスト手順**:
  1. 現在のDBスキーマを確認（`userInputSchema`カラムあり）
  2. ロールバックスクリプトを実行
  3. DBスキーマを確認（`userInputSchema`カラムなし）
  4. 既存データが保持されていることを確認
- **期待結果**:
  - ロールバック後、`userInputSchema`カラムが削除される
  - 他のカラム（`taskBreakdown`, `interfaceDefinitions`等）のデータが保持される
  - アプリケーションが正常に動作する（フォールバックが機能する）
- **実行コマンド**:
  ```bash
  # バックアップ作成
  cp myAgentDesk/data/myagentdesk.db myAgentDesk/data/myagentdesk.db.bak

  # マイグレーション状態確認
  cd myAgentDesk && npx drizzle-kit status

  # ロールバック実行（設計方針書セクション11.2参照）
  # SQLiteはALTER TABLE DROP COLUMNを直接サポートしないため、
  # テーブル再作成が必要

  # データ確認
  sqlite3 myAgentDesk/data/myagentdesk.db "PRAGMA table_info(job_version);"
  ```
- **注意事項**:
  - 本テストは本番環境では実行しない
  - テスト環境でのみ実行し、実行後は再度マイグレーションを適用する

---

## 8. サービス間データフロー検証

### DF-1: データフロー完全性
| 送信元 | データ項目 | 送信先 | 取得方法 | 検証状態 |
|--------|-----------|--------|---------|---------|
| JobAnalysisResponse | user_input_schema | JobGenerationResult | _build_result() | ⏳ 要実装 |
| JobGenerationResult | user_input_schema | JobGeneratorResponse | _convert_result() | ⏳ 要実装 |
| JobGeneratorResponse | user_input_schema | myAgentDesk API | HTTP Response | ⏳ 要実装 |
| myAgentDesk API | userInputSchema | jobVersion DB | updateGenerationResult() | ⏳ 要実装 |
| jobVersion DB | userInputSchema | UI | getUserInputSchema() | ⏳ 要実装 |

### DF-2: 空配列/null検証【禁止パターン検出】

**チェック方法**:
```bash
# テストファイルでの空配列/null使用を検出
grep -rn "user_input_schema.*=.*None" expertAgent/tests/
grep -rn "userInputSchema.*=.*null" myAgentDesk/tests/
```

**禁止**: テストで空配列/nullを「正常ケース」として使用することは禁止。
ただし、フォールバックテスト用の「異常ケース」としての使用は許可。

---

## 9. コンポーネント間整合性検証

### CI-1: user_input_schemaとinterface_definitionsの整合性
- **検証対象**: 両フィールドの用途が混同されていないか
- **検証方法**:
  ```bash
  # 使用箇所を確認
  grep -rn "interface_definitions" myAgentDesk/src/ --include="*.ts" --include="*.svelte"
  grep -rn "userInputSchema" myAgentDesk/src/ --include="*.ts" --include="*.svelte"
  ```
- **実行タイミング**（改善提案#5対応）:
  | フェーズ | 実行タイミング | 確認内容 |
  |---------|---------------|---------|
  | 単体テスト後 | Phase 3完了後 | 使用箇所のgrep検索 |
  | 結合テスト後 | Phase 4完了後 | データフロー図との整合性 |
  | E2Eテスト後 | Phase 5完了後 | 実際のUI動作確認 |
- **確認項目**:
  - [ ] UIフォーム生成には`userInputSchema`を優先使用
  - [ ] ワークフロー実行時のデータ渡しには`interfaceDefinitions`を使用
  - [ ] 両者を混同して使用していない
- **検証スクリプト**:
  ```bash
  # 整合性確認スクリプト（Phase 3後に実行）
  echo "=== userInputSchema使用箇所 ==="
  grep -rn "userInputSchema" myAgentDesk/src/ --include="*.ts" --include="*.svelte" | grep -v "test"

  echo "=== interface_definitions使用箇所 ==="
  grep -rn "interfaceDefinitions" myAgentDesk/src/ --include="*.ts" --include="*.svelte" | grep -v "test"

  echo "=== 確認ポイント ==="
  echo "1. runs/+page.svelte: userInputSchemaを使用しているか"
  echo "2. workflow実行API: interfaceDefinitionsを使用しているか"
  ```

### CI-2: 命名規則の整合性
- **検証対象**: Python（snake_case）とTypeScript（camelCase）の変換
- **検証方法**: コードレビュー
- **確認項目**:
  - [ ] Python: `user_input_schema`
  - [ ] TypeScript: `userInputSchema`
  - [ ] Database: `user_input_schema`
  - [ ] API Response: `user_input_schema`（snake_case）

---

## 10. テスト実行計画

### 実行順序
1. **Phase 1: サービス起動確認**
   ```bash
   ./scripts/dev-hybrid.sh start --local-only
   curl -s http://localhost:8004/health
   curl -s http://localhost:5173/
   ```

2. **Phase 2: expertAgent単体テスト**
   ```bash
   cd expertAgent
   uv run pytest tests/unit/test_job_generator_v2/test_user_input_schema.py -v
   uv run pytest tests/unit/langgraph/jobGeneratorV2/ -v --cov
   ```

3. **Phase 3: myAgentDesk単体テスト**
   ```bash
   cd myAgentDesk
   npm run test:unit -- tests/unit/utils/interface-schema.test.ts
   npm run test:unit -- tests/unit/repositories/job-version.test.ts

   # カバレッジ測定（改善提案#3対応）
   npm run test:unit -- --coverage
   # または
   npx vitest run --coverage
   ```

4. **Phase 4: 結合テスト**
   ```bash
   cd expertAgent
   uv run pytest tests/integration/langgraph/test_issue_410_integration.py -v
   ```

5. **Phase 5: E2Eテスト**
   ```bash
   # pytest E2E
   cd expertAgent
   uv run pytest tests/acceptance/test_issue_410_acceptance.py -v -s

   # Playwright E2E
   cd myAgentDesk
   npm run test:e2e -- tests/e2e/test_issue_410.spec.ts
   ```

6. **Phase 6: クロスサービスE2E**
   ```bash
   ./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
     --keyword "テスト検索" \
     --email "test@example.com"
   ```

### 成功基準
- [ ] すべてのpytest単体テストがパス
- [ ] すべてのvitest単体テストがパス
- [ ] expertAgentカバレッジ90%以上
- [ ] myAgentDeskカバレッジ90%以上
- [ ] 結合テストがパス
- [ ] pytest受入テストがパス
- [ ] Playwright E2Eテストがパス
- [ ] クロスサービスE2Eテストがパス
- [ ] すべての受入条件（AC-1〜AC-5）が検証済み
- [ ] デッドコードが検出されないこと
- [ ] 後方互換性が確認されていること

---

## 11. 補足事項

### 注意点
1. **マイグレーション実行順序**: `npx drizzle-kit generate` → `npx drizzle-kit migrate` の順序を厳守
2. **E2Eテストの実行タイミング**: APIとDBの修正が完了してから実施
3. **OpenAPI仕様の確認**: FastAPIはPydanticモデルから自動生成されるため、手動編集は不要

### 関連Issue
- #409: 複数独立タスク存在時のデータフロー修正（前提条件）✅ 対応済み
- #408: ユーザー入力フィールド名の整合性検証機能

### 参考資料
- 設計方針書: `dev-reports/feature/issue/410/design-policy.md`
- expertAgent API Reference: `expertAgent/docs/API_REFERENCE.md`
- myAgentDesk README: `myAgentDesk/README.md`

---

**作成日**: 2026-01-26
**更新日**: 2026-01-26
**レビュー状態**: ✅ レビュー完了（改善提案6件反映済み）

---

## 12. 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2026-01-26 | 1.0 | 初版作成 |
| 2026-01-26 | 1.1 | レビュー指摘事項を反映（改善提案6件対応） |

### v1.1 改善提案対応内容

| # | 改善提案 | 対応内容 |
|---|---------|---------|
| 1 | TC-008の検証ポイント具体化 | 期待されるログ出力と検証ポイント詳細を追加 |
| 2 | LLM生成フィールド名変動テスト追加 | TC-011を新規追加（検証パターン表付き） |
| 3 | myAgentDeskカバレッジ測定コマンド追加 | Phase 3に`npm run test:unit -- --coverage`を追記 |
| 4 | DBマイグレーションロールバック検証追加 | TC-012を新規追加（ロールバック手順付き） |
| 5 | CI-1実行タイミング明確化 | 実行タイミング表と検証スクリプトを追加 |
| 6 | OpenAPI仕様検証追加 | TC-003にOpenAPI仕様確認コマンドを追加 |
