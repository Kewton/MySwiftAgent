# GraphAI 環境変数展開仕様

## 概要

GraphAI ワークフロー内で使用可能な環境変数プレースホルダーの仕様を定義します。
この仕様は以下のコンポーネントで共有されます：

- **graphAiServer**: 実行時の環境変数展開 (`src/services/graphai.ts`)
- **expertAgent**: ワークフロー生成時のバリデーション (`jobGeneratorV2/validators/`)

## 許可された環境変数

| プレースホルダー | デフォルト値 | 用途 |
|-----------------|-------------|------|
| `${EXPERTAGENT_BASE_URL}` | `http://localhost:8004` | ExpertAgent API |
| `${GRAPHAISERVER_BASE_URL}` | `http://localhost:8005` | GraphAiServer API |
| `${MYVAULT_BASE_URL}` | `http://localhost:8003` | MyVault API |
| `${JOBQUEUE_BASE_URL}` | `http://localhost:8001` | JobQueue API |
| `${MYSCHEDULER_BASE_URL}` | `http://localhost:8002` | MyScheduler API |

## 使用例

```yaml
nodes:
  google_search:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search
      method: POST
      body:
        query: :source.query
```

## 展開タイミング

環境変数は **graphAiServer でワークフロー実行時** に展開されます。

```
expertAgent (V2生成)        graphAiServer (実行)
        │                          │
        │  ${EXPERTAGENT_BASE_URL} │
        │  ─────────────────────→  │
        │                          │  環境変数展開
        │                          │  ↓
        │                          │  http://localhost:8004
        │                          │
        ▼                          ▼
```

## 実装参照

### graphAiServer (展開処理)

```typescript
// graphAiServer/src/services/graphai.ts:86-92
const replacements: Record<string, string> = {
  '${EXPERTAGENT_BASE_URL}': process.env.EXPERTAGENT_BASE_URL || `http://localhost:${EXPERTAGENT_PORT}`,
  '${GRAPHAISERVER_BASE_URL}': process.env.GRAPHAISERVER_BASE_URL || `http://localhost:${GRAPHAISERVER_PORT}`,
  '${MYVAULT_BASE_URL}': process.env.MYVAULT_BASE_URL || `http://localhost:${MYVAULT_PORT}`,
  '${JOBQUEUE_BASE_URL}': process.env.JOBQUEUE_BASE_URL || `http://localhost:${JOBQUEUE_PORT}`,
  '${MYSCHEDULER_BASE_URL}': process.env.MYSCHEDULER_BASE_URL || `http://localhost:${MYSCHEDULER_PORT}`,
};
```

### expertAgent (バリデーション)

```python
# expertAgent/aiagent/langgraph/jobGeneratorV2/validators/agent_constraint_validator.py
# このリストは graphAiServer の replacements と同期する必要がある
ALLOWED_ENV_VARS = {
    "${EXPERTAGENT_BASE_URL}",
    "${GRAPHAISERVER_BASE_URL}",
    "${MYVAULT_BASE_URL}",
    "${JOBQUEUE_BASE_URL}",
    "${MYSCHEDULER_BASE_URL}",
}
```

## 変更手順

新しい環境変数を追加する場合：

1. **graphAiServer**: `src/services/graphai.ts` の `replacements` に追加
2. **expertAgent**: `agent_constraint_validator.py` の `ALLOWED_ENV_VARS` に追加
3. **このドキュメント**: 上記の表に追加
4. **テスト**: 両サービスのテストを更新

## 注意事項

- 許可リストにない環境変数パターンは、expertAgent のバリデーションでエラーになります
- 環境変数は大文字・アンダースコアのみ使用可能（`${[A-Z_][A-Z0-9_]*}`）
- 展開は graphAiServer 側で行われるため、expertAgent はプレースホルダーをそのまま出力します

---

*最終更新: 2026-01-09*
*Issue #342 対応*
