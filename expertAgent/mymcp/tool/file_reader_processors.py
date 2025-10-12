"""File Reader 形式処理モジュール

このモジュールは、各ファイル形式に対応した処理機能を提供します。

サポートする形式:
- 画像: JPEG/JPG/PNG (Vision API経由で解析)
- ドキュメント: PDF/MD/TXT/CSV (テキスト抽出)
- 音声: MP4 (Whisper API経由で文字起こし)
"""

import csv
import logging
from io import StringIO
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def process_image(file_path: Path, user_instruction: str, model: str = "gpt-4o") -> str:
    """画像ファイルをVision APIで解析します。

    Args:
        file_path: 画像ファイルのパス
        user_instruction: ユーザーからの指示（例: "この画像を説明してください"）
        model: 使用するVisionモデル（デフォルト: gpt-4o）

    Returns:
        str: Vision APIからの解析結果テキスト

    Raises:
        ValueError: Vision API呼び出しに失敗した場合
        FileNotFoundError: ファイルが存在しない場合

    Examples:
        >>> result = process_image(Path("/tmp/image.jpg"), "この画像を説明して")
        >>> print(result)
        "この画像には..."
    """
    import base64

    from openai import OpenAI

    from core.secrets import resolve_runtime_value

    logger.info(f"Processing image: {file_path} with model: {model}")

    if not file_path.exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")

    # 画像をBase64エンコード
    try:
        with open(file_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
        logger.debug(f"Image encoded to base64, size: {len(image_data)} chars")
    except Exception as e:
        logger.error(f"Failed to read/encode image: {e}")
        raise ValueError(f"Failed to read image file: {file_path}") from e

    # OpenAI API keyを取得
    api_key = resolve_runtime_value("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured in MyVault")

    # Vision API呼び出し
    try:
        client = OpenAI(api_key=str(api_key))
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_instruction},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1000,
        )

        result = response.choices[0].message.content
        if not result:
            raise ValueError("Vision API returned empty response")

        logger.info(f"Vision API success. Response length: {len(result)}")
        return result

    except Exception as e:
        logger.error(f"Vision API call failed: {e}")
        raise ValueError(f"Vision API error: {e}") from e


def process_pdf(
    file_path: Path,
    use_advanced: bool = False,
    extract_images: bool = False,
    output_dir: Optional[Path] = None
) -> str:
    """PDFファイルからテキストを抽出します。

    Args:
        file_path: PDFファイルのパス
        use_advanced: 高度な処理を使用するか（デフォルト: False）
                     True: ヘッダ/フッタ除去、段落推定、画像・リンク・添付ファイル抽出
                     False: シンプルなテキスト抽出のみ
        extract_images: 画像を抽出するか（use_advanced=Trueの場合のみ有効）
        output_dir: 出力ディレクトリ（use_advanced=Trueの場合のみ使用）

    Returns:
        str: 抽出されたテキスト
             use_advanced=True の場合は、チャンク化されたテキスト + メタデータ情報

    Raises:
        ValueError: PDF読み込みに失敗した場合
        FileNotFoundError: ファイルが存在しない場合

    Examples:
        >>> # シンプルなテキスト抽出
        >>> text = process_pdf(Path("/tmp/document.pdf"))
        >>> print(text[:100])
        "PDFの内容..."

        >>> # 高度な処理
        >>> text = process_pdf(Path("/tmp/document.pdf"), use_advanced=True, extract_images=True)
        >>> print(text)
        "=== PDF Processing Results ===\\n..."
    """
    logger.info(f"Processing PDF: {file_path}, advanced={use_advanced}")

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        if use_advanced:
            # 高度な処理を使用
            from mymcp.tool.pdf_processor_advanced import AdvancedPDFProcessor

            processor = AdvancedPDFProcessor()
            result = processor.process_pdf(
                file_path=file_path,
                extract_images=extract_images,
                output_dir=output_dir
            )

            # 結果を整形されたテキストとして返す
            output_lines = [
                "=== PDF Processing Results ===",
                f"Document ID: {result['doc_id']}",
                f"Total Pages: {result['total_pages']}",
                f"Total Chunks: {result['total_chunks']}",
                f"Total Images: {result['total_images']}",
                f"Total Links: {result['total_links']}",
                f"Total Outlines: {result['total_outlines']}",
                f"Total Attachments: {result['total_attachments']}",
                "",
                f"Chunks saved to: {result['chunks_file']}",
                "",
                "=== Metadata ===",
            ]

            # メタデータを追加
            metadata = result['metadata']
            output_lines.append(f"Filename: {metadata['filename']}")
            output_lines.append(f"File size: {metadata['file_size_bytes']:,} bytes")
            output_lines.append(f"Encrypted: {metadata['is_encrypted']}")

            if 'pdf_metadata' in metadata:
                pdf_meta = metadata['pdf_metadata']
                if pdf_meta.get('title'):
                    output_lines.append(f"Title: {pdf_meta['title']}")
                if pdf_meta.get('author'):
                    output_lines.append(f"Author: {pdf_meta['author']}")

            # アウトライン（しおり）がある場合
            if result['outlines']:
                output_lines.append("")
                output_lines.append("=== Outlines (Table of Contents) ===")
                for outline in result['outlines'][:10]:  # 最初の10件のみ
                    indent = "  " * outline['level']
                    page_info = f" (p.{outline['page']})" if outline['page'] else ""
                    output_lines.append(f"{indent}- {outline['title']}{page_info}")
                if len(result['outlines']) > 10:
                    output_lines.append(f"... and {len(result['outlines']) - 10} more")

            # リンクがある場合
            if result['links']:
                output_lines.append("")
                output_lines.append(f"=== Links ({len(result['links'])} total) ===")
                external_links = [
                    link for link in result['links'] if link.get('link_type') == 'external'
                ]
                if external_links:
                    output_lines.append(f"External links: {len(external_links)}")
                    for link in external_links[:5]:  # 最初の5件のみ
                        output_lines.append(f"  - {link.get('uri', 'N/A')}")

            # 添付ファイルがある場合
            if result['attachments']:
                output_lines.append("")
                output_lines.append("=== Attachments ===")
                for attach in result['attachments']:
                    output_lines.append(
                        f"- {attach['filename']} ({attach['size_bytes']:,} bytes)"
                    )

            # チャンクのサンプル（最初の3チャンク）
            output_lines.append("")
            output_lines.append("=== Text Chunks (sample) ===")

            import json
            chunks_file = Path(result['chunks_file'])
            if chunks_file.exists():
                with open(chunks_file, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i >= 3:  # 最初の3チャンクのみ
                            break
                        chunk = json.loads(line)
                        output_lines.append(
                            f"[Page {chunk['page']}, {chunk['type']}] {chunk['text_norm'][:100]}..."
                        )

            full_text = "\n".join(output_lines)
            logger.info(f"Advanced PDF processing complete. Output length: {len(full_text)}")
            return full_text

        else:
            # シンプルなテキスト抽出（既存の動作）
            reader = PdfReader(str(file_path))
            num_pages = len(reader.pages)
            logger.debug(f"PDF has {num_pages} pages")

            # 全ページのテキストを抽出
            text_parts = []
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                    logger.debug(f"Extracted {len(page_text)} chars from page {page_num}")

            full_text = "\n\n".join(text_parts)
            logger.info(f"PDF processing complete. Total text length: {len(full_text)}")
            return full_text

    except Exception as e:
        logger.error(f"Failed to process PDF: {e}")
        raise ValueError(f"PDF processing error: {e}") from e


def process_text(file_path: Path) -> str:
    """テキストファイル（TXT/MD）を読み込みます。

    Args:
        file_path: テキストファイルのパス

    Returns:
        str: ファイルの内容

    Raises:
        ValueError: ファイル読み込みに失敗した場合
        FileNotFoundError: ファイルが存在しない場合

    Examples:
        >>> text = process_text(Path("/tmp/document.txt"))
        >>> print(text)
        "テキストの内容..."
    """
    logger.info(f"Processing text file: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"Text file not found: {file_path}")

    try:
        # UTF-8で読み込み、失敗したら他のエンコーディングを試す
        encodings = ["utf-8", "utf-8-sig", "shift_jis", "cp932", "euc_jp"]

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding) as f:
                    content = f.read()
                logger.info(
                    f"Successfully read with {encoding}. Length: {len(content)}"
                )
                return content
            except UnicodeDecodeError:
                logger.debug(f"Failed to decode with {encoding}, trying next...")
                continue

        # すべてのエンコーディングで失敗
        raise ValueError(f"Could not decode file with any encoding: {encodings}")

    except Exception as e:
        logger.error(f"Failed to process text file: {e}")
        raise ValueError(f"Text file processing error: {e}") from e


def process_csv(file_path: Path) -> str:
    """CSVファイルを読み込み、整形されたテキストとして返します。

    Args:
        file_path: CSVファイルのパス

    Returns:
        str: 整形されたCSVデータ（表形式テキスト）

    Raises:
        ValueError: CSV読み込みに失敗した場合
        FileNotFoundError: ファイルが存在しない場合

    Examples:
        >>> text = process_csv(Path("/tmp/data.csv"))
        >>> print(text)
        "Column1,Column2,Column3\\nValue1,Value2,Value3..."
    """
    logger.info(f"Processing CSV file: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    try:
        # UTF-8で読み込み、失敗したら他のエンコーディングを試す
        encodings = ["utf-8", "utf-8-sig", "shift_jis", "cp932"]

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding, newline="") as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                # CSV内容を整形されたテキストに変換
                output = StringIO()
                writer = csv.writer(output)
                writer.writerows(rows)
                result = output.getvalue()

                logger.info(
                    f"Successfully read CSV with {encoding}. Rows: {len(rows)}, Length: {len(result)}"
                )
                return result

            except UnicodeDecodeError:
                logger.debug(f"Failed to decode CSV with {encoding}, trying next...")
                continue

        # すべてのエンコーディングで失敗
        raise ValueError(f"Could not decode CSV with any encoding: {encodings}")

    except Exception as e:
        logger.error(f"Failed to process CSV file: {e}")
        raise ValueError(f"CSV processing error: {e}") from e


def process_audio(
    file_path: Path, user_instruction: Optional[str] = None, model: str = "whisper-1"
) -> str:
    """音声ファイルをWhisper APIで文字起こしします。

    Args:
        file_path: 音声ファイルのパス（MP4/MP3/WAVなど）
        user_instruction: ユーザーからの指示（Whisperでは未使用、将来の拡張用）
        model: 使用するWhisperモデル（デフォルト: whisper-1）

    Returns:
        str: 文字起こし結果テキスト

    Raises:
        ValueError: Whisper API呼び出しに失敗した場合
        FileNotFoundError: ファイルが存在しない場合

    Examples:
        >>> result = process_audio(Path("/tmp/audio.mp4"))
        >>> print(result)
        "音声の文字起こし結果..."
    """
    from openai import OpenAI

    from core.secrets import resolve_runtime_value

    logger.info(f"Processing audio: {file_path} with model: {model}")

    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # OpenAI API keyを取得
    api_key = resolve_runtime_value("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured in MyVault")

    # Whisper API呼び出し
    try:
        client = OpenAI(api_key=str(api_key))

        with open(file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=model, file=audio_file, response_format="text"
            )

        # responseは直接テキスト文字列として返される（response_format="text"のため）
        if isinstance(response, str):
            result = response
        else:
            # 万が一オブジェクトが返ってきた場合の対応
            result = str(response)

        logger.info(f"Whisper API success. Transcription length: {len(result)}")
        return result

    except Exception as e:
        logger.error(f"Whisper API call failed: {e}")
        raise ValueError(f"Whisper API error: {e}") from e


def process_file(
    file_path: Path,
    mime_type: str,
    user_instruction: str = "ファイルの内容を要約してください",
) -> str:
    """ファイル形式に応じて適切な処理を実行します。

    Args:
        file_path: 処理対象のファイルパス
        mime_type: ファイルのMIME type
        user_instruction: ユーザーからの指示

    Returns:
        str: 処理結果テキスト

    Raises:
        ValueError: サポートされていない形式、または処理に失敗した場合

    Examples:
        >>> result = process_file(Path("/tmp/doc.pdf"), "application/pdf")
        >>> print(result)
        "PDFの内容..."
    """
    logger.info(f"Processing file: {file_path}, MIME: {mime_type}")

    # 画像処理
    if mime_type.startswith("image/"):
        return process_image(file_path, user_instruction)

    # PDF処理
    elif mime_type == "application/pdf":
        return process_pdf(file_path)

    # テキスト処理
    elif mime_type in ("text/plain", "text/markdown"):
        return process_text(file_path)

    # CSV処理
    elif mime_type == "text/csv":
        return process_csv(file_path)

    # 音声処理
    elif mime_type.startswith("audio/") or mime_type == "video/mp4":
        return process_audio(file_path, user_instruction)

    else:
        raise ValueError(f"Unsupported MIME type: {mime_type}")
