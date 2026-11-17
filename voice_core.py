# [셀 02] 음성 인식 STT / 답변 낭독 TTS | Ctrl+F로 [수정 포인트 ...] 검색
"""음성 비서 3차 코드의 Whisper STT/TTS 중 학습 도우미에 필요한 기능만 추출.

[셀 03] 이메일 전송·상시 마이크 감시·호출어·외부 DB는 필요하지 않아 포함하지 않습니다.
마이크 녹음은 Streamlit 기본 st.audio_input으로 수행하므로 별도 JS 컴포넌트가 없습니다.
"""
import io
import re
from openai import OpenAI

# [수정 포인트 V01] 필요하면 음성 모델·목소리만 여기서 변경합니다.
STT_MODEL = "whisper-1"
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "marin"
MAX_SPEECH_LENGTH = 3000


def transcribe_audio(audio_bytes, api_key):
    """브라우저에서 녹음한 WAV bytes → 한국어 텍스트."""
    if not audio_bytes:
        raise ValueError("녹음된 음성이 없습니다.")
    buffer = io.BytesIO(audio_bytes)
    buffer.name = "aivle_question.wav"  # Whisper가 파일 형식을 알 수 있게 확장자를 지정
    client = OpenAI(api_key=api_key, timeout=45)
    result = client.audio.transcriptions.create(model=STT_MODEL, file=buffer, language="ko")
    return (result.text or "").strip()


def clean_speech_text(text):
    """답변 화면의 마크다운과 근거 표시를 제거해 자연스러운 낭독용 문장으로 변환."""
    text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", str(text))
    text = re.sub(r"\[(?:D\d+|[PEORTB]\d{2})\]", "", text)
    text = re.sub(r"[*_`#]", "", text)
    text = re.sub(r"(?m)^\s*[-•]\s*", "", text)
    return " ".join(text.split()).strip()[:MAX_SPEECH_LENGTH]


def synthesize_answer(text, api_key):
    """채팅 답변을 MP3 오디오 bytes로 생성. 요청 시에만 호출되어 불필요한 과금을 방지."""
    speech_text = clean_speech_text(text)
    if not speech_text:
        raise ValueError("읽을 답변이 없습니다.")
    client = OpenAI(api_key=api_key, timeout=60)
    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=speech_text,
        response_format="mp3",
        instructions="한국어로 친절하고 자연스러운 학습 도우미처럼 차분한 해요체로 설명하세요. "
                     "입력에 없는 사실, 인사말, 웃음소리를 덧붙이지 마세요.",
    )
    return response.content
