# 包括的テスト結果レポート: Job/Task Generator 3シナリオ検証

**実施日**: 2025-10-20
**対象ブランチ**: `feature/issue/97`
**Phase**: Phase 7完了後の包括的検証
**テスト実行**: 3シナリオ × 3回実行 = 計9回

---

## 📋 実行概要

Phase 4-7でPydantic validation errorを完全解決した後、3つの代表的なシナリオで包括的な動作検証を実施しました。

### テスト対象シナリオ

| シナリオ | 要求内容 | 期待される動作 |
|---------|---------|--------------|
| **Scenario 1** | 企業名を入力すると、その企業の過去５年の売り上げとビジネスモデルの変化をまとめてメール送信する | 企業分析タスク → レポート作成 → メール送信 |
| **Scenario 2** | 指定したWebサイトからPDFファイルを抽出し、Google Driveにアップロード後、メールで通知します | PDF抽出 → Drive保存 → 通知メール |
| **Scenario 3** | This workflow searches for a newsletter in Gmail using a keyword, summarizes it, converts it to an MP3 podcast | Gmail検索 → 要約 → MP3変換 |

---

## 🧪 テスト実行結果

### 全体サマリー

| 指標 | 値 |
|------|---|
| **総実行回数** | 9回 (3シナリオ × 3回) |
| **成功回数** | 0回 (0%) |
| **失敗回数** | 9回 (100%) |
| **平均実行時間** | 524.39秒 (8.7分) |
| **失敗理由** | Recursion limit of 25 reached (8回) / Timeout (1回) |

---

## 📊 Scenario 1: 企業分析ワークフロー

**要求**: 企業名を入力すると、その企業の過去５年の売り上げとビジネスモデルの変化をまとめてメール送信する

### 実行結果

| Run | 実行時間 | HTTP Status | エラー内容 |
|-----|---------|------------|----------|
| **#1** | 489.47秒 | 500 | Recursion limit of 25 reached |
| **#2** | 600.00秒 | Timeout | HTTPConnectionPool timeout |
| **#3** | 521.11秒 | 500 | Recursion limit of 25 reached |

### 詳細データ

#### Run #1
```json
{
  "scenario": "Scenario 1: 企業分析",
  "run_number": 1,
  "timestamp": "2025-10-20T15:15:48.184784",
  "elapsed_time": 489.47,
  "status_code": 500,
  "success": false,
  "error": "Recursion limit of 25 reached without hitting a stop condition"
}
```

#### Run #2
```json
{
  "scenario": "Scenario 1: 企業分析",
  "run_number": 2,
  "timestamp": "2025-10-20T15:25:53.199196",
  "elapsed_time": 600.0,
  "status_code": null,
  "success": false,
  "error": "HTTPConnectionPool timeout (read timeout=600)"
}
```

#### Run #3
```json
{
  "scenario": "Scenario 1: 企業分析",
  "run_number": 3,
  "timestamp": "2025-10-20T15:34:39.311483",
  "elapsed_time": 521.11,
  "status_code": 500,
  "success": false,
  "error": "Recursion limit of 25 reached without hitting a stop condition"
}
```

---

## 📊 Scenario 2: PDF抽出・Google Driveアップロード

**要求**: 指定したWebサイトからPDFファイルを抽出し、Google Driveにアップロード後、メールで通知します

### 実行結果

| Run | 実行時間 | HTTP Status | エラー内容 |
|-----|---------|------------|----------|
| **#1** | 514.49秒 | 500 | Recursion limit of 25 reached |
| **#2** | 509.41秒 | 500 | Recursion limit of 25 reached |
| **#3** | 514.93秒 | 500 | Recursion limit of 25 reached |

### 詳細データ

#### Run #1
```json
{
  "scenario": "Scenario 2: PDF抽出",
  "run_number": 1,
  "timestamp": "2025-10-20T15:44:14.441577",
  "elapsed_time": 514.49,
  "status_code": 500,
  "success": false,
  "error": "Recursion limit of 25 reached without hitting a stop condition"
}
```

#### Run #2
```json
{
  "scenario": "Scenario 2: PDF抽出",
  "run_number": 2,
  "timestamp": "2025-10-20T15:52:48.370050",
  "elapsed_time": 509.41,
  "status_code": 500,
  "success": false,
  "error": "Recursion limit of 25 reached without hitting a stop condition"
}
```

#### Run #3
```json
{
  "scenario": "Scenario 2: PDF抽出",
  "run_number": 3,
  "timestamp": "2025-10-20T16:01:18.320831",
  "elapsed_time": 514.93,
  "status_code": 500,
  "success": false,
  "error": "Recursion limit of 25 reached without hitting a stop condition"
}
```

---

## 📊 Scenario 3: Gmail→要約→MP3ポッドキャスト

**要求**: This workflow searches for a newsletter in Gmail using a keyword, summarizes it, converts it to an MP3 podcast

### 実行結果

| Run | 実行時間 | HTTP Status | エラー内容 |
|-----|---------|------------|----------|
| **#1** | 519.05秒 | 500 | Recursion limit of 25 reached |
| **#2** | 519.43秒 | 500 | Recursion limit of 25 reached |
| **#3** | 522.87秒 | 500 | Recursion limit of 25 reached |

### 詳細データ

#### Run #1
```json
{
  "scenario": "Scenario 3: Gmail to Podcast",
  "run_number": 1,
  "timestamp": "2025-10-20T16:09:54.253072",
  "elapsed_time": 519.05,
  "status_code": 500,
  "success": false,
  "error": "Recursion limit of 25 reached without hitting a stop condition"
}
```

#### Run #2
```json
{
  "scenario": "Scenario 3: Gmail to Podcast",
  "run_number": 2,
  "timestamp": "2025-10-20T16:18:38.694622",
  "elapsed_time": 519.43,
  "status_code": 500,
  "success": false,
  "error": "Recursion limit of 25 reached without hitting a stop condition"
}
```

#### Run #3
```json
{
  "scenario": "Scenario 3: Gmail to Podcast",
  "run_number": 3,
  "timestamp": "2025-10-20T16:27:18.572439",
  "elapsed_time": 522.87,
  "status_code": 500,
  "success": false,
  "error": "Recursion limit of 25 reached without hitting a stop condition"
}
```

---

## 🔍 問題分析

### 発見された重大な問題: LangGraph Recursion Limit エラー

**エラー内容**:
```
Job generation failed: Recursion limit of 25 reached without hitting a stop condition.
You can increase the limit by setting the `recursion_limit` config key.
For troubleshooting, visit: https://python.langchain.com/docs/troubleshooting/errors/GRAPH_RECURSION_LIMIT
```

### 根本原因の推定

#### 1. ワークフローの無限ループ

LangGraphのワークフローが、以下のような循環構造に陥っている可能性が高い:

```
task_breakdown → evaluator (is_valid=False) → task_breakdown (retry) → evaluator (is_valid=False) → ...
```

#### 2. 終了条件の不備

ワークフロー内の条件分岐ロジックに問題があり、終了状態（END）に到達できていない可能性:

- `evaluator` ノードが常に `is_valid=False` を返す
- `task_breakdown` の retry 処理が無限ループする
- 各ノード間の遷移条件が適切に設定されていない

#### 3. Phase 7修正の副作用

Phase 7で `default_factory=list` を追加した結果、以下の問題が発生した可能性:

- LLMが空のレスポンス `{}` を返す
- `tasks=[]` や `interfaces=[]` の空配列により、次のノードでビジネスロジックエラー
- エラーハンドリングが retry ループを引き起こす

---

## 📈 統計データ

### 実行時間分布

| Scenario | Run #1 | Run #2 | Run #3 | 平均 |
|----------|--------|--------|--------|------|
| **Scenario 1** | 489.47s | 600.00s (timeout) | 521.11s | 536.86s |
| **Scenario 2** | 514.49s | 509.41s | 514.93s | 512.94s |
| **Scenario 3** | 519.05s | 519.43s | 522.87s | 520.45s |
| **全体平均** | - | - | - | **524.39s** |

### エラータイプ分布

| エラータイプ | 発生回数 | 割合 |
|------------|---------|------|
| **Recursion limit of 25** | 8回 | 88.9% |
| **HTTP Timeout** | 1回 | 11.1% |

---

## 🎯 Phase 4-7 の成果と限界

### ✅ Phase 4-7で解決した問題

| Phase | 解決した問題 | 技術的アプローチ |
|-------|------------|----------------|
| **Phase 4** | evaluator Pydanticエラー | `parse_json_array_field` validator |
| **Phase 5** | Timeout問題 | max_tokens削減 (32768 → 4096) |
| **Phase 6** | task_breakdown Pydanticエラー | `overall_summary` に `default=""` |
| **Phase 7** | interface_definition + task_breakdown Pydanticエラー | `default_factory=list` |

**成果**: Pydantic validation layer のエラーは完全解決

### ❌ 今回発見された新たな問題

**問題レベル**: ワークフローロジック層の欠陥

- Phase 4-7: Pydantic validation layer (データモデル層)
- **今回**: Workflow logic layer (ビジネスロジック層)

**影響範囲**: すべてのシナリオで100%再現 (9回中9回失敗)

---

## 🔄 Phase 8 推奨対策

### 優先度1: Recursion Limit の引き上げ (緊急対策)

**実装**:
```python
# expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/graph.py
workflow = StateGraph(JobTaskState)
workflow.compile(config={"recursion_limit": 50})  # 25 → 50 へ引き上げ
```

**期待効果**: エラーメッセージの先送り（根本解決ではない）

### 優先度2: 終了条件の明確化 (根本対策)

**問題箇所**: `evaluator` ノードの判定ロジック

**実装案**:
1. `is_valid=False` でも retry 回数が max_retry に達したら強制終了
2. Empty task/interface detection: `tasks=[]` や `interfaces=[]` の場合は retry せず失敗として終了
3. ノード間の遷移条件をログで可視化

### 優先度3: ログ解析による無限ループ箇所の特定

**実装**:
```bash
# expertAgent ログから循環パターンを抽出
grep -A 5 "task_breakdown" /tmp/expertAgent_phase7_v2.log | head -200
grep -A 5 "evaluator" /tmp/expertAgent_phase7_v2.log | head -200
```

**目的**: どのノード間でループしているかを特定

---

## 📝 次のアクション

### Phase 8 実施計画

1. **Step 1**: expertAgent ログ解析 (20分)
   - 循環パターンの特定
   - 無限ループ発生箇所の可視化

2. **Step 2**: 緊急対策実装 (10分)
   - `recursion_limit` を 50 へ引き上げ
   - 同シナリオで再テスト

3. **Step 3**: 根本対策実装 (30分)
   - evaluator の終了条件見直し
   - retry ロジックの改善
   - Empty response ハンドリング追加

4. **Step 4**: 再検証 (60分)
   - 3シナリオ × 3回 = 9回テスト
   - 成功率 80%以上を目標

---

## 📚 参考情報

### テスト実行コマンド

```bash
# Scenario 1 実行
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d @/tmp/scenario1.json \
  --max-time 600

# Scenario 2 実行
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d @/tmp/scenario2.json \
  --max-time 600

# Scenario 3 実行
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d @/tmp/scenario3.json \
  --max-time 600
```

### 生データ保存先

- Scenario 1: `/tmp/scenario1_results.json`
- Scenario 2: `/tmp/scenario2_results.json`
- Scenario 3: `/tmp/scenario3_results.json`

### 関連ドキュメント

- [Phase 4-6 総括レポート](./phase-4-6-summary.md)
- [Phase 7 詳細レポート](./phase-7-results.md)
- [LangGraph Recursion Limit ドキュメント](https://python.langchain.com/docs/troubleshooting/errors/GRAPH_RECURSION_LIMIT)

---

**作成者**: Claude Code
**レポート形式**: Markdown
**関連Issue**: #97
**次回作業**: Phase 8（Recursion Limit エラー対策）
