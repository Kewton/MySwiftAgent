---
model: opus
description: "Issue要件に基づく自動受入テスト実行"
phase: "9. 品質保証"
session: "worktree"
---

# 受入テストスキル

## 概要
Issue要件に基づいて自動受入テストを実行し、品質保証を行うスキルです。

## 使用方法
- `/acceptance-test [Issue番号]`
- 「受入テストを実行してください」
- 「Issue #123の受入条件を検証してください」

## 実行内容

あなたは品質保証の専門家として、包括的な受入テストを実施し、Issue要件の充足を検証します。

### 📋 事前準備

1. **Issue要件の分析**
   - ユーザーストーリーの確認
   - 受入条件（Acceptance Criteria）の抽出
   - 非機能要件の確認

2. **テスト環境の準備**
   - Playwright環境の確認
   - APIテストツールの準備
   - テストデータの準備

### 🎯 テストケース自動生成

1. **受入条件からのテストケース導出**
   ```typescript
   // Example: Given-When-Then形式からテストケース生成
   test('ユーザーがログインできる', async ({ page }) => {
     // Given: ログインページが表示されている
     await page.goto('/login');

     // When: 正しい認証情報を入力してログインボタンをクリック
     await page.fill('#username', 'test_user');
     await page.fill('#password', 'secure_password');
     await page.click('#login-button');

     // Then: ダッシュボードに遷移する
     await expect(page).toHaveURL('/dashboard');
     await expect(page.locator('.welcome-message')).toContainText('Welcome, test_user');
   });
   ```

2. **テストシナリオのマトリクス生成**
   | シナリオ | 入力条件 | 期待結果 | 優先度 |
   |---------|---------|---------|--------|
   | 正常ログイン | 有効な認証情報 | ダッシュボード遷移 | 高 |
   | パスワード誤り | 無効なパスワード | エラーメッセージ表示 | 高 |
   | ユーザー不在 | 存在しないユーザー | エラーメッセージ表示 | 中 |
   | セッションタイムアウト | 30分無操作 | ログイン画面へリダイレクト | 中 |

### 🔍 テスト実行

#### 1. E2Eテスト（Playwright）

```typescript
// UIテストの実行
import { test, expect } from '@playwright/test';

test.describe('受入テストスイート', () => {
  test.beforeEach(async ({ page }) => {
    // テスト環境のセットアップ
    await page.goto(process.env.BASE_URL || 'http://localhost:3000');
  });

  test('機能テスト: ユーザー管理', async ({ page }) => {
    // ユーザー作成
    await page.click('[data-testid="add-user-button"]');
    await page.fill('[data-testid="user-name"]', 'New User');
    await page.fill('[data-testid="user-email"]', 'user@example.com');
    await page.click('[data-testid="save-button"]');

    // 検証
    await expect(page.locator('[data-testid="user-list"]')).toContainText('New User');

    // スクリーンショット保存
    await page.screenshot({ path: 'test-results/user-creation.png' });
  });

  test('レスポンシブデザインテスト', async ({ page }) => {
    // デスクトップ表示
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('.navbar')).toBeVisible();

    // モバイル表示
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('.hamburger-menu')).toBeVisible();
  });
});
```

#### 2. APIテスト

```typescript
// APIエンドポイントのテスト
import { test, expect } from '@playwright/test';

test('API: ユーザー作成エンドポイント', async ({ request }) => {
  const response = await request.post('/api/users', {
    data: {
      name: 'Test User',
      email: 'test@example.com',
      role: 'user'
    }
  });

  expect(response.status()).toBe(201);
  const user = await response.json();
  expect(user).toHaveProperty('id');
  expect(user.name).toBe('Test User');
});

test('API: エラーハンドリング', async ({ request }) => {
  const response = await request.post('/api/users', {
    data: {
      name: '', // 必須フィールドが空
      email: 'invalid-email' // 無効なメール形式
    }
  });

  expect(response.status()).toBe(400);
  const error = await response.json();
  expect(error.errors).toContainEqual(
    expect.objectContaining({
      field: 'name',
      message: expect.stringContaining('required')
    })
  );
});
```

#### 3. パフォーマンステスト

```typescript
test('パフォーマンス: ページ読み込み時間', async ({ page }) => {
  const startTime = Date.now();
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
  const loadTime = Date.now() - startTime;

  // 3秒以内に読み込み完了
  expect(loadTime).toBeLessThan(3000);

  // Core Web Vitalsの測定
  const metrics = await page.evaluate(() => ({
    LCP: performance.getEntriesByType('largest-contentful-paint')[0]?.startTime,
    FID: performance.getEntriesByType('first-input')[0]?.processingStart,
    CLS: performance.getEntriesByType('layout-shift')
      .reduce((sum, entry) => sum + entry.value, 0)
  }));

  expect(metrics.LCP).toBeLessThan(2500); // 2.5秒以内
  expect(metrics.CLS).toBeLessThan(0.1); // 0.1以内
});
```

### 📊 テスト結果の分析

1. **結果サマリの生成**
   ```
   =============================================
   受入テスト実行結果
   =============================================
   実行日時: 2024-11-07 10:30:00
   Issue: #123 - ユーザー管理機能の実装

   テスト結果:
   ✅ 合格: 18/20 (90%)
   ❌ 失敗: 2/20 (10%)
   ⏭️ スキップ: 0/20 (0%)

   カテゴリ別結果:
   - 機能テスト: 10/10 ✅
   - UIテスト: 6/7 (1失敗)
   - APIテスト: 2/3 (1失敗)
   - パフォーマンス: すべて基準内 ✅
   ```

2. **失敗テストの詳細分析**
   ```
   ❌ 失敗テスト #1
   テスト名: モバイルレスポンシブ - 横スクロール
   失敗理由: 画面幅320pxで横スクロールが発生
   スクリーンショット: ./test-results/mobile-scroll-issue.png
   推奨修正:
   - .container クラスに overflow-x: hidden を追加
   - テーブル要素を横スクロール可能なコンテナでラップ

   ❌ 失敗テスト #2
   テスト名: API - 大量データ処理
   失敗理由: 1000件以上のデータでタイムアウト
   実行時間: 5.2秒（期待値: 3秒以内）
   推奨修正:
   - ページネーションの実装
   - クエリの最適化（インデックス追加）
   ```

### 🔄 フィードバックループ

1. **合否判定**
   ```typescript
   function determineTestResult(results: TestResults): TestVerdict {
     const passRate = results.passed / results.total;
     const criticalFailures = results.failures.filter(f => f.priority === 'critical');

     if (criticalFailures.length > 0) {
       return {
         verdict: 'FAIL',
         reason: 'クリティカルなテストが失敗',
         action: 'RETURN_TO_DEVELOPMENT'
       };
     }

     if (passRate < 0.9) {
       return {
         verdict: 'FAIL',
         reason: '合格率が90%未満',
         action: 'RETURN_TO_DEVELOPMENT'
       };
     }

     return {
       verdict: 'PASS',
       action: 'PROCEED_TO_NEXT_PHASE'
     };
   }
   ```

2. **差し戻し時の詳細フィードバック**
   - 失敗したテストケースのリスト
   - 各失敗の根本原因分析
   - 推奨される修正方法
   - 修正の優先順位
   - 参考となるコードサンプル

### 📈 レポート生成

1. **HTMLレポート**
   - Playwrightの標準レポート
   - カスタムダッシュボード
   - スクリーンショット/動画付き

2. **Markdownレポート**
   ```markdown
   # 受入テストレポート - Issue #123

   ## 実行サマリ
   - 実行時間: 5分32秒
   - 総テスト数: 20
   - 合格率: 90%

   ## テスト詳細
   ### ✅ 合格したテスト (18)
   - [x] ユーザー作成機能
   - [x] ユーザー編集機能
   ...

   ### ❌ 失敗したテスト (2)
   - [ ] モバイルレスポンシブ表示
   - [ ] 大量データ処理性能

   ## 推奨アクション
   1. モバイル表示のCSS修正
   2. APIのパフォーマンス改善

   ## エビデンス
   - [テスト実行ログ](./logs/test-run.log)
   - [スクリーンショット](./screenshots/)
   - [パフォーマンスメトリクス](./metrics/performance.json)
   ```

## 出力フォーマット

### 1. テスト実行コマンド
```bash
# Playwrightテスト実行
npx playwright test --project=chromium

# レポート生成
npx playwright show-report
```

### 2. 結果サマリ
```
テスト実行完了
合格: X/Y (Z%)
判定: PASS/FAIL
次のアクション: 続行/差し戻し
```

### 3. 詳細レポートリンク
- HTMLレポート: `./playwright-report/index.html`
- 失敗テストの詳細: `./test-results/failures.md`
- 修正推奨事項: `./test-results/recommendations.md`

## 品質基準

- [ ] すべての受入条件がテストケース化されている
- [ ] クリティカルパスがE2Eテストでカバーされている
- [ ] エラーケースが適切にテストされている
- [ ] パフォーマンス基準を満たしている
- [ ] アクセシビリティ基準を満たしている
- [ ] セキュリティテストが実施されている

## 注意事項

- テスト実行前に最新のコードがビルドされていることを確認
- テストデータは独立して管理（テスト間の依存を避ける）
- 並列実行時の競合状態に注意
- スクリーンショットは失敗時のみ保存（ストレージ節約）
- 3回連続で同じテストが失敗したらエスカレーション