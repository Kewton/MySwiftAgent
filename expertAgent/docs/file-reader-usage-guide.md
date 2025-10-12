# File Reader 利用ガイド

**最終更新**: 2025-10-12

## 📖 概要

File Reader は、Web上やローカルのファイルを読み込み、内容を抽出するMCPツールです。
PDF、画像、音声、テキストなど、様々なファイル形式に対応しています。

## 🚀 基本的な使い方

### **APIエンドポイント**

```
POST /aiagent-api/v1/aiagent/utility/file_reader
```

### **リクエスト形式**

```json
{
  "user_input": "ファイルの処理指示とURLまたはパス",
  "model_name": "gpt-4o-mini"
}
```

---

## 📝 ファイル形式別の推奨指示文

File Readerは**指示文の内容によって処理方法を自動選択**します。
適切な指示文を使用することで、期待通りの結果が得られます。

### 1️⃣ **PDFファイル**

**推奨指示文:**
```
下記ファイルのテキストを抽出してください。
https://example.com/document.pdf
```

または

```
下記PDFの内容を全て抽出してください。可能な限り元のファイルに忠実にして。
https://drive.google.com/file/d/FILE_ID/view
```

**実行される処理:**
- PyPDF2で全ページのテキストを抽出
- ページ区切り付きで返却（`--- Page 1 ---` 形式）
- **要約せず、全文をそのまま返す**

**出力例:**
```
--- Page 1 ---
Oracle Database 18cの紹介
Oracle ホワイト・ペーパー | 2018 年 7 月

--- Page 2 ---
1 | Oracle Database 18c の紹介
...
```

---

### 2️⃣ **画像ファイル（PNG/JPG/JPEG）**

**推奨指示文:**
```
下記画像の内容を説明してください。
https://example.com/image.png
```

または

```
下記画像ファイルのテキストを抽出してください（OCR）。
https://drive.google.com/file/d/FILE_ID/view
```

**実行される処理:**
- 画像をBase64エンコード
- OpenAI Vision API（gpt-4o）で解析
- **ユーザーの指示に応じた結果を返す**

**出力例:**
```
以下は抽出したテキストです：

左上：
- Node-RED
- フロー 1 フロー 2
...
```

⚠️ **重要**: 画像ファイルに対して「テキストを抽出してください」だけでは不十分です。
**「画像ファイルの」または「画像の内容を」と明示してください。**

---

### 3️⃣ **テキストファイル（TXT/MD）**

**推奨指示文:**
```
下記ファイルの内容を表示してください。
https://example.com/readme.txt
```

**実行される処理:**
- ファイルを直接読み込み
- UTF-8/Shift-JIS/EUC-JPなど複数エンコーディング対応
- 全文をそのまま返す

---

### 4️⃣ **CSVファイル**

**推奨指示文:**
```
下記CSVファイルのデータを抽出してください。
https://example.com/data.csv
```

**実行される処理:**
- CSV解析・整形
- カンマ区切りテキストとして返却

---

### 5️⃣ **音声ファイル（MP3/MP4/WAV）**

**推奨指示文:**
```
下記音声ファイルを文字起こししてください。
https://example.com/audio.mp3
```

**実行される処理:**
- OpenAI Whisper API（whisper-1）で文字起こし
- 全文テキストとして返却

---

## 🌐 対応ソース

### **1. インターネットURL（HTTP/HTTPS）**

```json
{
  "user_input": "下記ファイルのテキストを抽出してください。\nhttps://example.com/document.pdf"
}
```

- **タイムアウト**: 30秒
- **最大ファイルサイズ**: 50MB（デフォルト）

### **2. Google Drive**

```json
{
  "user_input": "下記PDFの内容を抽出してください。\nhttps://drive.google.com/file/d/1ABC123XYZ/view"
}
```

**対応URL形式:**
- `https://drive.google.com/file/d/FILE_ID/view`
- `https://drive.google.com/open?id=FILE_ID`

**認証方法:**
- MyVault経由でOAuth2トークンを自動取得
- ユーザーがGoogle認証を完了している必要あり

### **3. ローカルファイル**

```json
{
  "user_input": "下記ファイルの内容を表示してください。\n/tmp/document.pdf"
}
```

**許可ディレクトリ:**
- `/tmp`, `/var/tmp`
- `~/Downloads`, `~/Documents`

⚠️ セキュリティのため、上記ディレクトリ外のファイルはアクセス不可。

---

## ⚙️ 技術仕様

### **処理フロー**

```
1. ダウンロード
   ↓ (Web/Google Drive → /tmp/tmpXXXXXX.tmp)

2. MIME type検出
   ↓ (python-magic or mimetypes)

3. 形式別処理
   ↓ (PDF/画像/音声/テキスト/CSV)

4. 結果返却
   ↓ (全文テキストまたは解析結果)

5. クリーンアップ
   (一時ファイル自動削除)
```

### **使用API**

| 処理 | API | モデル | 備考 |
|------|-----|--------|------|
| **画像解析** | OpenAI Vision API | gpt-4o | max_tokens=1000 |
| **音声文字起こし** | OpenAI Whisper API | whisper-1 | response_format="text" |
| **PDF抽出** | PyPDF2 | - | ローカル処理 |

### **制限事項**

| 項目 | 制限値 | 備考 |
|------|--------|------|
| **ファイルサイズ** | 50MB | デフォルト設定、変更可能 |
| **HTTPタイムアウト** | 30秒 | ダウンロード時 |
| **Vision API max_tokens** | 1000トークン | 画像解析の出力長 |

---

## ❌ よくある失敗例と対処法

### **❌ 失敗例1: 画像ファイルで「テキストを抽出してください」のみ**

**エラーメッセージ:**
```
指定されたGoogle Driveのファイルは、PDFファイルではなく画像として表示されるため、
テキストを抽出できませんでした。
```

**原因:**
LLMが「テキスト抽出」=「PDF」と解釈し、ツールを呼び出さずに拒否。

**✅ 解決策:**
```
下記**画像ファイル**のテキストを抽出してください。
https://drive.google.com/file/d/FILE_ID/view
```

または

```
下記画像の内容を説明してください。
https://drive.google.com/file/d/FILE_ID/view
```

---

### **❌ 失敗例2: Google Drive URLの権限エラー**

**エラーメッセージ:**
```
Error: Permission denied for Google Drive file (ID: xxx).
File may be private or sharing is disabled.
```

**原因:**
- ファイルが非公開設定
- Google認証が未完了

**✅ 解決策:**
1. Google Drive側で「リンクを知っている全員」に共有設定
2. MyVaultでGoogle認証を完了

---

### **❌ 失敗例3: ローカルファイルのパスエラー**

**エラーメッセージ:**
```
Error: File path is outside allowed directories
```

**原因:**
許可ディレクトリ外のファイルを指定。

**✅ 解決策:**
- `/tmp/` または `~/Downloads/` にファイルを配置
- 絶対パスで指定

---

## 🔒 セキュリティ

### **実施済み対策**

1. **Path Traversal攻撃防止**
   - `Path.resolve()`で絶対パス化
   - 許可ディレクトリホワイトリスト検証

2. **ファイルサイズ制限**
   - デフォルト50MB
   - DoS攻撃対策

3. **一時ファイル管理**
   - 処理完了後に自動削除
   - `/tmp/` に保存（再起動で自動削除）

4. **認証**
   - Google Drive: OAuth2認証（MyVault管理）
   - API Key: MyVault経由で安全に取得

---

## 📊 使用例

### **例1: PDFホワイトペーパーの全文抽出**

**リクエスト:**
```json
{
  "user_input": "下記ファイルのテキスト情報を全て抽出して。可能な限り元のファイルに忠実にして。\nhttps://drive.google.com/file/d/1lcWOmZNTQK1EaoerS0Wyf4yINxWksOOc/view",
  "model_name": "gpt-4o-mini"
}
```

**レスポンス:**
```json
{
  "result": "以下は、指定されたPDFファイル「Oracle Database 18cの紹介」のテキスト内容です。\n\n---\n\n--- Page 1 ---\n \nOracle Database 18cの紹介 \nOracle ホワイト・ペーパー | 2018 年 7 月 \n\n--- Page 2 ---\n\n1 | Oracle Database 18c の紹介 ...",
  "type": "file_reader"
}
```

---

### **例2: スクリーンショットのOCR**

**リクエスト:**
```json
{
  "user_input": "下記画像ファイルのテキストを抽出してください。\nhttps://drive.google.com/file/d/1yQ4jurgJwj1HJmtaY14JX2QiX3q3w61D/view",
  "model_name": "gpt-4o-mini"
}
```

**レスポンス:**
```json
{
  "result": "以下は抽出したテキストです：\n\n左上：\n- Node-RED\n- フロー 1 フロー 2\n...",
  "type": "file_reader"
}
```

---

## 🛠️ トラブルシューティング

### **問題: 処理が遅い**

**原因候補:**
- ファイルサイズが大きい
- ネットワーク遅延
- API応答遅延（Vision/Whisper）

**対処法:**
- ファイルサイズを確認（50MB以下推奨）
- 安定したネットワーク環境で実行
- タイムアウト設定を調整（要コード変更）

---

### **問題: 画像のテキストが正確に読み取れない**

**原因:**
- 画像が不鮮明
- フォントが特殊
- Vision APIの制約

**対処法:**
- 高解像度の画像を使用
- 指示文を具体的にする（例: 「左上のテキストを読み取ってください」）
- max_tokensを増やす（要コード変更）

---

## 📚 関連ドキュメント

- **実装計画**: `docs/file-reader-implementation-plan.md`
- **進捗記録**: `docs/file-reader-progress.md`
- **テスト結果**: `workspace/claudecode/file-reader-test-results.md`

---

## 🆘 サポート

問題が発生した場合は、以下を確認してください：

1. **ログ確認**
   - `logs/expertagent.log`
   - `/tmp/mcp_file_reader_debug.log`

2. **環境変数確認**
   - `OPENAI_API_KEY`（MyVault経由）
   - `GOOGLE_CREDENTIALS_JSON`（MyVault経由）

3. **サービス起動確認**
   - `./scripts/dev-start.sh status`

---

**バージョン**: v1.0.0
**実装日**: 2025-10-12
**対応Issue**: #89
