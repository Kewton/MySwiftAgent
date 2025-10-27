# Phase 6-1 実装レポート: Task 3, 4, 5 の実機能移行

**作成日**: 2025-10-27
**ブランチ**: feature/issue/110
**対象**: Task 3（TTS音声生成）, Task 4（ファイルアップロード）, Task 5（公開リンク生成）

---

## 📋 Phase 6-1 の目的

Phase 2-5で採用した「モックアプローチ」から「実機能実装」への移行。
特に、Task 3, 4, 5を既存DirectAPI（`/utility/text_to_speech_drive`）を活用して実装。

---

## 🔍 実装前の調査結果

### 発見した既存DirectAPI

expertAgentに以下の統合APIが既に実装済みであることを確認：

**`POST /aiagent-api/v1/utility/text_to_speech_drive`**
- **機能**: TTS音声生成 + Google Drive アップロードを1つのAPIで実行
- **実行時間**: 5-10秒（Agent-based の 20-180秒に比べて大幅に高速）
- **使用技術**:
  - OpenAI TTS API (tts-1 / tts-1-hd)
  - Google Drive MCP Integration
  - MyVault認証

**リクエストスキーマ** (`TTSDriveRequest`):
```json
{
  "text": "ポッドキャストの台本テキスト",
  "drive_folder_url": "https://drive.google.com/drive/folders/...",
  "sub_directory": "podcasts/2025",
  "file_name": "podcast",
  "model": "tts-1",
  "voice": "alloy"
}
```

**レスポンススキーマ** (`TTSDriveResponse`):
```json
{
  "file_id": "1ABC...XYZ",
  "file_name": "podcast_20251027_143022.mp3",
  "web_view_link": "https://drive.google.com/file/d/1ABC...XYZ/view",
  "web_content_link": "https://drive.google.com/uc?id=1ABC...XYZ&export=download",
  "folder_path": "/MyDrive/podcasts/2025",
  "file_size_mb": 2.5
}
```

### 統合APIの影響範囲

**従来のタスク分離**:
- Task 3: TTS音声生成（script_text → audio_data_base64）
- Task 4: ファイルアップロード（audio_data_base64 → storage_path）
- Task 5: 公開リンク生成（storage_path → public_url）

**統合API活用後**:
- **Task 3**: TTS + Drive Upload（script_text → web_view_link + file info）
- **Task 4**: Pass-through（既にアップロード済み）
- **Task 5**: Pass-through（web_view_link が既に公開URL）

→ Task 4, 5 は実質的に不要だが、ワークフロー構造維持のため残す

---

## 🛠️ 実装内容

### 1. Task 3: tts_audio_generation_v3.yml

**変更点**:
- **v2（モック）**: LLMにmock audio_data_base64を生成させる（3ノード構成）
- **v3（実装）**: 統合DirectAPIを直接呼び出す（**2ノード構成**）

**ノード構成**:
1. **source**: 入力受付（script_text, drive_folder_url等）
2. **generate_audio**: `/utility/text_to_speech_drive` APIコール
3. **output**: 出力フォーマット（file_id, web_view_link等）

**主要な改善**:
- ✅ Node削減: 3ノード → 2ノード（build_tts_prompt削除）
- ✅ LLMコール削除: jsonoutput API → DirectAPI
- ✅ 実行時間短縮: 60秒（モック） → 5-10秒（実装）
- ✅ 実際の音声ファイル生成: OpenAI TTS API使用

**入力スキーマ**:
```yaml
script_text: "ポッドキャスト台本テキスト"
drive_folder_url: "https://drive.google.com/drive/folders/..." # Optional
sub_directory: "podcasts/2025" # Optional
file_name: "podcast" # Optional
model: "tts-1" # Optional (default: tts-1)
voice: "alloy" # Optional (default: alloy)
```

**出力スキーマ**:
```yaml
success: true
file_id: "1ABC...XYZ"
file_name: "podcast_20251027_143022.mp3"
web_view_link: "https://drive.google.com/file/d/1ABC...XYZ/view"
web_content_link: "https://drive.google.com/uc?id=1ABC...XYZ&export=download"
folder_path: "/MyDrive/podcasts/2025"
file_size_mb: 2.5
error_message: ""
```

---

### 2. Task 4: podcast_file_upload_v3.yml

**変更点**:
- **v2（モック）**: LLMにmock storage_pathを生成させる（3ノード構成）
- **v3（実装）**: Task 3の出力を転送するだけ（**1ノード構成**）

**ノード構成**:
1. **source**: Task 3からのfile info受付
2. **output**: storage_path（= web_view_link）を出力

**主要な改善**:
- ✅ Node削減: 3ノード → 1ノード
- ✅ LLMコール削除: jsonoutput API → なし（Pass-through）
- ✅ 実行時間短縮: 60秒（モック） → <1秒（Pass-through）

**入力スキーマ**:
```yaml
# Task 3 の出力をそのまま受け取る
file_id: "1ABC...XYZ"
file_name: "podcast_20251027_143022.mp3"
web_view_link: "https://drive.google.com/file/d/..."
file_size_mb: 2.5
```

**出力スキーマ**:
```yaml
success: true
storage_path: "https://drive.google.com/file/d/..." # = web_view_link
file_id: "1ABC...XYZ"
file_name: "podcast_20251027_143022.mp3"
file_size_mb: 2.5
error_message: ""
```

---

### 3. Task 5: generate_public_share_link_v3.yml

**変更点**:
- **v2（モック）**: LLMにmock public_urlを生成させる（3ノード構成）
- **v3（実装）**: Task 4の storage_path を public_url として転送（**1ノード構成**）

**ノード構成**:
1. **source**: Task 4からのstorage_path受付
2. **output**: public_url（= storage_path）を出力

**主要な改善**:
- ✅ Node削減: 3ノード → 1ノード
- ✅ LLMコール削除: jsonoutput API → なし（Pass-through）
- ✅ 実行時間短縮: 60秒（モック） → <1秒（Pass-through）

**入力スキーマ**:
```yaml
storage_path: "https://drive.google.com/file/d/..."
file_id: "1ABC...XYZ"
file_name: "podcast_20251027_143022.mp3"
```

**出力スキーマ**:
```yaml
success: true
public_url: "https://drive.google.com/file/d/..." # = storage_path
file_id: "1ABC...XYZ"
file_name: "podcast_20251027_143022.mp3"
error_message: ""
```

---

## 📊 パフォーマンス比較

| タスク | v2（モック） | v3（実装） | 改善率 |
|--------|-------------|-----------|--------|
| **Task 3: TTS生成** | 60秒（LLM） | 5-10秒（DirectAPI） | **83-92%削減** |
| **Task 4: アップロード** | 60秒（LLM） | <1秒（Pass-through） | **98%以上削減** |
| **Task 5: 公開リンク** | 60秒（LLM） | <1秒（Pass-through） | **98%以上削減** |
| **合計（Task 3-5）** | 180秒 | 6-11秒 | **94-97%削減** |

---

## 📁 作成ファイル

| ファイル名 | 説明 | ノード数 |
|-----------|------|---------|
| `tts_audio_generation_v3.yml` | Task 3実装版（TTS + Drive Upload統合API） | 2ノード |
| `podcast_file_upload_v3.yml` | Task 4実装版（Pass-through） | 1ノード |
| `generate_public_share_link_v3.yml` | Task 5実装版（Pass-through） | 1ノード |

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: Task 3は単一責任（TTS+Upload）、Task 4/5はシンプルなPass-through
- [x] **KISS原則**: シンプルな実装（不要なLLMコール削除）
- [x] **YAGNI原則**: 必要最小限（既存APIを活用）
- [x] **DRY原則**: 既存DirectAPIを再利用

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: expertAgentがDirectAPIを提供、GraphAIから呼び出す
- [x] レイヤー分離: GraphAI（orchestration） → expertAgent（TTS+Storage） → External APIs

### 設定管理ルール
- [x] 環境変数: `OPENAI_API_KEY` for TTS
- [x] myVault: Google Drive認証情報はmyVault + MCP経由で管理

### 品質担保方針
- [ ] **単体テスト**: まだ実施していない（次ステップ）
- [ ] **結合テスト**: まだ実施していない（次ステップ）
- [x] **Ruff linting**: YAMLファイルは対象外
- [x] **MyPy type checking**: YAMLファイルは対象外

### CI/CD準拠
- [x] PRラベル: `feature` ラベル予定（minor版数アップ）
- [x] コミットメッセージ: Conventional Commits規約準拠予定
- [ ] `pre-push-check-all.sh`: YAMLファイル変更のみのため対象外

---

## 📋 次のステップ（Phase 6-1テスト）

### 前提条件確認

以下の環境設定が必要：

1. **✅ expertAgentサービス起動**:
   ```bash
   cd expertAgent
   ./scripts/dev-start.sh
   ```

2. **✅ OpenAI API キー設定**:
   ```bash
   # .envファイルに設定済みか確認
   echo $OPENAI_API_KEY
   ```

3. **✅ Google Drive 認証設定**:
   - myVault に Google Drive 認証情報が登録済みか確認
   - MCP経由でGoogle Driveアクセス可能か確認

### テスト実施計画

#### **Test 1: Task 3単体テスト**

**目的**: 統合APIが正常に動作するか確認

**テストリクエスト**:
```json
{
  "user_input": {
    "script_text": "これはポッドキャストのテスト音声です。OpenAI TTSを使用して音声ファイルを生成し、Google Driveにアップロードします。",
    "drive_folder_url": "<your_drive_folder_url>",
    "sub_directory": "test/phase6-1",
    "file_name": "test_podcast",
    "model": "tts-1",
    "voice": "alloy"
  },
  "model_name": "tts_audio_generation_v3"
}
```

**期待される結果**:
- ✅ HTTP 200 OK
- ✅ file_id が返される
- ✅ web_view_link が有効なGoogle Drive URL
- ✅ ファイルサイズが 0より大きい
- ✅ 実行時間が 5-10秒程度

#### **Test 2: Task 3 → Task 4 連携テスト**

**目的**: Task 3の出力がTask 4で正しく処理されるか確認

#### **Test 3: Task 3 → Task 4 → Task 5 連携テスト**

**目的**: 3タスク連携で最終的にpublic_urlが正しく出力されるか確認

---

## 🚧 既知の課題・制約

### 1. Task 4, 5の冗長性

**問題**: Task 3の統合APIで既にアップロード完了しているため、Task 4, 5は実質的に不要

**現状の対応**: ワークフロー構造維持のためPass-throughとして残す

**将来の改善案**:
- workflowGeneratorAgentsに「統合タスク」の概念を追加
- Task 3-5を1つのタスクとして自動生成
- 既存の7タスク構造を最適化

### 2. Google Drive認証依存

**制約**: myVault + MCP でGoogle Drive認証が必要

**影響**: 認証設定がない環境ではTask 3が失敗する

**対策**: テスト前に認証設定の確認を必須化

### 3. OpenAI API キー依存

**制約**: OPENAI_API_KEY 環境変数が必要

**影響**: API キーがない環境ではTTS生成が失敗する

**対策**: テスト前にAPI キー設定の確認を必須化

---

## 📝 実装上の決定事項

### 1. なぜv3として新規作成したか？

**理由**:
- v2（モック）との互換性維持
- Phase 5の検証結果を保持
- ロールバックを容易にする

### 2. なぜTask 4, 5を削除せずPass-throughとしたか？

**理由**:
- workflowGeneratorAgentsが7タスク構造を前提としている
- Task 6 (email_body_composition) がTask 5の出力（public_url）を期待している
- ワークフロー全体の破壊的変更を避ける

### 3. なぜsub_directory等をオプションにしたか？

**理由**:
- テスト時に柔軟なディレクトリ構造を許容
- デフォルト値は統合API側で設定済み
- ユーザーの要件に応じてカスタマイズ可能

---

**作成者**: Claude Code
**作成日**: 2025-10-27
**ステータス**: ✅ 実装完了、テスト準備中
