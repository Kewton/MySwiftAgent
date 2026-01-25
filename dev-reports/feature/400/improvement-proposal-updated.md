# Issue #400 改善案（ユーザーフィードバック反映版）

## 概要

Issue #400「CLAUDE.md・pm-auto-devの改善」に対する詳細な改善案です。
ユーザーインタビューおよび追加フィードバックを反映しています。

---

## 1. CLAUDE.md の改善

### 1.1 プロジェクト位置づけの明確化

**現状の問題**: プロジェクト一覧テーブルがあるが、実態と乖離している。

**改善内容**:

```markdown
## 📊 プロジェクト構成

### アーキテクチャ概要

MySwiftAgentは以下の3層アーキテクチャで構成されています：

| 層 | プロジェクト | 説明 |
|----|------------|------|
| **Platform** | myVault, jobqueue, Valkey | インフラ・データ基盤 |
| **Agent** | expertAgent, mySwiftAgentCore | AIエージェント・ワークフロー実行 |
| **Frontend** | myAgentDesk, commonUI | ユーザーインターフェース |

### プロジェクト別役割

| プロジェクト | 役割 | 技術スタック | 備考 |
|-------------|------|-------------|------|
| **mySwiftAgentCore** | **メインワークフロー実行エンジン** | TypeScript + TaskFlow | **基本的にこちらを使用** |
| graphAiServer | GraphAI OSS連携用ワークフロー実行 | TypeScript + GraphAI | GraphAI OSSを使用する場合のみ |
| expertAgent | AIエージェント基盤・Job Generator | FastAPI + LangGraph | ジョブ生成・管理 |
| myAgentDesk | Web UI | SvelteKit | フロントエンド |
| jobqueue | ジョブキュー管理 | FastAPI + SQLite | ジョブの永続化・実行管理 |
| myVault | シークレット管理 | FastAPI + SQLite | APIキー等の安全な管理 |
| myscheduler | ジョブスケジューリング | FastAPI + APScheduler | 定期実行 |
| commonUI | 共通UIコンポーネント | TypeScript | 再利用可能なUI部品 |

### mySwiftAgentCore vs graphAiServer の使い分け

| 条件 | 使用するプロジェクト |
|------|---------------------|
| 通常のワークフロー実行 | **mySwiftAgentCore** |
| TaskFlow形式のワークフロー | **mySwiftAgentCore** |
| GraphAI OSS形式のワークフロー | graphAiServer |
| 新規ワークフロー開発（デフォルト） | **mySwiftAgentCore** |

**原則**: 基本的に**mySwiftAgentCore**を使用。GraphAI OSSを使用する場合に限りgraphAiServerを使用する。
```

### 1.2 Issue完遂チェックリストの追加

```markdown
## 🔍 Issue完遂チェックリスト【必須】

Issue実装完了時に以下を必ず確認すること：

### 受入条件の完全確認
- [ ] Issue本文の全受入条件（AC-1〜AC-N）に対応済み
- [ ] 各受入条件に対するテストまたは検証結果が存在
- [ ] スキップした受入条件がある場合、理由を明記

### 対応内容のドキュメント反映
- [ ] 変更したAPI仕様がAPI_REFERENCE.mdに反映
- [ ] 新規設定項目が設定ドキュメントに反映
- [ ] アーキテクチャ変更がarchitecture-overview.mdに反映

### 品質基準の達成
- [ ] 単体テストカバレッジ90%以上
- [ ] 静的解析エラー0件
- [ ] 受入テスト全パス
```

---

## 2. pm-auto-dev スラッシュコマンドの改善

### 2.1 Phase 6: ドキュメンテーション【必須化】

**現状**: Phase 6は「推奨」であり、スキップされることが多い。

**改善**:

```markdown
### Phase 6: ドキュメンテーション【必須】

**重要**: Issue実装で変更した内容は必ずドキュメントに反映すること。

#### 6-1. ドキュメント更新計画の立案

実装した内容に基づいて、更新が必要なドキュメントを特定：

| 変更種別 | 更新対象ドキュメント |
|---------|---------------------|
| API追加・変更 | `{project}/docs/API_REFERENCE.md` |
| 設定追加・変更 | `docs/design/environment-variables.md` |
| アーキテクチャ変更 | `docs/design/architecture-overview.md` |
| 新機能追加 | `README.md`, 関連ドキュメント |
| ワークフロー変更 | `GRAPHAI_WORKFLOW_GENERATION_RULES.md` |

#### 6-2. ドキュメント更新の実行

各対象ドキュメントを更新：

- **API仕様**: エンドポイント、リクエスト/レスポンス形式、エラーコード
- **設定**: 環境変数名、デフォルト値、説明
- **使用例**: 実際の使用方法、curlコマンド例

#### 6-3. ドキュメント更新の検証

- [ ] 更新内容が実装と一致しているか
- [ ] 既存ドキュメントとの整合性があるか
- [ ] 変更箇所がdiffで確認できるか

**スキップ条件（以下の場合のみスキップ可能）**:
- `internal` ラベル（内部リファクタリングのみ）
- `test-only` ラベル（テストコードのみの変更）
- `ci-only` ラベル（CI/CD設定のみの変更）
```

### 2.2 Phase 7: リグレッションテスト【新規追加】

```markdown
### Phase 7: リグレッションテスト【必須】

**目的**: 既存機能への影響がないことを確認するE2Eテストを実行。

#### 7-1. プロジェクト別リグレッションテスト

##### expertAgent / mySwiftAgentCore

```bash
# E2Eテストスクリプトの実行
./scripts/e2e-test.sh
```

**テスト内容**:
- ヘルスチェック（全サービス）
- ワークフロー生成API
- ワークフロー実行API
- 既存ワークフローの動作確認

##### myAgentDesk（フロントエンド）

```bash
# Playwrightリグレッションテスト
cd myAgentDesk && npm run test:e2e
```

**テスト内容**:
- UI表示確認
- ユーザー操作フロー
- API連携確認
- **ジョブの生成と実行**（expertAgent連携）
  - ジョブ生成リクエスト送信
  - ジョブステータス確認
  - ジョブ実行結果取得
  - 結果表示確認

##### 全体統合テスト

```bash
# 統合リグレッションテスト
./scripts/e2e-test.sh --full
```

**テスト内容**:
- サービス起動確認
- サービス間通信確認
- エンドツーエンドワークフロー実行
- ジョブ生成→キュー登録→実行→結果取得の一連フロー

#### 7-2. リグレッションテスト結果の記録

```json
{
  "status": "passed",
  "test_suites": [
    {"name": "expertAgent E2E", "passed": 10, "failed": 0},
    {"name": "mySwiftAgentCore E2E", "passed": 8, "failed": 0},
    {"name": "myAgentDesk Playwright", "passed": 15, "failed": 0},
    {"name": "Job Generation Flow", "passed": 5, "failed": 0}
  ],
  "regression_detected": false
}
```

#### 7-3. リグレッション検出時の対応

リグレッションが検出された場合：

1. 影響を受けたテストを特定
2. 原因を調査（今回の変更が原因か、既存バグか）
3. 今回の変更が原因の場合：
   - Phase 2（TDD実装）に戻って修正
   - 修正後、再度Phase 7を実行
4. 既存バグの場合：
   - 別Issueとして起票
   - 現Issueはそのまま進行
```

### 2.3 Phase 8: Issue完遂チェック【新規追加】

```markdown
### Phase 8: Issue完遂チェック【必須】

**目的**: Issue本文の全受入条件が対応されていることを確認。

#### 8-1. 受入条件の網羅性確認

Issue本文から全受入条件を抽出し、対応状況を確認：

```markdown
## Issue #{issue_number} 受入条件チェック

| AC | 受入条件 | 対応状況 | 検証方法 |
|----|---------|---------|---------|
| AC-1 | {受入条件1} | ✅ 完了 | テストケースTC-001で検証 |
| AC-2 | {受入条件2} | ✅ 完了 | テストケースTC-002で検証 |
| AC-3 | {受入条件3} | ⚠️ 一部対応 | 理由: {理由} |
| AC-4 | {受入条件4} | ❌ 未対応 | 理由: {理由} |
```

#### 8-2. 未対応・一部対応の処理

**完全対応の場合**（全てが✅）:
→ Phase 9（進捗報告）へ進む

**一部対応・未対応がある場合**:
1. 理由を明記
2. 対応可能な場合：Phase 2に戻って追加実装
3. 対応不可能な場合：ユーザーに確認

```
⚠️ Issue #{issue_number} の以下の受入条件が未完了です：

| AC | 受入条件 | 状況 | 理由 |
|----|---------|------|------|
| AC-3 | {受入条件} | 一部対応 | {理由} |
| AC-4 | {受入条件} | 未対応 | {理由} |

## 選択肢
1. 追加実装を行う（Phase 2に戻る）
2. 現状でクローズする（理由を記録）
3. フォローアップIssueを作成
```

#### 8-3. 完遂チェック結果の記録

```json
{
  "issue_number": {issue_number},
  "acceptance_criteria_total": 4,
  "acceptance_criteria_completed": 4,
  "completion_rate": "100%",
  "uncompleted_items": [],
  "status": "fully_completed"
}
```
```

---

## 3. pm-bug-fix スラッシュコマンドの改善

### 3.1 根本原因分析の強化（なぜなぜ分析）

```markdown
### Phase 2: 根本原因分析【必須強化】

**目的**: 類似バグの再発を防ぐため、真因まで深掘りする。

#### 2-1. なぜなぜ分析（5 Whys）

```markdown
## バグ: {バグの概要}

### 直接原因
{直接的なコード上の問題}

### なぜなぜ分析

| レベル | 問い | 答え |
|--------|------|------|
| Why 1 | なぜこのバグが発生したか？ | {答え1} |
| Why 2 | なぜ{答え1}が起きたか？ | {答え2} |
| Why 3 | なぜ{答え2}が起きたか？ | {答え3} |
| Why 4 | なぜ{答え3}が起きたか？ | {答え4} |
| Why 5 | なぜ{答え4}が起きたか？ | **真因**: {真因} |

### 真因
{特定された根本原因}

### 対策
| 対策 | 影響範囲 | 優先度 |
|------|---------|--------|
| {対策1} | {影響範囲} | 高 |
| {対策2} | {影響範囲} | 中 |
```

#### 2-2. 影響範囲の調査

```bash
# 類似パターンの検索
grep -rn "{バグの原因となったパターン}" --include="*.py" --include="*.ts"

# 同様の実装がある箇所を特定
```

**確認項目**:
- [ ] 同じ原因で発生しうる箇所が他にないか
- [ ] 対策が全ての該当箇所に適用されるか
- [ ] リグレッションテストで検出可能か

#### 2-3. 再発防止策の立案

| 再発防止策 | 実装方法 |
|-----------|---------|
| コードレビューチェック項目追加 | PR テンプレートに追加 |
| 静的解析ルール追加 | Ruff/ESLint カスタムルール |
| テストケース追加 | 単体/結合テストに追加 |
| ドキュメント更新 | 注意事項として記載 |
```

---

## 4. E2Eテストスクリプトの再配置

### 4.1 現状

```
mySwiftAgentCore/e2etest/
├── e2e-test-script.sh        # Issue #364用E2Eテスト
├── run_all_tests.sh
├── test_direct_llm.sh
├── test_gmail_send.sh
├── test_google_search.sh
└── test_json_output_agent.sh
```

### 4.2 改善案

```
scripts/
├── e2e-test.sh               # 統合E2Eテストスクリプト（新規）
└── e2e/
    ├── myswiftagentcore/     # mySwiftAgentCore用
    │   ├── run_all_tests.sh
    │   ├── test_direct_llm.sh
    │   ├── test_gmail_send.sh
    │   ├── test_google_search.sh
    │   └── test_json_output_agent.sh
    ├── expertagent/          # expertAgent用（将来）
    └── integration/          # サービス間統合テスト
        └── test_job_flow.sh  # ジョブ生成→実行フロー
```

### 4.3 移動タスク

```bash
# 1. ディレクトリ作成
mkdir -p scripts/e2e/myswiftagentcore
mkdir -p scripts/e2e/integration

# 2. ファイル移動
mv mySwiftAgentCore/e2etest/*.sh scripts/e2e/myswiftagentcore/

# 3. 統合スクリプト作成
# scripts/e2e-test.sh - 全E2Eテストを実行

# 4. 古いディレクトリ削除
rmdir mySwiftAgentCore/e2etest
```

---

## 5. 更新されたPhase構成

```
Phase 0: 初期設定とTodoリスト作成
Phase 1: Issue情報収集
Phase 1.5-A: 受入テスト計画立案
Phase 1.5-B: 受入テスト計画レビュー
Phase 2: TDD実装
Phase 2.5: TDD結果検証
Phase 2.6: 実装機能一覧の生成
Phase 2.7: 実装検証（デッドコード検出）
Phase 2.8: デッドコード解消イテレーション
Phase 3: 受入テスト実行
Phase 3.5: 受入テストファイル検証
Phase 3.6: 受入テスト結果妥当性確認
Phase 4: リファクタリング
Phase 5: 進捗報告
Phase 5.5: 品質チェック
Phase 6: ドキュメンテーション【必須化】      ← 変更
Phase 7: リグレッションテスト【新規】        ← 追加
Phase 8: Issue完遂チェック【新規】           ← 追加
```

---

## 6. 実装タスク一覧

| タスク | 優先度 | 対象ファイル |
|--------|--------|-------------|
| CLAUDE.mdプロジェクト位置づけ更新 | 高 | `CLAUDE.md` |
| Issue完遂チェックリスト追加 | 高 | `CLAUDE.md` |
| Phase 6 ドキュメンテーション必須化 | 高 | `.claude/commands/pm-auto-dev.md` |
| Phase 7 リグレッションテスト追加 | 高 | `.claude/commands/pm-auto-dev.md` |
| Phase 8 Issue完遂チェック追加 | 高 | `.claude/commands/pm-auto-dev.md` |
| pm-bug-fix 根本原因分析強化 | 中 | `.claude/commands/pm-bug-fix.md` |
| E2Eテストスクリプト再配置 | 中 | `scripts/e2e/` |
| myAgentDesk リグレッションテスト強化 | 中 | `myAgentDesk/tests/e2e/` |

---

## 7. 受入条件（Issue #400用）

### AC-1: CLAUDE.mdの更新
- [ ] プロジェクト位置づけテーブルが更新されている
- [ ] mySwiftAgentCore vs graphAiServer の使い分けが明記されている
- [ ] Issue完遂チェックリストが追加されている

### AC-2: pm-auto-devの更新
- [ ] Phase 6（ドキュメンテーション）が必須化されている
- [ ] Phase 7（リグレッションテスト）が追加されている
- [ ] Phase 8（Issue完遂チェック）が追加されている
- [ ] myAgentDeskのリグレッションテストにジョブ生成・実行が含まれている

### AC-3: pm-bug-fixの更新
- [ ] なぜなぜ分析（5 Whys）が追加されている
- [ ] 影響範囲調査が強化されている
- [ ] 再発防止策立案が追加されている

### AC-4: E2Eテストスクリプトの再配置
- [ ] mySwiftAgentCore/e2etest/ が scripts/e2e/myswiftagentcore/ に移動されている
- [ ] 統合E2Eテストスクリプト（scripts/e2e-test.sh）が作成されている

---

**作成日**: 2026-01-25
**更新日**: 2026-01-25（ユーザーフィードバック反映）
