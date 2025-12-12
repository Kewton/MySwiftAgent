# 要件定義書: commonUIのJob Configurationでのtaskインタフェース確認効率化

> Issue: [#277](https://github.com/kewton/MySwiftAgent/issues/277)
> 作成日: 2025-12-13
> ステータス: 要件定義完了

---

## 現状調査サマリ

### 対象プロジェクト
- **プロジェクト名**: commonUI
- **技術スタック**: Streamlit (Python)
- **関連モジュール**:
  - `commonUI/pages/7_🔧_Job_Configuration.py` - メイン対象
  - `commonUI/pages/8_🔧_TaskMasters.py` - TaskMaster管理画面
  - `commonUI/pages/9_🔌_InterfaceMasters.py` - InterfaceMaster管理画面

### 既存の類似機能
| 機能 | 場所 | 概要 |
|------|------|------|
| TaskMaster詳細表示 | `8_🔧_TaskMasters.py:133-143` | `load_task_master_detail()` でAPIから詳細取得 |
| InterfaceMaster詳細表示 | `9_🔌_InterfaceMasters.py:158-168` | `load_interface_detail()` でAPIから詳細取得 |
| Validation Panel | `7_🔧_Job_Configuration.py:387-459` | Task Interface Chainを表示（ID短縮表示のみ） |

### 使用されている設計パターン
- **HTTPClient**: `components/http_client.py` - JobQueue API通信の共通クライアント
- **Session State管理**: Streamlitのセッション状態でデータをキャッシュ
- **NotificationManager**: 操作結果の通知表示

### 参照したドキュメント
- `commonUI/README.md` - commonUIの全体構成
- `jobqueue/app/schemas/task_master.py` - TaskMasterスキーマ（`input_interface_id`, `output_interface_id`）
- `jobqueue/app/schemas/interface_master.py` - InterfaceMasterスキーマ（`input_schema`, `output_schema`）

### 制約事項
1. **API制約**: TaskMaster詳細取得とInterfaceMaster詳細取得は別APIエンドポイント
2. **UI制約**: Streamlitの再描画特性（st.rerun()による全体更新）
3. **パフォーマンス**: 複数API呼び出しによるレイテンシ考慮

---

## ユーザーストーリー

### 主要ストーリー
```
As a commonUIユーザー（開発者/運用担当者）
I want to Job ConfigurationページでTask選択時にそのTaskの入出力インタフェースを確認したい
So that 別画面に移動せずにワークフロー構築時のインタフェース整合性を効率的に確認できる
```

### サブストーリー
```
As a commonUIユーザー
I want to ワークフローのタスク一覧でインタフェース情報を一目で確認したい
So that タスク間のデータフロー（入出力の接続）を把握できる

As a commonUIユーザー
I want to インタフェースのJSON Schemaプロパティを展開表示したい
So that 具体的にどのようなデータ項目が入出力されるか理解できる
```

---

## 受入条件（Acceptance Criteria）

### AC1: タスク選択時のインタフェース情報表示
- **Given**: Job Configurationページで「Add Task to Workflow」パネルを表示している
- **When**: ドロップダウンからTaskMasterを選択する
- **Then**:
  - 選択したTaskの `input_interface_id` に紐づくInterfaceMasterの名前が表示される
  - 選択したTaskの `output_interface_id` に紐づくInterfaceMasterの名前が表示される
  - インタフェース未設定の場合は「未設定」と表示される

### AC2: インタフェースJSON Schemaの展開表示
- **Given**: TaskMasterのインタフェース情報が表示されている
- **When**: 「詳細を表示」ボタン/expanderをクリックする
- **Then**:
  - `input_schema` のプロパティ一覧（フィールド名、型、必須/任意）が表示される
  - `output_schema` のプロパティ一覧が表示される
  - JSON Schema全体をコピー可能なコードブロックで表示される

### AC3: ワークフロータスク一覧でのインタフェース表示
- **Given**: JobMasterを選択してワークフロータスク一覧が表示されている
- **When**: タスクリストを確認する
- **Then**:
  - 各タスク行に入力インタフェース名と出力インタフェース名が列として表示される
  - 表示が長すぎる場合はツールチップで全文表示される

### AC4: パフォーマンス要件
- **Given**: Job Configurationページを操作する
- **When**: タスク選択やインタフェース詳細表示を行う
- **Then**:
  - インタフェース情報の取得・表示は2秒以内に完了する
  - API呼び出しはキャッシュされ、同一セッション内で重複呼び出しを避ける

---

## 機能要件

### Must Have（必須）

| ID | 機能 | 詳細 |
|----|------|------|
| F1 | タスク選択時インタフェース表示 | `render_add_task_panel()` でTask選択時に入出力インタフェース名を表示 |
| F2 | インタフェース詳細取得API呼び出し | TaskMasterの `input_interface_id` / `output_interface_id` からInterfaceMaster詳細を取得 |
| F3 | ワークフロータスク一覧へのインタフェース列追加 | `render_workflow_tasks()` のDataFrameに入出力インタフェース列を追加 |

### Nice to Have（推奨）

| ID | 機能 | 詳細 |
|----|------|------|
| F4 | JSON Schemaプロパティ展開表示 | st.expanderでJSON Schemaのプロパティ一覧を表示 |
| F5 | インタフェース情報のキャッシュ | session_stateでInterfaceMaster詳細をキャッシュ |
| F6 | インタフェース整合性プレビュー | 追加前にインタフェース整合性（前タスクの出力 = 新タスクの入力）を表示 |

### Future Enhancement（将来拡張）

| ID | 機能 |
|----|------|
| F7 | ビジュアルワークフローエディタ（ノード接続形式） |
| F8 | インタフェース自動マッピング提案 |
| F9 | インタフェース比較ツール |

---

## 非機能要件

### パフォーマンス要件
- API呼び出しレイテンシ: インタフェース詳細取得 < 500ms
- UI応答時間: タスク選択からインタフェース表示まで < 2秒
- キャッシュ有効期間: セッション中は保持（ページリロードまで）

### ユーザビリティ要件
- インタフェース情報は折りたたみ可能（デフォルトは展開）
- 長いインタフェース名は省略表示 + ツールチップ
- インタフェース未設定時は明確に「未設定」と表示

### セキュリティ要件
- 追加のセキュリティ要件なし（既存のJobQueue API認証を使用）

### 互換性要件
- 既存のJob Configuration機能に影響を与えない（追加機能のみ）
- JobQueue API v1との互換性維持

---

## 技術的制約

### 使用する技術スタック
| 領域 | 技術 |
|------|------|
| フレームワーク | Streamlit |
| 言語 | Python 3.11+ |
| 通信 | HTTPClient (既存コンポーネント) |
| バックエンドAPI | JobQueue API (`/api/v1/task-masters`, `/api/v1/interface-masters`) |

### 既存システムとの連携
```
commonUI (Job Configuration)
    │
    ├── GET /api/v1/task-masters/{id}  → TaskMaster詳細取得
    │       ├── input_interface_id
    │       └── output_interface_id
    │
    └── GET /api/v1/interface-masters/{id}  → InterfaceMaster詳細取得
            ├── name
            ├── description
            ├── input_schema (JSON Schema)
            └── output_schema (JSON Schema)
```

### APIレスポンス形式

**TaskMaster詳細** (`GET /api/v1/task-masters/{id}`):
```json
{
  "id": "tm_XXXXX",
  "name": "company_search",
  "description": "Search for company information",
  "input_interface_id": "if_XXXXX",
  "output_interface_id": "if_YYYYY",
  ...
}
```

**InterfaceMaster詳細** (`GET /api/v1/interface-masters/{id}`):
```json
{
  "id": "if_XXXXX",
  "name": "CompanySearchInput",
  "description": "Input for company search",
  "input_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "company_name": {"type": "string"},
      "country": {"type": "string"}
    },
    "required": ["company_name"]
  },
  "output_schema": null
}
```

---

## リスクと対策

### 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|---------|------|
| API呼び出し増加によるレイテンシ | 中 | 中 | インタフェース情報をsession_stateでキャッシュ |
| InterfaceMasterが削除済みの場合 | 低 | 低 | エラーハンドリングで「取得不可」表示 |
| JSON Schemaの複雑なネスト構造 | 低 | 中 | 第1階層のプロパティのみ表示、詳細はJSONビューで対応 |

### ビジネスリスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| UI変更によるユーザー混乱 | 低 | 既存UIを維持し、情報追加のみ |
| 開発工数超過 | 低 | Must Have機能を優先し、Nice to Haveは段階的実装 |

---

## 影響範囲

### 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `commonUI/pages/7_🔧_Job_Configuration.py` | インタフェース表示機能追加 |
| `commonUI/tests/unit/test_job_configuration.py` | 新規テスト追加 |

### テスト追加

| テスト種別 | 対象 | 件数（目安） |
|-----------|------|------------|
| 単体テスト | インタフェース取得・表示ロジック | 5件 |
| 結合テスト | API連携（モック） | 3件 |
| 手動テスト | UI動作確認 | 3件 |

---

## 参照ドキュメント

- [commonUI README](../../../commonUI/README.md)
- [JobQueue API - TaskMaster Schema](../../../jobqueue/app/schemas/task_master.py)
- [JobQueue API - InterfaceMaster Schema](../../../jobqueue/app/schemas/interface_master.py)
- [Job Configuration Page](../../../commonUI/pages/7_🔧_Job_Configuration.py)

---

## 推奨アプローチ

1. **Phase 1**: タスク選択時のインタフェース名表示（F1, F2）
2. **Phase 2**: ワークフロータスク一覧へのインタフェース列追加（F3）
3. **Phase 3**: JSON Schemaプロパティ展開表示（F4, F5）
4. **Phase 4**: インタフェース整合性プレビュー（F6）
