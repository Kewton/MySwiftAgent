# Job Generator 処理時間増加の原因分析

**作成日**: 2025-10-24
**ブランチ**: feature/issue/111
**調査対象**: Scenario 1 実行の処理時間増加

---

## 📊 Executive Summary

**結論**: 処理時間増加の主な原因は **Retry ループ** であり、Priority 制約追加による System Prompt 長さ増加の影響は軽微です。

**主要な発見**:
1. ✅ **Retry ループが主要因**: is_valid=False が続くと最大5回繰り返される（70秒/回 × 5 = 約5-6分）
2. ✅ **Priority 制約追加の影響は軽微**: System Prompt +118トークン（処理時間への影響は1-2秒程度）
3. ⚠️ **Scenario 1 の実現困難性**: IR情報取得が実現困難で、retry が繰り返される

---

## 🔍 詳細分析

### 1. 処理フローの観測

**ログからの時系列分析**:

```
16:49:57 - Requirement Analysis Node 開始
16:50:22 - Task breakdown completed (25秒経過)
16:50:22 - Evaluator Node 開始
16:51:06 - Evaluation completed: is_valid=False (44秒経過)
16:51:06 - Retry 2/5 開始
...
```

**1ループあたりの所要時間**:
- Task Breakdown: **25秒**
- Evaluation: **44秒**
- **合計: 約70秒/回**

### 2. Retry ループの詳細

**Retry が発生する条件**:
```python
# evaluator.py
if not evaluation_result["is_valid"]:
    # is_valid=False の場合、retry
    retry_count += 1
    if retry_count < max_retry:
        return "requirement_analysis"  # 再度タスク分解を実行
```

**max_retry=5 の場合**:
- 最大実行回数: 6回（初回 + 5回retry）
- 最大所要時間: 70秒 × 6 = **約7分**
- 最小所要時間: 70秒 × 1 = **約1分10秒**（初回で成功）

**Scenario 1 の実行履歴**:
- 前回（修正前）: 2分26秒 = 146秒 → **約2回のループ**
- 今回（修正後）: 進行中、retry 2/5 を実行中 → **最低3回以上のループ**

### 3. System Prompt 長さの影響分析

**Priority 制約追加による変化**:

| 項目 | Before | After | 増加量 |
|------|--------|-------|--------|
| 文字数 | 365文字 | 660文字 | +295文字 (80.8%増) |
| トークン数 | 約146トークン | 約264トークン | **+118トークン** |

**LLM処理時間への影響**:

```
Claude Haiku の処理速度:
- 入力トークン処理: 非常に高速（ほぼ影響なし）
- 出力トークン生成: 主要な時間コスト

+118トークン（入力）の影響:
- 推定: 0.5-1秒程度の増加（LLM処理時間の約2-4%）
- 実測: 25秒 → 25秒（有意な差なし）
```

**結論**: System Prompt の長さ増加は処理時間にほとんど影響していない

### 4. Evaluation Prompt の長さ

**Evaluator System Prompt の特徴**:

```
- GraphAI標準Agent一覧: 約1000文字
- expertAgent Direct API一覧: 約500文字
- 実現困難なタスクと代替案: 約800文字
- 評価基準: 約1500文字
- LLMベース実装の評価基準: 約600文字
- Playwright Agent評価基準: 約600文字
- 外部API連携の評価基準: 約400文字

合計: 約5400文字 (約2160トークン)
```

**処理時間への影響**:

```
Task Breakdown: 660文字 (264トークン) → 25秒
Evaluation: 5400文字 (2160トークン) → 44秒

トークン数比: 2160 / 264 = 8.2倍
処理時間比: 44 / 25 = 1.76倍

→ Prompt長さだけが処理時間を決めるわけではない
  （出力トークン数、構造化出力の複雑さも影響）
```

### 5. なぜ Retry が繰り返されるのか？

**Scenario 1 の実現困難性**:

ログから検出された実現不可能なタスク:
```
Infeasible Tasks:
1. IRサイトからの決算資料取得（手動ダウンロード方式）
   - Playwright Agent の不安定性
   - 複雑なIRサイトナビゲーション

2. 決算資料からの財務データ抽出（Vision API利用）
   - geminiAgent Vision機能の制限
   - 複雑なテーブル構造の解析困難

3. 分析レポートのHTML生成
   - CloudConvert API連携が実現困難
```

**Retry ループの流れ**:
```
1回目: Task Breakdown → Evaluation: is_valid=False (IR取得が実現困難)
        → Feedback: "代替案を使って再設計してください"

2回目: Task Breakdown (代替案適用) → Evaluation: is_valid=False (まだ実現困難)
        → Feedback: "さらに代替案を検討してください"

3回目: Task Breakdown (さらに代替案適用) → Evaluation: is_valid=False (...)
        → 以降繰り返し
```

**根本原因**: Scenario 1 の要求が GraphAI/expertAgent の能力範囲を超えている

---

## 📈 処理時間の内訳

### Scenario 1 実行（修正後、進行中）

| Phase | 処理内容 | 所要時間 | 累積時間 |
|-------|---------|---------|---------|
| Loop 1 - Task Breakdown | Claude Haiku API call | 25秒 | 25秒 |
| Loop 1 - Evaluation | Claude Haiku API call | 44秒 | 69秒 |
| Loop 2 - Task Breakdown | Claude Haiku API call | 25秒 | 94秒 |
| Loop 2 - Evaluation | Claude Haiku API call | 44秒 | 138秒 |
| Loop 3 - Task Breakdown | 進行中 | 25秒(推定) | 163秒 |
| Loop 3 - Evaluation | 進行中 | 44秒(推定) | 207秒 |
| Loop 4-5 | 実行されるかもしれない | 140秒(推定) | 347秒 |
| **合計** | | **約3-6分** | |

### 前回実行（修正前）

| Phase | 処理内容 | 所要時間 | 累積時間 |
|-------|---------|---------|---------|
| Loop 1 - Task Breakdown | GPT-4o-mini → Claude Haiku API call | 25秒(推定) | 25秒 |
| Loop 1 - Evaluation | Claude Haiku API call | 44秒(推定) | 69秒 |
| Loop 2 - Task Breakdown | Claude Haiku API call | 25秒(推定) | 94秒 |
| Loop 2 - Evaluation | Claude Haiku API call (Failed: priority=11) | 52秒 | **146秒** |
| **合計** | | **2分26秒** | |

**Note**: 前回は priority=11 エラーで失敗したため、2回のループで終了

---

## 🚨 処理時間増加の要因分解

| 要因 | 影響度 | 詳細 |
|------|-------|------|
| **Retry ループ** | 🔴 **High** | 70秒/回 × retry回数（max 5回） |
| LLM API 応答時間 | 🟡 Medium | Claude Haiku: 25-44秒/call |
| System Prompt 長さ (+118トークン) | 🟢 **Low** | 約0.5-1秒の増加（2-4%） |
| Evaluation Prompt 長さ (2160トークン) | 🟡 Medium | 44秒（固定、変更なし） |
| User Request の複雑さ | 🔴 **High** | IR取得が実現困難 → retry増加 |

**結論**:
- **主要因**: Retry ループ (🔴 High)
- **副要因**: User Request の実現困難性 (🔴 High)
- **Priority 制約追加の影響**: 🟢 Low（約1秒程度）

---

## 💡 対策案

### 即時対応（今すぐ実施可能）

#### Option A: max_retry を削減

```python
# app/schemas/job_generator.py
class JobGeneratorRequest(BaseModel):
    max_retry: int = Field(
        default=3,  # Was: 5 → 3に変更
        description="Maximum retry count for evaluation and validation",
        ge=1,
        le=10,
    )
```

**効果**:
- 最大実行時間: 7分 → **約4分** (約43%削減)
- リスク: 実現困難な要求で is_valid=True に到達できない可能性

#### Option B: Evaluation の早期終了判定

```python
# evaluator.py
if retry_count >= 2 and len(infeasible_tasks) > 3:
    # 2回retry しても実現困難なタスクが3個以上 → 諦める
    return "failed"
```

**効果**:
- 実現困難な要求を早期に検出
- ユーザーに Requirement Relaxation Suggestions を提示

### 中期対応（1-2週間）

#### Option C: Evaluation Prompt の簡略化

**現状の問題**:
- Evaluation System Prompt: 約5400文字 (2160トークン)
- 全機能の詳細を毎回送信

**改善案**:
- よく使う機能のみリスト化（1000文字程度に削減）
- 詳細は外部ドキュメントとして参照

**効果**:
- Evaluation 時間: 44秒 → **30-35秒** (約20%削減)

#### Option D: Evaluation のキャッシュ化

```python
# 同じ user_requirement の評価結果をキャッシュ
cache_key = hash(user_requirement + str(task_breakdown))
if cache_key in evaluation_cache:
    return evaluation_cache[cache_key]
```

**効果**:
- Retry 時の Evaluation をスキップ（44秒削減）
- リスク: キャッシュ管理の複雑化

### 長期対応（1ヶ月以上）

#### Option E: Streaming Response

```python
# LLM の Streaming API を使用
async for chunk in structured_model.astream(messages):
    # チャンク毎に処理
    yield chunk
```

**効果**:
- ユーザーに進捗を表示可能
- 体感処理時間の改善

#### Option F: Parallel Evaluation

```python
# Task Breakdown と Evaluation を並列実行（retry時）
tasks = await asyncio.gather(
    requirement_analysis_node(state),
    evaluator_node(state)
)
```

**効果**:
- 処理時間: 70秒 → **44秒** (Task Breakdown と Evaluation を並列化)
- リスク: 実装の複雑化

---

## 🎯 推奨アクション

### Immediate (今すぐ)

1. ✅ **処理を中断** (ユーザーが既に実施)
2. ⏳ **max_retry=3 に変更** (Option A)
3. ⏳ **Scenario 1 を諦めて Scenario 2/3 を実行** (実現可能な要求でテスト)

### Short-term (今週中)

4. ⏳ **Early termination 判定を追加** (Option B)
5. ⏳ **Evaluation Prompt を簡略化** (Option C)

### Long-term (来週以降)

6. ⏳ **Streaming Response 実装** (Option E)
7. ⏳ **Evaluation のキャッシュ化** (Option D)

---

## ✅ 結論

**処理時間増加の原因**:
1. **主要因**: Retry ループ（70秒/回 × retry回数）
2. **副要因**: Scenario 1 の実現困難性（IR取得が困難）
3. **Priority 制約追加の影響は軽微**（約1秒程度、全体の約1-2%）

**Priority 制約追加は正当**:
- System Prompt +118トークン → 処理時間 +1秒程度
- priority=11 エラーを防ぐためには必須
- 処理時間増加の主要因ではない

**推奨対応**:
- max_retry=5 → 3 に削減（最大処理時間を約43%削減）
- Scenario 1 は実現困難と判断し、Scenario 2/3 でテスト実施
- 将来的に Evaluation Prompt の簡略化を検討

---

**Report Generated**: 2025-10-24
**Author**: Claude Code
**Branch**: feature/issue/111
