from mymcp.utils.html2markdown import getMarkdown
from mymcp.tool.generate_melmaga_script import generate_melmaga_script
from mymcp.googleapis.gmail.send import send_email
import ast
from mymcp.utils.generate_subject_from_text import generate_subject_from_text
from core.config import settings


def safe_string_to_list(input_str: str) -> list | None:
    """
    文字列形式のPythonリストリテラルを安全にリストオブジェクトに変換する。
    変換できない場合や、結果がリストでない場合はNoneを返す。
    """
    if not isinstance(input_str, str):
        print(f"Error: Input must be a string, got {type(input_str)}")
        return None
    try:
        # 文字列の前後にある空白を除去してから評価するのが安全
        prefix = "urls="
        result = input_str.removeprefix(prefix)
        evaluated_value = ast.literal_eval(result.strip())

        # 評価結果がリストであることを確認
        if isinstance(evaluated_value, list):
            return evaluated_value
        else:
            print(f"Warning: Input string evaluated to {type(evaluated_value).__name__}, not a list.")
            return None
    except (ValueError, SyntaxError, TypeError) as e:
        # 文字列が有効なPythonリテラルでない場合のエラー処理
        print(f"Error converting string to list: {e}")
        return None
    except Exception as e:
        # その他の予期せぬエラー
        print(f"An unexpected error occurred: {e}")
        return None


def generate_melmaga_and_send_email_from_urls(urls: list | str):
    """入力されたURLから情報を収集しメルマガを生成してメール送信します。

    指定されたURLを元にLLMを活用してメルマガを生成し、指定されたメールアドレスに送信します。
    【重要】：URLは最大5個まで指定可能です。wikipediaは指定不可です。
    各URLから情報を取得し、メルマガの本文を生成します。
    メルマガの件名は本文から自動生成されます。
    メルマガの本文は、各URLに対する情報をテーマごとにまとめたものになります。
    メルマガの本文は、各テーマごとにタイトル、概要、本文、まとめの順に構成されます。
    各テーマは、URLごとに分けられています。
    各テーマのタイトルは、URLから取得した情報を元に生成されます。

    Args:
        urls (list): メルマガを生成するためのURLのリスト。例）['https://sportsbull.jp/p/2047296/', 'https://www.expo2025.or.jp/']

    Returns:
        str: 生成したメルマガ

    """
    print(f"generate_melmaga_script_from_urls_tool: {urls}")

    try:
        if isinstance(urls, str):
            urls = safe_string_to_list(urls)
        if not isinstance(urls, list):
            raise ValueError("urls must be a list or a string")
        if not urls:
            raise ValueError("urls must not be empty")
        if len(urls) > 5:
            raise ValueError("urls must not exceed 5 items")

        input_info = ""
        _cnt = 0
        for url in urls:
            _cnt += 1
            print(f"URL: {url}")
            input_info += f"#: テーマ_{str(_cnt)}\n"
            input_info += f"## URL: {url}\n"
            input_info += "## 内容\n"
            input_info += f"{getMarkdown(url)}\n\n"
            input_info += "----------------"
        body = generate_melmaga_script(input_info)
        subject = generate_subject_from_text(body)
        return send_email(settings.MAIL_TO, subject, body)
    
    except ValueError as e:
        print(f"ValueError: {e}")
        return f"ValueError: {e}"
    except TypeError as e:
        print(f"TypeError: {e}")
        return f"TypeError: {e}"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"
