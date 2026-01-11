# 根本原因分析レポート: num:5 による HTTP 422 エラー

## 概要

| 項目 | 内容 |
|------|------|
| **発生日** | 2026-01-10 |
| **関連Issue** | #345 |
| **現象** | google_search API呼び出しで HTTP 422 エラー |
| **エラーメッセージ** | `Input should be less than or equal to 3` |
| **根本原因** | Few-shot例の `num: 5` が API制約 `le=3` に違反 |
| **修正状況** | 完了 |

---

## 1. 問題の経緯

### 1.1 初期調査（誤った仮説）

最初に発見した問題:
- ワークフローで `:source.query` という参照パターンが使用されていた
- 正しくは `:source.user_input.query` であるべき
- `reference_rules.py` と 6つの few_shot YAML を修正

この修正後もエラーは継続 → 別の原因が存在することが判明

### 1.2 真の根本原因の発見

デバッグワークフローを作成して調査:

```bash
# 参照解決は正常に動作していることを確認
curl -X POST "http://localhost:8005/api/runs" \
  -d '{"model_name": "debug_fetch", "user_input": {"query": "test"}}'
# → {"queries_array": ["test"]} と正しく解決

# 直接API呼び出しで真の原因を特定
curl -X POST "http://localhost:8004/aiagent-api/v1/utility/google_search" \
  -d '{"queries": ["test"], "num": 5}'
# → HTTP 422: "Input should be less than or equal to 3"

curl -X POST "http://localhost:8004/aiagent-api/v1/utility/google_search" \
  -d '{"queries": ["test"], "num": 3}'
# → HTTP 200: 正常にレスポンス
```

**真の原因**: `num: 5` が API制約 `le=3` に違反

---

## 2. 根本原因分析

### 2.1 A. なぜ誤ったワークフローを作り込んでしまったのか？

```
原因の連鎖:
1. Few-shot例 (search_pattern.yaml) に num: 5 が記載されていた
   ↓
2. LLMがFew-shot例を参考にワークフローを生成
   ↓
3. 生成されたワークフローも num: 5 を使用
   ↓
4. API呼び出し時に制約違反でエラー
```

#### 具体的な原因箇所

**Few-shot例 (修正前)**:
```yaml
# expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/prompt_builder/few_shot/search_pattern.yaml
search_api:
  agent: fetchAgent
  inputs:
    url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search
    method: POST
    body:
      queries:
        - :source.user_input.keyword
      num: 5  # ← API制約 le=3 に違反
```

**APIスキーマの制約**:
```python
# expertAgent/app/schemas/utilitySchemas.py:32
class SearchUtilityRequest(BaseModel):
    queries: List[str]
    num: int | None = Field(default=None, le=3, description="Number of results per query (max=3 to prevent timeout)")
```

#### なぜ num: 5 が設定されていたのか

| 可能性 | 分析 |
|-------|------|
| 過去の仕様変更 | 以前は le=5 または制約なしだった可能性が高い |
| 仕様変更時の更新漏れ | APIスキーマの制約を変更した際にFew-shot例を更新し忘れた |
| 手動テストの不足 | Few-shot例を変更後に実際のAPIで動作確認していなかった |

### 2.2 B. なぜワークフローの誤り検知・是正しきれなかったのか？

```
検知できなかった理由:
1. Few-shot例とAPIスキーマの整合性チェックが存在しない
2. ワークフロー生成時にパラメータのバリデーションがない
3. 生成後のワークフローを実際のAPIでテストする仕組みがない
```

#### 検知・是正の不備箇所

| プロセス | 現状 | 問題点 |
|---------|------|-------|
| Few-shot作成/更新時 | 手動レビューのみ | APIスキーマとの自動整合性チェックなし |
| ワークフロー生成時 | 構文チェックのみ | パラメータ値の妥当性チェックなし |
| ワークフロー登録時 | YAML構文検証のみ | API呼び出しパラメータの検証なし |
| 実行前 | なし | Dry-run/スモークテストなし |

---

## 3. 修正内容

### 3.1 即時修正（完了）

| ファイル | 修正内容 |
|---------|---------|
| `search_pattern.yaml` | `num: 5` → `num: 3` |
| `workflow_jm_*.yml` (v1.97) | `num: 5` → `num: 3` |

### 3.2 修正確認

```bash
# 修正後のワークフロー実行
curl -X POST "http://localhost:8005/api/runs" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "taskmaster/tm_01KEK2NB139EYH1ZVKRPR9N73K/workflow_jm_01KEK2NB21KQ6XV8HEWCWX3A57", "user_input": {"query": "test"}}'

# → HTTP 200: search_results に3件の結果を含む正常レスポンス
```

---

## 4. 再発防止策（提案）

### 4.1 短期対策（即時実施可能）

| 対策 | 詳細 | 優先度 |
|-----|------|-------|
| **Few-shot例の全件確認** | 全てのfew_shot/*.yamlをAPIスキーマと照合 | 🔴 高 |
| **Few-shot変更時チェックリスト** | API制約との整合性確認を必須化 | 🔴 高 |
| **ドキュメント更新** | num パラメータの制約をFew-shot例のコメントに明記 | 🟡 中 |

### 4.2 中期対策（設計・実装が必要）

| 対策 | 詳細 | 工数目安 |
|-----|------|---------|
| **Few-shot自動検証** | CIでFew-shot例をAPIスキーマに照らし合わせて検証 | 3-5日 |
| **生成時バリデーション** | ワークフロー生成時にAPIパラメータの妥当性をチェック | 5-7日 |
| **Dry-run機能** | ワークフロー登録前にスモークテストを自動実行 | 7-10日 |

### 4.3 長期対策（アーキテクチャ改善）

| 対策 | 詳細 |
|-----|------|
| **スキーマ駆動開発** | APIスキーマからFew-shot例のパラメータ制約を自動生成 |
| **Contract Testing** | Few-shot例とAPIの契約テストをCI/CDに組み込み |
| **Observability強化** | API制約違反を早期検知するモニタリング |

---

## 5. 教訓

### 5.1 根本原因

> **Few-shot例とAPIスキーマの間に整合性管理の仕組みがなかった**

### 5.2 学びのポイント

1. **手動管理の限界**: 複数箇所で同じ情報（API制約）を管理すると不整合が発生しやすい
2. **変更伝播の重要性**: APIスキーマを変更したら依存するすべての箇所を更新する仕組みが必要
3. **早期検証の価値**: 生成時・登録時にバリデーションがあれば実行前にエラーを検出できた

---

## 6. 関連ファイル

| ファイル | 役割 |
|---------|------|
| `expertAgent/app/schemas/utilitySchemas.py` | API制約定義 (`le=3`) |
| `expertAgent/.../few_shot/search_pattern.yaml` | Few-shot例（修正済み） |
| `graphAiServer/config/graphai/.../workflow_jm_*.yml` | 生成されたワークフロー（修正済み） |

---

## 7. ステータス

| 項目 | ステータス |
|------|----------|
| 即時修正 | ✅ 完了 |
| 動作確認 | ✅ 完了 |
| 根本原因分析 | ✅ 完了 |
| 再発防止策（短期） | 🔄 対応中 |
| 再発防止策（中長期） | 📝 提案段階 |
