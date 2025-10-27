# Phase 6: モックから実装への移行 - 作業計画

**作成日**: 2025-10-27
**ブランチ**: feature/issue/110
**前提**: Phase 5完了（workflowGeneratorAgents改善プロンプト適用確認済み）

---

## 📋 Phase 6 の目的

Phase 2-5で「モックアプローチ」を採用した以下の3タスクについて、実際のAPI連携実装に移行します：

| タスク | 現状（Phase 5） | 目標（Phase 6） |
|-------|--------------|--------------|
| **Task 3: TTS音声生成** | モック音声データ生成 | 実際のTTS API呼び出し |
| **Task 4: ファイルアップロード** | モックストレージパス生成 | 実際のクラウドストレージアップロード |
| **Task 7: メール送信** | モックメール送信結果生成 | 実際のメール送信API呼び出し |

---

## 🎯 対策案の提示

### 対策案1: expertAgent APIに実装機能を追加（推奨）

**アプローチ**:
1. expertAgentに新しいAPI endpoints を追加
2. GraphAI workflows からexpertAgent APIを呼び出す
3. expertAgent内部で外部サービス（Google Cloud, SendGrid等）を呼び出す

**メリット**:
- ✅ GraphAI workflowsの変更が最小限（URLの変更のみ）
- ✅ expertAgentで認証情報を一元管理
- ✅ expertAgentでエラーハンドリングやリトライロジックを実装可能
- ✅ 将来的な拡張性が高い

**デメリット**:
- ⚠️ expertAgentのコード変更が必要
- ⚠️ 外部サービスの認証情報設定が必要

**実装規模**: 中規模（1-2日）

---

### 対策案2: GraphAI workflows内で直接外部APIを呼び出す

**アプローチ**:
1. GraphAI workflows内のfetchAgentで直接外部サービスAPIを呼び出す
2. 認証情報は環境変数またはmyVaultで管理

**メリット**:
- ✅ expertAgentのコード変更不要
- ✅ 実装が直接的でシンプル

**デメリット**:
- ❌ GraphAI workflowsが外部サービスに直接依存
- ❌ 認証情報の管理が複雑
- ❌ エラーハンドリングがworkflow内で複雑化
- ❌ 複数のworkflowsで同じロジックを重複実装

**実装規模**: 小規模（0.5-1日）

---

### 対策案3: 段階的移行（最も推奨）

**アプローチ**:
1. **Phase 6-1**: 最も優先度が高いTask 4（ファイルアップロード）のみ実装
2. **Phase 6-2**: Task 7（メール送信）を実装
3. **Phase 6-3**: Task 3（TTS）を実装

各タスクで「対策案1」を採用し、expertAgent APIに段階的に機能追加。

**メリット**:
- ✅ リスクを分散（1タスクずつ検証）
- ✅ 各タスク完了時に動作確認可能
- ✅ 途中で方針変更可能
- ✅ 優先度に応じた実装順序

**デメリット**:
- ⚠️ 全体の完了まで時間がかかる

**実装規模**: 大規模（3-5日、分割可能）

---

## 📊 推奨案: 対策案3（段階的移行）

**理由**:
1. **リスク管理**: 1タスクずつ実装・検証することで、問題発生時の影響範囲を最小化
2. **優先順位**: ファイルアップロード → メール送信 → TTS の順で実装
3. **柔軟性**: 各Phase完了時にユーザーフィードバックを反映可能
4. **品質担保**: 各タスク完了時に十分なテストを実施

---

## 🚀 Phase 6-1: Task 4（ファイルアップロード）実装計画

### 優先順位が高い理由
- ✅ 最も基本的な機能（ファイル保存）
- ✅ 他のタスク（Task 5, 6, 7）の前提条件
- ✅ Google Cloud Storageは標準的で実装事例が豊富

### 実装ステップ

#### **Step 1: expertAgent APIエンドポイント追加**

**新規エンドポイント**: `POST /aiagent-api/v1/utility/upload-file`

**リクエスト**:
```json
{
  "file_content": "base64-encoded content",
  "file_name": "podcast.mp3",
  "content_type": "audio/mpeg",
  "bucket_name": "podcast-bucket"
}
```

**レスポンス**:
```json
{
  "success": true,
  "storage_path": "gs://podcast-bucket/uploads/podcast_20251027.mp3",
  "public_url": "https://storage.googleapis.com/podcast-bucket/uploads/podcast_20251027.mp3",
  "file_size_bytes": 2048000,
  "error_message": ""
}
```

**実装内容**:
1. Google Cloud Storage Python Client Library を使用
2. 認証情報はmyVaultで管理（`GOOGLE_CLOUD_STORAGE_CREDENTIALS`）
3. アップロード先バケットは環境変数で設定（`GCS_BUCKET_NAME`）
4. エラーハンドリング（ネットワークエラー、認証エラー、容量超過等）
5. リトライロジック（最大3回）

#### **Step 2: GraphAI workflow更新**

**修正対象**: `podcast_file_upload_v2.yml`

**変更点**:
- `url`: `http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput`
  → `http://localhost:8104/aiagent-api/v1/utility/upload-file`
- プロンプトから「モックデータ」の記述を削除
- リクエストボディを実際のアップロードAPIに合わせて変更

#### **Step 3: 単体テスト作成**

**テストケース**:
1. ✅ 正常系: ファイルアップロード成功
2. ✅ 異常系: 認証エラー
3. ✅ 異常系: ネットワークエラー
4. ✅ 異常系: ファイルサイズ超過
5. ✅ 異常系: バケット存在しない

#### **Step 4: 結合テスト実行**

**テストフロー**:
1. Task 3（TTS、モック）でダミー音声データ生成
2. **Task 4（ファイルアップロード、実装）で実際にGoogle Cloud Storageにアップロード**
3. Task 5（公開リンク生成）でアップロードされたファイルのリンク生成
4. リンクにアクセスしてファイルが取得できることを確認

#### **Step 5: ドキュメント作成**

**作成ドキュメント**:
- `phase-6-1-file-upload-implementation.md`: 実装レポート
- `GOOGLE_CLOUD_STORAGE_SETUP.md`: Google Cloud Storage設定手順

---

## 📅 Phase 6-1 の想定スケジュール

| Step | 作業内容 | 所要時間 |
|------|---------|---------|
| Step 1 | expertAgent APIエンドポイント追加 | 2-3時間 |
| Step 2 | GraphAI workflow更新 | 30分 |
| Step 3 | 単体テスト作成 | 1-2時間 |
| Step 4 | 結合テスト実行 | 1時間 |
| Step 5 | ドキュメント作成 | 1時間 |
| **合計** | **Phase 6-1完了** | **5-7時間** |

---

## 🔧 Phase 6-2, 6-3 の概要

### Phase 6-2: Task 7（メール送信）実装

**新規エンドポイント**: `POST /aiagent-api/v1/utility/send-email`

**外部サービス候補**:
- SendGrid（推奨、簡単なAPI）
- Amazon SES（AWS利用の場合）
- Gmail API（個人利用の場合）

**実装規模**: 4-6時間

---

### Phase 6-3: Task 3（TTS音声生成）実装

**新規エンドポイント**: `POST /aiagent-api/v1/utility/text-to-speech`

**外部サービス候補**:
- Google Cloud Text-to-Speech API（推奨、高品質）
- Amazon Polly（AWS利用の場合）
- OpenAI TTS API（新規）

**実装規模**: 4-6時間

---

## ✅ 制約条件チェック

### コード品質原則
- [x] **SOLID原則**: expertAgent APIに単一責任のエンドポイント追加
- [x] **KISS原則**: シンプルなAPI設計
- [x] **YAGNI原則**: 必要な機能のみ実装
- [x] **DRY原則**: 共通処理（認証、エラーハンドリング）はユーティリティ化

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: expertAgentがexpertレイヤー、外部サービス連携を担当
- [x] レイヤー分離: GraphAI（orchestration） → expertAgent（business logic） → External Services

### 設定管理ルール
- [x] 環境変数: `GCS_BUCKET_NAME`, `SENDGRID_API_KEY`, `GOOGLE_TTS_API_KEY`
- [x] myVault: `GOOGLE_CLOUD_STORAGE_CREDENTIALS`, `SENDGRID_API_KEY`

### 品質担保方針
- [x] 単体テストカバレッジ **90%以上**
- [x] 結合テストカバレッジ **50%以上**
- [x] Ruff linting エラーゼロ
- [x] MyPy type checking エラーゼロ

### CI/CD準拠
- [x] PRラベル: `feature` ラベル（minor版数アップ）
- [x] コミットメッセージ: Conventional Commits規約準拠
- [x] `pre-push-check-all.sh` 合格

---

## 📋 ユーザー承認待ち項目

以下の点についてご確認・ご承認をお願いします：

### 1. 対策案の選択

- [ ] **対策案1**: expertAgent APIに実装機能を追加（推奨）
- [ ] **対策案2**: GraphAI workflows内で直接外部APIを呼び出す
- [ ] **対策案3**: 段階的移行（最も推奨）

**推奨**: 対策案3（段階的移行）

---

### 2. Phase 6-1（ファイルアップロード）の実装承認

- [ ] **承認**: Phase 6-1の実装を開始する
- [ ] **保留**: Phase 6-1の実装を保留（理由を記載）
- [ ] **変更**: 実装方針を変更（変更内容を記載）

---

### 3. 外部サービスの選択

#### Task 4: ファイルアップロード
- [ ] **Google Cloud Storage**（推奨）
- [ ] **Amazon S3**
- [ ] **その他**:

#### Task 7: メール送信
- [ ] **SendGrid**（推奨）
- [ ] **Amazon SES**
- [ ] **Gmail API**
- [ ] **その他**:

#### Task 3: TTS音声生成
- [ ] **Google Cloud Text-to-Speech**（推奨）
- [ ] **Amazon Polly**
- [ ] **OpenAI TTS**
- [ ] **その他**:

---

### 4. 認証情報の管理方法

- [ ] **myVault**（推奨、既存の仕組み）
- [ ] **環境変数**（シンプル、開発環境のみ）
- [ ] **その他**:

---

## 📝 次のアクション

ユーザー承認後、以下の順序で作業を進めます：

1. ✅ Phase 6-1（ファイルアップロード）実装開始
2. ✅ expertAgent APIエンドポイント追加
3. ✅ 単体テスト作成
4. ✅ GraphAI workflow更新
5. ✅ 結合テスト実行
6. ✅ Phase 6-1完了レポート作成
7. ✅ Phase 6-2（メール送信）に進む（またはここで一旦停止）

---

**作成者**: Claude Code
**作成日**: 2025-10-27
**ステータス**: ✅ 作業計画作成完了、ユーザー承認待ち
