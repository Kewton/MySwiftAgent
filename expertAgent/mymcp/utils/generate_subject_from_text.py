from core.config import settings
from core.logger import getlogger

# import google.generativeai as genai
from mymcp.utils.execllm import execLlmApi

logger = getlogger()

# def getmodel():
#     # --- 1. APIクライアントの準備 ---
#     try:
#         # 環境変数などからAPIキーを取得
#         GOOGLE_API_KEY = settings.GOOGLE_API_KEY
#         if not GOOGLE_API_KEY:
#             raise ValueError("環境変数 'GOOGLE_API_KEY' が設定されていません。")

#         genai.configure(api_key=GOOGLE_API_KEY)

#         # 使用するモデルを選択 (例: gemini-1.5-flash)
#         # より高性能なモデルが必要な場合は 'gemini-1.5-pro-latest' など
#         model = genai.GenerativeModel('gemini-1.5-flash')

#         return model

#     except Exception as e:
#         print(f"Gemini API の初期化中にエラーが発生しました: {e}")
#         exit()


def generate_subject_from_text(text_body: str, max_length: int = 20) -> str:
    """
    Gemini API を使用して、与えられたテキスト本文からメールの件名を生成します。

    Args:
        text_body (str): 件名を生成したいテキスト本文。
        max_length (int): 生成する件名の最大文字数（目安）。

    Returns:
        str: 生成された件名。エラーの場合はエラーメッセージ。
    """
    if not text_body:
        return "エラー: テキスト本文が空です。"

    # --- 2. プロンプトの設計 ---
    prompt = f"""以下の文章の内容を正確に反映し、かつ簡潔で分かりやすい日本語の件名を1つだけ生成してください。
    件名は最大{max_length}文字程度にしてください。件名以外の余計な言葉（例：「はい、件名は～です」など）は含めないでください。

    --- 本文 ---
    {text_body}
    --- ここまで ---

    生成された件名:
    """

    # --- 3. API 呼び出し ---
    try:
        # 生成設定 (温度を低めに設定して一貫性を高める)
        # generation_config = genai.types.GenerationConfig(
        #     temperature=0.2,
        #     max_output_tokens=50 # 件名なので短めに設定
        # )

        # print("Generating subject...") # デバッグ用
        # model = getmodel()
        # response = model.generate_content(
        #     prompt,
        #     generation_config=generation_config
        # )
        # print("Generation complete.") # デバッグ用

        # # --- 4. 結果の取得と後処理 ---
        # generated_subject = response.text.strip()

        _messages = [
            {"role": "system", "content": "あなたは世界一のポッドキャスターです"},
            {"role": "user", "content": prompt},
        ]

        # 前後に不要な引用符などが付いていたら削除
        # generated_subject = generated_subject.strip('"`\'')
        generated_subject = execLlmApi(settings.OLLAMA_DEF_SMALL_MODEL, _messages)

        # 必要に応じてさらに後処理 (例: 長すぎる場合の切り詰め)
        if len(generated_subject) > max_length * 1.5:  # 多少のオーバーは許容
            logger.warning(
                f"Generated subject is longer than expected ({len(generated_subject)} chars). Truncating."
            )
            # 単純に切り詰めるか、再度生成を試みるかなどの戦略が必要
            generated_subject = generated_subject[:max_length] + "..."

        # 空の結果チェック
        if not generated_subject:
            return "エラー: 件名を生成できませんでした（空の結果）。"

        return generated_subject

    except Exception as e:
        logger.error(f"Error during subject generation: {e}", exc_info=True)
        # response オブジェクトが存在すれば、ブロック理由などを確認できる場合がある
        # try:
        #     if response and response.prompt_feedback:
        #         print(f"Prompt Feedback: {response.prompt_feedback}")
        #     # Gemini API の safety ratings によりブロックされた場合など
        #     if response and response.candidates and response.candidates[0].finish_reason.name != "STOP":
        #         print(f"Generation finished with reason: {response.candidates[0].finish_reason.name}")
        #         if response.candidates[0].safety_ratings:
        #             print(f"Safety Ratings: {response.candidates[0].safety_ratings}")

        # except Exception as inner_e:
        #     print(f"Error details unavailable or failed to access: {inner_e}")

        return f"エラー: 件名生成中にエラーが発生しました: {e}"
