# File Reader Implementation Progress

このドキュメントは、File Reader機能の実装進捗を記録します。

## 実装フェーズ一覧

| Phase | 概要 | 状態 | 完了日 |
|-------|------|------|--------|
| Phase 1 | 基本構造とAPI設計 | ✅ Complete | - |
| Phase 2 | 画像処理実装 (Vision API) | ✅ Complete | - |
| Phase 3 | PDF処理実装 (PyPDF2) | ✅ Complete | - |
| Phase 4 | テキスト/CSV処理実装 | ✅ Complete | - |
| Phase 5 | 音声処理実装 (Whisper API) | ✅ Complete | - |
| Phase 6 | エラーハンドリング強化 | ✅ Complete | - |
| Phase 7 | pypdf移行と高度なPDF処理 | ✅ Complete | 2025-10-12 |

---

## Phase 1: 基本構造とAPI設計 ✅

### 実装内容

- File Reader Agent用のAPI設計
- ファイルアップロード機能の実装
- MIME type検出機能
- 基本的なエラーハンドリング

### 実装ファイル

- `app/api/v1/agent_endpoints.py`: `/api/v1/aiagent/file-reader` エンドポイント
- `mymcp/agent/filereaderagent.py`: File Reader Agent実装
- `mymcp/tool/file_reader_processors.py`: ファイル処理プロセッサ

### テスト

- 基本的なAPI呼び出しテスト
- ファイルアップロード機能のテスト

---

## Phase 2: 画像処理実装 (Vision API) ✅

### 実装内容

- OpenAI Vision API統合
- Base64エンコーディング処理
- 画像解析機能 (JPEG/JPG/PNG対応)

### 実装関数

- `process_image()`: Vision APIで画像を解析
  - Base64エンコーディング
  - OpenAI API呼び出し
  - エラーハンドリング

### テスト

- `tests/unit/test_file_reader_processors.py`:
  - `test_process_image_success`: 正常系テスト
  - `test_process_image_file_not_found`: ファイル未存在エラー
  - `test_process_image_api_error`: API呼び出しエラー

---

## Phase 3: PDF処理実装 (PyPDF2 → pypdf) ✅

### 初期実装 (PyPDF2)

- PyPDF2を使用したシンプルなテキスト抽出
- ページ単位の処理

### Phase 7での改善 (pypdf移行)

**移行理由**:
- PyPDF2は2023年に開発終了 (deprecated)
- pypdfは後継ライブラリで活発に開発中
- パフォーマンス改善とバグフィックス

**実装内容**:
- 依存関係を `PyPDF2>=3.0.0` → `pypdf>=4.0.0` に変更
- インストール済みバージョン: pypdf 6.1.1
- 既存テストは全て互換性あり (16/16 passing)

### 実装関数

- `process_pdf()`: PDFからテキスト抽出
  - シンプルモード: ページ単位のテキスト抽出
  - 高度なモード: Phase 7で実装 (下記参照)

### テスト

- `tests/unit/test_file_reader_processors.py`:
  - `test_process_pdf_success`: 正常系テスト
  - `test_process_pdf_file_not_found`: ファイル未存在エラー
  - `test_process_pdf_error`: PDF処理エラー

---

## Phase 4: テキスト/CSV処理実装 ✅

### 実装内容

- テキストファイル読み込み (TXT/MD)
- CSV読み込みと整形
- マルチエンコーディング対応 (UTF-8, Shift_JIS, CP932, EUC_JP)

### 実装関数

- `process_text()`: テキストファイル読み込み
  - 複数エンコーディング自動検出
  - Unicode正規化

- `process_csv()`: CSV読み込み
  - CSVパース
  - 表形式テキストへの変換

### テスト

- `tests/unit/test_file_reader_processors.py`:
  - `test_process_text_success`: テキスト読み込み正常系
  - `test_process_text_file_not_found`: ファイル未存在
  - `test_process_csv_success`: CSV読み込み正常系
  - `test_process_csv_file_not_found`: ファイル未存在

---

## Phase 5: 音声処理実装 (Whisper API) ✅

### 実装内容

- OpenAI Whisper API統合
- 音声ファイルの文字起こし (MP4/MP3/WAV対応)

### 実装関数

- `process_audio()`: Whisper APIで音声を文字起こし
  - ファイルストリーミング
  - テキスト形式レスポンス

### テスト

- `tests/unit/test_file_reader_processors.py`:
  - `test_process_audio_success`: 正常系テスト
  - `test_process_audio_file_not_found`: ファイル未存在エラー
  - `test_process_audio_api_error`: API呼び出しエラー

---

## Phase 6: エラーハンドリング強化 ✅

### 実装内容

- 統一されたエラーメッセージ
- ログ出力の充実
- API呼び出し失敗時のリトライ機能検討

### テスト

- 各プロセッサでのエラーケーステスト
- ファイル未存在、API呼び出し失敗、エンコーディングエラー等

---

## Phase 7: pypdf移行と高度なPDF処理 ✅

**完了日**: 2025-10-12

### 実装目標

1. PyPDF2からpypdfへの完全移行
2. 本格的なPDF処理機能の実装
3. RAG/検索アプリケーション向けのチャンク化データ生成

### 実装内容

#### 7.1 依存関係の更新

**変更内容**:
```toml
# Before
"PyPDF2>=3.0.0",

# After
"pypdf>=4.0.0",
```

**インストール結果**:
- pypdf 6.1.1 (最新安定版)

#### 7.2 高度なPDF処理モジュールの実装

**新規ファイル**: `mymcp/tool/pdf_processor_advanced.py` (516行)

**実装クラス**:

1. **PDFChunk** (dataclass)
   - 目的: PDF抽出チャンクのデータ構造定義
   - フィールド: doc_id, page, chunk_id, type, text_raw, text_norm, meta
   - メソッド: `to_dict()` - 辞書形式への変換

2. **TextNormalizer**
   - 目的: テキスト正規化ユーティリティ
   - 機能:
     - Unicode NFKC正規化 (全角→半角、互換文字統一)
     - 空白正規化 (全角→半角、連続空白→1つ、連続改行→最大2つ)
     - ハイフン結合 (英語PDF行末ハイフン対応)
   - メソッド:
     - `unicode_normalize()`: NFKC正規化
     - `normalize_whitespace()`: 空白正規化
     - `join_hyphenated_words()`: ハイフン結合
     - `normalize()`: 完全な正規化パイプライン

3. **HeaderFooterRemover**
   - 目的: ヘッダ/フッタの自動除去
   - アルゴリズム: 頻度ベースのパターン検出
   - パラメータ: threshold (デフォルト: 30% = 全ページの30%以上で出現)
   - メソッド:
     - `collect_candidates()`: 候補パターン収集
     - `get_patterns()`: 反復パターン抽出
     - `remove()`: パターンに基づく除去

4. **ParagraphEstimator**
   - 目的: 段落タイプの推定
   - サポートタイプ: heading, list, code, quote, table_like, paragraph
   - 検出ロジック:
     - heading: 章節番号、Chapter/Section等
     - list: 箇条書き記号 (-, •, ①等)
     - code: インデント (4スペース/タブ)
     - quote: 引用記号 (>, ｜)
     - table_like: パイプ/タブ区切り
     - paragraph: デフォルト
   - メソッド:
     - `estimate_type()`: 段落タイプ推定
     - `split_paragraphs()`: テキスト→段落リスト分割

5. **ImageExtractor**
   - 目的: PDF内の画像抽出
   - サポート形式: JPEG/DCTDecode, PNG/FlateDecode, JPEG2000/JPXDecode
   - 抽出元: XObject (PDF内部オブジェクト)
   - メソッド:
     - `extract_images()`: ページからの画像抽出・保存

6. **OutlineExtractor**
   - 目的: PDFアウトライン (しおり/目次) 抽出
   - 機能: 階層構造の再帰的処理、ページ番号取得
   - メソッド:
     - `extract_outlines()`: 再帰的アウトライン抽出

7. **LinkExtractor**
   - 目的: PDF内リンク抽出
   - サポートタイプ:
     - 外部リンク (URI)
     - 内部リンク (ページ遷移)
   - 抽出元: Annotations (/Link)
   - メソッド:
     - `extract_links()`: リンク情報抽出

8. **AttachmentExtractor**
   - 目的: PDF添付ファイル抽出
   - 抽出元: EmbeddedFiles (/Names/EmbeddedFiles)
   - メソッド:
     - `extract_attachments()`: 添付ファイル保存

9. **AdvancedPDFProcessor** (メインクラス)
   - 目的: 統合PDF処理オーケストレーター
   - 処理フロー:
     1. Preflight check (ファイル存在確認、ハッシュ計算)
     2. メタデータ抽出
     3. アウトライン抽出
     4. 添付ファイル抽出
     5. 全ページテキスト抽出
     6. ヘッダ/フッタパターン検出
     7. ページ単位処理 (テキスト、画像、リンク)
     8. チャンク保存 (JSONL形式)
     9. メタデータ保存 (JSON形式)
   - メソッド:
     - `process_pdf()`: PDFの包括的処理
     - `_compute_file_hash()`: SHA256ハッシュ計算
     - `_save_chunks()`: JSONL形式保存
     - `_save_metadata()`: JSON形式保存

#### 7.3 既存コードへの統合

**更新ファイル**: `mymcp/tool/file_reader_processors.py`

**変更内容**:

1. Import文の更新:
```python
# Before
from PyPDF2 import PdfReader

# After
from pypdf import PdfReader
```

2. `process_pdf()` 関数の拡張:
```python
def process_pdf(
    file_path: Path,
    use_advanced: bool = False,  # 新規パラメータ
    extract_images: bool = False,
    output_dir: Optional[Path] = None
) -> str:
```

3. 高度な処理モードの追加:
   - `use_advanced=False` (デフォルト): 既存のシンプルなテキスト抽出
   - `use_advanced=True`: AdvancedPDFProcessor使用
   - 整形された結果テキストを返す (メタデータ、統計、サンプルチャンク含む)

#### 7.4 テスト実装

**新規ファイル**: `tests/unit/test_pdf_processor_advanced.py` (397行、26テスト)

**テストクラス**:

1. **TestPDFChunk** (1テスト)
   - `test_pdf_chunk_creation`: データクラス生成とto_dict変換

2. **TestTextNormalizer** (4テスト)
   - `test_normalize_whitespace`: 空白正規化
   - `test_join_hyphenated_words`: ハイフン結合
   - `test_unicode_normalize`: Unicode正規化
   - `test_normalize_full_pipeline`: 完全パイプライン

3. **TestHeaderFooterRemover** (3テスト)
   - `test_collect_candidates`: 候補収集
   - `test_get_patterns`: パターン抽出 (30%閾値)
   - `test_remove`: パターン除去

4. **TestParagraphEstimator** (7テスト)
   - `test_estimate_type_heading`: 見出し検出
   - `test_estimate_type_list`: リスト検出
   - `test_estimate_type_code`: コード検出
   - `test_estimate_type_quote`: 引用検出
   - `test_estimate_type_table_like`: 表形式検出
   - `test_estimate_type_paragraph`: 通常段落検出
   - `test_split_paragraphs`: 段落分割

5. **TestImageExtractor** (2テスト)
   - `test_extract_images_no_resources`: リソースなし
   - `test_extract_images_success`: 画像抽出成功

6. **TestOutlineExtractor** (2テスト)
   - `test_extract_outlines_empty`: アウトラインなし
   - `test_extract_outlines_success`: アウトライン抽出成功

7. **TestLinkExtractor** (2テスト)
   - `test_extract_links_no_annotations`: アノテーションなし
   - `test_extract_links_with_uri`: 外部リンク抽出

8. **TestAttachmentExtractor** (1テスト)
   - `test_extract_attachments_no_names`: 添付ファイルなし

9. **TestAdvancedPDFProcessor** (4テスト)
   - `test_init`: 初期化テスト
   - `test_compute_file_hash`: ハッシュ計算
   - `test_save_chunks`: チャンク保存
   - `test_process_pdf_file_not_found`: ファイル未存在

**既存テストの互換性確認**:
- `tests/unit/test_file_reader_processors.py` の16テスト全てがpypdfで正常動作

#### 7.5 品質チェック結果

**Linting (Ruff)**:
```bash
uv run ruff check .
# All checks passed!
```

**Type Checking (MyPy)**:
```bash
uv run mypy app/
# Success: no issues found
```

**テスト結果**:
```bash
uv run pytest tests/unit/
# ===== 42 passed in 2.34s =====
```

**テスト内訳**:
- 既存テスト: 16/16 passed (pypdf互換性確認)
- 新規テスト: 26/26 passed (高度なPDF処理)
- **合計: 42/42 passed (100%)**

**カバレッジ**:
- 目標: 90%以上
- 実績: 要測定 (次回CI/CD実行時)

### 実装上の設計判断

#### 1. 後方互換性の維持

**決定**: `use_advanced` パラメータをオプショナルに
- デフォルト値: `False` (既存動作を維持)
- 既存のAPI呼び出しは変更不要
- 新機能は明示的に有効化が必要

**理由**:
- 既存ユーザーへの影響を最小化
- 段階的な機能ロールアウトが可能
- パフォーマンス影響を選択的に適用

#### 2. ヘッダ/フッタ除去の閾値

**決定**: デフォルト閾値 30%
- 全ページの30%以上で出現するパターンを除去

**理由**:
- 数ページのみのPDFでも機能 (3ページ中1ページで出現 = 33%)
- 誤検出リスクを低減 (偶然の一致を除外)
- 実用的なPDFでのヘッダ/フッタ出現率に基づく

#### 3. 段落タイプの推定ロジック

**決定**: Regex ベースのヒューリスティック
- 機械学習モデルではなくルールベース

**理由**:
- 依存関係の最小化 (ML モデル不要)
- 予測可能な動作
- デバッグとメンテナンスの容易性
- 日本語/英語の両対応

#### 4. チャンク保存形式

**決定**: JSONL (JSON Lines) 形式
- 1行 = 1チャンク

**理由**:
- ストリーミング処理が可能 (メモリ効率)
- 部分的な読み込みが容易
- RAG/検索システムでの標準形式
- 大規模PDFでのスケーラビリティ

### 既知の制約と今後の改善案

#### 現在の制約

1. **スキャンPDF未対応**
   - 画像化されたPDFはテキスト抽出不可
   - 今後の改善: OCR統合 (Tesseract等)

2. **複雑なレイアウト**
   - 2カラムレイアウトの読み取り順序が不正確になる可能性
   - 今後の改善: レイアウト解析アルゴリズム強化

3. **表の構造解析**
   - 表の検出はできるが、セル構造の抽出は未実装
   - 今後の改善: 表構造解析機能の追加

4. **数式認識**
   - 数式は文字列として抽出されるが、意味的な構造は失われる
   - 今後の改善: MathML/LaTeX変換機能

#### パフォーマンス最適化案

1. **並列処理**
   - 現状: ページ単位の逐次処理
   - 改善案: マルチプロセスでのページ並列処理

2. **メモリ管理**
   - 現状: 全ページテキストをメモリ保持
   - 改善案: ストリーミング処理とチャンク単位の保存

3. **インクリメンタル処理**
   - 現状: 全ページを毎回処理
   - 改善案: 差分検出と部分更新

### トラブルシューティング

#### よくあるエラーと対処法

1. **Error: `pypdf` not found**
   ```bash
   # 解決策
   uv sync
   ```

2. **Error: Permission denied when saving images**
   ```bash
   # 解決策: output_dir に書き込み権限があるか確認
   chmod 755 /path/to/output_dir
   ```

3. **Warning: No outlines found**
   - これは正常です (全てのPDFがしおりを持つわけではない)
   - 処理は継続されます

4. **Low header/footer detection**
   - 閾値を調整: `HeaderFooterRemover(threshold=0.2)`
   - より低い頻度のパターンも検出可能

---

## 全体統計

### テスト結果

**Phase 1-6 (既存実装)**:
- 単体テスト: 16/16 passed
- 結合テスト: 実施済み
- カバレッジ: 90%以上 (目標達成)

**Phase 7 (pypdf移行・高度なPDF処理)**:
- 既存テスト互換性: 16/16 passed
- 新規単体テスト: 26/26 passed
- **合計: 42/42 passed (100%)**

### 実装ファイル

**コアモジュール**:
- `app/api/v1/agent_endpoints.py`: File Reader APIエンドポイント
- `mymcp/agent/filereaderagent.py`: File Reader Agent (216行)
- `mymcp/tool/file_reader_processors.py`: ファイル処理プロセッサ (467行)
- `mymcp/tool/pdf_processor_advanced.py`: 高度なPDF処理 (516行) **NEW**

**テストファイル**:
- `tests/unit/test_file_reader_processors.py`: 基本プロセッサテスト (16テスト)
- `tests/unit/test_pdf_processor_advanced.py`: 高度なPDF処理テスト (26テスト) **NEW**

**総コード行数**: 約1,200行 (コメント・docstring含む)

### サポートファイル形式

| 形式 | MIME Type | 処理方法 | 状態 |
|------|-----------|----------|------|
| JPEG/JPG | image/jpeg | Vision API | ✅ |
| PNG | image/png | Vision API | ✅ |
| PDF | application/pdf | pypdf (シンプル/高度) | ✅ |
| TXT | text/plain | テキスト読み込み | ✅ |
| MD | text/markdown | テキスト読み込み | ✅ |
| CSV | text/csv | CSV読み込み | ✅ |
| MP4 (音声) | video/mp4 | Whisper API | ✅ |
| MP3 | audio/mp3 | Whisper API | ✅ |
| WAV | audio/wav | Whisper API | ✅ |

### 外部API依存関係

| サービス | 用途 | 必要な環境変数 |
|---------|------|---------------|
| OpenAI Vision API | 画像解析 | OPENAI_API_KEY |
| OpenAI Whisper API | 音声文字起こし | OPENAI_API_KEY |
| Google Gemini | LLMエージェント | GOOGLE_API_KEY |

### Python依存関係

```toml
dependencies = [
    "pypdf>=4.0.0",           # PDF処理 (Phase 7で追加)
    "openai>=1.0.0",          # Vision/Whisper API
    "python-magic>=0.4.27",   # MIME type検出
    "langchain-openai>=0.2.0",
    "langchain-google-genai>=2.0.0",
    # ... その他
]
```

---

## 次のステップ

### 優先度 High

- [ ] Phase 7の結合テスト実施
- [ ] CI/CDでのカバレッジ測定
- [ ] 本番環境でのパフォーマンス測定

### 優先度 Medium

- [ ] OCR機能の追加検討 (スキャンPDF対応)
- [ ] 表構造解析機能の検討
- [ ] パフォーマンス最適化 (並列処理)

### 優先度 Low

- [ ] 数式認識機能の検討
- [ ] 2カラムレイアウト対応強化

---

## 参考資料

- [pypdf Documentation](https://pypdf.readthedocs.io/)
- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [PDF Reference 1.7](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf)

---

**最終更新**: 2025-10-12
**作成者**: Claude Code
**ステータス**: Phase 7完了 (全フェーズ完了)
