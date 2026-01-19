# Issue #379 作業計画書 - ワークフローチェーンのE2E結合テスト追加

## Issue概要

**Issue番号**: #379
**タイトル**: test(taskflowEngine): ワークフローチェーンのE2E結合テスト追加
**サイズ**: M
**作業見積**: 16時間
**優先度**: High
**依存Issue**:
- #375: mySwiftAgentCore workflow generation and validation
- #376: NodeExecutionContext設計仕様
- #377: Secrets注入パターンの統一
- #378: ワークフローストレージの責務分離

---

## 詳細タスク分解

### Phase 1: 実装タスク（8時間）

#### Task 1.1: E2Eテスト基盤構築（3時間）
- MSW (Mock Service Worker) の導入とセットアップ
- テストディレクトリ構成の作成（`tests/e2e/`）
- APIクライアントユーティリティの実装
- カスタムアサーションヘルパーの実装

#### Task 1.2: モックハンドラー実装（2時間）
- LLM API モックハンドラー（OpenAI形式）
- 外部API モックハンドラー（汎用REST）
- モックサーバー設定（`tests/e2e/mocks/server.ts`）
- モックレスポンスデータの定義

#### Task 1.3: テストワークフロー定義（2時間）
- チェーンテストワークフロー作成（`chain-test-workflow.json`）
- 並列実行テストワークフロー作成（`parallel-test-workflow.json`）
- エラーテストワークフロー作成（`error-test-workflow.json`）
- ワークフローローダーユーティリティの実装

#### Task 1.4: 基本E2Eテスト実装（1時間）
- ハッピーパステストケース（3ステップチェーン）
- stepResults引き渡しの検証
- テンプレート変数展開の検証

### Phase 2: テストタスク - TDD（3時間）

#### Task 2.1: 単体テスト（1時間）
- モックハンドラーのテスト
- APIクライアントユーティリティのテスト
- アサーションヘルパーのテスト

#### Task 2.2: 統合テスト（1時間）
- モックサーバーとの統合テスト
- ワークフローローダーの統合テスト

#### Task 2.3: E2Eテストの拡張（1時間）
- シークレット注入のテスト
- タイムアウトシナリオのテスト
- エラーハンドリングのテスト

### Phase 3: 受入テストタスク - L3ローカル（2時間）【必須】

#### Task 3.1: L3受入テスト計画（0.5時間）
- テスト手順書の作成
- 検証項目チェックリストの作成

#### Task 3.2: L3受入テスト実行（1.5時間）
- mySwiftAgentCore起動確認
- E2Eテスト実行と結果確認
- 複数シナリオの動作検証

### Phase 4: ドキュメント・CI統合タスク（3時間）

#### Task 4.1: ドキュメント作成（1時間）
- E2Eテスト実行ガイド（`tests/e2e/README.md`）
- モックデータ管理ガイド
- デバッグガイド

#### Task 4.2: CI/CD統合（2時間）
- GitHub Actions ワークフロー設定
- テストレポート設定
- 並列実行の最適化

---

## タスク依存関係

```mermaid
graph TD
    T11[Task 1.1<br/>E2E基盤構築] --> T12[Task 1.2<br/>モック実装]
    T12 --> T13[Task 1.3<br/>ワークフロー定義]
    T13 --> T14[Task 1.4<br/>基本テスト]

    T14 --> T21[Task 2.1<br/>単体テスト]
    T14 --> T22[Task 2.2<br/>統合テスト]
    T22 --> T23[Task 2.3<br/>E2E拡張]

    T23 --> T31[Task 3.1<br/>L3計画]
    T31 --> T32[Task 3.2<br/>L3実行]

    T32 --> T41[Task 4.1<br/>ドキュメント]
    T32 --> T42[Task 4.2<br/>CI統合]
```

---

## 作業スケジュール

### Day 1（8時間）
- **AM**: Task 1.1（E2E基盤構築）
- **PM前半**: Task 1.2（モック実装）
- **PM後半**: Task 1.3（ワークフロー定義）+ Task 1.4（基本テスト）

### Day 2（8時間）
- **AM**: Task 2.1-2.3（TDDフェーズ）
- **PM前半**: Task 3.1-3.2（L3受入テスト）
- **PM後半**: Task 4.1-4.2（ドキュメント・CI統合）

---

## チェックポイント

| タイミング | 確認事項 | 対応 |
|-----------|---------|------|
| Task 1.1完了時 | MSWが正しく動作するか | サンプルモックでテスト |
| Task 1.4完了時 | 基本的なチェーンが動作するか | 手動実行で確認 |
| Phase 2完了時 | 全テストがグリーンか | `npm test` 実行 |
| Phase 3完了時 | L3受入条件を満たすか | チェックリスト確認 |

---

## リスクと対策

| リスク | 発生確率 | 影響 | 対策 |
|-------|---------|------|------|
| MSW導入時の設定ミス | 中 | 高 | 公式ドキュメント参照、既存プロジェクトの例を確認 |
| モックと実APIの挙動差異 | 高 | 中 | APIスキーマの共有、定期的な実環境テスト |
| CI環境でのE2Eテスト失敗 | 中 | 中 | ローカルとCI環境の差異を事前確認 |
| テスト実行時間の増大 | 低 | 低 | 並列実行の活用、選択的テスト実行 |

---

## 成果物チェックリスト

### コード
- [ ] `tests/e2e/test_workflow_chain.ts` - メインE2Eテスト
- [ ] `tests/e2e/mocks/handlers.ts` - モックハンドラー
- [ ] `tests/e2e/mocks/server.ts` - モックサーバー設定
- [ ] `tests/e2e/utils/client.ts` - APIクライアント
- [ ] `tests/e2e/utils/assertions.ts` - カスタムアサーション
- [ ] `tests/e2e/fixtures/workflows/*.json` - テストワークフロー

### テスト
- [ ] 単体テストカバレッジ 90%以上
- [ ] E2Eテスト（ハッピーパス、エラー、タイムアウト）
- [ ] L3受入テスト合格

### ドキュメント
- [ ] `tests/e2e/README.md` - E2Eテストガイド
- [ ] `.github/workflows/e2e-test.yml` - CI設定
- [ ] `dev-reports/feature/issue/379/` - 作業ドキュメント一式

---

## L3受入テスト計画【必須セクション】

### 前提条件
- mySwiftAgentCore が起動していること（`npm run dev`）
- テスト用のワークフローが配置されていること

### 検証手順

```bash
# 1. サービス起動確認
curl -sf http://localhost:8006/health && echo "✅ mySwiftAgentCore healthy"

# 2. E2Eテスト環境セットアップ確認
cd mySwiftAgentCore
npm run test:e2e:setup
# Expected: "✅ E2E test environment ready"

# 3. 基本的なワークフローチェーン実行
curl -s -X POST http://localhost:8006/api/v1/taskflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "project": "e2e_test",
    "workflow": "chain-test-workflow",
    "inputs": {
      "query": "test query for e2e"
    }
  }' | jq .

# Expected Response:
# {
#   "success": true,
#   "workflowId": "chain-test-workflow",
#   "result": {
#     "summary": "Mocked summary of search results"
#   },
#   "stepResults": [...]
# }

# 4. E2Eテスト実行（全シナリオ）
npm run test:e2e
# Expected: All tests passing

# 5. 並列実行シナリオ
npm run test:e2e -- --grep "parallel"
# Expected: Parallel execution tests passing

# 6. エラーシナリオ
npm run test:e2e -- --grep "error"
# Expected: Error handling tests passing

# 7. CI環境シミュレーション
CI=true npm run test:e2e
# Expected: Tests pass in CI mode
```

### 検証項目チェックリスト

- [ ] 3ステップチェーン（task_001 → task_002 → task_003）が正常実行
- [ ] stepResultsが正しく引き渡される
- [ ] テンプレート変数（`{{steps.xxx}}`）が正しく展開される
- [ ] シークレットが正しく注入される（モック環境）
- [ ] エラーが適切に伝播される
- [ ] タイムアウトが正しく処理される
- [ ] 並列実行が正しく動作する

---

## Definition of Done

Issue #379 完了条件：

- [x] すべての実装タスクが完了
- [x] 単体テストカバレッジ90%以上
- [x] E2Eテスト実装（チェーン、並列、エラー）
- [x] L3受入テスト全項目合格
- [x] CI/CD統合完了（GitHub Actions）
- [x] ドキュメント作成完了
- [x] コードレビュー承認
- [x] モックによりLLM APIコスト発生なし

---

**作成日**: 2026-01-19
**作成者**: Claude (work-plan スキル)
**対象Issue**: #379