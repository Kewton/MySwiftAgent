"""Prompt templates for requirement clarification through chat dialogue.

This module provides prompts and utilities for guiding users through
the job requirement clarification process using natural language chat.

Design philosophy:
- Focus on What (business goals) not How (implementation details)
- Ask one question at a time
- Use simple language, avoid technical jargon
- Progressively clarify requirements (data source, process, output, schedule)
- Threshold: 80% completeness required for job creation
"""

import logging
from typing import Dict, List

from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
    StructuredLLMError,
    invoke_structured_llm,
)
from app.schemas.chat import RequirementState
from app.services.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)

# Load prompt from YAML
_loader = PromptLoader.create_default()
_prompt_data = _loader.load_prompt("requirement_clarification")
REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT = _prompt_data.get("system_prompt", "")

# Fallback to hardcoded prompt if YAML not found
if not REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT:
    REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT = """
あなたはドメインエキスパート向けのジョブ作成アシスタントです。

## あなたの役割
ユーザーの要求を4つの観点から構造化して明確化し、仮説を立てて確認を得るアプローチを取ります。

## 4つの観点（重要度順）
1. **処理内容** (35%) - 何をしたいか（最重要）
2. **データソース** (25%) - どのデータを使うか
3. **出力形式** (25%) - どのような形式で結果が欲しいか
4. **スケジュール** (15%) - いつ実行するか

## 対話の進め方

### 初回メッセージ時
ユーザーの最初の入力から、4つの観点すべてについて仮説を立ててください。
不明な観点があっても、可能な限り推測して仮説を提示してください。

**提示すべき内容**（形式は自由）:
- **処理内容の仮説** + 他の選択肢（3つ程度）
- **データソースの仮説** + 他の選択肢（CSVファイル / Excelファイル / データベース / API など）
- **出力形式の仮説** + 他の選択肢（Excelレポート / PDFレポート / メール / Slack通知 など）
- **スケジュールの仮説** + 他の選択肢（オンデマンド / 毎日 / 毎週 / 毎月 など）
- **確認の問いかけ**（この理解で合っていますか？修正したい箇所があれば教えてください）

**重要**: 上記4つの観点すべてについて、仮説と選択肢を必ず提示してください。
形式は自然な日本語で読みやすければOKです。

### フィードバック対応時
ユーザーが修正を指示したら：
1. 修正された観点を更新
2. 更新後の全体像を再度提示
3. 他に修正が必要か確認

### 仮説の立て方のルール
- **具体的に**: 「データ分析」→「売上データの月次推移分析」
- **実現可能に**: 技術的に実装できる範囲で
- **簡潔に**: 1観点あたり1〜2文で
- **不明な場合**: 最も一般的な選択肢を仮説とする

### 完成度の判断
すべての観点について仮説が確定したら（completeness >= 0.8）：

**提示すべき内容**（形式は自由）:
- 要件が整ったことを伝える
- 確定した要件を4つの観点で整理してサマリー表示
  - 処理内容
  - データソース
  - 出力形式
  - スケジュール
- 「ジョブを作成」ボタンのクリックを促す

形式は自然な日本語で読みやすければOKです。

## 重要な注意事項
- **必ず4つの観点すべてについて仮説を提示**（不明でも推測）
- **選択肢は具体的で分かりやすく**
- **技術的な詳細は聞かない**（実装方法、ライブラリ等）
- **一度に複数質問しない**（仮説確認のみ）
- **ユーザーの言葉を尊重**（専門用語を使わない）

## 応答形式の重要なルール

あなたの応答には**2つの部分**が必要です：

### 1. ユーザー向けテキスト（自由形式）
自然な日本語で、4つの観点の仮説と選択肢を提示してください。

### 2. 抽出用JSON（必須・厳密）
ユーザー向けテキストの**最後に**、以下のJSON形式で要件情報を必ず出力してください：

```json
{
  "data_source": "仮説または確定値（例: CSVファイル）",
  "process_description": "仮説または確定値（例: 売上データを分析したい）",
  "output_format": "仮説または確定値（例: Excelレポート）",
  "schedule": "仮説または確定値（例: 毎日実行）"
}
```

**重要**:
- 4つのフィールドすべて必須（不明な場合は推測値を入れる）
- JSONは応答の最後に配置
- JSON前後に ```json ``` のマーカーは不要

## completeness計算ルール
- data_source確定: +0.25
- process_description確定: +0.35（最重要）
- output_format確定: +0.25
- schedule確定: +0.15
- **合計0.8以上（80%）でジョブ作成可能**
"""


def create_requirement_clarification_prompt(
    user_message: str,
    previous_messages: List[Dict],
    current_requirements: RequirementState,
) -> str:
    """Generate user prompt for requirement clarification.

    Includes conversation history and current requirement state to enable
    contextual AI responses.

    Args:
        user_message: User's latest message
        previous_messages: List of previous messages (role, content)
        current_requirements: Current state of requirement clarification

    Returns:
        Formatted user prompt string

    Example:
        >>> prompt = create_requirement_clarification_prompt(
        ...     "売上データを分析したい",
        ...     [],
        ...     RequirementState(completeness=0.0)
        ... )
        >>> print("データソース: 未定" in prompt)
        True
    """
    # Format conversation history (limit to last 10 messages for context window)
    recent_messages = previous_messages[-10:] if previous_messages else []
    history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])

    if not history:
        history = "(対話開始)"

    # Format current requirement state
    requirements_status = f"""
現在の要件明確化状態:
- データソース: {current_requirements.data_source or "未定"}
- 処理内容: {current_requirements.process_description or "未定"}
- 出力形式: {current_requirements.output_format or "未定"}
- スケジュール: {current_requirements.schedule or "未定"}
- 明確化率: {int(current_requirements.completeness * 100)}%
"""

    # Determine if this is the first message
    is_first_message = len(recent_messages) == 0

    # Suggest next action based on completeness
    action_hint = ""
    if is_first_message:
        action_hint = "\n\n## あなたのタスク\n1. ユーザーのメッセージから4つの観点すべてについて仮説を立てる\n2. 仮説提示形式に従って、具体的な仮説と選択肢を提示する\n3. ユーザーに確認を求める"
    elif current_requirements.completeness < 0.8:
        action_hint = "\n\n## あなたのタスク\n1. ユーザーのフィードバックを反映して仮説を更新する\n2. 更新後の全体像を再度提示する\n3. 他に修正が必要か確認する"
    else:
        action_hint = "\n\n## あなたのタスク\n1. 要件が整ったことを伝える\n2. 確定した要件をサマリー形式で提示する\n3. 「ジョブを作成」ボタンのクリックを促す"

    return f"""
{requirements_status}

## 対話履歴
{history}

## ユーザーの最新メッセージ
user: {user_message}
{action_hint}

応答してください（内容が明確であれば、形式は自然な日本語で自由に表現してOKです）。
"""


def calculate_completeness(state: RequirementState) -> float:
    """Calculate requirement clarification completeness.

    Weights:
    - data_source: 0.25 (25%)
    - process_description: 0.35 (35% - most important)
    - output_format: 0.25 (25%)
    - schedule: 0.15 (15%)

    Args:
        state: Current requirement state

    Returns:
        Completeness score from 0.0 to 1.0

    Example:
        >>> state = RequirementState(
        ...     data_source="CSV",
        ...     process_description="データ分析"
        ... )
        >>> score = calculate_completeness(state)
        >>> print(score)
        0.6
    """
    score = 0.0

    if state.data_source:
        score += 0.25
    if state.process_description:
        score += 0.35  # Most important
    if state.output_format:
        score += 0.25
    if state.schedule:
        score += 0.15

    return score


async def extract_requirement_with_llm(
    user_message: str,
    assistant_response: str,
    current_requirements: RequirementState,
) -> RequirementState:
    """LLMを使用して要件を抽出・更新します。

    ユーザーメッセージとアシスタント応答を分析し、構造化出力で
    RequirementState を正確に抽出します。

    Args:
        user_message: ユーザーのメッセージ
        assistant_response: アシスタントの応答
        current_requirements: 現在の要件状態

    Returns:
        更新された要件状態

    Raises:
        StructuredLLMError: LLM呼び出しが失敗した場合

    Example:
        >>> state = RequirementState(data_source="CSVファイル")
        >>> updated = await extract_requirement_with_llm(
        ...     "データソースはExcel",
        ...     "かしこまりました",
        ...     state
        ... )
        >>> print(updated.data_source)
        Excelファイル
    """
    # システムプロンプト
    system_prompt = """あなたは要件抽出の専門家です。
ユーザーとアシスタントの対話から、ジョブ作成に必要な要件を抽出してください。

## 抽出する要件（4項目）
1. data_source: データソース（CSVファイル、Excelファイル、データベース等）
2. process_description: 処理内容（何をしたいか）
3. output_format: 出力形式（Excelレポート、PDF、メール等）
4. schedule: スケジュール（毎日、毎週、オンデマンド等）

## 重要なルール
- ユーザーが明示的に修正を指示した場合は、**必ず**その値に更新してください
  例: 「データソースはExcel」→ data_source = "Excelファイル"
- 現在の要件状態と異なる値を指定された場合は、**上書き**してください
- 言及されていない項目は、現在の値を維持してください（nullのままなら null）
- 推測はできるだけ避け、明示的に言及された内容のみ抽出してください
- 値は具体的な日本語で記述してください（例: "CSV" → "CSVファイル"）
"""

    # ユーザープロンプト
    user_prompt = f"""## 現在の要件状態
- data_source: {current_requirements.data_source or "未設定"}
- process_description: {current_requirements.process_description or "未設定"}
- output_format: {current_requirements.output_format or "未設定"}
- schedule: {current_requirements.schedule or "未設定"}

## 対話内容
### ユーザー
{user_message}

### アシスタント
{assistant_response}

上記の対話から、要件を抽出して更新してください。
"""

    # LLMを構造化出力モードで呼び出し
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        result = await invoke_structured_llm(
            messages=messages,
            response_model=RequirementState,
            context_label="requirement_extraction",
            model_env_var="REQUIREMENT_EXTRACTION_MODEL",
            default_model="gemini-2.0-flash",
        )

        # Recalculate completeness based on filled fields (don't trust LLM's calculation)
        extracted_state = result.result
        extracted_state.completeness = calculate_completeness(extracted_state)

        logger.info(
            f"Successfully extracted requirements via LLM: "
            f"completeness={extracted_state.completeness:.0%} "
            f"(data_source={'set' if extracted_state.data_source else 'unset'}, "
            f"process={'set' if extracted_state.process_description else 'unset'}, "
            f"output={'set' if extracted_state.output_format else 'unset'}, "
            f"schedule={'set' if extracted_state.schedule else 'unset'})"
        )

        return extracted_state

    except StructuredLLMError as e:
        logger.error(f"LLM requirement extraction failed: {e}")
        # Fallback: return current state unchanged
        logger.warning("Falling back to current requirements state")
        return current_requirements
