import html2text
from mymcp.googleapis.drive import get_or_create_folder, upload_file
from bs4 import BeautifulSoup
from mymcp.utils.file_operation import delete_file
import re
import requests
import uuid
from pathlib import Path
import re


def getMarkdown(url, isUpload=True):
    try:
        result = {
            "state": "failed",
            "result": ""
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            html_content = response.text
            # 関数を使ってHTMLをMarkdownに変換
            md1 = html_to_markdown(html_content)
            markdown_content = clean_markdown_text(md1)
            if markdown_content.startswith("JavaScript"):
                print("JavaScriptのページはスキップ")
                print(markdown_content)
                print("変換前１")
                print(html_content)
                print("変換前１")
                print(md1)
            result["state"] = "success"
            result["result"] = markdown_content
            
            if isUpload:
                # マークダウンファイル生成
                temp_dir = Path("./temp")
                try:
                    temp_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    return f"エラー: 一時ディレクトリ '{temp_dir}' の作成に失敗しました: {e}"
                unique_filename = f"{uuid.uuid4()}.md"
                md_file_path = temp_dir / unique_filename

                try:
                    with open(md_file_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                except IOError as e:
                    print(f"ファイルの書き込みエラー: {e}")

                # googl drive にアップロード
                folder_id = get_or_create_folder("./MyAiAgent/knowledge")
                upload_file(f"{url}.md", md_file_path, 'text/plain', folder_id)
                delete_file(str(md_file_path))
            print("Markdown変換完了")
            return result
        else:
            return str(response.status_code) + "エラー"
    except Exception as e:
        print(e)
        result["result"] = str(e)
        return result


def convert_html_to_markdown(html_content):
    print("convert start")
    # html2textのインスタンスを作成
    converter = html2text.HTML2Text()

    # リンクを無視する
    converter.ignore_links = True
    # 画像を無視する
    converter.ignore_images = True
    # 幅制限を無効にする
    converter.body_width = 0

    # HTMLをMarkdownに変換
    markdown_content = converter.handle(html_content)
    return markdown_content


def clean_markdown_text(markdown: str) -> str:
    """
    Markdownテキストをクリーンアップする関数
    """
    # [](...) 形式のリンクを除去
    markdown = re.sub(r'\[.*?\]\(.*?\)', '', markdown)
    # 「メディア」や「[特集]」など特定の単語・パターンを除去
    markdown = re.sub(r'メディア|特集', '', markdown)
    # 文字化け（�など）や制御文字を除去
    markdown = re.sub(r'[�\x00-\x1F\x7F-\x9F]', '', markdown)
    # PDFやバイナリ断片らしきものを除去（例: "endstream endobj"や"xref"など）
    markdown = re.sub(r'%PDF-[\d\.]+', '', markdown)
    markdown = re.sub(r'\d+\s+\d+\s+obj.*?endobj', '', markdown, flags=re.DOTALL)
    markdown = re.sub(r'xref.*?trailer.*?%%EOF', '', markdown, flags=re.DOTALL)
    markdown = re.sub(r'endstream endobj.*?trailer.*?%%EOF', '', markdown, flags=re.DOTALL)
    markdown = re.sub(r'trailer[\s\S]*?startxref[\s\S]*?%%EOF', '', markdown, flags=re.DOTALL)

    # 文字化けパターン（日本語・英数字・記号以外の連続）を除去
    markdown = re.sub(r'[^\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uFF00-\uFFEF\u0020-\u007E\n\r\t。、・「」（）【】『』《》〈〉［］｛｝！？：；…ー\-a-zA-Z0-9,\.\/\\@#\$%\^&\*\(\)_\+\=\|\[\]\{\}\'\"\<\>\~`]+', '', markdown)

    # 空行や余分な空白を整理
    markdown = re.sub(r'\n+', '\n', markdown)
    markdown = markdown.strip()

    print("clean end:")
    
    return markdown


def html_to_markdown(html_content):
    # BeautifulSoupでHTMLをパース
    soup = BeautifulSoup(html_content, 'html.parser')

    # 不要な要素を削除（例: スクリプト、スタイル、ナビゲーションなど）
    for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
        element.decompose()

    # html2textを設定してコードブロックに対応
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_links = False
    converter.ignore_images = True
    converter.bypass_tables = False
    converter.single_line_break = True
    converter.code_style = True  # コードブロックを適切に処理

    # HTMLをMarkdownに変換
    markdown = converter.handle(str(soup))

    return markdown
