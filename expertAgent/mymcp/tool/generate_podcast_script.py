from core.logger import getlogger
from mymcp.tool.tts_and_upload_drive import tts_and_upload_drive
from mymcp.utils.execllm import execLlmApi
from mymcp.utils.generate_subject_from_text import generate_subject_from_text

logger = getlogger()


def generate_podcast_mp3_and_upload(
    topic_details: str, model_name: str = "gpt-4o-mini", subject_max_length: int = 25
) -> str:
    """
    与えられたトピック詳細情報からポッドキャスト台本を生成し、
    その内容から件名を生成、テキストをMP3音声に変換してGoogle Driveにアップロードします。

    Args:
        topic_details (str): ポッドキャストのトピック、キーポイント、構成案などの詳細情報。
        model_name (str): 台本生成に使用するOpenAIモデル名 (デフォルト: gpt-4o)。
        subject_max_length (int): 生成する件名の最大文字数 (デフォルト: 25)。

    Returns:
        str: Google Driveへのアップロード結果を示すメッセージまたはファイルURL。
    """
    logger.info("generate_podcast_mp3_and_uploadを実行します")
    logger.info(f"Generating script for MP3 with model: {model_name}")
    logger.debug(f"Topic details length: {len(topic_details)}, Subject max length: {subject_max_length}")

    # 1. 台本生成
    script = generate_podcast_script(model_name=model_name, input_info=topic_details)

    if not script or not isinstance(script, str) or len(script.strip()) == 0:
        logger.error("台本の生成に失敗したか、内容が空です")
        return "エラー: 台本の生成に失敗したか、内容が空です。"

    logger.info(f"Script generated successfully, length: {len(script)}")

    # 2. 件名生成
    subject = generate_subject_from_text(script, subject_max_length)
    logger.info(f"Subject generated: {subject}")

    # 3. 音声化とアップロード
    try:
        upload_result = tts_and_upload_drive(subject, script)
        logger.info(f"TTS and upload completed: {upload_result}")
        return upload_result
    except Exception as e:
        logger.error(f"Error during TTS/Upload: {e}", exc_info=True)
        return f"エラー: 音声化またはアップロード中に問題が発生しました - {e}"


def generate_podcast_script(
    input_info: str, model_name: str = "gpt-4o-mini"
):  # model_name を引数に追加
    """指定された情報とモデル名からポッドキャスト台本を生成する"""
    _input = f"""
    あなたは、複数の情報源からのデータを統合してポッドキャスト台本を作成するツールです。
    以下の入力情報と指示に基づいて、指定されたトピックに関する一貫性のある台本テキストのみを出力してください。
    なお、AIにより音声化することを想定した改行としてください。

    # 1. 入力情報ソース
    {input_info}

    # 2. ポッドキャストパラメータ
    * **tone:** 深掘り討論

    # 3. 出力指示
    **台本構成:** 抽出・統合した情報に基づき、導入（トピックと情報源の概要説明）、本編（キーポイントの議論・展開）、結論（まとめ、考察）を含む一貫性のある台本を作成します。

    # 生成開始
    """

    _messages = [
        {"role": "system", "content": "あなたは世界一のポッドキャスターです"},
        {"role": "user", "content": _input},
    ]

    return execLlmApi(model_name, _messages)
