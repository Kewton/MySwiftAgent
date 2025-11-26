"""Prompt templates for multi-candidate requirement generation.

This module provides prompts and utilities for generating multiple
requirement interpretation candidates from user's initial message.

Design philosophy:
- Generate 2 distinct interpretations (A and B)
- Candidates differ in: depth, granularity, automation level
- Each candidate contains 4 aspects: data_source, process, output, schedule
- Confidence scores reflect interpretation certainty
"""

import logging
from typing import Optional

from app.services.prompt_loader import PromptLoader, PromptNotFoundError

logger = logging.getLogger(__name__)

# Load prompt from YAML
_loader = PromptLoader.create_default()
_prompt_data: dict = {}
MULTI_CANDIDATE_SYSTEM_PROMPT: str = ""
_USER_PROMPT_TEMPLATE: str = ""

try:
    _prompt_data = _loader.load_prompt("multi_candidate")
    MULTI_CANDIDATE_SYSTEM_PROMPT = str(_prompt_data.get("system_prompt", ""))
    _USER_PROMPT_TEMPLATE = str(_prompt_data.get("user_prompt_template", ""))
except PromptNotFoundError:
    logger.warning("multi_candidate prompt not found, using fallback")

# Fallback to hardcoded prompt if YAML not found
if not MULTI_CANDIDATE_SYSTEM_PROMPT:
    MULTI_CANDIDATE_SYSTEM_PROMPT = """
あなたは要件解釈の専門家です。
ユーザーの曖昧な入力から、2つの異なる解釈パターン（候補A・候補B）を生成してください。

## 生成ルール
1. 各候補は4つの観点（データソース、処理内容、出力形式、スケジュール）を含む
2. 候補Aと候補Bは**明確に異なる解釈**を提示
3. 各候補には簡潔なタイトル（10文字以内）を付ける
4. 確信度（confidence）は解釈の妥当性を0.0-1.0で表現

## 差別化の観点
- 処理の深さ: 簡易分析 vs 詳細分析
- 出力の粒度: サマリー vs 詳細レポート
- 自動化レベル: オンデマンド vs 定期実行
- データ範囲: 最新のみ vs 過去データ含む

## 候補ID
- candidate_id: "A" または "B" のみ使用
- Aは一般的・シンプルな解釈
- Bはより高度・詳細な解釈

## 確信度（confidence）の目安
- 0.8-1.0: ユーザー入力から明確に推測可能
- 0.6-0.8: 妥当な推測だが確認が必要
- 0.4-0.6: 推測的、複数の可能性あり
- 0.0-0.4: 情報不足で推測が困難

## 出力形式
JSON形式で出力してください。以下の構造を厳守：

{
  "candidates": [
    {
      "candidate_id": "A",
      "title": "簡易分析",
      "data_source": "CSVファイル",
      "process_description": "売上データの月別集計",
      "output_format": "Excelレポート",
      "schedule": "オンデマンド",
      "confidence": 0.85
    },
    {
      "candidate_id": "B",
      "title": "詳細分析",
      "data_source": "データベース",
      "process_description": "売上トレンド分析と予測",
      "output_format": "インタラクティブダッシュボード",
      "schedule": "毎日実行",
      "confidence": 0.75
    }
  ],
  "prompt_for_selection": "どちらの解釈がお望みに近いですか？AまたはBを選んでください。"
}

## 重要な注意事項
- 必ず2つの候補を生成
- 各候補のcandidate_idは "A" または "B"
- confidenceは0.0-1.0の範囲
- ユーザー入力が不明確でも、最善の推測で2候補を提示
"""

if not _USER_PROMPT_TEMPLATE:
    _USER_PROMPT_TEMPLATE = """
## ユーザーの入力
{user_message}

上記の入力から、2つの異なる要件解釈候補を生成してください。
JSON形式で出力してください。
"""


def create_multi_candidate_prompt(
    user_message: str,
    additional_context: Optional[str] = None,
) -> str:
    """Generate user prompt for multi-candidate generation.

    Creates a prompt that instructs the LLM to generate two distinct
    requirement interpretation candidates based on user's initial message.

    Args:
        user_message: User's initial message
        additional_context: Optional additional context to include

    Returns:
        Formatted user prompt string

    Example:
        >>> prompt = create_multi_candidate_prompt("売上データを分析したい")
        >>> print("売上データを分析したい" in prompt)
        True
    """
    # Format the user prompt with the message
    prompt = _USER_PROMPT_TEMPLATE.format(user_message=user_message)

    # Add additional context if provided
    if additional_context:
        prompt = f"{additional_context}\n\n{prompt}"

    return prompt.strip()


def get_system_prompt() -> str:
    """Get the system prompt for multi-candidate generation.

    Returns:
        System prompt string

    Example:
        >>> prompt = get_system_prompt()
        >>> print(len(prompt) > 0)
        True
    """
    return MULTI_CANDIDATE_SYSTEM_PROMPT
