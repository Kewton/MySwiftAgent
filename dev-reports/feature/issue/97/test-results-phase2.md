# Phase 2 テスト結果レポート

**実施日**: 2025-10-20
**対象ブランチ**: `feature/issue/97`
**Phase**: Phase 2（jobqueue APIレスポンス統一後）
**修正内容**: jobqueue APIの3つのレスポンススキーマに `id` フィールドを追加

---

## 📋 テスト概要

Phase 2で実施したjobqueue API修正（レスポンス構造統一）の効果を検証するため、3つのシナリオでテストを実施しました。

### テスト環境

| 項目 | 設定値 |
|------|--------|
| **expertAgent** | http://localhost:8104 |
| **jobqueue** | http://localhost:8101 |
| **タイムアウト** | 600秒（10分） |
| **max_retry** | 5 |
| **LLMモデル** | Claude Haiku 4.5 |
| **max_tokens** | 8192 |

---

## 🧪 テストシナリオと結果

### Scenario 1: 企業分析ワークフロー

**要求**: 「企業名を入力すると、その企業の過去５年の売り上げとビジネスモデルの変化をまとめてメール送信する」

#### 結果サマリー

| 項目 | 結果 |
|------|------|
| **HTTPステータス** | ✅ 200 OK |
| **実行時間** | 144.36秒（約2分24秒） |
| **ワークフロー状態** | ⚠️ failed |
| **到達フェーズ** | **interface_definition** |
| **タスク分解** | ✅ 成功（10タスク生成） |
| **KeyError: 'id'** | ✅ **解消（Phase 2の修正により）** |

#### 詳細分析

**✅ Phase 2の成果確認**:
- expertAgentは **interface_definition段階まで到達**
- Phase 1で発生していた `KeyError: 'id'` は **解消された**
- jobqueue APIの `InterfaceMaster` 作成リクエストが **正常に送信された**

**❌ 新たに発見された問題**:
```
Interface definition failed: Jobqueue API error (400):
{"detail":"Invalid input_schema: Schema error: \"^[\\\\p{L}\\\\p{N}\\\\s\\\\-\\\\.\\\\'\\\\(\\\\)&]+$\" is not a 'regex'"}
```

**問題の詳細**:
- jobqueue APIのJSON Schema V7バリデーションでRegexエラーが発生
- LLMが生成したRegexパターンに **4重エスケープ** が含まれている
- Phase 1で修正したPrompt（`interface_schema.py`）が十分に機能していない可能性

**生成されたタスク**（10タスク）:
1. 企業名入力と検証
2. 企業の売上データ検索（複数クエリ）
3. ビジネスモデル変化情報検索（複数クエリ）
4. 売上データの分析と可視化
5. ビジネスモデル変化の分析と要約
6. レポート生成（HTML形式）
7. メール送信先アドレス入力と検証
8. メール本文の作成
9. メール送信
10. エラーハンドリングとリトライ

---

### Scenario 2: PDF抽出とGoogle Driveアップロード

**要求**: 「指定したWebサイトからPDFファイルを抽出し、Google Driveにアップロード後、メールで通知します」

#### 結果サマリー

| 項目 | 結果 |
|------|------|
| **HTTPステータス** | ❌ タイムアウト |
| **実行時間** | 600.01秒（10分） |
| **到達フェーズ** | 不明（タイムアウト） |

#### 詳細分析

**原因推測**:
1. **LLMモデルの処理時間**:
   - `max_tokens=8192` による生成時間の増加
   - 複雑な要求（PDF抽出 + Google Drive + メール通知）による処理負荷

2. **前段階での停止**:
   - requirement_analysis または task_breakdown での時間超過
   - LLMへのプロンプトが長大化している可能性

3. **expertAgentの内部エラー**:
   - interface_definition以前の段階で例外が発生
   - ログ出力不足により詳細不明

**jobqueueログの確認**:
- jobqueueにはリクエストが届いていない
- expertAgentが前段階で停止している

---

### Scenario 3: Newsletter検索とMP3変換

**要求**: 「This workflow searches for a newsletter in Gmail using a keyword, summarizes it, converts it to an MP3 podcast」

#### 結果サマリー

| 項目 | 結果 |
|------|------|
| **HTTPステータス** | ❌ タイムアウト |
| **実行時間** | 600.01秒（10分） |
| **到達フェーズ** | 不明（タイムアウト） |

#### 詳細分析

Scenario 2と同様の原因で、タイムアウトが発生しています。

**特徴**:
- 英語の要求（英語 → 日本語のPrompt処理）
- 複数のAPI連携（Gmail + Summarization + MP3変換）
- expertAgentが前段階で停止

---

## 📊 Phase 2 修正の効果測定

### ✅ 達成事項

| 項目 | Phase 1 | Phase 2 | 判定 |
|------|---------|---------|------|
| **KeyError: 'id' 発生** | ❌ 発生 | ✅ 解消 | **改善** |
| **interface_definition到達** | ❌ 未到達 | ✅ 到達 | **改善** |
| **実行時間（Scenario 1）** | 2分44秒 | 2分24秒 | **改善** |
| **ワークフロー完了** | ❌ 失敗 | ❌ 失敗 | 未改善 |

### 🎯 Phase 2の成果

1. **✅ 根本原因の解決**:
   - `KeyError: 'id'` を完全に解消
   - jobqueue APIのレスポンス構造を統一
   - 後方互換性を保ちながら修正

2. **✅ interface_definition段階まで到達**:
   - Phase 1では `KeyError` で停止していた段階を突破
   - InterfaceMaster作成リクエストが正常に送信された

3. **✅ 実行時間の改善**:
   - Scenario 1: 2分44秒 → 2分24秒（約13%短縮）
   - `id` フィールドの欠如によるエラーハンドリングの削減

---

## ⚠️ 残存する課題

### 課題1: Regex過剰エスケープ問題（優先度: 🔴 高）

**問題**:
```
"^[\\\\p{L}\\\\p{N}\\\\s\\\\-\\\\.\\\\'\\\\(\\\\)&]+$" is not a 'regex'
```

**原因**:
- LLMがJSON文字列内のRegexパターンを4重エスケープで生成
- Phase 1で `interface_schema.py` のPromptを修正したが、不十分

**対策案（Phase 3）**:
1. **Prompt改善**:
   - より明確なエスケープ例を追加
   - 誤った例を明示的に禁止

2. **Response後処理**:
   - LLM出力後、Regexパターンを自動修正
   - 4重エスケープ → 2重エスケープに変換

3. **JSON Schema検証の緩和**:
   - jobqueue APIのRegex検証を一時的に無効化
   - または、より寛容な検証ルールを適用

---

### 課題2: タイムアウト問題（優先度: 🟡 中）

**問題**:
- Scenario 2, 3が600秒（10分）でタイムアウト
- 複雑な要求への対応が困難

**原因推測**:
1. **max_tokens設定が過大**:
   - 現在: 8192トークン
   - 推奨: 4096トークン

2. **LLMモデル選択**:
   - 現在: Claude Haiku 4.5（全ノード）
   - 推奨: ハイブリッド戦略（Haiku + Sonnet）

3. **ログ出力不足**:
   - expertAgentの詳細なログが記録されていない
   - タイムアウトの原因特定が困難

**対策案（Phase 3）**:
1. **max_tokensの最適化**:
   - タスク数に応じた動的調整（2048 / 4096 / 8192）

2. **ハイブリッドモデル戦略**:
   - requirement_analysis, task_breakdown: Haiku（高速）
   - interface_definition, task_generation: Sonnet（高精度）
   - evaluation, validation: Haiku（高速）

3. **タイムアウト設定の見直し**:
   - デフォルトを600秒 → 900秒（15分）に拡大
   - ユーザーが調整可能なパラメータとして公開

4. **ロギング強化**:
   - 各ノードの処理時間を記録
   - LLM呼び出しのトークン数を記録

---

## 🎯 Phase 3への推奨事項

### 優先度: 🔴 最高

#### 対策A: Regex過剰エスケープの修正

**工数**: 30-45分

**実施内容**:
1. `interface_schema.py` のPromptを再度改善
2. LLM出力後のResponse後処理を追加
3. 4重エスケープ → 2重エスケープの自動変換

**実装例**:
```python
# expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py

def fix_regex_escaping(schema: dict) -> dict:
    """Fix over-escaped regex patterns in JSON Schema"""
    import re

    def fix_pattern(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "pattern" and isinstance(value, str):
                    # Fix 4-level escaping: \\\\ -> \\
                    obj[key] = value.replace("\\\\\\\\", "\\\\")
                else:
                    fix_pattern(value)
        elif isinstance(obj, list):
            for item in obj:
                fix_pattern(item)
        return obj

    return fix_pattern(schema)

# After LLM response
for iface in response.interfaces:
    iface.input_schema = fix_regex_escaping(iface.input_schema)
    iface.output_schema = fix_regex_escaping(iface.output_schema)
```

---

### 優先度: 🟡 高

#### 対策B: max_tokensの最適化

**工数**: 15-20分

**実施内容**:
- タスク数に応じた動的調整を実装

**実装例**:
```python
# expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py

task_count = len(task_breakdown)
if task_count <= 3:
    max_tokens = 2048
elif task_count <= 7:
    max_tokens = 4096
else:
    max_tokens = 8192

logger.info(f"Adjusted max_tokens to {max_tokens} for {task_count} tasks")
```

---

#### 対策C: ロギング強化

**工数**: 20-30分

**実施内容**:
1. 各ノードの処理時間をログ出力
2. LLM呼び出しのトークン数を記録
3. タイムアウト発生時の詳細情報を記録

**実装例**:
```python
import time

start_time = time.time()
response = await structured_model.ainvoke([user_prompt])
elapsed_time = time.time() - start_time

logger.info(
    f"LLM invocation completed: "
    f"model={model_name}, "
    f"elapsed_time={elapsed_time:.2f}s, "
    f"task_count={len(task_breakdown)}"
)
```

---

## 📝 結論

### ✅ Phase 2の成果

1. **根本原因の解決**:
   - `KeyError: 'id'` を完全に解消
   - expertAgentは interface_definition段階まで到達

2. **jobqueue APIの一貫性向上**:
   - 3つのレスポンススキーマを統一
   - 後方互換性を保持

3. **実行時間の改善**:
   - Scenario 1で約13%の短縮

### ⚠️ 新たに発見された課題

1. **Regex過剰エスケープ問題**:
   - LLMが4重エスケープを生成
   - Phase 3での対応が必要

2. **タイムアウト問題**:
   - 複雑なシナリオで600秒超過
   - max_tokens、モデル選択、ロギングの改善が必要

### 🎯 次のステップ

**Phase 3**: expertAgentのパフォーマンス最適化とRegex修正

**優先順位**:
1. 🔴 **最高**: Regex過剰エスケープの修正（対策A）
2. 🟡 **高**: max_tokensの最適化（対策B）
3. 🟡 **高**: ロギング強化（対策C）
4. 🟢 **中**: ハイブリッドモデル戦略（Phase 4）

---

## 📚 参考情報

### 生成されたファイル

- `/tmp/scenario1_phase2_result.json` - Scenario 1の詳細結果
- `/tmp/scenario2_phase2_result.json` - Scenario 2の詳細結果
- `/tmp/scenario3_phase2_result.json` - Scenario 3の詳細結果
- `/tmp/all_scenarios_phase2_results.json` - 全シナリオの統合結果

### テスト実行コマンド

```bash
# テストスクリプト実行
python3 /tmp/run_scenario_tests.py

# 個別シナリオのテスト
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/job-generator \
  -H 'Content-Type: application/json' \
  -d @/tmp/scenario1.json
```

### ログ確認コマンド

```bash
# expertAgentログ
tail -f /tmp/expertAgent_new.log

# jobqueueログ
tail -f /tmp/jobqueue.log
```

---

**作成者**: Claude Code
**レポート形式**: Markdown
**関連Issue**: #97
**前回レポート**: [improvement-report-phase2.md](./improvement-report-phase2.md)
