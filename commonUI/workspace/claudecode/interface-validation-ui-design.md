# Interface Validation UI 統合設計書

## 作成日時
2025-10-17

## 目的
jobqueueで実装したInterface Validation Phase 3の機能をcommonUIに統合し、直感的なUI/UXを提供する。

---

## 1. 現状分析

### 1.1 commonUIの既存構成

```
commonUI/
├── pages/
│   ├── 1_📋_JobQueue.py         # ジョブ管理画面
│   ├── 2_⏰_MyScheduler.py       # スケジューラ管理画面
│   ├── 3_🔐_MyVault.py          # シークレット管理画面
│   └── 4_🗂️_JobMasters.py       # JobMaster管理画面
└── components/
    ├── http_client.py            # HTTPクライアント
    ├── job_master_form.py        # JobMasterフォーム
    ├── notifications.py          # 通知管理
    └── sidebar.py                # サイドバー
```

### 1.2 jobqueueのInterface Validation機能

**APIエンドポイント:**
- `POST /api/v1/interface-masters` - InterfaceMaster作成
- `GET /api/v1/interface-masters` - InterfaceMaster一覧取得
- `GET /api/v1/interface-masters/{id}` - InterfaceMaster詳細取得
- `PUT /api/v1/interface-masters/{id}` - InterfaceMaster更新
- `DELETE /api/v1/interface-masters/{id}` - InterfaceMaster削除
- `GET /api/v1/interface-masters/{id}/tasks` - 関連TaskMaster一覧
- `POST /api/v1/interface-masters/{id}/validate` - スキーマ検証テスト

**主要機能:**
1. InterfaceMaster CRUD操作
2. JSON Schema V7準拠のスキーマ定義
3. TaskMasterとの関連付け（input/output interface）
4. Job作成時の検証（validate_interfaces フラグ）
5. モックデータ生成
6. Worker実行時の自動検証

---

## 2. 設計方針

### 2.1 推奨アプローチ：**新規ページ作成**

**ページ名:** `5_🔗_Interfaces.py`

**理由:**
- ✅ Interface Validationは独立した機能領域
- ✅ JSON Schemaエディタなど専用UIが必要
- ✅ 将来的な機能拡張（検証履歴、統計など）を考慮
- ✅ 既存ページへの影響を最小化
- ✅ TaskMasterとの関連付けUIを独立して管理

### 2.2 却下したアプローチ

#### **オプション2: JobMastersページに統合**
- ❌ JobMasterとInterfaceMasterは異なる概念（JobMasterはJob定義、InterfaceMasterはデータ仕様）
- ❌ ページが複雑化しすぎる
- ❌ タブ構成が深くなりすぎる

#### **オプション3: TaskMasterページ作成**
- ❌ TaskMasterはJobMasterの内部要素（tasks配列）として既に存在
- ❌ TaskMaster単独の管理画面は不要

---

## 3. 画面設計

### 3.1 ページ構成

```
5_🔗_Interfaces.py
├── タブ1: 🆕 Create Interface
│   ├── InterfaceMaster作成フォーム
│   ├── JSON Schemaエディタ（Monaco Editor風）
│   ├── スキーマ検証ツール
│   └── モックデータ生成プレビュー
│
├── タブ2: 📋 Interface List
│   ├── InterfaceMaster一覧表示
│   ├── フィルタ（Active/Inactive, Schema Type）
│   ├── 検索機能
│   └── 詳細表示（行クリック）
│
├── タブ3: 🔗 TaskMaster Associations
│   ├── TaskMaster一覧（Interface関連付け状況）
│   ├── Interface関連付けフォーム
│   ├── 互換性検証結果表示
│   └── 検証エラー詳細
│
└── タブ4: 📊 Validation Insights (Phase 4以降)
    ├── 検証統計（成功/失敗率）
    ├── よくある検証エラー
    └── Interface使用状況
```

### 3.2 画面レイアウト

#### **タブ1: Create Interface**

```
┌─────────────────────────────────────────────────────────────┐
│ 🆕 Create New Interface                                      │
├─────────────────────────────────────────────────────────────┤
│ Interface Name: [                                ]           │
│ Description:    [                                ]           │
│                                                               │
│ Schema Type:    ○ Input Schema  ○ Output Schema             │
│                                                               │
│ ┌─ JSON Schema V7 Editor ────────────────────────────────┐  │
│ │ {                                                       │  │
│ │   "$schema": "http://json-schema.org/draft-07/schema#",│  │
│ │   "type": "object",                                    │  │
│ │   "properties": {                                      │  │
│ │     "result": { "type": "string" },                   │  │
│ │     "count": { "type": "integer" }                    │  │
│ │   },                                                   │  │
│ │   "required": ["result"]                              │  │
│ │ }                                                       │  │
│ │                                                        │  │
│ │ [✓ Validate Schema]  [📝 Format JSON]  [💾 Save]     │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ Validation Result ───────────────────────────────────┐  │
│ │ ✅ Schema is valid (Draft 7)                          │  │
│ │ Properties: 2, Required: 1                            │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ Mock Data Preview ───────────────────────────────────┐  │
│ │ {                                                      │  │
│ │   "result": "sample_string",                          │  │
│ │   "count": 42                                         │  │
│ │ }                                                      │  │
│ │ [🔄 Generate Mock Data]                               │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ Tags: [api, search, response]                                │
│ Is Active: ☑️                                                 │
│                                                               │
│ [🚀 Create Interface]                                        │
└─────────────────────────────────────────────────────────────┘
```

#### **タブ2: Interface List**

```
┌─────────────────────────────────────────────────────────────┐
│ 📋 Interface List                                            │
├─────────────────────────────────────────────────────────────┤
│ Filters: [All Status ▼] [Schema Type: All ▼]  Search: [   ]│
│ [🔄 Refresh]                                                 │
├─────────────────────────────────────────────────────────────┤
│ │ ID     │ Name                │ Type   │ Tasks │ Status │  │
│ ├────────┼────────────────────┼────────┼───────┼────────┤  │
│ │ if_01  │ SearchResult       │ Output │  5    │ Active │  │
│ │ if_02  │ EmailPayload       │ Input  │  3    │ Active │  │
│ │ if_03  │ UserProfile        │ Both   │  8    │ Active │  │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Selected: SearchResult Interface ─────────────────────┐  │
│ │ ID: if_01                                              │  │
│ │ Description: Search API response structure            │  │
│ │                                                         │  │
│ │ [📋 Details] [✏️ Edit] [🗑️ Delete] [🔗 View Tasks]    │  │
│ │                                                         │  │
│ │ ├─ Schema (Output) ─────────────────────────────────┤  │  │
│ │ │ {                                                  │  │  │
│ │ │   "type": "object",                               │  │  │
│ │ │   "properties": {                                 │  │  │
│ │ │     "results": { "type": "array" },              │  │  │
│ │ │     "count": { "type": "integer" }               │  │  │
│ │ │   }                                               │  │  │
│ │ │ }                                                  │  │  │
│ │ └────────────────────────────────────────────────────┘  │  │
│ │                                                         │  │
│ │ ├─ Associated TaskMasters ──────────────────────────┤  │  │
│ │ │ • search_task (Output)                           │  │  │
│ │ │ • transform_task (Input)                         │  │  │
│ │ │ • email_generator_task (Input)                   │  │  │
│ │ └────────────────────────────────────────────────────┘  │  │
│ └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### **タブ3: TaskMaster Associations**

```
┌─────────────────────────────────────────────────────────────┐
│ 🔗 TaskMaster Interface Associations                         │
├─────────────────────────────────────────────────────────────┤
│ Select TaskMaster: [search_task               ▼]            │
│                                                               │
│ ┌─ Current Configuration ───────────────────────────────┐  │
│ │ TaskMaster: search_task                               │  │
│ │ Version: 3                                            │  │
│ │                                                        │  │
│ │ Input Interface:  [None                    ▼] 🔗       │  │
│ │ Output Interface: [SearchResult Interface  ▼] 🔗       │  │
│ │                                                        │  │
│ │ [💾 Update Associations]                              │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ Validation Preview ──────────────────────────────────┐  │
│ │ ✅ Output Schema Valid                                │  │
│ │                                                        │  │
│ │ Next Task: transform_task                             │  │
│ │ Input Schema: EmailPayload Interface                  │  │
│ │                                                        │  │
│ │ ⚠️ Compatibility Warning:                              │  │
│ │ SearchResult.count (integer) cannot map to           │  │
│ │ EmailPayload.subject (string) without transformation │  │
│ │                                                        │  │
│ │ Suggestion: Add intermediate transformation task      │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ All TaskMasters ─────────────────────────────────────┐  │
│ │ │ Task          │ Input IF  │ Output IF  │ Compat │  │  │
│ │ ├───────────────┼───────────┼────────────┼────────┤  │  │
│ │ │ search_task   │ None      │ SearchRes  │   ✅   │  │  │
│ │ │ transform_task│ SearchRes │ EmailPay   │   ⚠️   │  │  │
│ │ │ send_email    │ EmailPay  │ None       │   ✅   │  │  │
│ └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 新規コンポーネント設計

### 4.1 `components/interface_form.py`

**責務:** InterfaceMaster作成/編集フォームのレンダリング

**主要機能:**
- JSON Schemaエディタ（`st.text_area` with syntax highlighting）
- スキーマ検証（Draft 7準拠）
- モックデータ生成プレビュー
- バリデーションエラー表示

**インターフェース:**
```python
class InterfaceForm:
    @staticmethod
    def render_interface_form(mode: str = "create", initial_data: dict | None = None) -> dict | None:
        """
        Render interface creation/edit form.

        Args:
            mode: "create" or "edit"
            initial_data: Initial form data for edit mode

        Returns:
            Form data dict if submitted, None otherwise
        """
```

### 4.2 `components/schema_editor.py`

**責務:** JSON Schemaエディタコンポーネント

**主要機能:**
- JSON syntax highlighting（`st.code` + `st.text_area`）
- リアルタイムバリデーション
- フォーマット整形（`json.dumps(indent=2)`）
- スキーマテンプレート提供

**インターフェース:**
```python
class SchemaEditor:
    @staticmethod
    def render_schema_editor(
        label: str,
        initial_schema: dict | None = None,
        height: int = 300
    ) -> tuple[dict | None, bool]:
        """
        Render JSON Schema editor with validation.

        Returns:
            (schema_dict, is_valid)
        """
```

### 4.3 `components/interface_validator.py`

**責務:** Interface互換性検証UI

**主要機能:**
- TaskMaster間のInterface互換性チェック
- 検証エラーの視覚化
- 修正提案の表示

**インターフェース:**
```python
class InterfaceValidator:
    @staticmethod
    def render_compatibility_check(
        task_masters: list[dict],
        interfaces: dict[str, dict]
    ) -> None:
        """
        Render interface compatibility validation UI.

        Shows compatibility matrix and detailed error messages.
        """
```

---

## 5. 実装計画

### Phase 1: 基本機能（MVP）

**目標:** InterfaceMaster CRUD操作を提供

**タスク:**
1. ✅ `5_🔗_Interfaces.py` ページ作成
2. ✅ `components/interface_form.py` 実装
3. ✅ InterfaceMaster一覧表示
4. ✅ InterfaceMaster作成フォーム
5. ✅ InterfaceMaster詳細表示
6. ✅ InterfaceMaster編集・削除機能

**完了基準:**
- InterfaceMasterのCRUD操作が可能
- 基本的なJSON Schemaエディタが動作
- API連携が正常に機能

### Phase 2: 高度なエディタ機能

**目標:** JSON Schemaエディタの使いやすさ向上

**タスク:**
1. ✅ `components/schema_editor.py` 実装
2. ✅ リアルタイムバリデーション
3. ✅ スキーマテンプレート提供
4. ✅ モックデータ生成プレビュー
5. ✅ スキーマフォーマット整形

**完了基準:**
- JSON編集がスムーズ
- バリデーションエラーがわかりやすい
- テンプレートから簡単に開始できる

### Phase 3: TaskMaster統合

**目標:** TaskMasterとの関連付けUI

**タスク:**
1. ✅ TaskMaster一覧取得API統合
2. ✅ Interface関連付けフォーム実装
3. ✅ `components/interface_validator.py` 実装
4. ✅ 互換性検証UI実装
5. ✅ 検証エラー詳細表示

**完了基準:**
- TaskMasterにInterfaceを関連付け可能
- 互換性エラーが視覚的にわかる
- 修正提案が表示される

### Phase 4: 分析・インサイト（将来実装）

**目標:** Interface使用状況の可視化

**タスク:**
1. ⏳ 検証統計ダッシュボード
2. ⏳ よくある検証エラー分析
3. ⏳ Interface使用頻度グラフ
4. ⏳ パフォーマンスメトリクス表示

**完了基準:**
- Interface使用状況が可視化される
- よくあるエラーパターンがわかる
- パフォーマンス問題を早期発見できる

---

## 6. 技術的考慮事項

### 6.1 JSON Schemaエディタの実装方法

**オプション1: st.text_area（推奨）**
```python
schema_json = st.text_area(
    "JSON Schema",
    value=json.dumps(initial_schema, indent=2),
    height=300,
    help="Edit JSON Schema (Draft 7)"
)
```
- ✅ Streamlitネイティブ
- ✅ 簡単実装
- ❌ Syntax highlighting なし

**オプション2: streamlit-ace（高度）**
```python
from streamlit_ace import st_ace

schema_json = st_ace(
    value=json.dumps(initial_schema, indent=2),
    language="json",
    theme="monokai",
    height=300
)
```
- ✅ Syntax highlighting
- ✅ 行番号表示
- ❌ 外部依存関係

**推奨:** Phase 1では `st.text_area`、Phase 2で `streamlit-ace` 導入

### 6.2 スキーマ検証ライブラリ

**使用ライブラリ:** `jsonschema`（既にjobqueueで使用中）

```python
from jsonschema import Draft7Validator, ValidationError

def validate_schema(schema: dict, data: dict) -> tuple[bool, list[str]]:
    """Validate data against JSON Schema Draft 7."""
    validator = Draft7Validator(schema)
    errors = []

    for error in validator.iter_errors(data):
        errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}")

    return len(errors) == 0, errors
```

### 6.3 モックデータ生成

**使用ライブラリ:** `tests/utils/interface_mock.py`（既存実装を再利用）

```python
from tests.utils.interface_mock import InterfaceMockGenerator

mock_data = InterfaceMockGenerator.generate_mock_data(schema)
st.json(mock_data)
```

---

## 7. ユーザーフロー

### 7.1 新しいInterfaceを作成してTaskMasterに関連付ける

```
1. ユーザーが「5_🔗_Interfaces」ページにアクセス
   ↓
2. 「Create Interface」タブを選択
   ↓
3. Interface名、説明を入力
   ↓
4. JSON Schemaをエディタで編集
   ↓
5. 「Validate Schema」ボタンでスキーマ検証
   ↓
6. 検証成功 → 「Generate Mock Data」でプレビュー確認
   ↓
7. 「Create Interface」ボタンでInterfaceMaster作成
   ↓
8. 「TaskMaster Associations」タブに移動
   ↓
9. TaskMasterを選択し、作成したInterfaceを関連付け
   ↓
10. 「Update Associations」で保存
    ↓
11. 互換性チェック結果が表示される
```

### 7.2 既存ジョブの検証エラーをトラブルシューティング

```
1. JobQueueページでジョブ実行失敗を確認
   ↓
2. エラーメッセージ「Task 1 output validation failed」
   ↓
3. 「5_🔗_Interfaces」ページに移動
   ↓
4. 「TaskMaster Associations」タブで該当TaskMasterを選択
   ↓
5. 互換性検証結果を確認
   ↓
6. エラー詳細：「Property 'subject' is required but missing」
   ↓
7. 修正提案：「Add transformation task to map 'count' to 'subject'」
   ↓
8. JobMastersページで中間変換TaskMasterを追加
   ↓
9. 再度検証 → 互換性 ✅ に変更
   ↓
10. ジョブ再実行 → 成功
```

---

## 8. テスト計画

### 8.1 単体テスト

**対象:** `components/interface_form.py`, `components/schema_editor.py`, `components/interface_validator.py`

**テストケース:**
- JSON Schema検証ロジック（有効/無効なスキーマ）
- モックデータ生成ロジック
- 互換性チェックロジック

### 8.2 統合テスト

**対象:** `5_🔗_Interfaces.py` ページ全体

**テストケース:**
- InterfaceMaster作成フロー
- InterfaceMaster更新フロー
- TaskMaster関連付けフロー
- 検証エラー表示フロー

### 8.3 E2Eテスト

**シナリオ:**
1. InterfaceMaster作成 → TaskMaster関連付け → Job作成 → 検証成功
2. InterfaceMaster作成 → TaskMaster関連付け → Job作成 → 検証失敗 → エラー確認

---

## 9. ドキュメント計画

### 9.1 ユーザーガイド追加

**ファイル:** `commonUI/docs/interface-validation-ui-guide.md`

**内容:**
- Interface Validation UIの使い方
- JSON Schemaエディタの使い方
- TaskMaster関連付け方法
- トラブルシューティング手順

### 9.2 README.md更新

**追加内容:**
- Interface Validation機能の説明
- 新しいページ「5_🔗_Interfaces」の紹介
- スクリーンショット

---

## 10. マイルストーン

| Phase | タスク | 期限 | 担当 | ステータス |
|-------|--------|------|------|----------|
| Phase 1 | 基本機能（MVP） | - | Claude Code | 🔲 未着手 |
| Phase 2 | 高度なエディタ機能 | - | Claude Code | 🔲 未着手 |
| Phase 3 | TaskMaster統合 | - | Claude Code | 🔲 未着手 |
| Phase 4 | 分析・インサイト | - | - | ⏳ 将来実装 |

---

## 11. リスクと対策

### リスク1: JSON Schemaエディタの使いにくさ

**対策:**
- Phase 2で `streamlit-ace` を導入してSyntax highlightingを実装
- スキーマテンプレート機能で初期学習コストを削減
- インラインバリデーションでリアルタイムフィードバック

### リスク2: 複雑なスキーマの視覚的理解が困難

**対策:**
- モックデータプレビュー機能でスキーマの具体例を表示
- スキーマ構造の可視化（ツリービュー）を検討
- よくあるスキーマパターンのサンプル提供

### リスク3: TaskMaster互換性チェックの複雑さ

**対策:**
- 段階的なUI実装（まずは簡易版、徐々に高度化）
- 明確なエラーメッセージと修正提案を提供
- チュートリアルと実例の充実

---

## 12. 次のアクション

**ユーザー承認後の作業:**

1. **設計レビュー:** この設計書をレビューし、承認を得る
2. **Phase 1実装開始:**
   - `5_🔗_Interfaces.py` ページ作成
   - `components/interface_form.py` 実装
   - 基本的なCRUD機能実装
3. **テスト実装:**
   - 単体テスト作成
   - 統合テスト作成
4. **ドキュメント作成:**
   - ユーザーガイド作成
   - README.md更新

---

## 付録A: APIエンドポイント一覧

### InterfaceMaster API

| Method | Endpoint | 説明 |
|--------|----------|------|
| POST | `/api/v1/interface-masters` | InterfaceMaster作成 |
| GET | `/api/v1/interface-masters` | InterfaceMaster一覧取得 |
| GET | `/api/v1/interface-masters/{id}` | InterfaceMaster詳細取得 |
| PUT | `/api/v1/interface-masters/{id}` | InterfaceMaster更新 |
| DELETE | `/api/v1/interface-masters/{id}` | InterfaceMaster削除 |
| GET | `/api/v1/interface-masters/{id}/tasks` | 関連TaskMaster一覧 |
| POST | `/api/v1/interface-masters/{id}/validate` | スキーマ検証テスト |

### TaskMaster API（Interface関連）

| Method | Endpoint | 説明 |
|--------|----------|------|
| GET | `/api/v1/task-masters` | TaskMaster一覧取得 |
| GET | `/api/v1/task-masters/{id}` | TaskMaster詳細取得 |
| PUT | `/api/v1/task-masters/{id}` | TaskMaster更新（input/output_interface_id含む） |

---

**作成者:** Claude Code
**日時:** 2025-10-17
**バージョン:** 1.0
