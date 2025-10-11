import os
import tempfile

from openai import OpenAI
from pydub import AudioSegment

from core.logger import getlogger
from core.secrets import resolve_runtime_value

logger = getlogger()


def _resolve_openai_key() -> str:
    api_key = resolve_runtime_value("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")
    return str(api_key)


def tts_old(speech_file_path, _input):
    client = OpenAI(api_key=_resolve_openai_key())
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input=_input,
        instructions="Speak in a cheerful and positive tone.",
    ) as response:
        response.stream_to_file(speech_file_path)


def tts(speech_file_path: str, _input: str):
    """
    テキストを音声に変換し、MP3ファイルとして保存します。
    入力が1000文字を超える場合は1000文字ごとに分割して処理し、最後に結合します。

    Args:
        speech_file_path (str): 保存するMP3ファイルのパス。
        _input (str): 音声に変換するテキスト。
    """
    client = OpenAI(api_key=_resolve_openai_key())
    chunk_size = 1500  # OpenAI TTSの推奨または安全な文字数に調整することを推奨します

    if len(_input) <= chunk_size:
        # 1000文字以下の場合はそのまま処理
        try:
            with client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",  # 最新の推奨モデルを確認してください
                voice="coral",
                input=_input,
                instructions=(
                    "Speak in a cheerful and positive tone."
                ),  # 指示は必要に応じて調整
            ) as response:
                response.stream_to_file(speech_file_path)
            print(f"音声ファイルが '{speech_file_path}' に保存されました。")
        except Exception as e:
            print(f"TTS処理中にエラーが発生しました: {e}")
            if os.path.exists(speech_file_path):
                os.remove(speech_file_path)  # エラー時は中途半端なファイルを削除
    else:
        logger.info(
            f"テキストが {len(_input)} 文字で、{chunk_size} 文字を超えています。分割して処理します。"
        )
        # 1000文字を超える場合は分割して処理
        text_chunks = [
            _input[i : i + chunk_size] for i in range(0, len(_input), chunk_size)
        ]
        temp_audio_files = []
        temp_dir = tempfile.mkdtemp()  # 一時ディレクトリを作成

        try:
            print(f"テキストを {len(text_chunks)} 個のチャンクに分割して処理します...")
            for i, chunk in enumerate(text_chunks):
                temp_speech_file_path = os.path.join(temp_dir, f"temp_audio_{i}.mp3")
                print(
                    f"チャンク {i + 1}/{len(text_chunks)} を処理中: '{chunk[:30]}...'"
                )
                try:
                    with client.audio.speech.with_streaming_response.create(
                        model="gpt-4o-mini-tts",  # 最新の推奨モデルを確認してください
                        voice="coral",
                        input=chunk,
                        instructions=(
                            "Speak in a cheerful and positive tone."
                        ),  # 指示は必要に応じて調整
                    ) as response:
                        response.stream_to_file(temp_speech_file_path)
                    temp_audio_files.append(temp_speech_file_path)
                except Exception as e:
                    print(f"チャンク {i + 1} のTTS処理中にエラーが発生しました: {e}")
                    logger.error(
                        f"チャンク {i + 1} のTTS処理中にエラーが発生しました: {e}"
                    )
                    # エラーが発生したチャンクはスキップするか、全体を中止するか選択
                    # ここではエラーが発生しても処理を続け、生成できたファイルのみ結合します
                    continue

            if not temp_audio_files:
                print("音声ファイルを生成できませんでした。")
                logger.error("音声ファイルを生成できませんでした。")
                return

            # 生成された一時MP3ファイルを結合
            print("一時音声ファイルを結合中...")
            combined_audio = AudioSegment.empty()
            for temp_file in temp_audio_files:
                try:
                    segment = AudioSegment.from_mp3(temp_file)
                    combined_audio += segment
                except Exception as e:
                    logger.error(
                        f"ファイル '{temp_file}' の読み込みまたは結合中にエラー: {e}"
                    )
                    print(f"ファイル '{temp_file}' の読み込みまたは結合中にエラー: {e}")
                    continue

            if len(combined_audio) > 0:
                combined_audio.export(speech_file_path, format="mp3")
                print(
                    f"結合された音声ファイルが '{speech_file_path}' に保存されました。"
                )
            else:
                print("結合する音声がありませんでした。")
                if os.path.exists(speech_file_path):
                    os.remove(speech_file_path)

        finally:
            # 一時ファイルを削除
            print("一時ファイルを削除中...")
            for temp_file in temp_audio_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logger.error(
                            f"一時ファイル '{temp_file}' の削除中にエラー: {e}"
                        )
                        print(f"一時ファイル '{temp_file}' の削除中にエラー: {e}")
            # 一時ディレクトリを削除
            if os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except Exception as e:
                    logger.error(f"一時ディレクトリ '{temp_dir}' の削除中にエラー: {e}")
                    print(f"一時ディレクトリ '{temp_dir}' の削除中にエラー: {e}")
