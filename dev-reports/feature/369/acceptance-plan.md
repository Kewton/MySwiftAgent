# 受入テスト計画書

**Issue**: #369
**作成日**: 2026年1月17日
**作成者**: acceptance-plan

---

## 1. 概要

### 対象Issue
- **番号**: #369
- **タイトル**: taskflowGeneratorAgent: SecurityValidator のバッククォート誤検出修正
- **プロジェクト**: mySwiftAgentCore
- **親Issue**: #364 (taskflowGeneratorAgent 実装)

### 参照ドキュメント
- Issue: #369
- 設計方針書: `dev-reports/feature/issue/369/design-policy.md`
- アーキテクチャレビュー: `dev-reports/feature/issue/369/architecture-review.md`

---

## 2. 単体テスト結果レビュー

### カバレッジ
- 現在: 全プロジェクトテスト 931/931 パス
- SecurityValidatorテスト: 39/39 パス
- 判定: ✅ PASS

### テスト品質評価
| 指標 | 値 | 判定 |
|------|-----|------|
| SecurityValidator総テスト数 | 39 | ✅ |
| Issue #369専用テスト数 | 10 | ✅ |
| コンテキスト判定テスト数 | 6 | ✅ |
| メトリクス収集テスト数 | 4 | ✅ |
| デバッグログテスト数 | 2 | ✅ |

### モック使用の妥当性
- **評価**: ✅ 適切
- モックは最小限（ValidationContext のみ）
- 実際のSecurityValidatorインスタンスを使用してテスト
- パターンマッチングは実際の正規表現で実行

### 単体テストでカバーされている項目
1. ✅ transform ステップでの JavaScript テンプレートリテラル許可
2. ✅ shell ステップでのバッククォート検出
3. ✅ code_js ステップの shell フィールドでのバッククォート検出
4. ✅ コンテキスト判定ロジック（Set/RegExp ベース）
5. ✅ メトリクス収集機能
6. ✅ デバッグログ機能

---

## 3. 受入条件分析

### AC-1: JavaScript テンプレートリテラルが誤検出されない
- **原文**: JavaScript テンプレートリテラルが誤検出されない
- **分類**: 機能要件
- **テスト方法**: 単体テスト / E2E テスト
- **検証ポイント**:
  1. transform ステップの expression で `` `Hello ${name}` `` が許可される
  2. code_js ステップの code で `` `Result: ${value}` `` が許可される
  3. isValid が true を返す

### AC-2: 実際のシェルコマンド置換は検出される
- **原文**: 実際のシェルコマンド置換は検出される
- **分類**: セキュリティ要件
- **テスト方法**: 単体テスト / E2E テスト
- **検証ポイント**:
  1. shell ステップでバッククォート `` `rm -rf /` `` が検出される
  2. exec ステップでバッククォートが検出される
  3. code_js の shell フィールドでバッククォートが検出される
  4. SHELL_INJECTION エラーコードが返される

### AC-3: E2E テストの task_002 が成功する
- **原文**: E2E テストの task_002 が成功する
- **分類**: 機能要件（結合）
- **テスト方法**: E2E テスト（実際のワークフロー検証）
- **検証ポイント**:
  1. Summarize Search Results タスクが SecurityValidator を通過する
  2. ワークフロー全体が正常に検証される

### AC-4: 単体テストで検出パターンを検証
- **原文**: 単体テストで検出パターンを検証
- **分類**: テスト要件
- **テスト方法**: 単体テスト
- **検証ポイント**:
  1. SecurityValidator.test.ts に Issue #369 専用テストが存在する
  2. コンテキスト別のテストケースが網羅されている

---

## 4. 設計方針検証

### DP-1: コンテキスト認識型検証
- **設計方針**: ステップタイプとフィールドパスに基づいてコンテキストを判定し、適切なセキュリティルールを適用する
- **検証方法**: 単体テスト / コード確認
- **テスト項目**:
  1. `isShellContext()` メソッドが正しくコンテキストを判定する
  2. `getContextType()` メソッドが4種類のコンテキストを返す
  3. SHELL_STEP_TYPES Set が O(1) ルックアップを実現する

### DP-2: 設定の外部化
- **設計方針**: セキュリティ設定を `security-config.ts` に分離し、テスタビリティと保守性を向上
- **検証方法**: ファイル構造確認 / 単体テスト
- **テスト項目**:
  1. `security-config.ts` ファイルが存在する
  2. `SHELL_STEP_TYPES`, `SHELL_FIELD_PATTERNS` 等がエクスポートされている
  3. カスタム設定がコンストラクタ経由で注入可能

### DP-3: メトリクス収集
- **設計方針**: 検証パフォーマンスと検出パターンの統計情報を収集する
- **検証方法**: 単体テスト / API 呼び出し
- **テスト項目**:
  1. `collectMetrics: true` 設定でメトリクスが収集される
  2. `getMetrics()` メソッドで統計情報を取得できる
  3. `validationDurationMs` が正しく計測される

### DP-4: デバッグログ
- **設計方針**: `debug: true` 設定でコンテキスト判定のログを出力する
- **検証方法**: 単体テスト / コンソール出力確認
- **テスト項目**:
  1. `debug: true` 設定でログが出力される
  2. `debug: false` 設定でログが出力されない

---

## 5. デッドコード検証計画

### F-1: isShellContext メソッド
- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/SecurityValidator.ts`
- **種別**: private method
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -n "isShellContext" src/taskflowGeneratorAgent/validator/validators/SecurityValidator.ts
  ```
- **E2E確認**: `checkDangerousPatterns` から呼び出されることを確認

### F-2: getContextType メソッド
- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/SecurityValidator.ts`
- **種別**: private method
- **検証方法**:
  ```bash
  grep -n "getContextType" src/taskflowGeneratorAgent/validator/validators/SecurityValidator.ts
  ```
- **E2E確認**: `checkDangerousPatterns` から呼び出されることを確認

### F-3: security-config.ts エクスポート
- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/security-config.ts`
- **種別**: module exports
- **検証方法**:
  ```bash
  grep -n "import.*security-config" src/taskflowGeneratorAgent/validator/validators/SecurityValidator.ts
  ```
- **E2E確認**: SecurityValidator がインポートして使用していることを確認

### F-4: getMetrics メソッド
- **ファイル**: `src/taskflowGeneratorAgent/validator/validators/SecurityValidator.ts`
- **種別**: public method
- **検証方法**:
  ```bash
  grep -rn "getMetrics" tests/unit/taskflowGeneratorAgent/
  ```
- **E2E確認**: テストから呼び出されていることを確認

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| N/A (単体テスト) | - | - |

このIssueはSecurityValidatorの内部ロジック修正のため、外部サービスは不要です。

### 起動コマンド
```bash
# 単体テスト実行
cd mySwiftAgentCore
npm test
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| N/A | - | - |

### テストデータ
- テストワークフロー定義（テストコード内で定義）
- バッククォートを含む各種パターン

---

## 7. テスト項目

### TC-001: transform ステップでの JavaScript テンプレートリテラル許可
- **テスト観点**: JavaScript コンテキストではバッククォートが許可される
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. SecurityValidator インスタンスが作成済み
- **テスト手順**:
  1. transform ステップを含むワークフローを作成
  2. expression に JavaScript テンプレートリテラルを含める
  3. validate() を実行
- **期待結果**:
  - isValid: true
  - errors: []
- **pytestメソッド**: `should allow JavaScript template literals in transform expressions`

### TC-002: shell ステップでのバッククォート検出
- **テスト観点**: シェルコンテキストではバッククォートが検出される
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. SecurityValidator インスタンスが作成済み
- **テスト手順**:
  1. shell ステップを含むワークフローを作成
  2. command にバッククォートを含める
  3. validate() を実行
- **期待結果**:
  - isValid: false
  - errors に SHELL_INJECTION が含まれる
- **pytestメソッド**: `should detect backticks in shell step`

### TC-003: code_js の shell フィールドでのバッククォート検出
- **テスト観点**: code_js ステップでも shell 関連フィールドでは検出される
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. SecurityValidator インスタンスが作成済み
- **テスト手順**:
  1. code_js ステップを含むワークフローを作成
  2. config.shell フィールドにバッククォートを含める
  3. validate() を実行
- **期待結果**:
  - isValid: false
  - errors に SHELL_INJECTION が含まれる
- **pytestメソッド**: `should detect backticks in code_js shell field`

### TC-004: コンテキスト判定の堅牢性（Set ベース）
- **テスト観点**: SHELL_STEP_TYPES が Set として正しく動作する
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. security-config.ts がインポート可能
- **テスト手順**:
  1. SHELL_STEP_TYPES をインポート
  2. 各シェルタイプ（shell, exec, bash, cmd, system, spawn）が含まれることを確認
- **期待結果**:
  - すべてのシェルタイプが Set に含まれる
- **pytestメソッド**: `should include all shell step types in SHELL_STEP_TYPES`

### TC-005: コンテキスト判定の堅牢性（RegExp ベース）
- **テスト観点**: SHELL_FIELD_PATTERNS が正規表現として正しく動作する
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. security-config.ts がインポート可能
- **テスト手順**:
  1. SHELL_FIELD_PATTERNS をインポート
  2. 各パターンがシェル関連フィールドパスにマッチすることを確認
- **期待結果**:
  - `.shell`, `.exec`, `.command` 等にマッチする
- **pytestメソッド**: `should match shell field patterns correctly`

### TC-006: メトリクス収集機能
- **テスト観点**: collectMetrics オプションでメトリクスが収集される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. SecurityValidator インスタンスが collectMetrics: true で作成済み
- **テスト手順**:
  1. ワークフローを検証
  2. getMetrics() を呼び出す
- **期待結果**:
  - metrics が null ではない
  - totalStepsChecked > 0
  - validationDurationMs > 0
- **pytestメソッド**: `should collect metrics when enabled`

### TC-007: デバッグログ機能
- **テスト観点**: debug オプションでログが出力される
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-4
- **テスト種別**: 単体テスト
- **テスト方法**: vitest + console.debug spy
- **前提条件**:
  1. SecurityValidator インスタンスが debug: true で作成済み
- **テスト手順**:
  1. console.debug をスパイ
  2. ワークフローを検証
  3. console.debug が呼び出されたことを確認
- **期待結果**:
  - console.debug が呼び出される
  - ログに [SecurityValidator] プレフィックスが含まれる
- **pytestメソッド**: `should output debug logs when enabled`

### TC-008: 設定の外部化確認
- **テスト観点**: security-config.ts からの設定インポートが正しく動作する
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. security-config.ts が存在する
- **テスト手順**:
  1. security-config.ts からエクスポートをインポート
  2. 各エクスポートが定義されていることを確認
- **期待結果**:
  - SHELL_STEP_TYPES, SHELL_FIELD_PATTERNS, ValidationContextType 等がエクスポートされている
- **pytestメソッド**: `should export security configuration`

### TC-009: カスタム設定の注入
- **テスト観点**: コンストラクタ経由でカスタム設定を注入できる
- **関連する受入条件**: AC-4
- **関連する設計方針**: DP-2
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. SecurityValidator クラスがインポート可能
- **テスト手順**:
  1. additionalShellStepTypes を含む設定でインスタンスを作成
  2. カスタムステップタイプがシェルコンテキストとして認識されることを確認
- **期待結果**:
  - カスタムステップタイプでバッククォートが検出される
- **pytestメソッド**: `should accept custom shell step types`

### TC-010: 複合パターン検証（JavaScript + シェル混在）
- **テスト観点**: 同一ワークフロー内でコンテキストが正しく判定される
- **関連する受入条件**: AC-1, AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 単体テスト
- **テスト方法**: vitest
- **前提条件**:
  1. SecurityValidator インスタンスが作成済み
- **テスト手順**:
  1. transform ステップ（テンプレートリテラル）と shell ステップ（バッククォート）を含むワークフローを作成
  2. validate() を実行
- **期待結果**:
  - transform ステップは許可される
  - shell ステップのバッククォートは検出される
  - isValid: false（shell ステップのエラーのため）
- **pytestメソッド**: `should correctly handle mixed context workflow`

---

## 8. テスト実行計画

### 実行順序
1. 単体テスト実行（npm test）
2. ESLint チェック実行（npm run lint）
3. TypeScript 型チェック実行（npm run type-check）

### 実行コマンド
```bash
cd mySwiftAgentCore

# 全テスト実行
npm test

# SecurityValidator テストのみ実行
npm test -- --reporter=verbose SecurityValidator

# Issue #369 関連テストのみ実行
npm test -- --reporter=verbose -t "Issue #369"
```

### 成功基準
- [x] すべての vitest テストがパス（931/931）
- [x] SecurityValidator テストがパス（39/39）
- [x] Issue #369 専用テストがパス（10/10）
- [x] ESLint エラーなし
- [x] TypeScript 型エラーなし
- [x] すべての受入条件が検証済み
- [x] デッドコードが検出されないこと

---

## 9. コンポーネント間整合性検証

### CI-1: バリデータ整合性
- **検証対象**: SecurityValidator と他のバリデータ
- **確認項目**:
  - [x] SecurityValidator が ValidationPipeline に正しく組み込まれている
  - [x] 他のバリデータと競合するルールがない

### CI-2: 設定ファイル整合性
- **検証対象**: security-config.ts と SecurityValidator.ts
- **確認項目**:
  - [x] すべてのエクスポートが正しくインポートされている
  - [x] 型定義が一致している

---

## 10. 補足事項

### 実装完了状況
本計画書作成時点で、以下の実装が完了しています：

1. **security-config.ts** - 新規作成
   - `ValidationContextType` enum
   - `SHELL_STEP_TYPES` Set
   - `SHELL_FIELD_PATTERNS` RegExp[]
   - `SecurityMetrics` interface
   - `SecurityValidatorConfig` interface

2. **SecurityValidator.ts** - 修正済み
   - `isShellContext()` メソッド追加
   - `getContextType()` メソッド追加
   - `getMetrics()` メソッド追加
   - `debugLog()` メソッド追加
   - コンテキスト認識型検証ロジック実装

3. **SecurityValidator.test.ts** - 拡張済み
   - Issue #369 専用テスト 10件追加
   - 合計 39件のテストケース

### アーキテクチャレビュー結果
- **評価**: ✅ 承認（条件付き）
- 承認条件はすべて満たされています：
  1. ✅ コンテキスト判定ロジックの堅牢性向上
  2. ✅ 包括的なテストケースの作成
  3. ✅ ドキュメントの充実化

### テスト結果サマリ
```
Test Files  60 passed (60)
     Tests  931 passed (931)
  Duration  21.56s
```
