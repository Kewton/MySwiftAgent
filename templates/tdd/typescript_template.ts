/**
 * TDD実装テンプレート - TypeScript版
 * 機能: [機能名をここに記載]
 * Issue: #[Issue番号]
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';

// ========================================
// 🔴 RED PHASE - 失敗するテストを書く
// ========================================

describe('UserAuthentication', () => {
  describe('正常系テスト', () => {
    it('有効な認証情報でログインできる', async () => {
      // Arrange
      const username = 'test_user';
      const password = 'secure_password_123';

      // Act
      const result = await authenticateUser(username, password);

      // Assert
      expect(result.isAuthenticated).toBe(true);
      expect(result.user?.username).toBe(username);
      expect(result.token).toBeDefined();
    });

    it('ログイン成功後にセッションが作成される', async () => {
      // Arrange
      const username = 'test_user';
      const password = 'secure_password_123';

      // Act
      const result = await authenticateUser(username, password);
      const session = await getSession(result.token!);

      // Assert
      expect(session).toBeDefined();
      expect(session?.userId).toBe(result.user?.id);
      expect(session?.expiresAt).toBeInstanceOf(Date);
    });
  });

  describe('異常系テスト', () => {
    it('無効なパスワードでログイン失敗', async () => {
      // Arrange
      const username = 'test_user';
      const password = 'wrong_password';

      // Act
      const result = await authenticateUser(username, password);

      // Assert
      expect(result.isAuthenticated).toBe(false);
      expect(result.errorMessage).toBe('Invalid credentials');
      expect(result.user).toBeNull();
    });

    it('存在しないユーザーでログイン失敗', async () => {
      // Arrange
      const username = 'non_existent_user';
      const password = 'any_password';

      // Act
      const result = await authenticateUser(username, password);

      // Assert
      expect(result.isAuthenticated).toBe(false);
      expect(result.errorMessage).toBe('User not found');
      expect(result.user).toBeNull();
    });

    it('空文字でのログイン失敗', async () => {
      // Act & Assert
      await expect(authenticateUser('', 'password'))
        .rejects.toThrow('Username cannot be empty');

      await expect(authenticateUser('username', ''))
        .rejects.toThrow('Password cannot be empty');
    });

    describe.each([
      ['u'.repeat(256), 'password', 'Username too long'],
      ['username', 'p'.repeat(256), 'Password too long'],
      ['user@', 'password', 'Invalid username format'],
      ['username', 'pass', 'Password too short'],
    ])('入力検証エラー', (username, password, expectedError) => {
      it(`${expectedError} の場合エラーになる`, async () => {
        await expect(authenticateUser(username, password))
          .rejects.toThrow(expectedError);
      });
    });
  });

  describe('セキュリティテスト', () => {
    it('SQLインジェクション対策', async () => {
      // Arrange
      const maliciousUsername = "admin' OR '1'='1";
      const password = 'password';

      // Act
      const result = await authenticateUser(maliciousUsername, password);

      // Assert
      expect(result.isAuthenticated).toBe(false);
      expect(result.errorMessage).toBe('Invalid username format');
    });

    it('ブルートフォース対策', async () => {
      // Arrange
      const username = 'test_user';
      const wrongPassword = 'wrong_password';
      const attempts = [];

      // Act - 5回連続で失敗
      for (let i = 0; i < 5; i++) {
        attempts.push(await authenticateUser(username, wrongPassword));
      }

      // Assert - 5回目以降はレート制限
      expect(attempts[4].errorMessage).toContain('Too many attempts');
    });
  });
});

// ========================================
// 🟢 GREEN PHASE - テストを通す最小限の実装
// ========================================

interface User {
  id: number;
  username: string;
  email?: string;
}

interface AuthResult {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  errorMessage: string | null;
}

interface Session {
  userId: number;
  token: string;
  expiresAt: Date;
}

// 仮のユーザーデータベース
const MOCK_USERS = new Map<string, {
  id: number;
  username: string;
  passwordHash: string;
  email: string;
}>([
  ['test_user', {
    id: 1,
    username: 'test_user',
    passwordHash: hashPassword('secure_password_123'),
    email: 'test@example.com'
  }]
]);

// セッションストア
const sessions = new Map<string, Session>();

// ログイン試行記録
const loginAttempts = new Map<string, { count: number; lastAttempt: Date }>();

function hashPassword(password: string): string {
  // 実際の実装ではbcryptなどを使用
  return Buffer.from(password).toString('base64');
}

function generateToken(): string {
  // 実際の実装ではcrypto.randomBytesなどを使用
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

async function authenticateUser(
  username: string,
  password: string
): Promise<AuthResult> {
  // 入力検証
  if (!username) {
    throw new Error('Username cannot be empty');
  }
  if (!password) {
    throw new Error('Password cannot be empty');
  }
  if (username.length > 255) {
    throw new Error('Username too long');
  }
  if (password.length > 255) {
    throw new Error('Password too long');
  }
  if (username.includes('@') || username.includes("'")) {
    return {
      isAuthenticated: false,
      user: null,
      token: null,
      errorMessage: 'Invalid username format'
    };
  }
  if (password.length < 8) {
    throw new Error('Password too short');
  }

  // レート制限チェック
  const attempts = loginAttempts.get(username);
  if (attempts) {
    const timeSinceLastAttempt = Date.now() - attempts.lastAttempt.getTime();
    if (attempts.count >= 5 && timeSinceLastAttempt < 60000) {
      return {
        isAuthenticated: false,
        user: null,
        token: null,
        errorMessage: 'Too many attempts. Please try again later.'
      };
    }
  }

  // ユーザー存在確認
  const userData = MOCK_USERS.get(username);
  if (!userData) {
    updateLoginAttempts(username, false);
    return {
      isAuthenticated: false,
      user: null,
      token: null,
      errorMessage: 'User not found'
    };
  }

  // パスワード検証
  const passwordHash = hashPassword(password);
  if (passwordHash !== userData.passwordHash) {
    updateLoginAttempts(username, false);
    return {
      isAuthenticated: false,
      user: null,
      token: null,
      errorMessage: 'Invalid credentials'
    };
  }

  // 認証成功
  updateLoginAttempts(username, true);
  const user: User = {
    id: userData.id,
    username: userData.username,
    email: userData.email
  };

  const token = generateToken();

  // セッション作成
  sessions.set(token, {
    userId: user.id,
    token,
    expiresAt: new Date(Date.now() + 3600000) // 1時間後
  });

  return {
    isAuthenticated: true,
    user,
    token,
    errorMessage: null
  };
}

function updateLoginAttempts(username: string, success: boolean): void {
  if (success) {
    loginAttempts.delete(username);
  } else {
    const current = loginAttempts.get(username) || { count: 0, lastAttempt: new Date() };
    loginAttempts.set(username, {
      count: current.count + 1,
      lastAttempt: new Date()
    });
  }
}

async function getSession(token: string): Promise<Session | null> {
  const session = sessions.get(token);
  if (!session) {
    return null;
  }

  // セッション有効期限チェック
  if (session.expiresAt < new Date()) {
    sessions.delete(token);
    return null;
  }

  return session;
}

// ========================================
// 🔵 REFACTOR PHASE - コードを改善する
// ========================================

// リポジトリパターンの適用
class UserRepository {
  async findByUsername(username: string): Promise<User | null> {
    const userData = MOCK_USERS.get(username);
    if (!userData) {
      return null;
    }
    return {
      id: userData.id,
      username: userData.username,
      email: userData.email
    };
  }

  async verifyPassword(username: string, password: string): Promise<boolean> {
    const userData = MOCK_USERS.get(username);
    if (!userData) {
      return false;
    }
    return hashPassword(password) === userData.passwordHash;
  }
}

// サービスクラスの分離
class SessionService {
  private sessions = new Map<string, Session>();

  createSession(userId: number): string {
    const token = generateToken();
    this.sessions.set(token, {
      userId,
      token,
      expiresAt: new Date(Date.now() + 3600000)
    });
    return token;
  }

  getSession(token: string): Session | null {
    const session = this.sessions.get(token);
    if (!session) {
      return null;
    }

    if (session.expiresAt < new Date()) {
      this.sessions.delete(token);
      return null;
    }

    return session;
  }
}

// レート制限サービス
class RateLimiter {
  private attempts = new Map<string, { count: number; lastAttempt: Date }>();
  private readonly maxAttempts = 5;
  private readonly windowMs = 60000;

  isBlocked(key: string): boolean {
    const attempt = this.attempts.get(key);
    if (!attempt) {
      return false;
    }

    const timeSinceLastAttempt = Date.now() - attempt.lastAttempt.getTime();
    return attempt.count >= this.maxAttempts && timeSinceLastAttempt < this.windowMs;
  }

  recordAttempt(key: string, success: boolean): void {
    if (success) {
      this.attempts.delete(key);
    } else {
      const current = this.attempts.get(key) || { count: 0, lastAttempt: new Date() };
      this.attempts.set(key, {
        count: current.count + 1,
        lastAttempt: new Date()
      });
    }
  }
}

// 入力検証クラス
class InputValidator {
  validateCredentials(username: string, password: string): void {
    if (!username) {
      throw new Error('Username cannot be empty');
    }
    if (!password) {
      throw new Error('Password cannot be empty');
    }
    if (username.length > 255) {
      throw new Error('Username too long');
    }
    if (password.length > 255) {
      throw new Error('Password too long');
    }
    if (password.length < 8) {
      throw new Error('Password too short');
    }
  }

  isValidUsernameFormat(username: string): boolean {
    return !username.includes('@') && !username.includes("'");
  }
}

// 認証サービス（リファクタリング版）
class AuthenticationService {
  constructor(
    private userRepository: UserRepository,
    private sessionService: SessionService,
    private rateLimiter: RateLimiter,
    private validator: InputValidator
  ) {}

  async authenticate(username: string, password: string): Promise<AuthResult> {
    // 入力検証
    this.validator.validateCredentials(username, password);

    if (!this.validator.isValidUsernameFormat(username)) {
      return this.createFailureResult('Invalid username format');
    }

    // レート制限チェック
    if (this.rateLimiter.isBlocked(username)) {
      return this.createFailureResult('Too many attempts. Please try again later.');
    }

    // ユーザー検証
    const user = await this.userRepository.findByUsername(username);
    if (!user) {
      this.rateLimiter.recordAttempt(username, false);
      return this.createFailureResult('User not found');
    }

    // パスワード検証
    const isValidPassword = await this.userRepository.verifyPassword(username, password);
    if (!isValidPassword) {
      this.rateLimiter.recordAttempt(username, false);
      return this.createFailureResult('Invalid credentials');
    }

    // 認証成功
    this.rateLimiter.recordAttempt(username, true);
    const token = this.sessionService.createSession(user.id);

    return {
      isAuthenticated: true,
      user,
      token,
      errorMessage: null
    };
  }

  private createFailureResult(errorMessage: string): AuthResult {
    return {
      isAuthenticated: false,
      user: null,
      token: null,
      errorMessage
    };
  }
}

// エクスポート用のファサード
const authService = new AuthenticationService(
  new UserRepository(),
  new SessionService(),
  new RateLimiter(),
  new InputValidator()
);

export { authenticateUser, getSession, AuthResult, User, Session };

// ========================================
// 📊 COVERAGE CHECK - カバレッジ確認
// ========================================

// package.json に以下のスクリプトを追加:
// "test:tdd": "jest --coverage --coverageDirectory=test-results/coverage/tdd --coverageThreshold='{\"global\":{\"branches\":80,\"functions\":90,\"lines\":90,\"statements\":90}}'"