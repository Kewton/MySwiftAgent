# Phase 10: Task 3 の output ノード誤りの原因調査レポート

**作成日**: 2025-10-28
**ブランチ**: feature/issue/110
**担当**: Claude Code

---

## 🔍 調査目的

Task 3 のワークフロー (`audio_file_generation_and_drive_upload.yml`) の output ノードが、存在しないフィールド名を参照している根本原因を特定する。

---

## 📊 問題の詳細

### ワークフローの output ノード（誤り）

**ファイル**: `audio_file_generation_and_drive_upload.yml` (lines 57-66)

```yaml
output:
  agent: copyAgent
  inputs:
    result:
      success: :call_tts_drive_api.success           # ← 存在しない
      file_name: :call_tts_drive_api.file_name       # ← OK
      public_url: :call_tts_drive_api.public_url     # ← 存在しない (実際は web_view_link)
      drive_file_id: :call_tts_drive_api.drive_file_id  # ← 存在しない (実際は file_id)
      error_message: :call_tts_drive_api.error_message  # ← 存在しない
  isResult: true
```

### 実際の API レスポンス

**API**: `/v1/utility/text_to_speech_drive`

**実際のレスポンス**:
```json
{
  "file_id": "1C9-cyLGi4QqxzUBjF8qSxR_W2VzOb0Py",
  "file_name": "1adc235c-3447-444c-8386-f236b6455251.mp3",
  "web_view_link": "https://drive.google.com/file/d/1C9-cyLGi4QqxzUBjF8qSxR_W2VzOb0Py/view?usp=drivesdk",
  "web_content_link": "https://drive.google.com/uc?id=1C9-cyLGi4QqxzUBjF8qSxR_W2VzOb0Py&export=download",
  "folder_path": "ルート",
  "file_size_mb": 2.97
}
```

### フィールド名の不一致

| ワークフロー参照 | 実際のAPIフィールド | 存在 |
|---------------|------------------|------|
| `success` | (存在しない) | ❌ |
| `file_name` | `file_name` | ✅ |
| `public_url` | `web_view_link` | ❌ |
| `drive_file_id` | `file_id` | ❌ |
| `error_message` | (存在しない) | ❌ |
| (参照なし) | `web_content_link` | - |
| (参照なし) | `folder_path` | - |
| (参照なし) | `file_size_mb` | - |

---

## 🔎 根本原因の特定

### 調査手順

1. ✅ **Task 3 の実際の実行結果を確認** → API は正しいレスポンスを返している
2. ✅ **expert_agent_capabilities.yaml を確認** → API のレスポンス形式が記載されていない
3. ✅ **API 実装を確認** → `TTSDriveResponse` スキーマで正しく定義されている
4. ✅ **workflowGeneratorAgents の生成ロジックを推測** → レスポンス形式不明のため推測で生成

### 根本原因1: expert_agent_capabilities.yaml にレスポンス形式が記載されていない

**ファイル**: `aiagent/langgraph/jobTaskGeneratorAgents/utils/config/expert_agent_capabilities.yaml` (lines 88-94)

**現在の定義**:
```yaml
- name: "Text-to-Speech + Google Drive"
  endpoint: "/v1/utility/text_to_speech_drive"
  description: "音声合成 + Google Driveアップロード"
  use_cases:
    - "テキストを音声ファイル（MP3）に変換"
    - "自動でGoogle Driveにアップロード"
    - "公開リンクを返却"
  # ← output_schema が存在しない！
```

**問題点**:
- API のエンドポイントと説明のみ記載
- **レスポンス形式（output schema）が記載されていない**
- workflowGeneratorAgents が参照すべきフィールド名が不明

### 根本原因2: API 実装の正しいレスポンス形式

**ファイル**: `app/schemas/ttsSchemas.py` (lines 103-133)

**TTSDriveResponse スキーマ**:
```python
class TTSDriveResponse(BaseModel):
    """TTS + Drive Upload API レスポンス

    Google Driveにアップロードされた音声ファイル情報
    """

    file_id: str = Field(
        ...,
        description="Google Drive ファイルID",
    )
    file_name: str = Field(
        ...,
        description="アップロードされたファイル名",
    )
    web_view_link: str = Field(
        ...,
        description="ファイル閲覧用URL",
    )
    web_content_link: Optional[str] = Field(
        None,
        description="ファイルダウンロード用URL",
    )
    folder_path: str = Field(
        ...,
        description="アップロード先フォルダパス",
    )
    file_size_mb: float = Field(
        ...,
        description="ファイルサイズ（MB）",
    )
```

**エンドポイントドキュメント**: `app/api/v1/tts_endpoints.py` (lines 214-223)

```python
"""
レスポンス例:
```json
{
  "file_id": "1a2b3c4d5e",
  "file_name": "greeting.mp3",
  "web_view_link": "https://drive.google.com/file/d/1a2b3c4d5e/view",
  "web_content_link": "https://drive.google.com/uc?id=1a2b3c4d5e",
  "folder_path": "podcasts/2025",
  "file_size_mb": 0.15
}
```
"""
```

### 根本原因3: workflowGeneratorAgents が推測でフィールド名を生成

**問題の流れ**:
1. workflowGeneratorAgents がワークフローを生成
2. `expert_agent_capabilities.yaml` を参照して API 情報を取得
3. **レスポンス形式が記載されていないため、推測でフィールド名を決定**
4. 一般的な命名規則に基づき `public_url`, `drive_file_id` を使用
5. 実際の API は `web_view_link`, `file_id` を返す
6. **フィールド名の不一致により、output ノードが正しい値を返さない**

---

## 🎯 根本原因まとめ

### 主要な原因

**expert_agent_capabilities.yaml に API のレスポンス形式（output schema）が記載されていない**

- 記載されているのは: `endpoint`, `description`, `use_cases` のみ
- 記載されていないのは: **レスポンスフィールド名、型、説明**

### 影響範囲

**すべての Utility API で同様の問題が発生する可能性**

expert_agent_capabilities.yaml の他の API 定義も確認:
```yaml
utility_apis:
  - name: "Gmail検索"
    endpoint: "/v1/utility/gmail/search"
    description: "Gmail検索（高速・AIフレンドリー）"
    use_cases: [...]
    # ← output_schema なし

  - name: "Gmail送信"
    endpoint: "/v1/utility/gmail/send"
    description: "メール送信（高速・Direct API）"
    use_cases: [...]
    # ← output_schema なし

  # ... 他のAPIも同様
```

**影響**:
- workflowGeneratorAgents が生成するすべてのワークフローで、API レスポンスフィールドの参照が推測になる
- 実際の API 実装とフィールド名が一致しない可能性が高い

---

## 💡 対策案

### 対策案1: Task 3 のワークフロー output ノード修正【即座】

**目的**: 現在のワークフローを修正して、正しいフィールド名を参照

**実施内容**: `audio_file_generation_and_drive_upload.yml` を手動修正

**変更前**:
```yaml
output:
  agent: copyAgent
  inputs:
    result:
      success: :call_tts_drive_api.success
      file_name: :call_tts_drive_api.file_name
      public_url: :call_tts_drive_api.public_url
      drive_file_id: :call_tts_drive_api.drive_file_id
      error_message: :call_tts_drive_api.error_message
  isResult: true
```

**変更後**:
```yaml
output:
  agent: copyAgent
  inputs:
    result:
      success: true  # ← 固定値（API呼び出し成功時は常にtrue）
      file_name: :call_tts_drive_api.file_name
      public_url: :call_tts_drive_api.web_view_link  # ← 修正
      drive_file_id: :call_tts_drive_api.file_id     # ← 修正
      file_size_mb: :call_tts_drive_api.file_size_mb  # ← 追加
      error_message: ""  # ← 固定値（エラー時はGraphAIが例外を投げる）
  isResult: true
```

**メリット**:
- ✅ 即座に問題解決
- ✅ Task 3 のテストが正常に完了する

**デメリット**:
- ⚠️ 手動修正のため、再生成時に同じ問題が発生
- ⚠️ 根本原因は解決しない

**想定工数**: 10分

---

### 対策案2: expert_agent_capabilities.yaml にレスポンス形式を追加【根本解決】

**目的**: API のレスポンス形式を明示し、workflowGeneratorAgents が正確なフィールド名を使用できるようにする

**実施内容**: `expert_agent_capabilities.yaml` に `output_schema` を追加

**追加内容**:
```yaml
- name: "Text-to-Speech + Google Drive"
  endpoint: "/v1/utility/text_to_speech_drive"
  description: "音声合成 + Google Driveアップロード"
  use_cases:
    - "テキストを音声ファイル（MP3）に変換"
    - "自動でGoogle Driveにアップロード"
    - "公開リンクを返却"
  # NEW: output_schema を追加
  output_schema:
    file_id:
      type: "string"
      description: "Google Drive ファイルID"
      required: true
    file_name:
      type: "string"
      description: "アップロードされたファイル名"
      required: true
    web_view_link:
      type: "string"
      description: "ファイル閲覧用URL（公開リンク）"
      required: true
    web_content_link:
      type: "string"
      description: "ファイルダウンロード用URL"
      required: false
    folder_path:
      type: "string"
      description: "アップロード先フォルダパス"
      required: true
    file_size_mb:
      type: "number"
      description: "ファイルサイズ（MB）"
      required: true
```

**workflowGeneratorAgents の修正**:
- プロンプトに output_schema を含める
- LLM が正確なフィールド名を使用してワークフローを生成

**メリット**:
- ✅ 根本原因を解決
- ✅ 将来的に再生成しても正しいワークフローが生成される
- ✅ 他の API にも適用可能

**デメリット**:
- ⚠️ すべての Utility API に output_schema を追加する必要がある（9 API）
- ⚠️ workflowGeneratorAgents のプロンプト修正が必要

**想定工数**: 2-3時間

---

### 対策案3: API 仕様からの自動スキーマ抽出【長期的】

**目的**: Pydantic スキーマから自動的に output_schema を生成し、手動メンテナンスを不要にする

**実施内容**:
1. expertAgent の API エンドポイントから Pydantic スキーマを読み取る
2. スキーマを YAML 形式に変換
3. expert_agent_capabilities.yaml を自動生成

**実装案**:
```python
# scripts/generate_api_capabilities.py
from app.schemas.ttsSchemas import TTSDriveResponse
from pydantic import BaseModel
import yaml

def extract_schema(model: type[BaseModel]) -> dict:
    """Pydantic モデルから output_schema を抽出"""
    schema = {}
    for field_name, field_info in model.model_fields.items():
        schema[field_name] = {
            "type": field_info.annotation.__name__,
            "description": field_info.description,
            "required": field_info.is_required(),
        }
    return schema

# TTSDriveResponse から自動抽出
output_schema = extract_schema(TTSDriveResponse)
print(yaml.dump(output_schema, allow_unicode=True))
```

**メリット**:
- ✅ API 実装と YAML 定義の一貫性を保証
- ✅ Pydantic スキーマ変更時に自動更新
- ✅ 手動メンテナンス不要

**デメリット**:
- ⚠️ 実装コストが高い
- ⚠️ CI/CD パイプラインへの組み込みが必要

**想定工数**: 1日

---

## 📋 推奨対応フロー

### Phase 1: 即座の対応（対策案1）

**目的**: 現在のワークフローを修正して動作確認

**手順**:
1. ✅ `audio_file_generation_and_drive_upload.yml` を手動修正
2. ✅ Task 3 を再テスト
3. ✅ output ノードが正しい値を返すことを確認

**期待される成果**:
- Task 3 の output ノードが正しい値を返す
- 統合テストが正常に完了する

**想定工数**: 30分

---

### Phase 2: 根本解決（対策案2）

**目的**: expert_agent_capabilities.yaml に output_schema を追加

**手順**:
1. ✅ `/v1/utility/text_to_speech_drive` API の output_schema を追加
2. ✅ workflowGeneratorAgents のプロンプトを修正
3. ✅ Task 3 のワークフローを再生成
4. ✅ 自動生成されたワークフローが正しいフィールド名を使用することを確認

**期待される成果**:
- workflowGeneratorAgents が正確なフィールド名を使用したワークフローを生成
- 将来的に再生成しても同じ問題が発生しない

**想定工数**: 2-3時間

---

### Phase 3: 長期的改善（対策案3）【オプション】

**目的**: API 仕様からの自動スキーマ抽出

**手順**:
1. ✅ スキーマ抽出スクリプトの実装
2. ✅ CI/CD パイプラインへの組み込み
3. ✅ すべての Utility API に適用

**期待される成果**:
- API 実装と YAML 定義の一貫性保証
- 手動メンテナンス不要

**想定工数**: 1日

---

## ✅ 制約条件チェック

### コード品質原則
- [x] **DRY原則**: API 仕様の重複を排除（Pydantic スキーマとYAML定義）

### アーキテクチャガイドライン
- [x] **単一情報源の原則**: Pydantic スキーマを唯一の情報源とする

### 品質担保方針
- [x] **テスト**: ワークフロー修正後に統合テスト実施

---

## 🎯 次のアクション

**ユーザーに確認すべき事項**:

1. **優先する対策**: 対策案1（即座の修正）、対策案2（根本解決）、対策案3（長期的改善）のどれを実施するか？
2. **他の API への影響**: 他の Utility API（Gmail送信、Google Drive Upload等）も同様の問題がある可能性。すべて修正するか？
3. **workflowGeneratorAgents の修正**: プロンプトに output_schema を含めるか？

**推奨対応**:
- まず、**対策案1**（Task 3 のワークフロー修正）を実施し、動作確認
- 動作確認後、**対策案2**（expert_agent_capabilities.yaml に output_schema 追加）で根本解決
- 余裕があれば、**対策案3**（自動スキーマ抽出）で長期的改善

---

## 📝 結論

**根本原因**: expert_agent_capabilities.yaml に API のレスポンス形式（output schema）が記載されていないため、workflowGeneratorAgents が推測で誤ったフィールド名を使用した。

**immediate fix**: Task 3 のワークフロー output ノードを手動修正（`public_url` → `web_view_link`, `drive_file_id` → `file_id`）

**root cause fix**: expert_agent_capabilities.yaml に output_schema を追加し、workflowGeneratorAgents が正確なフィールド名を使用できるようにする

**long-term fix**: Pydantic スキーマから自動的に output_schema を抽出し、手動メンテナンスを不要にする

---

**作業完了**: 2025-10-28
