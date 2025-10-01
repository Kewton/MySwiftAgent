import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError # RefreshErrorをインポート
from core.config import settings

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

# 環境変数からパスを取得（Noneの場合は空文字列などにしても良いが、ここではNoneのまま扱う）
# 環境変数が設定されていない場合はエラーになるようにする
TOKEN_PATH = settings.GOOGLE_APIS_TOKEN_PATH
CREDENTIALS_PATH = settings.GOOGLE_APIS_CREDENTIALS_PATH


def get_googleapis_service(_serviceName):
    # パスが環境変数で設定されているか確認
    if not TOKEN_PATH:
        print("エラー: 環境変数 GOOGLE_APIS_TOKEN_PATH が設定されていません。")
        return None
    if not CREDENTIALS_PATH:
        print("エラー: 環境変数 GOOGLE_APIS_CREDENTIALS_PATH が設定されていません。")
        return None

    print("認証情報を確認します...")
    creds = None
    # トークンファイルが存在すれば読み込む
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            print(f"既存のトークンファイルを読み込みました: {TOKEN_PATH}")
        except Exception as e:
            print(f"トークンファイルの読み込みに失敗しました: {e}")
            creds = None  # 読み込み失敗時はcredsをNoneにする

    # creds が存在しない、または無効な場合 (読み込み失敗も含む)
    if not creds or not creds.valid:
        print("有効な認証情報がない、または期限切れです。")
        # credsが存在し、期限切れで、リフレッシュトークンがある場合 -> リフレッシュ試行
        if creds and creds.expired and creds.refresh_token:
            print("リフレッシュトークンを使用してアクセストークンを更新します...")
            try:
                creds.refresh(Request())
                print("トークンのリフレッシュに成功しました。")
                # リフレッシュ成功後、トークンファイルを更新
                with open(TOKEN_PATH, 'w') as token_file:
                    token_file.write(creds.to_json())
                print(f"更新されたトークンを保存しました: {TOKEN_PATH}")
            except RefreshError as e:
                print(f"トークンのリフレッシュに失敗しました (RefreshError): {e}")
                print("リフレッシュに失敗したため、再認証を行います。")
                # リフレッシュ失敗時は既存のトークンファイルを削除し、再認証へ
                try:
                    os.remove(TOKEN_PATH)
                    print(f"古いトークンファイルを削除しました: {TOKEN_PATH}")
                except OSError as rm_e:
                    print(f"古いトークンファイルの削除に失敗しました: {rm_e}")
                creds = None # credsをNoneにして再認証フローへ
            except Exception as e:
                print(f"トークンのリフレッシュ中に予期せぬエラーが発生しました: {e}")
                creds = None # credsをNoneにして再認証フローへ

        # creds が None (最初から存在しない、読み込み失敗、リフレッシュ失敗) の場合 -> 新規認証フロー
        if not creds:  # この条件チェックを追加
            print("新しい認証情報を取得します...")# クレデンシャルファイルの存在チェック
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"エラー: クレデンシャルファイルが見つかりません: {CREDENTIALS_PATH}")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                # run_local_serverはブラウザを開き、ユーザーの操作を待ちます
                creds = flow.run_local_server(
                    port=0, # 利用可能なポートを自動選択
                    authorization_prompt_message="ブラウザを開いて認証してください: {url}",
                    success_message="認証が完了しました。このウィンドウは閉じて構いません。",
                    open_browser=True,  # 自動でブラウザを開く
                    # access_type='offline' と prompt='consent' は run_local_server 内で適切に処理されるはずですが、
                    # 明示的に authorization_url_params で指定することも可能です。
                    # authorization_url_params={
                    #     'access_type': 'offline', # リフレッシュトークンを要求
                    #     'prompt': 'consent'     # 常に同意画面を表示（必要に応じて）
                    # }
                )
                print("新しい認証情報の取得に成功しました。")
                # 新しいトークンを保存
                with open(TOKEN_PATH, 'w') as token_file:
                    token_file.write(creds.to_json())
                print(f"新しいトークンを保存しました: {TOKEN_PATH}")
            except Exception as e:
                print(f"認証フロー中にエラーが発生しました: {e}")
                return None  # 認証に失敗したら None を返す

    # 認証情報が最終的に有効かチェック
    if not creds or not creds.valid:
        print("エラー: 有効な認証情報を取得できませんでした。")
        return None

    # Google APIサービスのビルド
    try:
        print(f"'{_serviceName}' サービスをビルドします...")
        if _serviceName == "gmail":
            service = build('gmail', 'v1', credentials=creds)
        elif _serviceName == "drive":
            service = build('drive', 'v3', credentials=creds)
        elif _serviceName == "sheets":
            # Sheets API v4 を使用
            service = build('sheets', 'v4', credentials=creds)
        else:
            print(f"エラー: 不明なサービス名です: {_serviceName}")
            return None
        print("サービスのビルドに成功しました。")
        return service
    except Exception as e:
        print(f"Google APIサービスのビルドに失敗しました: {e}")
        return None
