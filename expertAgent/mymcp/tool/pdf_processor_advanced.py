"""Advanced PDF Processor with pypdf

pypdfを使用した高度なPDF処理モジュール。

提供機能:
- テキスト抽出と正規化（ヘッダ/フッタ除去、段落推定）
- 画像抽出（XObject）
- メタデータ・しおり・リンク・添付ファイル抽出
- チャンク化とJSONL出力
"""

import hashlib
import json
import logging
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class PDFChunk:
    """PDF抽出チャンクのデータ構造"""

    doc_id: str
    page: int
    chunk_id: str
    type: str  # paragraph, heading, list, code, quote, table_like
    text_raw: str
    text_norm: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


class TextNormalizer:
    """テキスト正規化ユーティリティ"""

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """空白文字の正規化"""
        # 全角スペースを半角に
        text = text.replace("\u3000", " ")
        # 連続する空白を1つに
        text = re.sub(r"[ \t]+", " ", text)
        # 連続する改行を最大2つに（段落区切り保持）
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def join_hyphenated_words(text: str) -> str:
        """行末ハイフンの結合（英語PDF対応）"""
        # 行末の "-\n" + 次行の単語を結合
        text = re.sub(r"-\s*\n\s*([a-z])", r"\1", text)
        return text

    @staticmethod
    def unicode_normalize(text: str) -> str:
        """Unicode正規化（NFKC）"""
        # 全角英数字を半角に、合字を分解
        return unicodedata.normalize("NFKC", text)

    @classmethod
    def normalize(cls, text: str) -> str:
        """完全な正規化パイプライン"""
        text = cls.unicode_normalize(text)
        text = cls.normalize_whitespace(text)
        text = cls.join_hyphenated_words(text)
        return text


class HeaderFooterRemover:
    """ヘッダ/フッタ除去ユーティリティ"""

    def __init__(self, threshold: float = 0.3):
        """
        Args:
            threshold: 反復頻度の閾値（0.3 = 全ページの30%以上で出現）
        """
        self.threshold = threshold
        self.header_candidates: Counter = Counter()
        self.footer_candidates: Counter = Counter()

    def collect_candidates(self, pages_text: list[str]) -> None:
        """各ページの先頭/末尾行を収集"""
        for text in pages_text:
            lines = text.split("\n")
            if len(lines) < 3:
                continue

            # 先頭2行をヘッダ候補
            header = "\n".join(lines[:2]).strip()
            if header and len(header) < 200:  # 長すぎる行は除外
                self.header_candidates[header] += 1

            # 末尾2行をフッタ候補
            footer = "\n".join(lines[-2:]).strip()
            if footer and len(footer) < 200:
                self.footer_candidates[footer] += 1

    def get_patterns(self, total_pages: int) -> tuple[set[str], set[str]]:
        """反復パターンを抽出"""
        min_count = int(total_pages * self.threshold)

        headers = {
            pattern for pattern, count in self.header_candidates.items() if count >= min_count
        }
        footers = {
            pattern for pattern, count in self.footer_candidates.items() if count >= min_count
        }

        logger.debug(f"Found {len(headers)} header patterns, {len(footers)} footer patterns")
        return headers, footers

    def remove(self, text: str, headers: set[str], footers: set[str]) -> str:
        """ヘッダ/フッタを削除"""
        lines = text.split("\n")

        # ヘッダ削除
        for header_pattern in headers:
            header_lines = header_pattern.split("\n")
            if "\n".join(lines[: len(header_lines)]) == header_pattern:
                lines = lines[len(header_lines) :]

        # フッタ削除
        for footer_pattern in footers:
            footer_lines = footer_pattern.split("\n")
            if "\n".join(lines[-len(footer_lines) :]) == footer_pattern:
                lines = lines[: -len(footer_lines)]

        return "\n".join(lines)


class ParagraphEstimator:
    """段落推定ユーティリティ"""

    # 段落タイプ判定パターン
    HEADING_PATTERN = re.compile(r"^(?:第?\d+[章節条項]|Chapter\s+\d+|Section\s+\d+)", re.IGNORECASE)
    LIST_PATTERN = re.compile(r"^[\s]*[-•・*■○①②③④⑤⑥⑦⑧⑨⑩]\s+")
    CODE_PATTERN = re.compile(r"^[\s]{4,}|^\t")  # インデントされたコード

    @classmethod
    def estimate_type(cls, paragraph: str) -> str:
        """段落タイプを推定"""
        first_line = paragraph.split("\n")[0].strip()

        if cls.HEADING_PATTERN.match(first_line):
            return "heading"
        elif cls.LIST_PATTERN.match(first_line):
            return "list"
        elif cls.CODE_PATTERN.match(first_line):
            return "code"
        elif first_line.startswith(">") or first_line.startswith("｜"):
            return "quote"
        elif "|" in first_line or "\t" in paragraph:  # 簡易表検出
            return "table_like"
        else:
            return "paragraph"

    @classmethod
    def split_paragraphs(cls, text: str) -> list[tuple[str, str]]:
        """テキストを段落に分割し、タイプを推定

        Returns:
            list[tuple[type, text]]: (段落タイプ, テキスト) のリスト
        """
        # 空行2連続で分割
        blocks = re.split(r"\n\n+", text)

        paragraphs = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            para_type = cls.estimate_type(block)
            paragraphs.append((para_type, block))

        return paragraphs


class OutlineExtractor:
    """アウトライン（しおり/目次）抽出ユーティリティ"""

    @staticmethod
    def extract_outlines(reader: PdfReader) -> list[dict[str, Any]]:
        """PDFのアウトライン（しおり）を抽出

        Args:
            reader: pypdf PdfReader object

        Returns:
            list[dict]: アウトライン情報のリスト
        """
        outlines_info = []

        try:
            if not reader.outline:
                logger.debug("No outlines found in PDF")
                return outlines_info

            def process_outline_item(item, level: int = 0) -> None:
                """再帰的にアウトラインアイテムを処理"""
                if isinstance(item, list):
                    for subitem in item:
                        process_outline_item(subitem, level)
                else:
                    # アウトラインアイテムの情報を取得
                    title = item.get("/Title", "")

                    # ページ番号を取得（可能な場合）
                    page_num = None
                    try:
                        if "/Page" in item:
                            page_obj = item["/Page"]
                            if hasattr(page_obj, "idnum"):
                                # ページオブジェクトからページ番号を検索
                                for idx, page in enumerate(reader.pages):
                                    if page.indirect_reference.idnum == page_obj.idnum:
                                        page_num = idx + 1
                                        break
                    except Exception as e:
                        logger.debug(f"Could not extract page number for outline: {e}")

                    outlines_info.append({
                        "title": title,
                        "level": level,
                        "page": page_num,
                    })

            process_outline_item(reader.outline)
            logger.debug(f"Extracted {len(outlines_info)} outline items")

        except Exception as e:
            logger.warning(f"Failed to extract outlines: {e}")

        return outlines_info


class LinkExtractor:
    """リンク（Annotations）抽出ユーティリティ"""

    @staticmethod
    def extract_links(page, page_num: int) -> list[dict[str, Any]]:
        """ページからリンク（Annotations）を抽出

        Args:
            page: pypdf Page object
            page_num: ページ番号

        Returns:
            list[dict]: 抽出されたリンク情報のリスト
        """
        links_info = []

        try:
            if "/Annots" not in page:
                return links_info

            annots = page["/Annots"]
            if not annots:
                return links_info

            for annot in annots:
                try:
                    annot_obj = annot.get_object()

                    # アノテーションのタイプ
                    subtype = annot_obj.get("/Subtype", "")

                    # Linkアノテーションのみ処理
                    if subtype != "/Link":
                        continue

                    link_info = {
                        "page": page_num,
                        "type": "link",
                    }

                    # アクション情報を取得
                    if "/A" in annot_obj:
                        action = annot_obj["/A"]
                        action_type = action.get("/S", "")

                        # 外部URI
                        if action_type == "/URI" and "/URI" in action:
                            link_info["uri"] = action["/URI"]
                            link_info["link_type"] = "external"

                        # 内部リンク（GoTo）
                        elif action_type == "/GoTo" and "/D" in action:
                            link_info["destination"] = str(action["/D"])
                            link_info["link_type"] = "internal"

                    # 直接の宛先（/Dest）
                    elif "/Dest" in annot_obj:
                        link_info["destination"] = str(annot_obj["/Dest"])
                        link_info["link_type"] = "internal"

                    links_info.append(link_info)

                except Exception as e:
                    logger.debug(f"Could not process annotation: {e}")

            if links_info:
                logger.debug(f"Extracted {len(links_info)} links from page {page_num}")

        except Exception as e:
            logger.warning(f"Failed to extract links from page {page_num}: {e}")

        return links_info


class AttachmentExtractor:
    """添付ファイル（EmbeddedFiles）抽出ユーティリティ"""

    @staticmethod
    def extract_attachments(reader: PdfReader, output_dir: Path) -> list[dict[str, Any]]:
        """PDF内の添付ファイルを抽出

        Args:
            reader: pypdf PdfReader object
            output_dir: 添付ファイル保存先ディレクトリ

        Returns:
            list[dict]: 抽出された添付ファイルの情報リスト
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        attachments_info = []

        try:
            # /Names → /EmbeddedFiles から取得
            if "/Names" not in reader.trailer.get("/Root", {}):
                logger.debug("No embedded files found in PDF")
                return attachments_info

            root = reader.trailer["/Root"]
            names = root.get("/Names")
            if not names:
                return attachments_info

            embedded_files = names.get("/EmbeddedFiles")
            if not embedded_files:
                return attachments_info

            # NameTree から添付ファイル情報を取得
            names_array = embedded_files.get("/Names", [])

            # Names配列は [name1, filespec1, name2, filespec2, ...] の形式
            for i in range(0, len(names_array), 2):
                try:
                    filename = names_array[i]
                    filespec = names_array[i + 1].get_object()

                    # EmbeddedFile情報を取得
                    ef = filespec.get("/EF", {})
                    embedded_file = ef.get("/F")

                    if not embedded_file:
                        continue

                    embedded_file_obj = embedded_file.get_object()
                    file_data = embedded_file_obj.get_data()

                    # ファイル保存
                    safe_filename = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
                    filepath = output_dir / safe_filename

                    with open(filepath, "wb") as f:
                        f.write(file_data)

                    attachments_info.append({
                        "filename": filename,
                        "safe_filename": safe_filename,
                        "path": str(filepath),
                        "size_bytes": len(file_data),
                    })

                    logger.debug(f"Extracted attachment: {filename} ({len(file_data)} bytes)")

                except Exception as e:
                    logger.warning(f"Failed to extract attachment {i // 2}: {e}")

        except Exception as e:
            logger.warning(f"Failed to access embedded files: {e}")

        return attachments_info


class ImageExtractor:
    """PDF画像抽出ユーティリティ"""

    @staticmethod
    def extract_images(page, page_num: int, output_dir: Path) -> list[dict[str, Any]]:
        """ページから画像を抽出

        Args:
            page: pypdf Page object
            page_num: ページ番号
            output_dir: 画像保存先ディレクトリ

        Returns:
            list[dict]: 抽出された画像の情報リスト
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        images_info = []

        try:
            if "/Resources" not in page or "/XObject" not in page["/Resources"]:
                return images_info

            xobjects = page["/Resources"]["/XObject"]

            for idx, obj_name in enumerate(xobjects):
                obj = xobjects[obj_name]

                if obj["/Subtype"] != "/Image":
                    continue

                # 画像データ取得
                try:
                    image_data = obj.get_data()
                    width = obj.get("/Width", 0)
                    height = obj.get("/Height", 0)

                    # フィルタ判定で拡張子決定
                    filter_type = obj.get("/Filter", "")
                    if filter_type == "/DCTDecode":
                        ext = "jpg"
                    elif filter_type == "/FlateDecode":
                        ext = "png"
                    elif filter_type == "/JPXDecode":
                        ext = "jp2"
                    else:
                        ext = "bin"

                    # ファイル保存
                    filename = f"page{page_num:04d}_img{idx:03d}.{ext}"
                    filepath = output_dir / filename

                    with open(filepath, "wb") as f:
                        f.write(image_data)

                    images_info.append(
                        {
                            "filename": filename,
                            "path": str(filepath),
                            "width": width,
                            "height": height,
                            "format": ext,
                            "size_bytes": len(image_data),
                        }
                    )

                    logger.debug(f"Extracted image: {filename} ({width}x{height}, {ext})")

                except Exception as e:
                    logger.warning(f"Failed to extract image {idx} from page {page_num}: {e}")

        except Exception as e:
            logger.error(f"Failed to access XObjects on page {page_num}: {e}")

        return images_info


class AdvancedPDFProcessor:
    """高度なPDF処理クラス"""

    def __init__(self, doc_id: Optional[str] = None):
        """
        Args:
            doc_id: ドキュメントID（指定しない場合はファイルハッシュを使用）
        """
        self.doc_id = doc_id
        self.text_normalizer = TextNormalizer()
        self.header_footer_remover = HeaderFooterRemover()
        self.paragraph_estimator = ParagraphEstimator()
        self.image_extractor = ImageExtractor()
        self.outline_extractor = OutlineExtractor()
        self.link_extractor = LinkExtractor()
        self.attachment_extractor = AttachmentExtractor()

    def process_pdf(
        self,
        file_path: Path,
        extract_images: bool = True,
        output_dir: Optional[Path] = None,
    ) -> dict[str, Any]:
        """PDFを包括的に処理

        Args:
            file_path: PDFファイルパス
            extract_images: 画像抽出を行うか
            output_dir: 画像・チャンク出力先ディレクトリ

        Returns:
            dict: 処理結果（メタデータ、チャンク、画像情報等）
        """
        logger.info(f"Processing PDF: {file_path}")

        # doc_id生成（未指定の場合はファイルハッシュ）
        if not self.doc_id:
            self.doc_id = self._compute_file_hash(file_path)

        # 出力ディレクトリ設定
        if output_dir is None:
            output_dir = file_path.parent / f"{file_path.stem}_extract"
        output_dir.mkdir(parents=True, exist_ok=True)

        # PDFリーダー初期化
        reader = PdfReader(str(file_path))

        # プリフライトチェック
        metadata = self._preflight(reader, file_path)

        # アウトライン（しおり）抽出
        outlines = self.outline_extractor.extract_outlines(reader)

        # 添付ファイル抽出
        attachments_dir = output_dir / "attachments" / self.doc_id
        attachments = self.attachment_extractor.extract_attachments(reader, attachments_dir)

        # 全ページテキスト抽出（ヘッダ/フッタ検出用）
        pages_text_raw = []
        for page in reader.pages:
            text = page.extract_text()
            pages_text_raw.append(text)

        # ヘッダ/フッタパターン検出
        self.header_footer_remover.collect_candidates(pages_text_raw)
        headers, footers = self.header_footer_remover.get_patterns(len(reader.pages))

        # ページごとに処理
        chunks = []
        all_images = []
        all_links = []

        for page_num, page in enumerate(reader.pages, start=1):
            logger.debug(f"Processing page {page_num}/{len(reader.pages)}")

            # テキスト抽出と処理
            text_raw = pages_text_raw[page_num - 1]
            text_cleaned = self.header_footer_remover.remove(text_raw, headers, footers)
            text_norm = self.text_normalizer.normalize(text_cleaned)

            # 段落分割とチャンク化
            paragraphs = self.paragraph_estimator.split_paragraphs(text_norm)

            for para_idx, (para_type, para_text) in enumerate(paragraphs):
                chunk_id = f"{self.doc_id}_p{page_num:04d}_c{para_idx:03d}"
                text_hash = hashlib.sha256(para_text.encode()).hexdigest()[:16]

                chunk = PDFChunk(
                    doc_id=self.doc_id,
                    page=page_num,
                    chunk_id=chunk_id,
                    type=para_type,
                    text_raw=para_text,
                    text_norm=para_text,
                    meta={
                        "source": "pypdf",
                        "hash": text_hash,
                        "has_images": False,  # 後で更新
                        "has_links": False,   # 後で更新
                    },
                )
                chunks.append(chunk)

            # リンク抽出
            links = self.link_extractor.extract_links(page, page_num)
            all_links.extend(links)

            # リンクがあるページのチャンクにフラグ設定
            if links:
                for chunk in chunks:
                    if chunk.page == page_num:
                        chunk.meta["has_links"] = True

            # 画像抽出
            if extract_images:
                images_dir = output_dir / "images" / self.doc_id
                images = self.image_extractor.extract_images(page, page_num, images_dir)
                all_images.extend(images)

                # 画像があるページのチャンクにフラグ設定
                if images:
                    for chunk in chunks:
                        if chunk.page == page_num:
                            chunk.meta["has_images"] = True

        # チャンクをJSONLで保存
        chunks_file = output_dir / "chunks.jsonl"
        self._save_chunks(chunks, chunks_file)

        # メタデータ保存
        result = {
            "doc_id": self.doc_id,
            "metadata": metadata,
            "total_pages": len(reader.pages),
            "total_chunks": len(chunks),
            "total_images": len(all_images),
            "total_links": len(all_links),
            "total_outlines": len(outlines),
            "total_attachments": len(attachments),
            "chunks_file": str(chunks_file),
            "images": all_images,
            "links": all_links,
            "outlines": outlines,
            "attachments": attachments,
        }

        metadata_file = output_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(
            f"PDF processing complete: {len(chunks)} chunks, "
            f"{len(all_images)} images, {len(all_links)} links, "
            f"{len(outlines)} outlines, {len(attachments)} attachments"
        )
        return result

    def _preflight(self, reader: PdfReader, file_path: Path) -> dict[str, Any]:
        """プリフライトチェック"""
        metadata = {
            "filename": file_path.name,
            "file_size_bytes": file_path.stat().st_size,
            "num_pages": len(reader.pages),
            "is_encrypted": reader.is_encrypted,
        }

        # PDFメタデータ取得
        if reader.metadata:
            metadata["pdf_metadata"] = {
                "title": reader.metadata.get("/Title", ""),
                "author": reader.metadata.get("/Author", ""),
                "subject": reader.metadata.get("/Subject", ""),
                "creator": reader.metadata.get("/Creator", ""),
                "producer": reader.metadata.get("/Producer", ""),
            }

        logger.info(f"Preflight: {metadata['num_pages']} pages, encrypted={metadata['is_encrypted']}")
        return metadata

    def _compute_file_hash(self, file_path: Path) -> str:
        """ファイルハッシュ計算"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]

    def _save_chunks(self, chunks: list[PDFChunk], output_file: Path) -> None:
        """チャンクをJSONL形式で保存"""
        with open(output_file, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(chunks)} chunks to {output_file}")
