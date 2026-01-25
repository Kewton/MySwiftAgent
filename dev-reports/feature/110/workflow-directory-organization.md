# Workflow Directory Organization Implementation

**作成日**: 2025-10-28
**ブランチ**: feature/issue/110
**担当**: Claude Code

---

## 📋 概要

LLMワークフローYMLの整理・管理を改善するため、以下の2つの機能を実装しました：

1. **graphAiServer**: Workflow Registration APIにdirectoryパラメータを追加
2. **workflowGeneratorAgents**: 生成したワークフローを `/taskmaster/{task_master_id}/` ディレクトリに保存

---

## 🎯 実装内容

### 1. graphAiServer: Directory Parameter for Workflow Registration

#### 実装場所
- `graphAiServer/src/types/workflow.ts`
- `graphAiServer/src/app.ts`

#### 変更内容

**型定義の追加**:
```typescript
export interface WorkflowRegisterRequest {
  workflow_name: string;
  yaml_content: string;
  overwrite?: boolean;
  directory?: string;  // 🆕 追加
}
```

**エンドポイント実装**:
```typescript
// Step 2: Construct target directory path
const target_dir = directory
  ? path.join(WORKFLOW_DIR, directory)
  : WORKFLOW_DIR;

// Step 3: Create directory if not exists
if (!fs.existsSync(target_dir)) {
  fs.mkdirSync(target_dir, { recursive: true });
}
```

#### 使用例

```bash
# ルートディレクトリに保存
curl -X POST http://localhost:8000/api/v1/workflows/register \
  -d '{"workflow_name": "test", "yaml_content": "..."}'
# → config/graphai/test.yml

# サブディレクトリに保存
curl -X POST http://localhost:8000/api/v1/workflows/register \
  -d '{"workflow_name": "test", "yaml_content": "...", "directory": "taskmaster/tm_123"}'
# → config/graphai/taskmaster/tm_123/test.yml
```

#### セキュリティ

- **Path traversal protection**: `directory` に `..` を含む場合は拒否
- **Automatic directory creation**: 存在しないディレクトリは自動作成（`recursive: true`）

---

### 2. workflowGeneratorAgents: TaskMaster-based Directory Organization

#### 実装場所
- `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/workflow_tester.py`

#### 変更内容

**_register_workflow() 関数の拡張**:
```python
async def _register_workflow(
    client: httpx.AsyncClient,
    workflow_name: str,
    yaml_content: str,
    task_master_id: str | int | None = None,  # 🆕 追加
) -> tuple[bool, dict[str, Any], int, str | None]:
    payload = {
        "workflow_name": workflow_name,
        "yaml_content": yaml_content,
        "overwrite": True,
    }

    # Add directory parameter if task_master_id is provided
    if task_master_id:
        payload["directory"] = f"taskmaster/{task_master_id}"
        logger.info("Registering workflow to directory: taskmaster/%s", task_master_id)
```

**workflow_tester_node() の更新**:
```python
task_master_id = state.get("task_master_id")

# Register workflow with task_master_id
registered, register_body, register_status, workflow_file_path = \
    await _register_workflow(client, workflow_name, yaml_content, task_master_id)
```

#### ディレクトリ構造

```
config/graphai/
├── taskmaster/                              # TaskMaster毎のディレクトリ
│   ├── tm_01K8K5RNX5CQTPD6P7GBGCWRHR/
│   │   └── keyword_analysis_podcast_theme_definition.yml
│   ├── tm_01K8K5RNXSV8ECSA4546RB4VFZ/
│   │   └── podcast_script_generation.yml
│   └── tm_01K8K5RNY9870DXQF9Q91Z3FMP/
│       └── tts_audio_generation.yml
└── other_workflows.yml                      # 既存のワークフロー
```

---

## ✅ テスト結果

### graphAiServer API Tests

| テストケース | directory パラメータ | 保存先 | 結果 |
|------------|-------------------|--------|------|
| 1 | 未指定 | `config/graphai/test_root.yml` | ✅ |
| 2 | `"test0001"` | `config/graphai/test0001/test_single.yml` | ✅ |
| 3 | `"test/0001"` | `config/graphai/test/0001/test_nested.yml` | ✅ |
| 4 | `"../etc"` | エラーメッセージで拒否 | ✅ |

### workflowGeneratorAgents Tests

| テストケース | task_master_id | 保存先 | 結果 |
|------------|----------------|--------|------|
| Test 1 | `tm_TEST_DIRECTORY_FEATURE` | `config/graphai/taskmaster/tm_TEST_DIRECTORY_FEATURE/test_directory_feature_workflow.yml` | ✅ |
| Test 2 | `tm_01K8K5RNX5CQTPD6P7GBGCWRHR` | `config/graphai/taskmaster/tm_01K8K5RNX5CQTPD6P7GBGCWRHR/keyword_analysis_podcast_theme_definition.yml` | ✅ |

---

## 📊 品質メトリクス

### graphAiServer

- ✅ TypeScript type checking: No errors
- ✅ ESLint: All checks passed
- ✅ Build: Successful

### workflowGeneratorAgents

- ✅ Ruff linting: All checks passed
- ✅ Ruff formatting: Already formatted
- ✅ MyPy type checking: No issues found

---

## 💡 メリット

### 1. ワークフロー整理の改善

**Before**:
```
config/graphai/
├── keyword_analysis_podcast_theme_definition.yml
├── podcast_script_generation.yml
├── tts_audio_generation.yml
└── ... (100+ workflows in flat structure)
```

**After**:
```
config/graphai/
└── taskmaster/
    ├── tm_01K8K5RNX5CQTPD6P7GBGCWRHR/
    │   └── keyword_analysis_podcast_theme_definition.yml
    ├── tm_01K8K5RNXSV8ECSA4546RB4VFZ/
    │   └── podcast_script_generation.yml
    └── tm_01K8K5RNY9870DXQF9Q91Z3FMP/
        └── tts_audio_generation.yml
```

### 2. 管理性の向上

- ✅ **TaskMaster毎にグループ化**: 関連するワークフローをまとめて管理
- ✅ **名前衝突防止**: 異なるTaskMasterで同じワークフロー名を使っても衝突しない
- ✅ **発見しやすさ**: TaskMaster IDでワークフローを即座に特定
- ✅ **スケーラビリティ**: 数百のワークフローでも整理された状態を維持

### 3. 後方互換性

- ✅ `directory` パラメータは**オプション**（未指定でもエラーにならない）
- ✅ 既存のワークフロー（ルートディレクトリに保存）は引き続き動作
- ✅ 既存のAPIクライアントは修正不要

---

## 📝 ドキュメント更新

### graphAiServer

- ✅ `graphAiServer/README.md`: Workflow Registration Endpoint セクション追加
- ✅ `graphAiServer/docs/API_ENDPOINTS.md`: 詳細なAPI仕様追加

### expertAgent

- ✅ `expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/workflow_tester.py`: Docstring更新

---

## 🔄 移行ガイド

### 既存のワークフロー

既存のワークフロー（ルートディレクトリに保存）は**そのまま使用可能**です。移行は任意です。

### 新規ワークフロー

workflowGeneratorAgentsで生成する新規ワークフローは自動的に `/taskmaster/{task_master_id}/` ディレクトリに保存されます。

### 手動登録の場合

手動でワークフローを登録する場合、`directory` パラメータを使用してサブディレクトリを指定できます：

```bash
curl -X POST http://localhost:8000/api/v1/workflows/register \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "my_workflow",
    "yaml_content": "...",
    "directory": "taskmaster/tm_YOUR_TASK_ID"
  }'
```

---

## 📦 コミット履歴

```bash
d23e4e8 feat(workflowGenerator): save generated workflows to /taskmaster/{task_master_id}/ directory
84b1bf2 docs(graphAiServer): add workflow registration API documentation
ada7a9a feat(graphAiServer): add directory parameter to workflow registration
```

---

## 🎯 今後の拡張案

### 1. JobMaster-based Organization

TaskMaster単位だけでなく、JobMaster単位でのグループ化も検討：

```
config/graphai/
├── jobmaster/
│   └── jm_01K8K5RNZWTMBD9N30K5HTVX9P/
│       ├── task_000_workflow.yml
│       ├── task_001_workflow.yml
│       └── task_002_workflow.yml
└── taskmaster/
    └── ...
```

### 2. Workflow Version Management

ワークフローのバージョン管理機能の追加：

```
config/graphai/taskmaster/tm_123/
├── workflow_v1.yml
├── workflow_v2.yml
└── workflow_latest.yml  # symlink
```

### 3. Auto-cleanup

古いワークフローの自動削除機能：

- 30日以上使用されていないワークフローを自動アーカイブ
- アーカイブ先: `config/graphai/archive/{year}/{month}/`

---

## 📚 参考資料

- [graphAiServer API Documentation](../../../graphAiServer/docs/API_ENDPOINTS.md)
- [workflowGeneratorAgents Implementation](../../../expertAgent/aiagent/langgraph/workflowGeneratorAgents/)
- [Issue #110](https://github.com/your-org/MySwiftAgent/issues/110) (if applicable)
