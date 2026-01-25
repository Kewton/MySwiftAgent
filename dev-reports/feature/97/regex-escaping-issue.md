# Regex過剰エスケープ問題の詳細分析と解決策

**作成日**: 2025-10-20
**対象ブランチ**: `feature/issue/97`
**優先度**: 🔴 最高
**推定工数**: 30-45分

---

## 📋 問題の概要

Phase 2のテストで、Scenario 1が interface_definition段階で以下のエラーにより失敗しました：

```
Interface definition failed: Jobqueue API error (400):
{"detail":"Invalid input_schema: Schema error: \"^[\\\\p{L}\\\\p{N}\\\\s\\\\-\\\\.\\\\'\\\\(\\\\)&]+$\" is not a 'regex'"}
```

**問題の本質**: LLMが生成したJSON SchemaのRegexパターンに **4重のバックスラッシュエスケープ** が含まれており、JSON Schema V7のRegex検証で不正と判定される。

---

## 🔍 根本原因の詳細分析

### 1. エスケープの段階的変換

**正しいエスケープの流れ**:
```
1. Python正規表現: \d{4}-\d{2}-\d{2}
   ↓ (Pythonソース内での表現)
2. Pythonソース: "\\d{4}-\\d{2}-\\d{2}"
   ↓ (JSON文字列への変換)
3. JSON文字列: "\\d{4}-\\d{2}-\\d{2}"  # 2重エスケープ（正しい）
```

**LLMが生成している誤ったエスケープ**:
```
1. LLMの内部表現: \d{4}-\d{2}-\d{2}
   ↓ (誤った2回エスケープ)
2. LLMの出力: "\\\\d{4}-\\\\d{2}-\\\\d{2}"  # 4重エスケープ（誤り）
   ↓ (JSON文字列として解釈)
3. 実際のRegex: \\d{4}-\\d{2}-\\d{2}  # リテラルバックスラッシュ（誤り）
```

### 2. 具体的なエラー箇所

**Scenario 1で生成されたパターン**:
```json
{
  "pattern": "^[\\\\p{L}\\\\p{N}\\\\s\\\\-\\\\.\\\\'\\\\(\\\\)&]+$"
}
```

**意図したパターン**:
```json
{
  "pattern": "^[\\p{L}\\p{N}\\s\\-\\.\\'\\'\\(\\)&]+$"
}
```

**解釈の違い**:
```
4重エスケープ: \\\\p{L}  →  実際のRegex: \\p{L}  →  "リテラル\p{L}"（誤り）
2重エスケープ: \\p{L}    →  実際のRegex: \p{L}   →  "Unicode文字クラスL"（正しい）
```

### 3. なぜLLMが4重エスケープを生成するか

**原因の推測**:
1. **Prompt内の例が誤解を招く**:
   - Phase 1で修正したPrompt例が不十分
   - JSON文字列内のエスケープルールが明確でない

2. **LLMの学習データの影響**:
   - 一部のプログラミング言語（Python heredoc、bash等）では4重エスケープが必要
   - LLMがJSON文字列とそれらを混同している

3. **コンテキストの不足**:
   - "JSON Schema V7のpatternフィールド"という明確な指定が不足
   - 実行環境（Python → JSON → Regex Engine）の説明が不足

---

## 💡 解決策の提案

### 方法1: Prompt改善による予防（推奨）

**実施ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/interface_schema.py`

**改善内容**:

#### A. 明確な説明の追加

```python
5. **Regex pattern記述の注意**:

   【重要】あなたが生成するのは **JSON文字列内のRegexパターン** です。

   **エスケープルール**:
   - `\d`, `\w`, `\s` などの特殊文字は **2重エスケープ**: `\\d`, `\\w`, `\\s`
   - Unicode property escapes (`\p{L}`) も **2重エスケープ**: `\\p{L}`
   - 通常の文字クラス (`[a-z]`, `[0-9]`) は **エスケープ不要**
   - JSON内でエスケープが必要な文字（`"`）は **2重エスケープ**: `\\"`

   **絶対にやってはいけないこと**:
   - ❌ 4重エスケープ: `\\\\d` は間違い！
   - ❌ 6重エスケープ: `\\\\\\d` は間違い！
   - ❌ バックスラッシュを重複させる: `\\\\\\\\` は間違い！

   **正しい例**:
   ```json
   {
     "pattern": "^\\d{4}-\\d{2}-\\d{2}$",           // 正しい: 日付形式（YYYY-MM-DD）
     "pattern": "^[a-zA-Z0-9_]+$",                  // 正しい: 英数字とアンダースコア
     "pattern": "^[\\p{L}\\p{N}\\s\\-\\.]+$",       // 正しい: Unicode文字、数字、空白、ハイフン、ドット
     "pattern": "^https?://[\\w\\-\\.]+(:\\d+)?$"   // 正しい: URL形式
   }
   ```

   **間違った例（絶対に生成しないこと）**:
   ```json
   {
     "pattern": "^\\\\d{4}-\\\\d{2}-\\\\d{2}$",         // ❌ 誤り: 4重エスケープ
     "pattern": "^[\\\\p{L}\\\\p{N}\\\\s]+$",           // ❌ 誤り: Unicode propertyの4重エスケープ
     "pattern": "^\\\\\\\\w+$"                          // ❌ 誤り: 6重エスケープ
   }
   ```
```

#### B. Few-shot例の追加

```python
### 例4: 企業名の入力（Unicode文字対応）

**タスク**: 企業名を入力として受け取る

**入力スキーマ**（正しいRegex）:
```json
{
  "type": "object",
  "properties": {
    "company_name": {
      "type": "string",
      "description": "企業名（日本語、英語、記号を含む）",
      "pattern": "^[\\p{L}\\p{N}\\s\\-\\.\\(\\)&]+$",
      "minLength": 1,
      "maxLength": 200
    }
  },
  "required": ["company_name"],
  "additionalProperties": false
}
```

**説明**:
- `\\p{L}`: Unicode文字（日本語、英語等）を表すため **2重エスケープ**
- `\\p{N}`: Unicode数字を表すため **2重エスケープ**
- `\\s`, `\\-`, `\\.`: 空白、ハイフン、ドットを表すため **2重エスケープ**
- `\\(`, `\\)`: 括弧を表すため **2重エスケープ**
- `&`: エスケープ不要（通常の文字）
```

### 方法2: Response後処理による自動修正（推奨）

**実施ファイル**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py`

**実装コード**:

```python
import re
from typing import Any


def fix_regex_over_escaping(schema: dict[str, Any]) -> dict[str, Any]:
    """Fix over-escaped regex patterns in JSON Schema.

    This function fixes common over-escaping issues in JSON Schema patterns:
    - Quadruple backslash (\\\\) → Double backslash (\\)
    - Sextuple backslash (\\\\\\) → Double backslash (\\)

    Args:
        schema: JSON Schema dictionary

    Returns:
        Fixed JSON Schema dictionary

    Examples:
        >>> schema = {"pattern": "^\\\\\\\\d{4}$"}
        >>> fix_regex_over_escaping(schema)
        {"pattern": "^\\\\d{4}$"}
    """
    def fix_pattern_value(value: str) -> str:
        """Fix a single pattern string."""
        # Fix quadruple backslash → double backslash
        # \\\\d → \\d, \\\\p{L} → \\p{L}, etc.
        fixed = value.replace("\\\\\\\\", "\\\\")

        # Fix sextuple backslash → double backslash (rare but possible)
        fixed = fixed.replace("\\\\\\\\\\\\", "\\\\")

        return fixed

    def traverse_and_fix(obj: Any) -> Any:
        """Recursively traverse and fix all pattern fields."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "pattern" and isinstance(value, str):
                    # Fix the pattern string
                    original = value
                    fixed = fix_pattern_value(value)
                    if original != fixed:
                        logger.debug(
                            f"Fixed over-escaped regex pattern:\n"
                            f"  Before: {original}\n"
                            f"  After:  {fixed}"
                        )
                    obj[key] = fixed
                else:
                    # Recursively process nested objects
                    obj[key] = traverse_and_fix(value)
        elif isinstance(obj, list):
            return [traverse_and_fix(item) for item in obj]

        return obj

    return traverse_and_fix(schema)


# ===== interface_definition_node関数内で使用 =====

async def interface_definition_node(state: JobGeneratorState) -> dict:
    """Define interface schemas for each task with regex over-escaping fix."""

    # ... （既存のコード）

    # Invoke LLM with structured output
    response = await structured_model.ainvoke([user_prompt])

    # Log raw response for debugging
    logger.debug(f"LLM generated {len(response.interfaces)} interfaces")

    # ===== 新規追加: Regex過剰エスケープの自動修正 =====
    for iface in response.interfaces:
        # Fix over-escaped regex patterns in input/output schemas
        iface.input_schema = fix_regex_over_escaping(iface.input_schema)
        iface.output_schema = fix_regex_over_escaping(iface.output_schema)

        # Log fixed schemas for debugging
        logger.debug(
            f"Interface {iface.task_id} ({iface.interface_name}):\n"
            f"  Input Schema: {iface.input_schema}\n"
            f"  Output Schema: {iface.output_schema}"
        )
    # ===== ここまで追加 =====

    # Create InterfaceMasters in jobqueue
    interface_masters = {}
    for interface_def in response.interfaces:
        # ... （既存のコード）
```

### 方法3: JSON Schema検証の緩和（非推奨）

**実施ファイル**: `jobqueue/app/services/interface_validator.py`

**注意**: この方法は根本解決ではなく、一時的な回避策です。

```python
@staticmethod
def validate_json_schema_v7(schema: dict) -> None:
    """Validate JSON Schema V7 format with relaxed regex validation."""

    # ... （既存のコード）

    # Check regex patterns (with relaxed validation)
    def check_patterns(obj: Any, path: str = "root") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}"
                if key == "pattern" and isinstance(value, str):
                    try:
                        # Attempt to compile the regex
                        re.compile(value)
                    except re.error as e:
                        # ===== 新規追加: 4重エスケープを自動修正して再試行 =====
                        try:
                            fixed_pattern = value.replace("\\\\\\\\", "\\\\")
                            re.compile(fixed_pattern)
                            errors.append(
                                f"Regex pattern at {current_path} has over-escaping "
                                f"(auto-fixable): '{value}' → '{fixed_pattern}'"
                            )
                        except re.error:
                            errors.append(
                                f"Invalid regex pattern at {current_path}: "
                                f"'{value}' - {str(e)}"
                            )
                        # ===== ここまで追加 =====
                else:
                    check_patterns(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_patterns(item, f"{path}[{i}]")

    check_patterns(schema)
```

---

## 🎯 推奨する実装順序

### Phase 3-A: 緊急対応（即時実施）

**所要時間**: 15-20分

1. **Response後処理の実装**（方法2）
   - `interface_definition.py` に `fix_regex_over_escaping()` 関数を追加
   - LLM出力後に自動修正を適用
   - デバッグログで修正内容を記録

**メリット**:
- ✅ 即座に問題を解決
- ✅ LLMの出力に依存しない
- ✅ 既存のPromptに影響なし

**デメリット**:
- ⚠️ 根本解決ではない（LLMが誤った出力を生成し続ける）

---

### Phase 3-B: 根本対応（推奨）

**所要時間**: 30-45分

1. **Prompt改善の実装**（方法1）
   - `interface_schema.py` のPromptを大幅に改善
   - 明確な説明、Few-shot例の追加
   - 誤った例の明示的な禁止

2. **検証テストの実施**
   - Scenario 1で再テスト
   - LLMが正しい2重エスケープを生成するか確認

3. **Response後処理の維持**
   - Phase 3-Aで実装した自動修正を継続
   - 二重の安全策として機能

**メリット**:
- ✅ 根本的な解決
- ✅ 将来的なエラーを予防
- ✅ LLMの学習効果

**デメリット**:
- ⚠️ Prompt改善の効果が不確実（LLMの挙動に依存）

---

## 📊 期待される効果

### Phase 3-A（Response後処理のみ）

| 項目 | 改善前 | 改善後 | 効果 |
|------|--------|--------|------|
| **Scenario 1** | interface_definition で失敗 | task_generation まで進行可能 | ✅ |
| **実行時間** | 144秒（失敗） | 200-300秒（推定） | ⚠️ |
| **成功率** | 0% | 50-70%（推定） | ✅ |

### Phase 3-B（Prompt改善 + Response後処理）

| 項目 | 改善前 | 改善後 | 効果 |
|------|--------|--------|------|
| **Scenario 1** | interface_definition で失敗 | 正常完了 | ✅ |
| **実行時間** | 144秒（失敗） | 150-200秒 | ✅ |
| **成功率** | 0% | 80-90% | ✅ |
| **LLM品質** | 4重エスケープ生成 | 2重エスケープ生成 | ✅ |

---

## 🧪 検証方法

### テストケース1: シンプルなパターン

**入力要求**:
```
企業名を入力すると売上情報を返すAPI
```

**期待される出力**（修正前）:
```json
{
  "pattern": "^[\\\\p{L}\\\\p{N}\\\\s]+$"  // ❌ 4重エスケープ
}
```

**期待される出力**（修正後）:
```json
{
  "pattern": "^[\\p{L}\\p{N}\\s]+$"  // ✅ 2重エスケープ
}
```

### テストケース2: 複雑なパターン

**入力要求**:
```
メールアドレスとURLを含むフォームデータを受け取るAPI
```

**期待される出力**（修正前）:
```json
{
  "email": {
    "pattern": "^[\\\\w\\\\-\\\\.]+@[\\\\w\\\\-\\\\.]+\\\\.[a-zA-Z]{2,}$"  // ❌
  },
  "url": {
    "pattern": "^https?://[\\\\w\\\\-\\\\.]+(:\\\\d+)?(/.*)?$"  // ❌
  }
}
```

**期待される出力**（修正後）:
```json
{
  "email": {
    "pattern": "^[\\w\\-\\.]+@[\\w\\-\\.]+\\.[a-zA-Z]{2,}$"  // ✅
  },
  "url": {
    "pattern": "^https?://[\\w\\-\\.]+(:\\d+)?(/.*)?$"  // ✅
  }
}
```

### 検証コマンド

```bash
# Scenario 1の再実行
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/job-generator \
  -H 'Content-Type: application/json' \
  -d '{"user_requirement": "企業名を入力すると売上情報を返すAPI", "max_retry": 3}' \
  --max-time 300 | jq '.status'

# 期待結果: "success" または "completed"
```

---

## 🚀 実装の開始

Phase 3-Aの実装から開始することを推奨します。以下のコマンドで確認できます：

```bash
# 現在のブランチ
git branch

# 変更するファイル
# - expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/interface_definition.py
```

実装後、Scenario 1で再テストして効果を確認します。

---

**作成者**: Claude Code
**レポート形式**: Markdown
**関連Issue**: #97
**関連レポート**:
- [test-results-phase2.md](./test-results-phase2.md)
- [improvement-report-phase2.md](./improvement-report-phase2.md)
