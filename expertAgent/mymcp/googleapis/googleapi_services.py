"""Google API services with project-specific encrypted credentials."""
import atexit
import os
from typing import Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from core.config import settings
from core.google_creds import SCOPES, google_creds_manager

# Temp file cleanup
_temp_files = []


def _cleanup_temp_files():
    """Clean up temporary credential files on exit."""
    for path in _temp_files:
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"🧹 Cleaned up temp file: {path}")
        except Exception as e:
            print(f"⚠ Failed to clean up {path}: {e}")


atexit.register(_cleanup_temp_files)


def get_googleapis_service(
    _serviceName: str, project: Optional[str] = None
) -> Optional[any]:
    """
    Get Google API service with project-specific encrypted credentials.

    Args:
        _serviceName: Service name (gmail, drive, sheets)
        project: Project name (uses default if None)

    Returns:
        Google API service object or None if authentication fails
    """
    project_name = project or settings.MYVAULT_DEFAULT_PROJECT or "default"
    print(f"🔐 Project: {project_name} - 認証情報を確認します...")

    try:
        # Get decrypted credentials paths from encrypted storage
        credentials_path = google_creds_manager.get_credentials_path(project_name)
        _temp_files.append(credentials_path)

        token_path = google_creds_manager.get_token_path(project_name)
        if token_path:
            _temp_files.append(token_path)
    except FileNotFoundError as e:
        print(f"❌ Credentials not found: {e}")
        print(
            f"📝 Please add GOOGLE_CREDENTIALS_JSON to MyVault project: {project_name}"
        )
        print("   Use commonUI → MyVault → Google認証タブ to upload credentials")
        return None
    except ValueError as e:
        print(f"❌ Decryption failed: {e}")
        print("   Check GOOGLE_CREDS_ENCRYPTION_KEY in MyVault")
        return None
    except Exception as e:
        print(f"❌ Failed to get credentials: {e}")
        return None

    creds: Optional[Credentials] = None

    # Load token if exists
    if token_path and os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            print(f"✓ 既存のトークンを読み込みました")
        except Exception as e:
            print(f"⚠ トークンの読み込みに失敗: {e}")
            creds = None

    # Check validity and refresh if needed
    if not creds or not creds.valid:
        print("🔄 認証情報が無効または期限切れです")

        if creds and creds.expired and creds.refresh_token:
            print("🔄 リフレッシュトークンで更新を試みます...")
            try:
                creds.refresh(Request())
                print("✓ トークンのリフレッシュに成功")

                # Save refreshed token
                token_json = creds.to_json()
                google_creds_manager.save_token(token_json, project_name)
                print(f"✓ 更新されたトークンを保存しました (project: {project_name})")
                print(
                    "ℹ️  MyVaultへの手動更新を推奨: commonUI → MyVault → Google認証タブ"
                )
            except RefreshError as e:
                print(f"❌ リフレッシュ失敗: {e}")
                print("🔄 再認証が必要です")
                creds = None
            except Exception as e:
                print(f"❌ 予期せぬエラー: {e}")
                creds = None

        # New authentication flow
        if not creds:
            print("🆕 新規認証フローを開始します...")

            if not os.path.exists(credentials_path):
                print(f"❌ クレデンシャルファイルが見つかりません")
                print(
                    "   commonUI → MyVault → Google認証タブ から credentials.json をアップロードしてください"
                )
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(
                    port=0,
                    authorization_prompt_message="🌐 ブラウザを開いて認証してください: {url}",
                    success_message="✅ 認証完了。このウィンドウは閉じて構いません。",
                    open_browser=True,
                )
                print("✓ 新規認証に成功しました")

                # Save new token
                token_json = creds.to_json()
                google_creds_manager.save_token(token_json, project_name)
                print(f"✓ 新しいトークンを保存しました (project: {project_name})")
                print(
                    "ℹ️  MyVaultへの手動更新を推奨: commonUI → MyVault → Google認証タブ"
                )
            except Exception as e:
                print(f"❌ 認証フロー失敗: {e}")
                return None

    # Final validation
    if not creds or not creds.valid:
        print("❌ 有効な認証情報を取得できませんでした")
        return None

    # Build service
    try:
        print(f"🔧 '{_serviceName}' サービスをビルドします...")
        if _serviceName == "gmail":
            service = build("gmail", "v1", credentials=creds)
        elif _serviceName == "drive":
            service = build("drive", "v3", credentials=creds)
        elif _serviceName == "sheets":
            service = build("sheets", "v4", credentials=creds)
        else:
            print(f"❌ 不明なサービス名: {_serviceName}")
            return None

        print("✅ サービスのビルドに成功しました")
        return service
    except Exception as e:
        print(f"❌ サービスのビルド失敗: {e}")
        return None
