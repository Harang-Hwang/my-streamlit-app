# [셀 02] 음성 인식 STT / 답변 낭독 TTS — 환경설정과 연결
"""사용자가 요청한 경우에만 음성 API를 호출합니다."""
import io
import re
from openai import OpenAI

STT_MODELS = ("whisper-1", "gpt-4o-mini-transcribe")
TTS_MODELS = ("gpt-4o-mini-tts", "tts-1", "tts-1-hd")
ALL_VOICES = ("marin", "cedar", "alloy", "ash", "ballad", "coral", "echo", "fable",
              "nova", "onyx", "sage", "shimmer", "verse")
CLASSIC_VOICES = ("alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer")
MAX_SPEECH_LENGTH = 3000


def transcribe_audio(audio_bytes, api_key, model="whisper-1"):
    if not audio_bytes: raise ValueError("녹음된 음성이 없습니다.")
    if model not in STT_MODELS: raise ValueError("지원하지 않는 음성 인식 모델입니다.")
    buffer = io.BytesIO(audio_bytes)
    buffer.name = "aivle_question.wav"
    client = OpenAI(api_key=api_key, timeout=45)
    result = client.audio.transcriptions.create(model=model, file=buffer, language="ko")
    return (result.text or "").strip()


def clean_speech_text(text):
    text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", str(text))
    text = re.sub(r"\[(?:D\d+|[PEORTB]\d{2})\]", "", text)
    text = re.sub(r"[*_`#]", "", text)
    text = re.sub(r"(?m)^\s*[-•]\s*", "", text)
    return " ".join(text.split()).strip()[:MAX_SPEECH_LENGTH]


def synthesize_answer(text, api_key, model="gpt-4o-mini-tts", voice="marin", speed=1.0):
    """음성 모델·목소리·속도 지정. 답변의 사실관계를 바꾸지 않습니다."""
    speech_text = clean_speech_text(text)
    if not speech_text: raise ValueError("읽을 답변이 없습니다.")
    if model not in TTS_MODELS: raise ValueError("지원하지 않는 음성 합성 모델입니다.")
    choices = ALL_VOICES if model == "gpt-4o-mini-tts" else CLASSIC_VOICES
    if voice not in choices: raise ValueError("선택한 모델에서 지원하지 않는 목소리입니다.")
    speed = float(speed)
    if not 0.25 <= speed <= 4.0: raise ValueError("속도는 0.25~4.0 사이여야 합니다.")
    client = OpenAI(api_key=api_key, timeout=60)
    kwargs = dict(model=model, voice=voice, input=speech_text, response_format="mp3", speed=speed)
    if model == "gpt-4o-mini-tts":
        kwargs["instructions"] = ("한국어 문장을 또렷하고 자연스럽게 읽으세요. "
            "원문에 없는 사실이나 인사말, 웃음소리를 덧붙이지 마세요.")
    response = client.audio.speech.create(**kwargs)
    return response.content
