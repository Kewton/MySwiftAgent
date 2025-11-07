/**
 * 受入テストサンプルシナリオ - ユーザー管理機能
 * Issue: #123 - ユーザー管理機能の実装
 *
 * 受入条件:
 * 1. ユーザーは新規アカウントを作成できる
 * 2. ユーザーはログインできる
 * 3. ユーザーはプロフィールを更新できる
 * 4. 管理者はユーザー一覧を表示できる
 */

import { test, expect, Page } from '@playwright/test';
import { UserTestHelper } from './helpers/user-test-helper';

// ========================================
// テスト設定とヘルパー
// ========================================

const testData = {
  newUser: {
    username: `test_user_${Date.now()}`,
    email: `test_${Date.now()}@example.com`,
    password: 'SecurePass123!',
    fullName: 'Test User'
  },
  adminUser: {
    username: 'admin',
    password: 'AdminPass123!'
  }
};

// ページオブジェクトモデル
class UserManagementPage {
  constructor(private page: Page) {}

  async navigateToSignUp() {
    await this.page.goto('/signup');
    await this.page.waitForSelector('[data-testid="signup-form"]');
  }

  async navigateToLogin() {
    await this.page.goto('/login');
    await this.page.waitForSelector('[data-testid="login-form"]');
  }

  async fillSignUpForm(userData: typeof testData.newUser) {
    await this.page.fill('[data-testid="username-input"]', userData.username);
    await this.page.fill('[data-testid="email-input"]', userData.email);
    await this.page.fill('[data-testid="password-input"]', userData.password);
    await this.page.fill('[data-testid="confirm-password-input"]', userData.password);
    await this.page.fill('[data-testid="fullname-input"]', userData.fullName);
  }

  async submitSignUp() {
    await this.page.click('[data-testid="signup-submit"]');
  }

  async login(username: string, password: string) {
    await this.page.fill('[data-testid="username-input"]', username);
    await this.page.fill('[data-testid="password-input"]', password);
    await this.page.click('[data-testid="login-submit"]');
  }

  async isLoggedIn(): Promise<boolean> {
    try {
      await this.page.waitForSelector('[data-testid="user-menu"]', { timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  async logout() {
    await this.page.click('[data-testid="user-menu"]');
    await this.page.click('[data-testid="logout-button"]');
  }
}

// ========================================
// 受入テストシナリオ
// ========================================

test.describe('ユーザー管理機能の受入テスト', () => {
  let page: Page;
  let userPage: UserManagementPage;

  test.beforeEach(async ({ page: testPage }) => {
    page = testPage;
    userPage = new UserManagementPage(page);
  });

  test.describe('UC-001: 新規ユーザー登録', () => {
    test('正常な情報で新規ユーザーを作成できる', async () => {
      // Given: ユーザー登録ページにアクセスしている
      await userPage.navigateToSignUp();

      // When: 有効なユーザー情報を入力して送信する
      await userPage.fillSignUpForm(testData.newUser);
      await userPage.submitSignUp();

      // Then: 登録が成功し、ウェルカムページに遷移する
      await expect(page).toHaveURL('/welcome');
      await expect(page.locator('[data-testid="welcome-message"]'))
        .toContainText(`Welcome, ${testData.newUser.fullName}!`);

      // And: 確認メールが送信される（メッセージ表示を確認）
      await expect(page.locator('[data-testid="email-sent-notification"]'))
        .toBeVisible();
      await expect(page.locator('[data-testid="email-sent-notification"]'))
        .toContainText('Confirmation email has been sent');

      // スクリーンショットを保存
      await page.screenshot({
        path: 'test-results/screenshots/user-registration-success.png',
        fullPage: true
      });
    });

    test('重複するユーザー名でエラーが表示される', async () => {
      // Given: 既存のユーザー名を使用
      const duplicateUser = {
        ...testData.newUser,
        username: 'existing_user'
      };

      await userPage.navigateToSignUp();

      // When: 重複するユーザー名で登録を試みる
      await userPage.fillSignUpForm(duplicateUser);
      await userPage.submitSignUp();

      // Then: エラーメッセージが表示される
      await expect(page.locator('[data-testid="error-message"]'))
        .toContainText('Username already exists');

      // And: フォームはリセットされない
      await expect(page.locator('[data-testid="email-input"]'))
        .toHaveValue(duplicateUser.email);
    });

    test('パスワードの強度検証が機能する', async () => {
      await userPage.navigateToSignUp();

      // 弱いパスワードを入力
      await page.fill('[data-testid="password-input"]', 'weak');

      // パスワード強度インジケーターを確認
      await expect(page.locator('[data-testid="password-strength"]'))
        .toHaveAttribute('data-strength', 'weak');
      await expect(page.locator('[data-testid="password-requirements"]'))
        .toBeVisible();

      // 強いパスワードを入力
      await page.fill('[data-testid="password-input"]', 'StrongP@ssw0rd123!');
      await expect(page.locator('[data-testid="password-strength"]'))
        .toHaveAttribute('data-strength', 'strong');
    });
  });

  test.describe('UC-002: ユーザーログイン', () => {
    test('正しい認証情報でログインできる', async () => {
      // Given: ログインページにアクセスしている
      await userPage.navigateToLogin();

      // When: 有効な認証情報を入力してログインする
      await userPage.login('test_user', 'SecurePass123!');

      // Then: ダッシュボードに遷移する
      await expect(page).toHaveURL('/dashboard');
      await expect(await userPage.isLoggedIn()).toBe(true);

      // And: ユーザーメニューに名前が表示される
      await expect(page.locator('[data-testid="user-menu"]'))
        .toContainText('test_user');
    });

    test('無効な認証情報でログイン失敗', async () => {
      await userPage.navigateToLogin();

      // 無効なパスワードでログイン試行
      await userPage.login('test_user', 'WrongPassword');

      // エラーメッセージが表示される
      await expect(page.locator('[data-testid="login-error"]'))
        .toContainText('Invalid username or password');

      // ログインページに留まる
      await expect(page).toHaveURL('/login');
    });

    test('連続ログイン失敗でアカウントロック', async () => {
      await userPage.navigateToLogin();

      // 5回連続でログイン失敗
      for (let i = 0; i < 5; i++) {
        await userPage.login('test_user', 'WrongPassword');
        await page.waitForTimeout(500);
      }

      // アカウントロックメッセージが表示される
      await expect(page.locator('[data-testid="account-locked"]'))
        .toContainText('Account locked due to multiple failed attempts');

      // キャプチャが表示される
      await expect(page.locator('[data-testid="captcha"]')).toBeVisible();
    });
  });

  test.describe('UC-003: プロフィール更新', () => {
    test.beforeEach(async () => {
      // 事前にログイン
      await userPage.navigateToLogin();
      await userPage.login('test_user', 'SecurePass123!');
      await page.goto('/profile');
    });

    test('プロフィール情報を更新できる', async () => {
      // Given: プロフィールページにいる
      await expect(page).toHaveURL('/profile');

      // When: プロフィール情報を更新する
      await page.fill('[data-testid="fullname-input"]', 'Updated Name');
      await page.fill('[data-testid="bio-input"]', 'This is my bio');
      await page.selectOption('[data-testid="timezone-select"]', 'Asia/Tokyo');
      await page.click('[data-testid="save-profile"]');

      // Then: 成功メッセージが表示される
      await expect(page.locator('[data-testid="success-message"]'))
        .toContainText('Profile updated successfully');

      // And: 更新された情報が表示される
      await page.reload();
      await expect(page.locator('[data-testid="fullname-input"]'))
        .toHaveValue('Updated Name');
    });

    test('プロフィール画像をアップロードできる', async () => {
      // ファイル選択ダイアログをトリガー
      const fileInput = page.locator('[data-testid="avatar-upload"]');
      await fileInput.setInputFiles('templates/acceptance/test-assets/avatar.jpg');

      // アップロード完了を待つ
      await expect(page.locator('[data-testid="upload-progress"]'))
        .toHaveAttribute('data-status', 'complete');

      // 新しいアバターが表示される
      await expect(page.locator('[data-testid="user-avatar"]'))
        .toHaveAttribute('src', /avatar.*\.jpg/);
    });
  });

  test.describe('UC-004: 管理者機能', () => {
    test.beforeEach(async () => {
      // 管理者としてログイン
      await userPage.navigateToLogin();
      await userPage.login(testData.adminUser.username, testData.adminUser.password);
    });

    test('管理者はユーザー一覧を表示できる', async () => {
      // Given: 管理者ダッシュボードにアクセス
      await page.goto('/admin/users');

      // Then: ユーザー一覧が表示される
      await expect(page.locator('[data-testid="users-table"]')).toBeVisible();

      // And: ユーザー数が表示される
      const userCount = await page.locator('[data-testid="user-row"]').count();
      expect(userCount).toBeGreaterThan(0);

      // And: 各ユーザーに対してアクションボタンがある
      const firstUserRow = page.locator('[data-testid="user-row"]').first();
      await expect(firstUserRow.locator('[data-testid="edit-user"]')).toBeVisible();
      await expect(firstUserRow.locator('[data-testid="disable-user"]')).toBeVisible();
    });

    test('管理者はユーザーを検索できる', async () => {
      await page.goto('/admin/users');

      // 検索機能をテスト
      await page.fill('[data-testid="search-users"]', 'test');
      await page.click('[data-testid="search-button"]');

      // 検索結果が表示される
      await expect(page.locator('[data-testid="search-results"]'))
        .toContainText('Found');

      // フィルターされたユーザーのみ表示
      const userRows = page.locator('[data-testid="user-row"]');
      const count = await userRows.count();
      for (let i = 0; i < count; i++) {
        const username = await userRows.nth(i).locator('[data-testid="username"]').textContent();
        expect(username?.toLowerCase()).toContain('test');
      }
    });

    test('管理者はユーザーを無効化できる', async () => {
      await page.goto('/admin/users');

      // 最初のユーザーを無効化
      const firstUserRow = page.locator('[data-testid="user-row"]').first();
      const username = await firstUserRow.locator('[data-testid="username"]').textContent();

      await firstUserRow.locator('[data-testid="disable-user"]').click();

      // 確認ダイアログが表示される
      await expect(page.locator('[data-testid="confirm-dialog"]'))
        .toContainText(`Are you sure you want to disable user ${username}?`);

      await page.click('[data-testid="confirm-button"]');

      // 成功メッセージが表示される
      await expect(page.locator('[data-testid="success-message"]'))
        .toContainText('User has been disabled');

      // ユーザーのステータスが更新される
      await expect(firstUserRow.locator('[data-testid="user-status"]'))
        .toHaveText('Disabled');
    });
  });

  // ========================================
  // パフォーマンステスト
  // ========================================

  test.describe('パフォーマンス要件', () => {
    test('ログインページは3秒以内に読み込まれる', async () => {
      const startTime = Date.now();
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(3000);
    });

    test('ユーザー一覧は1000件でも5秒以内に表示される', async () => {
      // 管理者としてログイン
      await userPage.navigateToLogin();
      await userPage.login(testData.adminUser.username, testData.adminUser.password);

      const startTime = Date.now();
      await page.goto('/admin/users?limit=1000');
      await page.waitForSelector('[data-testid="users-table"]');
      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(5000);
    });
  });

  // ========================================
  // アクセシビリティテスト
  // ========================================

  test.describe('アクセシビリティ要件', () => {
    test('キーボードのみで操作できる', async () => {
      await page.goto('/login');

      // Tabキーでフォーカス移動
      await page.keyboard.press('Tab'); // username
      await page.keyboard.type('test_user');
      await page.keyboard.press('Tab'); // password
      await page.keyboard.type('SecurePass123!');
      await page.keyboard.press('Tab'); // submit button
      await page.keyboard.press('Enter');

      // ログイン成功を確認
      await expect(page).toHaveURL('/dashboard');
    });

    test('スクリーンリーダー対応', async () => {
      await page.goto('/signup');

      // ARIA属性が適切に設定されている
      await expect(page.locator('[data-testid="username-input"]'))
        .toHaveAttribute('aria-label', 'Username');
      await expect(page.locator('[data-testid="email-input"]'))
        .toHaveAttribute('aria-label', 'Email address');
      await expect(page.locator('[data-testid="password-input"]'))
        .toHaveAttribute('aria-label', 'Password');

      // エラーメッセージにaria-live属性
      await page.fill('[data-testid="username-input"]', 'a'); // 短すぎる
      await page.click('[data-testid="signup-submit"]');
      await expect(page.locator('[data-testid="error-message"]'))
        .toHaveAttribute('aria-live', 'polite');
    });
  });
});

// ========================================
// テスト後処理
// ========================================

test.afterAll(async () => {
  // テスト結果のサマリを生成
  console.log('✅ 受入テスト完了');
  console.log('📊 詳細レポートは test-results/playwright-report/index.html を参照');
});