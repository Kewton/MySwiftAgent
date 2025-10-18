# CommonUI ユーザーシナリオ・操作手順ガイド

本ドキュメントでは、CommonUIを使用した典型的なユーザーシナリオと、各シナリオにおける操作手順を説明します。

---

## 📋 目次

1. [シナリオ1: 新規InterfaceMaster作成](#シナリオ1-新規interfacemaster作成)
2. [シナリオ2: 新規TaskMaster作成](#シナリオ2-新規taskmaster作成)
3. [シナリオ3: 新規JobMaster作成](#シナリオ3-新規jobmaster作成)
4. [シナリオ4: JobMasterにタスクを設定](#シナリオ4-jobmasterにタスクを設定)
5. [シナリオ5: Jobの実行と監視](#シナリオ5-jobの実行と監視)
6. [シナリオ6: インターフェース互換性エラーの修正](#シナリオ6-インターフェース互換性エラーの修正)
7. [シナリオ7: 失敗したタスクの再実行](#シナリオ7-失敗したタスクの再実行)

---

## シナリオ1: 新規InterfaceMaster作成

**目的**: API間のデータ受け渡しを定義するInterfaceMasterを作成する

**前提条件**:
- CommonUIにアクセス可能
- JobQueueサービスが起動中

### 操作手順

| ステップ | 画面/タブ | 操作内容 | 入力例 | 期待される結果 |
|---------|----------|---------|-------|--------------|
| 1 | Home | 「InterfaceMasters」メニューをクリック | - | InterfaceMaster管理画面が表示される |
| 2 | InterfaceMasters / 🆕 Create | 「Name」フィールドに名前を入力 | `CompanySearchInterface` | - |
| 3 | InterfaceMasters / 🆕 Create | 「Description」フィールドに説明を入力 | `Interface for company search input/output` | - |
| 4 | InterfaceMasters / 🆕 Create | Input Schemaの「Template」ドロップダウンから選択 | `Company Search` | テンプレートのJSONが自動入力される |
| 5 | InterfaceMasters / 🆕 Create | 必要に応じてInput SchemaのJSONを編集 | プロパティの追加・変更 | ✅ Valid JSON Schema 表示を確認 |
| 6 | InterfaceMasters / 🆕 Create | Output Schemaの「Template」ドロップダウンから選択 | `Simple Object` | テンプレートのJSONが自動入力される |
| 7 | InterfaceMasters / 🆕 Create | 必要に応じてOutput SchemaのJSONを編集 | プロパティの追加・変更 | ✅ Valid JSON Schema 表示を確認 |
| 8 | InterfaceMasters / 🆕 Create | 「Is Active」チェックボックスを確認（デフォルトON） | - | チェック済み |
| 9 | InterfaceMasters / 🆕 Create | 「✨ Create InterfaceMaster」ボタンをクリック | - | 成功メッセージが表示される |
| 10 | InterfaceMasters / 📋 List | 作成したInterfaceMasterが一覧に表示されることを確認 | - | 新規InterfaceMasterが表示される |

**保存されるデータ**:
- データベース: `interface_masters` テーブルに永続化
- 再起動後もデータは保持される

---

## シナリオ2: 新規TaskMaster作成

**目的**: 実行可能なタスクの定義（TaskMaster）を作成し、InterfaceMasterと紐付ける

**前提条件**:
- InterfaceMasterが既に作成済み（シナリオ1完了）

### 操作手順

| ステップ | 画面/タブ | 操作内容 | 入力例 | 期待される結果 |
|---------|----------|---------|-------|--------------|
| 1 | Home | 「TaskMasters」メニューをクリック | - | TaskMaster管理画面が表示される |
| 2 | TaskMasters / 🆕 Create | 「Name」フィールドに名前を入力 | `company_search` | - |
| 3 | TaskMasters / 🆕 Create | 「Description」フィールドに説明を入力 | `Search for company information` | - |
| 4 | TaskMasters / 🆕 Create | 「HTTP Method」ドロップダウンから選択 | `POST` | - |
| 5 | TaskMasters / 🆕 Create | 「URL」フィールドにエンドポイントURLを入力 | `https://api.example.com/companies/search` | - |
| 6 | TaskMasters / 🆕 Create | 「Max Retries」フィールドに数値を入力 | `3` | - |
| 7 | TaskMasters / 🆕 Create | 「Retry Delay (seconds)」フィールドに数値を入力 | `5` | - |
| 8 | TaskMasters / 🆕 Create | 「Input Interface」ドロップダウンから選択 | `CompanySearchInterface (if_XXX)` | - |
| 9 | TaskMasters / 🆕 Create | 「Output Interface」ドロップダウンから選択 | `CompanySearchInterface (if_XXX)` | - |
| 10 | TaskMasters / 🆕 Create | 「Timeout (seconds)」フィールドに数値を入力 | `30` | - |
| 11 | TaskMasters / 🆕 Create | 「Is Active」チェックボックスを確認 | - | チェック済み |
| 12 | TaskMasters / 🆕 Create | 「✨ Create TaskMaster」ボタンをクリック | - | 成功メッセージが表示される |
| 13 | TaskMasters / 📋 List | 作成したTaskMasterが一覧に表示されることを確認 | - | 新規TaskMasterが表示される |

**保存されるデータ**:
- データベース: `task_masters` テーブルに永続化
- InterfaceMasterとの紐付け情報も保存される

---

## シナリオ3: 新規JobMaster作成

**目的**: 複数のTaskMasterを組み合わせて実行するJobMasterを作成する

**前提条件**:
- JobQueue画面にアクセス可能

### 操作手順

| ステップ | 画面/タブ | 操作内容 | 入力例 | 期待される結果 |
|---------|----------|---------|-------|--------------|
| 1 | Home | 「JobMasters」メニューをクリック | - | JobMaster管理画面が表示される |
| 2 | JobMasters / 🆕 Create Master | 「Name」フィールドに名前を入力 | `Company Research Workflow` | - |
| 3 | JobMasters / 🆕 Create Master | 「Description」フィールドに説明を入力 | `Comprehensive company research and analysis workflow` | - |
| 4 | JobMasters / 🆕 Create Master | 「HTTP Method」ドロップダウンから選択 | `POST` | - |
| 5 | JobMasters / 🆕 Create Master | 「URL」フィールドにエンドポイントURLを入力 | `https://api.example.com/workflows/company-research` | - |
| 6 | JobMasters / 🆕 Create Master | 「Timeout (sec)」フィールドに数値を入力 | `300` | - |
| 7 | JobMasters / 🆕 Create Master | 「Max Attempts」フィールドに数値を入力 | `3` | - |
| 8 | JobMasters / 🆕 Create Master | 「Backoff Strategy」ドロップダウンから選択 | `exponential` | - |
| 9 | JobMasters / 🆕 Create Master | 「Backoff Seconds」フィールドに数値を入力 | `5` | - |
| 10 | JobMasters / 🆕 Create Master | 「TTL (sec)」フィールドに数値を入力 | `3600` | - |
| 11 | JobMasters / 🆕 Create Master | 「Tags」フィールドにタグを入力（カンマ区切り） | `research, analysis` | - |
| 12 | JobMasters / 🆕 Create Master | 「✨ Create Job Master」ボタンをクリック | - | 成功メッセージが表示される |
| 13 | JobMasters / 📋 List Masters | 作成したJobMasterが一覧に表示されることを確認 | - | 新規JobMasterが表示される |

**保存されるデータ**:
- データベース: `job_masters` テーブルに永続化
- この時点ではタスクは未設定（シナリオ4で設定）

---

## シナリオ4: JobMasterにタスクを設定

**目的**: JobMasterに実行するTaskMasterを追加し、順序を設定し、インターフェース互換性を検証する

**前提条件**:
- JobMasterが作成済み（シナリオ3完了）
- TaskMasterが作成済み（シナリオ2完了）

### 操作手順

| ステップ | 画面/タブ | 操作内容 | 入力例 | 期待される結果 |
|---------|----------|---------|-------|--------------|
| 1 | Home | 「Job Configuration」メニューをクリック | - | Job Configuration画面が表示される |
| 2 | Job Configuration | 「Select JobMaster」ドロップダウンから選択 | `Company Research Workflow (jm_XXX)` | 選択したJobMasterが表示される |
| 3 | Job Configuration | 左カラム「➕ Add Task to Workflow」セクションに移動 | - | - |
| 4 | Job Configuration | 「Select TaskMaster to add」ドロップダウンから選択 | `company_search (tm_XXX)` | タスクの説明が表示される |
| 5 | Job Configuration | 「➕ Add to Workflow」ボタンをクリック | - | 成功メッセージ、タスクリストに追加される |
| 6 | Job Configuration | 手順4-5を繰り返して2つ目のタスクを追加 | `company_analysis (tm_YYY)` | タスクリストに追加される |
| 7 | Job Configuration | 手順4-5を繰り返して3つ目のタスクを追加 | `report_generation (tm_ZZZ)` | タスクリストに追加される |
| 8 | Job Configuration | 「📋 Workflow Tasks」セクションでタスク順序を確認 | Order: 0, 1, 2 | タスクが順番に表示される |
| 9 | Job Configuration | （必要に応じて）タスクの順序を変更 | Move Up/Down ボタン使用 | 順序が変更される |
| 10 | Job Configuration | 右カラム「🔍 Workflow Validation」セクションに移動 | - | - |
| 11 | Job Configuration | 「🔍 Validate Workflow」ボタンをクリック | - | 検証結果が表示される |
| 12 | Job Configuration | 検証結果を確認 | ✅ Workflow is valid! | すべてのインターフェースが互換性あり |
| 13 | Job Configuration | （検証成功の場合）「🚀 Publish Workflow Version」セクションに移動 | - | - |
| 14 | Job Configuration | 「🚀 Publish Version」ボタンをクリック | - | バージョンが公開される |

**保存されるデータ**:
- データベース: `job_master_tasks` テーブルにタスク紐付け情報が永続化
- タスクの追加・削除・順序変更は即座にDBに保存される
- 検証結果のみセッションステート（一時保存）

**データ永続性**:
- ✅ ブラウザを閉じても、サーバーを再起動しても、タスク設定は保持される
- ✅ 検証が失敗しても、設定済みタスクは削除されない
- ✅ 後日、同じJobMasterを選択すれば続きから作業可能

---

## シナリオ5: Jobの実行と監視

**目的**: 設定済みのJobMasterからJobを作成・実行し、その進行状況を監視する

**前提条件**:
- JobMasterにタスクが設定済み（シナリオ4完了）
- ワークフローの検証が成功している

### 操作手順（Job作成）

| ステップ | 画面/タブ | 操作内容 | 入力例 | 期待される結果 |
|---------|----------|---------|-------|--------------|
| 1 | Home | 「JobMasters」メニューをクリック | - | JobMaster管理画面が表示される |
| 2 | JobMasters / 📊 From Master | 「Select Master Template」ドロップダウンから選択 | `Company Research Workflow (jm_XXX)` | マスター設定が表示される |
| 3 | JobMasters / 📊 From Master | マスターのデフォルト設定を確認 | - | Method, URL, Timeout等が表示される |
| 4 | JobMasters / 📊 From Master | （任意）「Job Name」フィールドに上書き名を入力 | `Toyota Corporation Research` | - |
| 5 | JobMasters / 📊 From Master | （任意）「Request Body Override (JSON)」に入力データを入力 | `{"company_name": "Toyota", "country": "Japan"}` | - |
| 6 | JobMasters / 📊 From Master | （任意）「Priority」スライダーで優先度を設定 | `3` (1=最高, 10=最低) | - |
| 7 | JobMasters / 📊 From Master | 「🚀 Create Job from Master」ボタンをクリック | - | Jobが作成され、Job IDが表示される |

### 操作手順（Job監視）

| ステップ | 画面/タブ | 操作内容 | 入力例 | 期待される結果 |
|---------|----------|---------|-------|--------------|
| 8 | Home | 「Job Execution」メニューをクリック | - | Job Execution History画面が表示される |
| 9 | Job Execution | 「Select JobMaster」ドロップダウンから選択 | `Company Research Workflow (jm_XXX)` | Jobリストが表示される |
| 10 | Job Execution | （任意）「Status Filter」でステータスを絞り込み | `running` | 実行中のJobのみ表示 |
| 11 | Job Execution | （任意）「Auto Refresh」チェックボックスをON | - | 自動的に5秒ごとにリフレッシュされる |
| 12 | Job Execution | Jobリストから監視したいJobをクリック | `Toyota Corporation Research` | Job詳細とタスク一覧が表示される |
| 13 | Job Execution | Job詳細セクションでステータス・実行時間を確認 | Status: 🔄 RUNNING | - |
| 14 | Job Execution | 「📊 Task Execution Timeline」でタスクの進行状況を確認 | Task 0: ✓ SUCCEEDED, Task 1: 🔄 RUNNING | - |
| 15 | Job Execution | （各タスクのExpander）タスク詳細を展開 | - | Input Data, Output Data, Error等が表示される |
| 16 | Job Execution | Jobが完了するまで監視を継続 | - | Status: ✓ SUCCEEDED または ✗ FAILED |

**ステータスの意味**:
- ⏳ `queued`: 実行待ち
- 🔄 `running`: 実行中
- ✓ `succeeded`: 成功
- ✗ `failed`: 失敗
- ⏹ `canceled`: キャンセル済み

---

## シナリオ6: インターフェース互換性エラーの修正

**目的**: ワークフロー検証でインターフェース互換性エラーが発生した場合の対処方法

**前提条件**:
- JobMasterにタスクが設定済み
- 検証実行時にエラーが発生

### エラー例

```
❌ Workflow validation failed. Please fix the errors below.

🔴 Incompatible interfaces: Task 0 (company_search, output=CompanySearchInterface) → Task 1 (company_analysis, input=CompanyAnalysisInterface)
  - Missing property: company_analysis.input requires 'website' but company_search.output does not provide it
```

### 操作手順

| ステップ | 画面/タブ | 操作内容 | 解決方法 | 期待される結果 |
|---------|----------|---------|---------|--------------|
| 1 | Job Configuration | 検証エラーメッセージを確認 | Missing property を特定 | `website` プロパティが不足 |
| 2 | Home | 「InterfaceMasters」メニューをクリック | - | InterfaceMaster一覧が表示される |
| 3 | InterfaceMasters / 📋 List | エラーに関連するInterfaceMasterを検索 | `CompanySearchInterface` | - |
| 4 | InterfaceMasters / 📋 List | 該当InterfaceMasterの行をクリック | - | 詳細が表示される |
| 5 | InterfaceMasters / 📋 List | 「✏️ Edit」ボタンをクリック | - | 編集フォームが表示される |
| 6 | InterfaceMasters / 📋 List | Output SchemaのJSONを編集 | `website` プロパティを追加 | ✅ Valid JSON Schema 表示 |
| 7 | InterfaceMasters / 📋 List | 「💾 Update InterfaceMaster」ボタンをクリック | - | 更新成功メッセージ |
| 8 | Home | 「Job Configuration」メニューに戻る | - | - |
| 9 | Job Configuration | 同じJobMasterを選択 | `Company Research Workflow` | タスクリストが表示される（保存済み） |
| 10 | Job Configuration | 「🔄 Re-validate」ボタンをクリック | - | 再検証が実行される |
| 11 | Job Configuration | 検証結果を確認 | ✅ Workflow is valid! | エラーが解消されている |
| 12 | Job Configuration | 「🚀 Publish Version」ボタンをクリック | - | バージョンが公開される |

**重要なポイント**:
- ✅ タスク設定は検証失敗時も保存されている（削除されない）
- ✅ InterfaceMasterを修正後、JobMasterを再選択すれば続きから作業可能
- ✅ 検証は何度でも実行可能

---

## シナリオ7: 失敗したタスクの再実行

**目的**: Job実行中に失敗したタスクを特定し、該当タスクから再実行する

**前提条件**:
- Jobが実行され、途中のタスクで失敗している

### 操作手順

| ステップ | 画面/タブ | 操作内容 | 入力例 | 期待される結果 |
|---------|----------|---------|-------|--------------|
| 1 | Home | 「Job Execution」メニューをクリック | - | Job Execution History画面が表示される |
| 2 | Job Execution | 「Status Filter」で `failed` を選択 | - | 失敗したJobのみ表示される |
| 3 | Job Execution | 失敗したJobをクリック | `Tesla Inc Research` | Job詳細が表示される |
| 4 | Job Execution | Job詳細セクションでステータスを確認 | Status: ✗ FAILED | - |
| 5 | Job Execution | 「🔍 Task Details」セクションで失敗タスクを特定 | Task 1: company_analysis - ✗ FAILED | Expanderが自動的に展開される |
| 6 | Job Execution | エラーメッセージを確認 | **Error:** Analysis service timeout after 30s | 原因を特定 |
| 7 | Job Execution | タスク詳細の「🔄 Retry from this Task」ボタンをクリック | - | 再実行が開始される |
| 8 | Job Execution | 自動的にリフレッシュされる | - | Jobステータスが更新される |
| 9 | Job Execution | （任意）「Auto Refresh」をONにして監視 | - | 5秒ごとに自動更新 |
| 10 | Job Execution | タスクの進行状況を確認 | Task 1: 🔄 RUNNING → ✓ SUCCEEDED | - |
| 11 | Job Execution | 後続タスクも実行される | Task 2: ✓ SUCCEEDED | - |
| 12 | Job Execution | Jobステータスを最終確認 | Status: ✓ SUCCEEDED | 成功 |

**再実行の仕組み**:
- 失敗したタスク以降が再実行される
- 前のタスクの出力データは再利用される
- `attempt` カウンターがインクリメントされる

---

## 📊 画面遷移図

```
Home
├─ InterfaceMasters (🔌)
│  ├─ 🆕 Create InterfaceMaster
│  └─ 📋 List InterfaceMasters
│     └─ 🔍 InterfaceMaster Detail (選択時)
│        ├─ 📋 Schemas
│        ├─ 🔗 Usage
│        └─ ⚙️ Config
│
├─ TaskMasters (🔧)
│  ├─ 🆕 Create TaskMaster
│  └─ 📋 List TaskMasters
│     └─ 🔍 TaskMaster Detail (選択時)
│        ├─ 📋 Definition
│        ├─ 🔌 Interfaces
│        └─ ⚙️ Config
│
├─ JobMasters (🗂️)
│  ├─ 🆕 Create Master
│  ├─ 📋 List Masters
│  │  └─ 🔍 Master Detail (選択時)
│  │     ├─ 📋 Definition
│  │     ├─ 📊 Jobs
│  │     └─ ⚙️ Config
│  └─ 📊 From Master (Job作成)
│
├─ Job Configuration (🔧)
│  ├─ 📂 Select JobMaster
│  ├─ 📋 Workflow Tasks (左カラム)
│  ├─ ➕ Add Task to Workflow (左カラム)
│  ├─ 🔍 Workflow Validation (右カラム)
│  └─ 🚀 Publish Workflow Version (右カラム)
│
└─ Job Execution (🚀)
   ├─ 📂 Select JobMaster
   ├─ 📋 Job Execution History
   └─ 📄 Job Details (選択時)
      ├─ 📊 Task Execution Timeline
      └─ 🔍 Task Details
```

---

## 💡 ベストプラクティス

### InterfaceMaster作成時

- ✅ 名前は明確で一貫性のある命名規則を使用（例: `XxxYyyInterface`）
- ✅ テンプレートを活用して時間を節約
- ✅ JSON Schema Draft 7の仕様に準拠
- ✅ `required` プロパティを適切に設定
- ⚠️ 既存のInterfaceMasterを変更する場合、影響を受けるTaskMasterを確認

### TaskMaster作成時

- ✅ 説明文を詳細に記載（後で検索しやすくなる）
- ✅ 適切なリトライ設定（Max Retries, Retry Delay）
- ✅ タイムアウト値は実際のAPI応答時間に基づいて設定
- ✅ InterfaceMasterは必ず設定（検証エラーを防ぐ）

### Job Configuration時

- ✅ タスクの順序は論理的な依存関係に従う
- ✅ 検証を実行してからPublish
- ✅ 検証エラーは放置せず、即座に修正
- 💡 検証が失敗してもタスク設定は保存されているので、後日修正可能

### Job実行監視時

- ✅ Auto Refreshを有効にして自動更新
- ✅ 失敗タスクのエラーメッセージを確認
- ✅ Input/Output Dataを確認してデータの流れを理解
- 💡 再実行は失敗タスク以降のみが対象

---

## 🔧 トラブルシューティング

### よくある問題と解決方法

| 問題 | 原因 | 解決方法 |
|------|------|---------|
| InterfaceMaster作成時に「Invalid JSON」エラー | JSON構文エラー | JSONの構文を確認（カンマ、括弧、クォートの位置） |
| TaskMaster作成時にInterfaceが選択できない | InterfaceMasterが未作成 | 先にInterfaceMasterを作成する |
| Workflow検証で「Missing property」エラー | 前のタスクの出力に必要なプロパティがない | Output InterfaceMasterにプロパティを追加 |
| Job実行時に即座に失敗 | URL不正、認証エラー | TaskMasterのURL、認証情報を確認 |
| タスクが追加できない | 同じTaskMasterが既に追加済み | 1つのJobMasterに同じTaskMasterは1回のみ追加可能 |
| 検証結果が表示されない | ページをリロードした | 検証結果はセッションステート（一時保存）のため、再度「Validate」をクリック |

---

## 📚 関連ドキュメント

- [CommonUI README](../../commonUI/README.md)
- [JobQueue API Documentation](../../jobqueue/README.md)
- [データベーススキーマ](../../jobqueue/docs/database-schema.md)

---

**作成日**: 2025-10-18
**バージョン**: 1.0.0
**対象**: CommonUI v0.2.1
