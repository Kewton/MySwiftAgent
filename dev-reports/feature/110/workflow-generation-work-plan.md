# シナリオ4 LLMワークフロー生成・動作確認 作業計画書

**作成日**: 2025-10-26  
**対象**: シナリオ4「キーワード→Podcast生成・メール送信」の6タスク  
**ブランチ**: feature/issue/110  
**担当**: Claude Code

---

## 📋 プロジェクト概要

### 目的

Job Generator で生成されたシナリオ4の各タスクに対して、workflowGeneratorAgentsを使用してGraphAI LLMワークフローYAMLを自動生成し、動作確認を実施する。

### 対象シナリオ

**シナリオ4**: ユーザーがキーワード入力するとそれに関連するポッドキャストを生成してそのリンクをメール送信する

- **JobMaster ID**: `jm_01K8DXE62NFJNB0SHJZPAWQWVT`
- **Job ID**: `j_01K8DXE64XH73JXJTKGXPZDA1P`
- **Status**: `success` ⭐ (唯一の完全成功シナリオ)
- **タスク数**: 6

---

## 🎯 対象タスク一覧

| # | TaskMaster ID | タスク名 | 説明 |
|---|--------------|---------|------|
| 1 | `tm_01K8DXE601HMZWW0K5HR9FDYCQ` | キーワード分析と構成案作成 | キーワードからポッドキャスト構成案を作成 |
| 2 | `tm_01K8DXE60MMZW6PTEFX2EXQB1E` | ポッドキャストスクリプトの生成 | 構成案からスクリプト（台本）を生成 |
| 3 | `tm_01K8DXE614QCAMG90V7Y9XHMXC` | 音声コンテンツの生成 | TTSエンジンでMP3音声ファイル生成 |
| 4 | `tm_01K8DXE61HWT5JKMTQBHDY31EB` | ホスティングとリンク取得 | クラウドストレージにアップロード・URL取得 |
| 5 | `tm_01K8DXE6219B7KJKNZZHZ07Q1B` | メールコンテンツの作成 | メール件名・本文を作成 |
| 6 | `tm_01K8DXE62F5HG3T16GS2GFQD2W` | メール送信 | SMTP/メールAPIで送信 |

---

## 🛠️ 使用技術・API

### Workflow Generator API

- **エンドポイント**: `POST /aiagent-api/v1/workflow-generator`
- **入力**: `job_master_id` または `task_master_id` (XOR)
- **出力**: `WorkflowGeneratorResponse`
  - workflows: WorkflowResult[]
  - status: "success" | "failed" | "partial_success"
  - 統計情報: total_tasks, successful_tasks, failed_tasks
  - generation_time_ms

### LangGraph Agent

- **実装**: `aiagent.langgraph.workflowGeneratorAgents`
- **機能**:
  - タスク情報からGraphAI workflow YAML自動生成
  - Self-repair loop (最大3回リトライ)
  - Validation機能

---

## 📊 Phase 構成

### Phase 1: 事前調査・環境確認 (1時間)

#### 1.1 workflowGeneratorAgents 仕様確認

- [x] API仕様の確認 (workflow_generator_endpoints.py)
- [x] スキーマ定義の確認 (workflow_generator.py)
- [x] LangGraph Agent実装の確認

#### 1.2 シナリオ4 データ確認

- [x] JobMaster情報の取得
- [x] 6タスクの TaskMaster情報取得
- [x] InterfaceMaster 定義の確認

#### 1.3 環境確認

- [ ] expertAgent API サーバー起動確認
- [ ] jobqueue API サーバー起動確認
- [ ] データベース接続確認

---

### Phase 2: 一括ワークフロー生成 (2-3時間)

#### 2.1 JobMaster単位での生成

**目的**: 6タスク全体のワークフローを一括生成

**リクエスト**:
```json
{
  "job_master_id": "jm_01K8DXE62NFJNB0SHJZPAWQWVT"
}
```

**期待される出力**:
- 6個の WorkflowResult
- 各タスクの YAML コンテンツ
- validation_result
- retry_count

**検証項目**:
- [ ] 全6タスクのYAML生成成功
- [ ] YAML構文の妥当性
- [ ] GraphAI仕様への準拠
- [ ] InterfaceMasterとの整合性

#### 2.2 生成結果の保存

**保存先**: `/tmp/scenario4_workflows/`

- `task_001_keyword_analysis.yaml`
- `task_002_script_generation.yaml`
- `task_003_audio_generation.yaml`
- `task_004_hosting_upload.yaml`
- `task_005_email_content.yaml`
- `task_006_email_send.yaml`

---

### Phase 3: 個別タスク検証 (3-4時間)

#### 3.1 タスク1: キーワード分析と構成案作成

**リクエスト**:
```json
{
  "task_master_id": "tm_01K8DXE601HMZWW0K5HR9FDYCQ"
}
```

**検証ポイント**:
- [ ] INPUT interface: ユーザーキーワード受付
- [ ] OUTPUT interface: JSON形式の構成案
- [ ] LLM Agent使用の適切性
- [ ] プロンプト設計の妥当性

**動作確認内容**:
- サンプルキーワード: "AI技術の最新動向"
- 期待される構成案: トピック、セクションリスト、トーン、ターゲット

#### 3.2 タスク2: ポッドキャストスクリプトの生成

**検証ポイント**:
- [ ] INPUT: task_001の構成案を受け取る
- [ ] OUTPUT: 話者・セリフを含むスクリプト
- [ ] 依存関係の正しい実装

**動作確認内容**:
- INPUT: タスク1の出力をモック
- 期待される出力: 台本形式のテキスト

#### 3.3 タスク3: 音声コンテンツの生成

**検証ポイント**:
- [ ] INPUT: タスク2のスクリプト
- [ ] OUTPUT: MP3ファイル（URL or binary）
- [ ] TTS API連携の実装

**動作確認内容**:
- `/v1/utility/text_to_speech_drive` API使用確認
- 音声ファイル生成確認

#### 3.4 タスク4: ホスティングとリンク取得

**検証ポイント**:
- [ ] INPUT: タスク3の音声ファイル
- [ ] OUTPUT: 公開アクセス可能なURL
- [ ] Google Drive Upload API連携

**動作確認内容**:
- クラウドストレージへのアップロード
- 永続的なURL取得

#### 3.5 タスク5: メールコンテンツの作成

**検証ポイント**:
- [ ] INPUT: タスク4のポッドキャストURL
- [ ] OUTPUT: メール件名・本文（JSON）
- [ ] テンプレート生成の妥当性

**動作確認内容**:
- サンプルURL: https://drive.google.com/file/xxx
- 期待される出力: メール構造化データ

#### 3.6 タスク6: メール送信

**検証ポイント**:
- [ ] INPUT: タスク5のメールデータ
- [ ] OUTPUT: 送信成功ステータス
- [ ] Gmail API連携の実装

**動作確認内容**:
- `/v1/utility/gmail/send` API使用確認
- 実際のメール送信（テスト用アドレス）

---

### Phase 4: End-to-End 動作確認 (2-3時間)

#### 4.1 全タスク連携テスト

**テストシナリオ**:
1. ユーザーがキーワード "機械学習の基礎" を入力
2. タスク1で構成案生成
3. タスク2でスクリプト生成
4. タスク3で音声ファイル生成
5. タスク4でGoogle Driveにアップロード
6. タスク5でメールコンテンツ作成
7. タスク6でメール送信

**検証ポイント**:
- [ ] タスク間のデータフロー
- [ ] 各インタフェースの整合性
- [ ] エラーハンドリング
- [ ] 処理時間の測定

#### 4.2 異常系テスト

**テストケース**:
- [ ] 不正なキーワード入力
- [ ] TTS API エラー
- [ ] Google Drive アップロード失敗
- [ ] Gmail API エラー

---

### Phase 5: 結果評価・ドキュメント作成 (2時間)

#### 5.1 評価指標

| 評価項目 | 目標 | 測定方法 |
|---------|------|---------|
| ワークフロー生成成功率 | 100% (6/6) | API レスポンス status |
| YAML構文妥当性 | 100% | YAML parser検証 |
| InterfaceMaster整合性 | 100% | スキーマ検証 |
| End-to-End成功率 | 80%以上 | 実行テスト |
| 平均生成時間 | < 10秒/タスク | generation_time_ms |

#### 5.2 成果物

**必須ドキュメント**:
1. `workflow-generation-results.md`: 生成結果レポート
2. `workflow-validation-report.md`: 検証結果詳細
3. `e2e-test-report.md`: End-to-End テストレポート
4. `workflow-improvement-proposals.md`: 改善提案

**成果物（YAML）**:
- 6個のGraphAI workflow YAMLファイル
- サンプル入出力データ

---

## ⚠️ 制約条件・前提条件

### 技術的制約

1. **ID型の制約**:
   - API仕様は `job_master_id: int | None` だが、実際はULID文字列
   - 実装側で文字列→数値変換処理が必要

2. **API依存**:
   - `/v1/utility/text_to_speech_drive` API の実装状況
   - `/v1/utility/gmail/send` API の実装状況
   - Google Drive Upload API の利用可能性

3. **LLM制約**:
   - プロンプト設計の品質
   - 構造化出力の安定性
   - リトライ回数の上限（max_retry=3）

### 前提条件

- [x] expertAgent APIサーバーが起動している
- [ ] jobqueue APIサーバーが起動している
- [x] シナリオ4のJobMaster/TaskMaster/InterfaceMasterが登録済み
- [ ] Google APIキー・認証情報が設定済み
- [ ] テスト用Gmailアカウントが利用可能

---

## 🎯 成功基準

### 必須要件（Phase 2）

- [x] 6タスク全てのワークフローYAML生成成功
- [ ] YAML構文エラーゼロ
- [ ] validation_result がすべて valid

### 推奨要件（Phase 3-4）

- [ ] 各タスクの個別動作確認完了
- [ ] End-to-Endテスト成功（1回以上）
- [ ] エラーハンドリングの検証完了

### オプション要件（Phase 5）

- [ ] パフォーマンス改善提案の作成
- [ ] ワークフロー最適化案の提示
- [ ] 再利用可能なテンプレート化

---

## 📅 スケジュール

| Phase | タスク | 予定工数 | 開始予定 | 完了予定 |
|-------|-------|---------|---------|---------|
| Phase 1 | 事前調査・環境確認 | 1時間 | 即時 | +1時間 |
| Phase 2 | 一括ワークフロー生成 | 2-3時間 | +1時間 | +4時間 |
| Phase 3 | 個別タスク検証 | 3-4時間 | +4時間 | +8時間 |
| Phase 4 | End-to-End動作確認 | 2-3時間 | +8時間 | +11時間 |
| Phase 5 | 結果評価・ドキュメント | 2時間 | +11時間 | +13時間 |

**総予定工数**: 10-13時間

---

## 🔄 リスクと対策

### リスク1: API ID型不整合

**リスク**: ULID文字列と整数型の不整合によるエラー

**対策**:
- 文字列IDをそのまま送信してAPIの変換処理に任せる
- エラー発生時は数値変換処理の実装を検討

### リスク2: Direct API未実装

**リスク**: TTS APIやGmail APIが未実装でワークフロー実行不可

**対策**:
- Phase 1でAPI実装状況を確認
- 未実装の場合はモック実装を検討
- ワークフロー生成のみ実施し、実行はスキップ

### リスク3: LLM出力の不安定性

**リスク**: YAML生成時の構造化出力失敗

**対策**:
- Self-repair loop (最大3回リトライ)
- JSON recovery fallbackの活用
- プロンプト改善提案の作成

### リスク4: End-to-End テスト環境不足

**リスク**: Google API認証情報がない

**対策**:
- テストスキップ可能な設計
- モックデータでの部分検証
- ドキュメントで制約を明記

---

## 📝 ドキュメント管理

### 保存先

`dev-reports/feature/issue/110/`

### ファイル構成

```
dev-reports/feature/issue/110/
├── workflow-generation-work-plan.md           # 本ドキュメント
├── workflow-generation-results.md             # Phase 2: 生成結果
├── workflow-validation-report.md              # Phase 3: 検証レポート
├── e2e-test-report.md                         # Phase 4: E2Eテスト
└── workflow-improvement-proposals.md          # Phase 5: 改善提案
```

---

## ✅ チェックリスト

### Phase 1: 事前調査

- [x] workflowGeneratorAgents API仕様確認
- [x] シナリオ4データ取得
- [ ] expertAgent APIサーバー起動確認
- [ ] jobqueue APIサーバー起動確認

### Phase 2: ワークフロー生成

- [ ] JobMaster IDでのAPI呼び出し
- [ ] 6タスク全てのYAML取得
- [ ] YAML構文検証
- [ ] 結果レポート作成

### Phase 3: 個別検証

- [ ] タスク1検証
- [ ] タスク2検証
- [ ] タスク3検証
- [ ] タスク4検証
- [ ] タスク5検証
- [ ] タスク6検証

### Phase 4: E2Eテスト

- [ ] テストシナリオ実行
- [ ] 異常系テスト
- [ ] パフォーマンス測定

### Phase 5: 評価・ドキュメント

- [ ] 評価指標の測定
- [ ] ドキュメント作成
- [ ] 改善提案の作成

---

**作成日**: 2025-10-26  
**作成者**: Claude Code  
**バージョン**: 1.0
