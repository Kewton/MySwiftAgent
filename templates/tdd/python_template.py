"""
TDD実装テンプレート - Python版
機能: [機能名をここに記載]
Issue: #[Issue番号]
"""

import pytest
from typing import Optional, Dict, Any
from unittest.mock import Mock, patch

# ========================================
# 🔴 RED PHASE - 失敗するテストを書く
# ========================================

class TestUserAuthentication:
    """ユーザー認証機能のテストクラス"""

    def test_正常なログイン(self):
        """
        Given: 有効なユーザー名とパスワード
        When: ログインを実行
        Then: 認証成功し、ユーザーオブジェクトが返される
        """
        # Arrange
        username = "test_user"
        password = "secure_password_123"

        # Act
        result = authenticate_user(username, password)

        # Assert
        assert result.is_authenticated is True
        assert result.user.username == username
        assert result.token is not None

    def test_無効なパスワードでログイン失敗(self):
        """
        Given: 有効なユーザー名と無効なパスワード
        When: ログインを実行
        Then: 認証失敗し、適切なエラーメッセージが返される
        """
        # Arrange
        username = "test_user"
        password = "wrong_password"

        # Act
        result = authenticate_user(username, password)

        # Assert
        assert result.is_authenticated is False
        assert result.error_message == "Invalid credentials"
        assert result.user is None

    def test_存在しないユーザーでログイン失敗(self):
        """
        Given: 存在しないユーザー名
        When: ログインを実行
        Then: 認証失敗し、適切なエラーメッセージが返される
        """
        # Arrange
        username = "non_existent_user"
        password = "any_password"

        # Act
        result = authenticate_user(username, password)

        # Assert
        assert result.is_authenticated is False
        assert result.error_message == "User not found"
        assert result.user is None

    def test_空文字でのログイン失敗(self):
        """
        Given: 空のユーザー名またはパスワード
        When: ログインを実行
        Then: バリデーションエラーが返される
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError) as exc_info:
            authenticate_user("", "password")
        assert "Username cannot be empty" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            authenticate_user("username", "")
        assert "Password cannot be empty" in str(exc_info.value)

    @pytest.mark.parametrize("username,password,expected_error", [
        ("u" * 256, "password", "Username too long"),
        ("username", "p" * 256, "Password too long"),
        ("user@", "password", "Invalid username format"),
        ("username", "pass", "Password too short"),
    ])
    def test_入力検証エラー(self, username, password, expected_error):
        """
        Given: 不正な形式の入力値
        When: ログインを実行
        Then: 適切なバリデーションエラーが返される
        """
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            authenticate_user(username, password)
        assert expected_error in str(exc_info.value)

# ========================================
# 🟢 GREEN PHASE - テストを通す最小限の実装
# ========================================

from dataclasses import dataclass
from typing import Optional
import hashlib
import secrets

@dataclass
class User:
    """ユーザーモデル"""
    username: str
    email: Optional[str] = None
    id: Optional[int] = None

@dataclass
class AuthResult:
    """認証結果モデル"""
    is_authenticated: bool
    user: Optional[User] = None
    token: Optional[str] = None
    error_message: Optional[str] = None

# 仮のユーザーデータベース
MOCK_USERS = {
    "test_user": {
        "password_hash": hashlib.sha256("secure_password_123".encode()).hexdigest(),
        "email": "test@example.com",
        "id": 1
    }
}

def authenticate_user(username: str, password: str) -> AuthResult:
    """
    ユーザー認証を実行する

    Args:
        username: ユーザー名
        password: パスワード

    Returns:
        AuthResult: 認証結果

    Raises:
        ValueError: 入力値が不正な場合
    """
    # 入力検証
    if not username:
        raise ValueError("Username cannot be empty")
    if not password:
        raise ValueError("Password cannot be empty")
    if len(username) > 255:
        raise ValueError("Username too long")
    if len(password) > 255:
        raise ValueError("Password too long")
    if "@" in username:
        raise ValueError("Invalid username format")
    if len(password) < 8:
        raise ValueError("Password too short")

    # ユーザー存在確認
    if username not in MOCK_USERS:
        return AuthResult(
            is_authenticated=False,
            error_message="User not found"
        )

    # パスワード検証
    user_data = MOCK_USERS[username]
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    if password_hash != user_data["password_hash"]:
        return AuthResult(
            is_authenticated=False,
            error_message="Invalid credentials"
        )

    # 認証成功
    user = User(
        username=username,
        email=user_data["email"],
        id=user_data["id"]
    )

    token = secrets.token_urlsafe(32)

    return AuthResult(
        is_authenticated=True,
        user=user,
        token=token
    )

# ========================================
# 🔵 REFACTOR PHASE - コードを改善する
# ========================================

class UserRepository:
    """ユーザーリポジトリ（リファクタリング版）"""

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """ユーザー名でユーザーを検索"""
        return MOCK_USERS.get(username)

class PasswordHasher:
    """パスワードハッシュ処理（リファクタリング版）"""

    def hash(self, password: str) -> str:
        """パスワードをハッシュ化"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify(self, password: str, hash: str) -> bool:
        """パスワードを検証"""
        return self.hash(password) == hash

class InputValidator:
    """入力検証（リファクタリング版）"""

    def validate_credentials(self, username: str, password: str) -> None:
        """認証情報を検証"""
        if not username:
            raise ValueError("Username cannot be empty")
        if not password:
            raise ValueError("Password cannot be empty")
        if len(username) > 255:
            raise ValueError("Username too long")
        if len(password) > 255:
            raise ValueError("Password too long")
        if "@" in username:
            raise ValueError("Invalid username format")
        if len(password) < 8:
            raise ValueError("Password too short")

class AuthenticationService:
    """認証サービス（リファクタリング版）"""

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        input_validator: InputValidator
    ):
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.input_validator = input_validator

    def authenticate(self, username: str, password: str) -> AuthResult:
        """ユーザー認証を実行（改善版）"""
        # 入力検証
        self.input_validator.validate_credentials(username, password)

        # ユーザー検索
        user_data = self.user_repository.find_by_username(username)
        if not user_data:
            return AuthResult(
                is_authenticated=False,
                error_message="User not found"
            )

        # パスワード検証
        if not self.password_hasher.verify(password, user_data["password_hash"]):
            return AuthResult(
                is_authenticated=False,
                error_message="Invalid credentials"
            )

        # 認証成功
        user = User(
            username=username,
            email=user_data["email"],
            id=user_data["id"]
        )

        token = secrets.token_urlsafe(32)

        return AuthResult(
            is_authenticated=True,
            user=user,
            token=token
        )

# グローバル関数をリファクタリング版に置き換え
_auth_service = AuthenticationService(
    UserRepository(),
    PasswordHasher(),
    InputValidator()
)

def authenticate_user(username: str, password: str) -> AuthResult:
    """ユーザー認証を実行（ファサード）"""
    return _auth_service.authenticate(username, password)

# ========================================
# 📊 COVERAGE CHECK - カバレッジ確認
# ========================================

if __name__ == "__main__":
    # カバレッジ付きでテスト実行
    import subprocess
    import sys

    print("🧪 TDDサイクルを実行中...")
    print("=" * 50)

    # テスト実行
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--cov=.",
        "--cov-report=term-missing",
        "--cov-report=html:test-results/coverage/tdd",
        "--cov-fail-under=90"
    ])

    if result.returncode == 0:
        print("\n✅ すべてのテストが成功しました！")
        print("📊 カバレッジ基準を満たしています（90%以上）")
    else:
        print("\n❌ テストが失敗したか、カバレッジが不足しています")
        print("📝 test-results/coverage/tdd/index.html でカバレッジレポートを確認してください")
        sys.exit(1)