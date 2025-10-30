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

from typing import List, Dict
from app.schemas.chat import RequirementState


REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT = """
あなたはドメインエキスパート向けのジョブ作成アシスタントです。

## あなたの役割
1. ユーザーの曖昧な要求を段階的に明確化する
2. 技術的な詳細ではなく、ビジネス上の目的（What）に焦点を当てる
3. 必要最小限の情報を収集し、実装方法（How）は自動で決定する

## 明確化すべき要件
以下の4つの要件を順番に明確化してください：

1. **データソース** (重要度: 25%)
   - どのデータを使うか
   - 例: CSVファイル、Excelファイル、データベース、Google Sheets、API

2. **処理内容** (重要度: 35% - 最重要)
   - 何をしたいか
   - 例: データ分析、レポート生成、メール送信、通知、集計

3. **出力形式** (重要度: 25%)
   - どのような形式で結果が欲しいか
   - 例: Excelレポート、PDFドキュメント、メール、Slack通知、JSON API

4. **スケジュール** (重要度: 15%)
   - いつ実行するか
   - 例: オンデマンド、毎日朝9時、毎週月曜日、毎月1日

## 対話のガイドライン

### 質問の仕方
- **一度に1つの質問** をする（複数質問は避ける）
- **専門用語を避け**、わかりやすい言葉を使う
- ユーザーが迷っている場合は**選択肢を提示**する
- 具体例を示して理解を助ける

### 質問の順序
1. まず処理内容を聞く（最重要）
2. 次にデータソースを聞く
3. 出力形式を聞く
4. 最後にスケジュールを聞く

### 応答の形式
- 自然な日本語で会話する
- 箇条書きは最小限に
- ユーザーの回答を確認・要約する
- 次に何を聞くか明示する

### completeness計算ルール
- data_source明確: +0.25
- process_description明確: +0.35（最重要）
- output_format明確: +0.25
- schedule明確: +0.15
- **合計0.8以上（80%）でジョブ作成可能**

### 明確化完了の判断
completenessが0.8以上になったら、以下のように提案してください：

「要件が整いました！以下の内容でジョブを作成しますか？

📋 要件サマリー
- データソース: [X]
- 処理内容: [Y]
- 出力形式: [Z]
- スケジュール: [W]

「ジョブを作成」ボタンをクリックしてください。」

## 注意事項
- 実装方法（プログラミング言語、ライブラリ等）は聞かない
- APIの技術的詳細は聞かない
- ユーザーが技術的な質問をしても、ビジネス要件に誘導する
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
    history = "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in recent_messages]
    )

    if not history:
        history = "(対話開始)"

    # Format current requirement state
    requirements_status = f"""
現在の要件明確化状態:
- データソース: {current_requirements.data_source or '未定'}
- 処理内容: {current_requirements.process_description or '未定'}
- 出力形式: {current_requirements.output_format or '未定'}
- スケジュール: {current_requirements.schedule or '未定'}
- 明確化率: {int(current_requirements.completeness * 100)}%
"""

    # Suggest next question if completeness < 80%
    next_question_hint = ""
    if current_requirements.completeness < 0.8:
        if not current_requirements.process_description:
            next_question_hint = "\n（ヒント: まず処理内容を聞きましょう）"
        elif not current_requirements.data_source:
            next_question_hint = "\n（ヒント: 次はデータソースを聞きましょう）"
        elif not current_requirements.output_format:
            next_question_hint = "\n（ヒント: 次は出力形式を聞きましょう）"
        elif not current_requirements.schedule:
            next_question_hint = "\n（ヒント: 最後にスケジュールを聞きましょう）"

    return f"""
{requirements_status}{next_question_hint}

## 対話履歴
{history}

## ユーザーの最新メッセージ
user: {user_message}

## あなたのタスク
1. ユーザーの最新メッセージから要件を抽出する
2. 不明な点があれば1つ質問を返す（複数質問禁止）
3. 要件が十分明確（80%以上）なら、ジョブ作成を提案する
4. 自然な日本語で応答する

応答してください。
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


def extract_requirement_from_message(
    user_message: str, assistant_response: str, current: RequirementState
) -> RequirementState:
    """Extract requirement information from conversation messages.

    This is a simple keyword-based extraction for Phase 1.
    Future phases will use LLM structured output for better accuracy.

    Args:
        user_message: User's message
        assistant_response: Assistant's response
        current: Current requirement state

    Returns:
        Updated requirement state

    Example:
        >>> state = RequirementState(completeness=0.0)
        >>> updated = extract_requirement_from_message(
        ...     "CSVファイルを使います",
        ...     "かしこまりました",
        ...     state
        ... )
        >>> print(updated.data_source)
        CSVファイル
    """
    updated = current.model_copy()

    # Combine both messages for analysis
    combined_text = f"{user_message} {assistant_response}"

    # Simple keyword-based extraction
    # Data source
    if not updated.data_source:
        if "CSV" in combined_text or "csv" in combined_text:
            updated.data_source = "CSVファイル"
        elif "Excel" in combined_text or "excel" in combined_text or "エクセル" in combined_text:
            updated.data_source = "Excelファイル"
        elif "データベース" in combined_text or "DB" in combined_text or "PostgreSQL" in combined_text or "MySQL" in combined_text:
            updated.data_source = "データベース"
        elif "Google Sheets" in combined_text or "Googleスプレッドシート" in combined_text:
            updated.data_source = "Google Sheets"
        elif "API" in combined_text:
            updated.data_source = "API"

    # Process description (extract from user message mainly)
    if not updated.process_description and len(user_message) > 5:
        # Simple heuristic: if user message mentions action verbs
        action_keywords = ["分析", "集計", "生成", "送信", "通知", "処理", "計算", "作成"]
        if any(keyword in user_message for keyword in action_keywords):
            updated.process_description = user_message[:100]  # Limit length

    # Output format
    if not updated.output_format:
        if "Excel" in combined_text and "レポート" in combined_text:
            updated.output_format = "Excelレポート"
        elif "PDF" in combined_text:
            updated.output_format = "PDFドキュメント"
        elif "メール" in combined_text or "email" in combined_text:
            updated.output_format = "メール"
        elif "Slack" in combined_text:
            updated.output_format = "Slack通知"
        elif "JSON" in combined_text or "API" in combined_text:
            updated.output_format = "JSON API"

    # Schedule
    if not updated.schedule:
        if "毎日" in combined_text:
            updated.schedule = "毎日実行"
        elif "毎週" in combined_text:
            updated.schedule = "毎週実行"
        elif "毎月" in combined_text:
            updated.schedule = "毎月実行"
        elif "オンデマンド" in combined_text or "手動" in combined_text:
            updated.schedule = "オンデマンド実行"

    # Recalculate completeness
    updated.completeness = calculate_completeness(updated)

    return updated
