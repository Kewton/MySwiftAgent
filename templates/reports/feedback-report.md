# 📊 品質保証フィードバックレポート

**実行日時**: {{execution_date}}
**Issue番号**: #{{issue_number}}
**機能名**: {{feature_name}}
**実行環境**: {{environment}}

---

## 📈 実行サマリ

| 項目 | 結果 |
|------|------|
| **判定** | {{verdict}} |
| **総テスト数** | {{total_tests}} |
| **成功** | ✅ {{passed_tests}} ({{pass_rate}}%) |
| **失敗** | ❌ {{failed_tests}} ({{fail_rate}}%) |
| **スキップ** | ⏭️ {{skipped_tests}} ({{skip_rate}}%) |
| **実行時間** | ⏱️ {{execution_time}} |

### テストカバレッジ

| メトリクス | 達成値 | 目標値 | 状態 |
|-----------|--------|--------|------|
| **行カバレッジ** | {{line_coverage}}% | 90% | {{line_status}} |
| **分岐カバレッジ** | {{branch_coverage}}% | 80% | {{branch_status}} |
| **関数カバレッジ** | {{function_coverage}}% | 90% | {{function_status}} |

---

## 🎯 受入条件の検証結果

### ✅ 合格した受入条件

{{#each passed_acceptance_criteria}}
- [x] **{{this.criteria}}**
  - テストケース: {{this.test_name}}
  - 実行時間: {{this.execution_time}}ms
{{/each}}

### ❌ 不合格の受入条件

{{#each failed_acceptance_criteria}}
- [ ] **{{this.criteria}}**
  - テストケース: {{this.test_name}}
  - 失敗理由: {{this.failure_reason}}
  - エラーメッセージ: `{{this.error_message}}`
  - スクリーンショット: [{{this.screenshot}}]({{this.screenshot_path}})
{{/each}}

---

## 🔍 失敗分析

### 失敗テスト詳細

{{#each failed_tests_detail}}
#### {{@index}}. {{this.test_name}}

**ファイル**: `{{this.file}}:{{this.line}}`
**カテゴリ**: {{this.category}}
**優先度**: {{this.priority}}

**失敗内容**:
```
{{this.actual_result}}
```

**期待される結果**:
```
{{this.expected_result}}
```

**スタックトレース**:
```
{{this.stack_trace}}
```

**再現手順**:
1. {{this.step1}}
2. {{this.step2}}
3. {{this.step3}}

---
{{/each}}

## 💡 改善推奨事項

### 🔴 緊急対応が必要な項目

{{#each critical_issues}}
1. **{{this.title}}**
   - 影響範囲: {{this.impact}}
   - 推奨対応: {{this.recommendation}}
   - 参考コード:
   ```{{this.language}}
   {{this.code_sample}}
   ```
{{/each}}

### 🟡 中期的な改善項目

{{#each medium_priority_issues}}
1. **{{this.title}}**
   - 現状: {{this.current_state}}
   - 改善案: {{this.improvement}}
   - 期待効果: {{this.expected_benefit}}
{{/each}}

### 🟢 将来的な検討事項

{{#each future_considerations}}
- {{this.item}}
{{/each}}

---

## 📊 パフォーマンス分析

### レスポンスタイム

| エンドポイント/ページ | 平均時間 | 最大時間 | 基準値 | 判定 |
|---------------------|---------|---------|--------|------|
{{#each performance_metrics}}
| {{this.endpoint}} | {{this.avg_time}}ms | {{this.max_time}}ms | {{this.threshold}}ms | {{this.status}} |
{{/each}}

### Core Web Vitals

| メトリクス | 測定値 | 目標値 | 状態 |
|-----------|--------|--------|------|
| **LCP** (Largest Contentful Paint) | {{lcp}}s | < 2.5s | {{lcp_status}} |
| **FID** (First Input Delay) | {{fid}}ms | < 100ms | {{fid_status}} |
| **CLS** (Cumulative Layout Shift) | {{cls}} | < 0.1 | {{cls_status}} |

---

## 🔄 差し戻し判定

### 判定結果: **{{return_decision}}**

{{#if should_return}}
### 差し戻し理由

1. {{return_reason_1}}
2. {{return_reason_2}}
3. {{return_reason_3}}

### 修正必須項目

| 優先度 | 項目 | 推定作業時間 | 担当推奨 |
|--------|------|-------------|----------|
{{#each required_fixes}}
| {{this.priority}} | {{this.item}} | {{this.estimated_hours}}h | {{this.suggested_assignee}} |
{{/each}}

### 再テスト条件

- [ ] すべての必須修正項目が完了
- [ ] 単体テストカバレッジ90%以上
- [ ] 失敗していた受入テストが成功
- [ ] パフォーマンス基準を満たす

{{else}}
### 次工程への移行承認

✅ すべての受入条件を満たしています。次の工程へ進めることができます。

**承認条件**:
- 受入テスト合格率: {{pass_rate}}%（基準: 90%以上）
- カバレッジ達成: {{coverage_achieved}}
- パフォーマンス基準: クリア
- セキュリティチェック: パス

{{/if}}

---

## 📎 エビデンス

### テスト実行ログ
- [完全なテストログ](./test-results/full-test-log.txt)
- [エラーログのみ](./test-results/error-log.txt)

### スクリーンショット・動画
- [失敗時のスクリーンショット](./test-results/screenshots/failures/)
- [テスト実行動画](./test-results/videos/)

### カバレッジレポート
- [HTMLカバレッジレポート](./test-results/coverage/lcov-report/index.html)
- [カバレッジサマリ](./test-results/coverage/coverage-summary.json)

### パフォーマンスデータ
- [Lighthouse レポート](./test-results/lighthouse-report.html)
- [パフォーマンストレース](./test-results/performance-trace.json)

---

## 🎬 アクションアイテム

### 即座に対応が必要

- [ ] {{action_item_1}}
- [ ] {{action_item_2}}
- [ ] {{action_item_3}}

### 次のスプリントで対応

- [ ] {{next_sprint_item_1}}
- [ ] {{next_sprint_item_2}}

### バックログへ追加

- [ ] {{backlog_item_1}}
- [ ] {{backlog_item_2}}

---

## 📝 レビュアーコメント

**レビュアー**: {{reviewer_name}}
**レビュー日時**: {{review_date}}

{{reviewer_comments}}

---

## 🔄 イテレーション履歴

| イテレーション | 日時 | 合格率 | 主な修正内容 |
|--------------|------|--------|-------------|
{{#each iteration_history}}
| {{this.iteration}} | {{this.date}} | {{this.pass_rate}}% | {{this.fixes}} |
{{/each}}

---

**レポート生成**: 自動生成 by TDD/受入テストスキル
**バージョン**: v1.0.0
**次回実行予定**: {{next_execution_schedule}}