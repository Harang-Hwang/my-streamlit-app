# [셀 03] 공통 UI, 디자인, 사용자 설정, 질문 데이터
"""AIVLE Guide 7차 통합본 — 학습 시간표와 RAG 챗봇."""
import calendar
import csv
import hashlib
import html
import io
import json
import os
import re
import sqlite3
import tempfile
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

st.set_page_config(
    page_title="AIVLE Guide | 에이블스쿨 학습 도우미",
    page_icon="🎓", layout="wide", initial_sidebar_state="expanded",
)

def today_kst():
    return datetime.now(ZoneInfo("Asia/Seoul")).date()

S = st.session_state
DEFAULT_MENU = ["AI에게 질문하기", "홈", "에이블스쿨이란?", "노하우", "학습전략", "환경설정"]
LOGO_URL = "https://raw.githubusercontent.com/Jangrae/img/master/aivle.png"
DEFAULTS = {
    "page": "홈", "messages": [], "pdf_hash": None, "pdf_name": None,
    "pdf_bytes": None, "source_choice": "첨부 PDF", "feedback": {}, "show_popular": True,
    "weekly_hours": 8, "level": "기초", "goal": "Python·데이터 분석 기초 익히기",
    "days": {"월":1.0,"화":1.0,"수":1.0,"목":1.0,"금":1.0,"토":2.0,"일":1.0},
    "study_checks": {}, "study_logs": [], "study_events": [], "next_week_focus": "",
    "calendar_anchor": today_kst(), "calendar_view": "월", "audio_responses": {},
    "answer_format": "표준", "answer_tone": "자신감을 주는", "tts_model": "gpt-4o-mini-tts",
    "tts_voice": "marin", "tts_speed": 1.0, "stt_model": "whisper-1",
    "theme_mode": "시스템", "menu_order": list(DEFAULT_MENU), "chat_height": 500,
}
for key, default in DEFAULTS.items():
    if key not in S:
        S[key] = default
# 구버전의 메뉴 순서가 남아 있어도 제거된 문의 메뉴로 이동하지 않도록 정리
S.menu_order = ["AI에게 질문하기"] + [x for x in S.menu_order if x in DEFAULT_MENU and x != "AI에게 질문하기"]
if set(S.menu_order) != set(DEFAULT_MENU):
    S.menu_order = list(DEFAULT_MENU)
if S.page not in DEFAULT_MENU:
    S.page = "AI에게 질문하기"

# [UI-S01] Streamlit의 정적 테마를 재설정하는 대신 앱 전체 색을 CSS로 전환합니다.
# 시스템 선택 시 브라우저/OS의 prefers-color-scheme을 따릅니다.
LIGHT = {"bg":"#FFFFFF", "side":"#FFFFFF", "surface":"#FFFFFF", "text":"#24332F",
         "sub":"#647771", "border":"#E5ECE8", "hero_a":"#FFFFFF", "hero_b":"#FFFFFF",
         "lightbtn":"#F2F6F4", "soft":"#F5F8F6"}
DARK = {"bg":"#111B1A", "side":"#172622", "surface":"#22302C", "text":"#E9F4EF",
        "sub":"#B2C9BF", "border":"#476056", "hero_a":"#27493D", "hero_b":"#1A2D27",
        "lightbtn":"#2A463A", "soft":"#20382E"}

def css_vars(palette):
    return "".join(f"--guide-{key.replace('_','-')}:{value};" for key,value in palette.items())

if S.theme_mode == "다크":
    vars_css = f":root {{{css_vars(DARK)}}}"
elif S.theme_mode == "라이트":
    vars_css = f":root {{{css_vars(LIGHT)}}}"
else:
    vars_css = (f":root {{{css_vars(LIGHT)}}} "
                f"@media (prefers-color-scheme:dark) {{:root {{{css_vars(DARK)}}}}}")

st.markdown("<style>" + vars_css + """
/* 공통: 여백을 충분히 확보하고 카드·제목·선 두께를 통일 */
.stApp, [data-testid="stAppViewContainer"] {background:var(--guide-bg)!important;color:var(--guide-text)!important;}
[data-testid="stMainBlockContainer"] {
    max-width: 1220px !important;
    padding-top: 3rem !important;
    padding-bottom: 3rem !important;
}
[data-testid="stSidebar"] {background:var(--guide-side)!important;color:var(--guide-text)!important;}
.stApp h1,.stApp h2,.stApp h3,.stApp p,.stApp li,.stApp label,
.stApp [data-testid="stMarkdownContainer"] {color:var(--guide-text);}
.stApp h1 {letter-spacing:-.035em;}
.stApp [data-testid="stCaptionContainer"] {color:var(--guide-sub)!important;}
.stApp [data-testid="stVerticalBlockBorderWrapper"] > div,
.stApp [data-testid="stExpander"],.stApp [data-testid="stChatMessage"] {
 border-color:var(--guide-border)!important;}
.stApp input,.stApp textarea,.stApp [data-baseweb="select"] > div {
 background:var(--guide-surface)!important;color:var(--guide-text)!important;
 border-color:var(--guide-border)!important;}
.hero {background:var(--guide-hero-b);border:1px solid var(--guide-border);
 border-radius:16px;padding:25px 30px;margin:4px 0 18px;}
.hero small {color:var(--guide-sub);letter-spacing:1.2px;font-weight:700;}
.hero h1 {margin:7px 0;font-size:30px;color:var(--guide-text)!important;}
.hero p {color:var(--guide-sub)!important;font-size:15px;line-height:1.65;margin:0;}
.panel {border:1px solid var(--guide-border);border-radius:12px;
 background:var(--guide-surface);padding:17px;min-height:110px;}
.panel strong {color:var(--guide-text);}
.panel p {font-size:14px;line-height:1.55;margin:9px 0 0;}
.muted {font-size:13px;color:var(--guide-sub);}
/* 주요 버튼: 글자 항상 흰색, Hover 색 반전 없이 살짝 확대 */
.stApp button[kind="primary"],.stApp button[data-testid="stBaseButton-primary"] {
 background:#146F58!important;border:1px solid #146F58!important;color:#FFFFFF!important;
 transition:transform .16s ease,box-shadow .16s ease!important;}
.stApp button[kind="primary"] *, .stApp button[data-testid="stBaseButton-primary"] * {
 color:#FFFFFF!important;}
.stApp button[kind="primary"]:hover,.stApp button[kind="primary"]:focus,
.stApp button[kind="primary"]:active,.stApp button[data-testid="stBaseButton-primary"]:hover,
.stApp button[data-testid="stBaseButton-primary"]:focus,.stApp button[data-testid="stBaseButton-primary"]:active {
 background:#146F58!important;border-color:#146F58!important;color:#FFFFFF!important;
 transform:scale(1.018);box-shadow:0 3px 11px rgba(7,84,61,.14)!important;}
.stApp button[kind="primary"]:hover *, .stApp button[kind="primary"]:focus *,
.stApp button[kind="primary"]:active * {color:#FFFFFF!important;}
/* 사이드바: 현재 메뉴와 AI 메뉴를 명확하지만 단정하게 구분 */
[data-testid="stSidebar"] .stButton button {text-align:left;justify-content:flex-start;
 background:transparent;border:0;border-radius:9px;box-shadow:none;
 color:var(--guide-text);font-weight:600;padding:9px 12px;min-height:41px;}
[data-testid="stSidebar"] .stButton button:hover {background:var(--guide-lightbtn)!important;}
[data-testid="stSidebar"] .stButton button[kind="primary"] {background:var(--guide-lightbtn)!important;
 color:var(--guide-text)!important;border:0!important;transform:none!important;box-shadow:none!important;}
[data-testid="stSidebar"] .stButton button[kind="primary"] * {color:var(--guide-text)!important;}
[data-testid="stSidebar"] .st-key-nav_ai button,
[data-testid="stSidebar"] .st-key-nav_ai button:hover,
[data-testid="stSidebar"] .st-key-nav_ai button:focus,
[data-testid="stSidebar"] .st-key-nav_ai button:active {
 background:#146F58!important;color:#FFFFFF!important;border:1px solid #146F58!important;
 font-weight:800!important;box-shadow:none!important;min-height:49px!important;}
[data-testid="stSidebar"] .st-key-nav_ai button * {color:#FFFFFF!important;}
[data-testid="stSidebar"] .st-key-nav_ai button:hover {transform:scale(1.015)!important;}
/* 추천질문: 클릭 후에도 같은 연한 색을 유지 */
.st-key-recs_full button,.st-key-recs_popup button,
.st-key-recs_full button:focus,.st-key-recs_popup button:focus,
.st-key-recs_full button:active,.st-key-recs_popup button:active,
.st-key-recs_full button:hover,.st-key-recs_popup button:hover {
 background:var(--guide-lightbtn)!important;color:var(--guide-text)!important;
 border:1px solid var(--guide-border)!important;box-shadow:none!important;outline:0!important;}
.st-key-recs_full button:hover,.st-key-recs_popup button:hover {transform:scale(1.012);}
/* 일정 저장 및 AI 채팅 전송: Streamlit primaryFormSubmit 포함, 항상 흰 글씨 */
.stApp [data-testid="stFormSubmitButton"] button[kind="primary"],
.stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"],
.stApp [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"],
.stApp [data-testid="stFormSubmitButton"] button[kind="primary"]:is(:hover,:focus,:active),
.stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:is(:hover,:focus,:active),
.stApp [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"]:is(:hover,:focus,:active) {
 background:#146F58!important;border:1px solid #146F58!important;
 color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
 transition:transform .16s ease,box-shadow .16s ease!important;
}
.stApp [data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
.stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover,
.stApp [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
 transform:scale(1.018)!important;box-shadow:0 3px 11px rgba(7,84,61,.14)!important;
}
.stApp [data-testid="stFormSubmitButton"] button:is([kind="primary"],[kind="primaryFormSubmit"],[data-testid="stBaseButton-primaryFormSubmit"]) :is(p,span,div),
.stApp [data-testid="stFormSubmitButton"] button:is([kind="primary"],[kind="primaryFormSubmit"],[data-testid="stBaseButton-primaryFormSubmit"]):is(:hover,:focus,:active) :is(p,span,div) {
 color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
/* 비활성 전송 버튼에도 흰 글씨 유지 */
.stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:disabled,
.stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:disabled * {
 color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
/* 플로팅 AI 버튼: 조금 더 작게, 위로 이동, 글자는 더 크게 */
.st-key-chat_float {position:fixed;right:25px;bottom:50px;z-index:9998;width:56px;}
.st-key-chat_float button,.st-key-chat_float button:hover,.st-key-chat_float button:focus {
 width:56px!important;height:56px!important;min-height:56px!important;
 border:0!important;border-radius:50%!important;background:#146F58!important;
 color:#FFFFFF!important;font-size:28px!important;font-weight:850!important;letter-spacing:-.03em;
 line-height:1!important;padding:0!important;box-shadow:0 5px 16px rgba(16,58,44,.19)!important;}
.st-key-chat_float button * {color:#FFFFFF!important;}
.st-key-chat_float button:hover {transform:scale(1.05)!important;}
/* 검색 근거: 제목·발췌·번호 동일한 글자 크기 */
.evidence-card {background:var(--guide-surface);color:var(--guide-text);
 border:1px solid var(--guide-border);border-radius:9px;margin:7px 0;padding:12px 14px;}
.evidence-card p,.evidence-card div,.evidence-card strong {
 color:var(--guide-text)!important;font-size:14px!important;line-height:1.6!important;}
.evidence-card .evidence-excerpt {white-space:pre-wrap;overflow-wrap:anywhere;}
/* 월 달력: 학습 완료시간이 길수록 진해지는 정돈된 7열 레이아웃 */
.guide-month-wrap {overflow-x:auto;margin:10px 0 14px;}
.guide-month {width:100%;min-width:560px;table-layout:fixed;border-spacing:5px;border-collapse:separate;}
.guide-month th {font-size:13px;font-weight:650;text-align:center;color:var(--guide-sub);
 padding:6px 0;}
.guide-month td {vertical-align:top;border-radius:9px;height:82px;padding:10px 10px 8px;
 border:1px solid var(--guide-border);background:var(--guide-surface);color:var(--guide-text);}
.guide-month td.other-month {opacity:.37;}
.guide-month td.today-cell {outline:2px solid #2A9B7D;outline-offset:-2px;}
.guide-month td .day-num {display:block;font-size:13px;font-weight:750;color:inherit!important;}
.guide-month td .day-total {display:block;margin-top:13px;font-size:12px;
 font-weight:650;color:inherit!important;white-space:nowrap;}
.guide-legend {font-size:12px;color:var(--guide-sub);margin:3px 0 12px;}
.guide-legend span {display:inline-block;width:13px;height:13px;border-radius:3px;vertical-align:-2px;
 margin:0 3px 0 9px;border:1px solid var(--guide-border);}
/* 주/일 시간표: 제목과 실제 시간대만 명료하게 출력 */
.guide-heatmap-wrap {overflow:auto;max-height:610px;border:1px solid var(--guide-border);
 border-radius:11px;background:var(--guide-surface);margin:12px 0 14px;}
.guide-heatmap {border-collapse:separate;border-spacing:3px;width:100%;min-width:560px;
 color:var(--guide-text);font-size:12px;}
.guide-heatmap th {background:var(--guide-surface);color:var(--guide-text);position:sticky;
 top:0;z-index:2;padding:7px 5px;min-width:72px;border-bottom:1px solid var(--guide-border);}
.guide-heatmap td {height:30px;text-align:center;border-radius:5px;background:var(--guide-soft);
 color:var(--guide-text);font-size:11px;min-width:68px;}
.guide-heatmap td span {color:inherit!important;font-size:11px;font-weight:650;}
.guide-heatmap .guide-hour {position:sticky;left:0;z-index:1;background:var(--guide-surface);
 font-weight:600;color:var(--guide-sub);min-width:65px;padding:5px;}

/* 6차 UI: 내용 중심 흰 배경. 메뉴·텍스트 줄바꿈과 클릭 후 버튼 스타일 유지 */
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {font-size:12px;white-space:nowrap;}
[data-testid="stSidebar"] {border-right:1px solid var(--guide-border);}
.stApp [data-testid="stMainBlockContainer"] h1 {font-size:clamp(1.65rem,3vw,2.2rem);}
.stApp .st-key-home_time_panel {background:var(--guide-surface);border:1px solid var(--guide-border);border-radius:16px;padding:16px 18px;}
.stApp .st-key-aivle_popular button {text-align:left;white-space:normal;height:auto;}
.stApp .st-key-chat_float button p {font-size:28px!important;line-height:1!important;}
/* 일정명은 시간표 내부에서 줄바꿈하며 너무 긴 이름은 2줄까지만 표시 */
.guide-month td .day-task {display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
 overflow:hidden;overflow-wrap:anywhere;font-size:12px;font-weight:650;margin-top:4px;
 color:inherit!important;line-height:1.35;}
.guide-month td .day-more {font-size:11px;font-weight:600;color:inherit!important;opacity:.85;}
.guide-heatmap td .guide-task-title {display:-webkit-box;-webkit-line-clamp:2;
 -webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere;
 font-size:11px!important;line-height:1.25!important;padding:3px 5px;text-align:left;}
.guide-heatmap td {height:48px;min-width:76px;}
/* 근거 발췌, 유형, 페이지 모두 14px 통일 */
.stApp .evidence-card,.stApp .evidence-card * {font-size:14px!important;line-height:1.65!important;}
.stApp .guide-month th,.stApp .guide-month td {border-color:var(--guide-border);}
.stApp .st-key-home_time_panel [data-testid="stVerticalBlockBorderWrapper"] {border-color:var(--guide-border)!important;}
</style>""", unsafe_allow_html=True)


MENU_ICON = {"AI에게 질문하기":"💬", "홈":"🏠", "에이블스쿨이란?":"🎓",
             "노하우":"💡", "학습전략":"📚", "환경설정":"⚙️"}
# 팀에서 선정한 실제 테스트 질문. 버튼은 문서 검색의 입력만 지정하며 답을 미리 작성하지 않습니다.
QUESTIONS = [
    "비전공자 기준으로 수업시간 외 자율학습하려면 주에 몇시간정도, 어떻게 공부하면 좋을지 알려주세요",
    "미니프로젝트 난이도와 후기를 알려주세요",
    "에이블스쿨 과정에 참여하면 취업을 위한 포트폴리오를 준비하는데 도움이 되나요?",
    "과정을 수료하면 취업이 보장되나요?",
    "에이블스쿨에 지원하려고 하는데 아직 국민내일배움카드가 없어요. 카드 없이 지원해도 괜찮나요? 그리고 교육비는 무료인지, 제가 따로 내야 하는 돈이 있는지도 궁금해요.",
    "저는 코딩을 거의 해본 적이 없는데 DX 컨설턴트 과정에 들어가도 따라갈 수 있을까요? 개강 전에 어떤 것부터 공부하면 좋은지 순서대로 알려주세요.",
    "출석인정요청은 언제까지 가능한가요?",
    "AI 개발자와 DX 컨설턴트 트랙의 차이는 무엇인가요?",
]
DB = Path(tempfile.gettempdir()) / "aivle_guide_qcounts_v3.sqlite3"
DEFAULT_PDF = Path(__file__).parent / "AIVLE School 백서.pdf"


def navigate(page):
    S.page = page
    st.rerun()


def count_question(q):
    q = " ".join(q.strip().split())[:200]
    if not q: return
    try:
        with sqlite3.connect(DB, timeout=10) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS counts (q TEXT PRIMARY KEY, n INTEGER NOT NULL)")
            conn.execute("INSERT INTO counts(q,n) VALUES (?,1) ON CONFLICT(q) DO UPDATE SET n=n+1", (q,))
    except sqlite3.Error: pass


def top_questions():
    try:
        with sqlite3.connect(DB, timeout=10) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS counts (q TEXT PRIMARY KEY, n INTEGER NOT NULL)")
            return conn.execute("SELECT q,n FROM counts ORDER BY n DESC, q LIMIT 5").fetchall()
    except sqlite3.Error: return []


def get_api_key():
    key = os.getenv("OPENAI_API_KEY", "")
    if key: return key
    try: return st.secrets.get("OPENAI_API_KEY", "")
    except Exception: return ""
# [셀 04] PDF 선택 / RAG 연결 / 학습계획·시간표 공통 로직
from rag_core import rag_pipeline

# [HOTFIX 01] 음성 기능을 app.py 안에 정의합니다.
# GitHub의 voice_core.py가 누락되거나 이전 버전이어도 앱 시작 단계에서 ImportError가 발생하지 않습니다.
# OpenAI SDK도 음성 버튼을 누를 때만 불러옵니다. (API 키는 Streamlit Secrets에서 사용)
STT_MODELS = ("whisper-1", "gpt-4o-mini-transcribe")
TTS_MODELS = ("gpt-4o-mini-tts", "tts-1", "tts-1-hd")
ALL_VOICES = ("marin", "cedar", "alloy", "ash", "ballad", "coral", "echo", "fable",
              "nova", "onyx", "sage", "shimmer", "verse")
CLASSIC_VOICES = ("alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer")
MAX_SPEECH_LENGTH = 3000


def _voice_client(api_key, timeout=60):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI 음성 SDK를 불러오지 못했습니다. "
            "requirements.txt에 openai가 포함되어 있는지 확인하고 앱을 다시 배포해 주세요."
        ) from exc
    return OpenAI(api_key=api_key, timeout=timeout)


def transcribe_audio(audio_bytes, api_key, model="whisper-1"):
    """STT. 음성 기능을 사용할 때만 OpenAI를 불러옵니다."""
    if not audio_bytes:
        raise ValueError("녹음된 음성이 없습니다.")
    if model not in STT_MODELS:
        raise ValueError("지원하지 않는 음성 인식 모델입니다.")
    buffer = io.BytesIO(audio_bytes)
    buffer.name = "aivle_question.wav"
    response = _voice_client(api_key, 45).audio.transcriptions.create(
        model=model, file=buffer, language="ko"
    )
    return (response.text or "").strip()


def _clean_speech_text(text):
    text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", str(text))
    text = re.sub(r"\[(?:D\d+|[PEORTB]\d{2})\]", "", text)
    text = re.sub(r"[*_`#]", "", text)
    text = re.sub(r"(?m)^\s*[-•]\s*", "", text)
    return " ".join(text.split()).strip()[:MAX_SPEECH_LENGTH]


def synthesize_answer(text, api_key, model="gpt-4o-mini-tts", voice="marin", speed=1.0):
    """TTS. 답변 텍스트는 그대로 두고 음성 합성만 수행합니다."""
    speech_text = _clean_speech_text(text)
    if not speech_text:
        raise ValueError("읽을 답변이 없습니다.")
    if model not in TTS_MODELS:
        raise ValueError("지원하지 않는 음성 합성 모델입니다.")
    voices = ALL_VOICES if model == "gpt-4o-mini-tts" else CLASSIC_VOICES
    if voice not in voices:
        raise ValueError("선택한 모델에서 지원하지 않는 목소리입니다.")
    speed = float(speed)
    if not 0.25 <= speed <= 4.0:
        raise ValueError("속도는 0.25~4.0 사이여야 합니다.")
    kwargs = dict(model=model, voice=voice, input=speech_text,
                  response_format="mp3", speed=speed)
    if model == "gpt-4o-mini-tts":
        kwargs["instructions"] = (
            "한국어 문장을 또렷하고 자연스럽게 읽으세요. "
            "원문에 없는 사실이나 인사말, 웃음소리를 덧붙이지 마세요."
        )
    response = _voice_client(api_key).audio.speech.create(**kwargs)
    return response.content


@st.cache_resource(show_spinner="백서 검색 인덱스를 만드는 중...", max_entries=4)
def build_retriever(file_bytes, file_hash, api_key, document_name):
    """업로드 PDF bytes → 실제 PDF 파일 경로 → RAG → 재사용 캐시."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as temp:
        temp.write(file_bytes)
        pdf_path = temp.name
    try:
        rag = rag_pipeline(pdf_path, api_key)
    finally:
        if os.path.exists(pdf_path): os.unlink(pdf_path)
    rag.document_name = document_name
    return rag


def active_document():
    if S.source_choice == "기본 백서" and DEFAULT_PDF.exists():
        return DEFAULT_PDF.name, DEFAULT_PDF.read_bytes()
    if S.source_choice == "첨부 PDF" and S.pdf_bytes:
        return S.pdf_name, S.pdf_bytes
    return None, None


def answer_question(question):
    document_name, pdf_bytes = active_document()
    if pdf_bytes is None:
        return "사이드바의 '백서 업로드'에서 PDF 파일을 먼저 등록해 주세요.", []
    api_key = get_api_key()
    if not api_key:
        return "OPENAI_API_KEY가 없습니다. Streamlit Secrets에 API 키를 등록해 주세요.", []
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    rag = build_retriever(pdf_bytes, digest, api_key, document_name)
    result = rag.ask(question, answer_format=S.answer_format)
    return result.answer, result.sources


def strip_display_citations(text):
    """화면과 음성에서는 내부 [D번호]만 숨기고 원래의 출처 카드 정보는 유지합니다."""
    text = re.sub(r"\[\s*D\s*\d+\s*\]", "", str(text), flags=re.I)
    text = re.sub(r"【\s*D\s*\d+\s*】", "", text, flags=re.I)
    return re.sub(r" {2,}", " ", text).strip()


def chat_history_container():
    """지원되는 Streamlit 버전에서는 채팅 컨테이너를 자동으로 맨 아래로 스크롤합니다."""
    try:
        return st.container(height=int(S.chat_height), border=True, autoscroll=True)
    except TypeError:
        # 구버전에서도 채팅 메시지가 있으면 기본 자동 스크롤 기능을 사용합니다.
        return st.container(height=int(S.chat_height), border=True)


def tone_render(text):
    """근거 답변 본문은 공통으로 보존하고 문장 앞의 안내 어조만 바꿉니다.

    모든 톤은 동일한 RAG 답변과 동일한 출처를 공유하므로 사실 내용은 달라지지 않습니다.
    """
    openers = {
        "차분한": "",
        "다정한": "차근차근 함께 살펴볼게요.\n\n",
        "엄격한": "확인된 근거와 조건을 중심으로 정리합니다.\n\n",
        "자신감을 주는": "좋은 질문이에요. 확인된 근거를 차근차근 살펴볼게요.\n\n",
        "격려하는 코치": "목표를 분명히 하고 핵심부터 확인해 볼까요?\n\n",
    }
    return openers.get(S.answer_tone, "") + text


def submit_question(question):
    question = question.strip()
    if not question: return
    S.messages.append({"role":"user", "content":question})
    count_question(question)
    try:
        response, sources = answer_question(question)
    except Exception as exc:
        response = (f"문서 검색 또는 답변 생성 중 오류가 발생했습니다: `{type(exc).__name__}`. "
                    "API 키·백서·설치 패키지를 확인해 주세요.")
        sources = []
    name,_=active_document()
    S.messages.append({"role":"assistant", "content":response, "sources":sources, "question":question, "document_name":name})


def document_upload():
    """사이드바 유일한 PDF 업로드 영역. Streamlit 기본 드래그앤드롭 지원."""
    st.markdown("**📄 백서 업로드**")
    uploaded = st.file_uploader("PDF 파일을 끌어놓거나 찾아보기", type=["pdf"], key="sidebar_pdf_upload")
    if uploaded is not None:
        content = uploaded.getvalue()
        digest = hashlib.sha256(content).hexdigest()
        if digest != S.pdf_hash:
            S.pdf_hash, S.pdf_bytes, S.pdf_name = digest, content, uploaded.name
            S.source_choice = "첨부 PDF"
            # selectbox가 이전에 '기본 백서'를 가리키더라도 새 업로드 PDF를 즉시 선택합니다.
            S["sidebar_source_select"] = "첨부 PDF"
            S.messages, S.audio_responses = [], {}
        st.caption(f"✅ {uploaded.name}")
    options = ["첨부 PDF"]
    if DEFAULT_PDF.exists(): options.insert(0, "기본 백서")
    selected = st.selectbox("사용할 답변 자료", options,
        index=options.index(S.source_choice) if S.source_choice in options else 0,
        key="sidebar_source_select")
    if selected != S.source_choice:
        S.source_choice = selected
        # 서로 다른 PDF의 근거 D번호가 한 대화에 섞이지 않게 초기화합니다.
        S.messages, S.audio_responses = [], {}
    current_name, current_bytes = active_document()
    if not current_bytes:
        st.caption("PDF가 아직 없습니다. 사이드바에 드래그해서 등록해 주세요.")
        return
    st.caption(f"현재 문서: {current_name}")
    if get_api_key():
        try:
            rag = build_retriever(current_bytes, hashlib.sha256(current_bytes).hexdigest(),
                                  get_api_key(), current_name)
            # 벡터화 결과는 서버에서 캐시하되 불필요한 청크 개수 안내는 출력하지 않습니다.
            pass
        except Exception as exc:
            st.error(f"PDF 벡터화 실패 ({type(exc).__name__}).")
    else:
        st.warning("API 키가 등록되지 않았습니다.")
    


def rerun_after_question(prefix):
    if prefix == "popup": st.rerun(scope="fragment")
    else: st.rerun()


# [UI-C01] 공통 학습 일정 데이터: 월 → 주 → 일 / 기본값 월, 완료 시간 기준으로 색상 표시
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
CATEGORIES = ["개념 학습", "코드 실습", "복습", "프로젝트 준비", "기타"]


def _minutes(hhmm):
    hour, minute = map(int, hhmm.split(":"))
    return hour * 60 + minute


def event_minutes(event):
    return max(0, _minutes(event["end"]) - _minutes(event["start"]))


def week_start(anchor):
    return anchor - timedelta(days=anchor.weekday())


def month_start(anchor):
    return anchor.replace(day=1)


def change_month(anchor, offset):
    """12월→1월과 윤년을 포함해 현재 '일'을 보존하는 월 이동."""
    number = anchor.year * 12 + anchor.month - 1 + offset
    year, month_zero = divmod(number, 12)
    month = month_zero + 1
    return date(year, month, min(anchor.day, calendar.monthrange(year, month)[1]))


def shift_calendar(anchor, view, offset):
    if view == "월":
        return change_month(anchor, offset)
    if view == "주":
        return anchor + timedelta(days=7 * offset)
    return anchor + timedelta(days=offset)


def events_in_range(start, end):
    """start 이상 end 미만의 일정을 정렬해 반환."""
    return sorted((e for e in S.study_events if start <= date.fromisoformat(e["date"]) < end),
                  key=lambda e: (e["date"], e["start"], e["end"]))


def union_minutes(events):
    """동일한 시간대에 겹치는 일정은 실제 학습시간에서 중복 집계하지 않습니다."""
    slots = sorted((_minutes(e["start"]), _minutes(e["end"])) for e in events)
    if not slots:
        return 0
    merged = []
    for a, b in slots:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return sum(b-a for a,b in merged)


def completed_minutes(events):
    """완료로 표시한 학습 시간만 색상과 학습한 총 시간에 반영."""
    return union_minutes(e for e in events if e.get("status") == "완료")


def fmt_hours(minutes):
    hours = minutes / 60
    return f"{hours:.1f}시간" if minutes else "0시간"


def month_heatmap_html(anchor, events):
    """월간 달력: 일별 완료 학습시간에 따라 초록 계열 단계별 농도 적용."""
    year, month = anchor.year, anchor.month
    month_days = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    by_date = {}
    for e in events:
        by_date.setdefault(e["date"], []).append(e)
    head = "".join(f"<th>{day}</th>" for day in WEEKDAYS)
    rows = [f'<thead><tr>{head}</tr></thead><tbody>']
    today = today_kst()
    for week in month_days:
        cells = []
        for day in week:
            day_events = by_date.get(day.isoformat(), [])
            minutes = completed_minutes(day_events)
            
            # 완료 학습시간 기준 5단계 색상
            level = (0 if minutes == 0 else
            1 if minutes < 3 * 60 else
            2 if minutes < 5 * 60 else
            3 if minutes < 7 * 60 else
            4 if minutes < 8 * 60 else 5)
            
            shades = [
                    "var(--guide-surface)",  # 0시간
                    "#E7F5EF",               # 1단계
                    "#B6DEC9",               # 2단계
                    "#298565",               # 3단계
                    "#176649",               # 4단계
                    "#083F32"                # 5단계
                    ]
                    
            bg = shades[level]
            color = "#FFFFFF" if level >= 3 else "#173D32"

            classes = ("other-month " if day.month != month else "") + ("today-cell" if day == today else "")
            plan_count = sum(e.get("status") != "완료" for e in day_events)
            tooltip = (f"{day:%Y-%m-%d} / 완료 {fmt_hours(minutes)} / "
                       f"계획 {plan_count}건")
            if day_events:
                tooltip += " / " + " · ".join(f"{e['start']}~{e['end']} {e['title']} ({e['status']})" for e in day_events[:5])
            titles = list(dict.fromkeys(str(e.get("title", "")).strip() for e in day_events if e.get("title")))
            note = "".join(f'<span class="day-task">{html.escape(t)}</span>' for t in titles[:2])
            if len(titles) > 2:
                note += f'<span class="day-more">+{len(titles)-2}개</span>' 
            cells.append(f'<td class="{classes}" title="{html.escape(tooltip, quote=True)}" '
                         f'style="background:{bg};color:{color}!important">'
                         f'<span class="day-num">{day.day}</span>{note}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    rows.append("</tbody>")
    legend = ('<div class="guide-legend">완료한 학습시간 · 적음'
              '<span style="background:rgba(28,141,105,.16)"></span>'
              '<span style="background:rgba(28,141,105,.29)"></span>'
              '<span style="background:rgba(28,141,105,.44)"></span>'
              '<span style="background:rgba(20,115,87,.68)"></span>'
              '<span style="background:#12664F"></span>많음</div>')
    return '<div class="guide-month-wrap"><table class="guide-month">' + ''.join(rows) + '</table></div>' + legend


def heatmap_html(start, events, days=7):
    """주/일: 시간대별 완료시간 표시, 계획된 일정은 마우스 오버로 확인."""
    heads = "".join(f"<th>{(start+timedelta(days=d)):%m/%d} ({WEEKDAYS[(start+timedelta(days=d)).weekday()]})</th>" for d in range(days))
    rows = [f'<thead><tr><th>시간</th>{heads}</tr></thead><tbody>']
    if events:
        low = min(_minutes(e['start']) // 60 for e in events)
        high = max((_minutes(e['end']) - 1) // 60 for e in events)
        first_hour, last_hour = max(0, min(8, low)), min(23, max(22, high))
    else:
        first_hour, last_hour = 8, 22
    for hour in range(first_hour, last_hour+1):
        t0, t1 = hour*60, (hour+1)*60
        row = [f'<tr><td class="guide-hour">{hour:02d}:00</td>']
        for d in range(days):
            iso = (start + timedelta(days=d)).isoformat()
            blocks = [e for e in events if e['date']==iso
                      and _minutes(e['start']) < t1 and _minutes(e['end']) > t0]
            completed = [e for e in blocks if e['status']=="완료"]
            clipped = []
            for e in completed:
                clipped.append({'start':f'{max(t0,_minutes(e["start"]))//60:02d}:{max(t0,_minutes(e["start"]))%60:02d}',
                                'end':f'{min(t1,_minutes(e["end"]))//60:02d}:{min(t1,_minutes(e["end"]))%60:02d}'})
            used = min(60, union_minutes(clipped))
            background = f"rgba(19,135,101,{0.12 + 0.72*used/60:.3f})" if used else "var(--guide-soft)"
            ink = '#FFFFFF' if used >= 48 else 'var(--guide-text)'
            tooltip = html.escape(' / '.join(f"{e['start']}~{e['end']} {e['title']} ({e['status']})" for e in blocks),quote=True)
            names = list(dict.fromkeys(str(e.get("title", "")).strip() for e in blocks if e.get("title")))
            label = (f'<span class="guide-task-title">{html.escape(" · ".join(names[:2]))}</span>'
                     if names else "")
            row.append(f'<td title="{tooltip}" style="background:{background};color:{ink}">{label}</td>')
        row.append('</tr>')
        rows.append(''.join(row))
    rows.append('</tbody>')
    minimum = 'min-width:560px;' if days==7 else 'min-width:250px;'
    return '<div class="guide-heatmap-wrap"><table class="guide-heatmap" style="'+minimum+'">' + ''.join(rows) + '</table></div>'


def render_schedule(prefix, editable=True, show_stats=True, show_event_list=True):
    """홈과 학습전략이 같은 S.study_events, 달력 날짜와 보기 모드를 공유합니다."""
    options = ["월", "주", "일"]
    key_view = f"{prefix}_schedule_view"
    # 서로 다른 페이지에서 번갈아 볼 때도 마지막 선택 보기 유지
    if S.get(key_view) != S.calendar_view:
        S[key_view] = S.calendar_view
    def view_changed():
        # Streamlit 버전에 따라 선택된 항목을 다시 누르면 None이 될 수 있어 월을 기본값으로 복원합니다.
        S.calendar_view = S.get(key_view) or "월"
    # 한 줄 구성: 이전 · 오늘 · 다음 · 기준 날짜 · 시간표 보기
    # 날짜/보기 변경 콜백은 rerun 시 먼저 반영되므로 탐색 버튼도 현재 보기를 사용합니다.
    nav_a, nav_b, nav_c, picker, view_picker = st.columns(
        [1.05, 0.8, 1.05, 1.85, 2.25], vertical_alignment="bottom", gap="small"
    )
    with nav_a:
        prev = st.button("‹ 이전", key=f"{prefix}_previous", use_container_width=True)
    with nav_b:
        now = st.button("오늘", key=f"{prefix}_today", use_container_width=True)
    with nav_c:
        following = st.button("다음 ›", key=f"{prefix}_next", use_container_width=True)
    date_key = f"{prefix}_jump_date"
    if S.get(date_key) != S.calendar_anchor:
        S[date_key] = S.calendar_anchor
    def changed_date():
        S.calendar_anchor = S[date_key]
    with picker:
        st.date_input("기준 날짜", key=date_key, on_change=changed_date)
    with view_picker:
        st.segmented_control("시간표 보기", options, key=key_view, on_change=view_changed)
    view = S.calendar_view
    if prev or following:
        S.calendar_anchor = shift_calendar(S.calendar_anchor, view, -1 if prev else 1)
    elif now:
        S.calendar_anchor = today_kst()
    anchor = S.calendar_anchor
    if view == "월":
        first = month_start(anchor)
        after = change_month(first, 1)
        events = events_in_range(first, after)
        title = f"{first:%Y년 %m월}"
        total = sum(completed_minutes([e for e in events if e['date']==d.isoformat()])
                    for d in (first+timedelta(days=i) for i in range((after-first).days)))
        distinct = len({e['date'] for e in events if e['status']=="완료"})
        st.markdown(f"**{title}**")
        if show_stats:
            a,b,c = st.columns(3)
            a.metric("완료한 학습", fmt_hours(total))
            b.metric("공부한 날짜", f"{distinct}일")
            c.metric("등록 일정", f"{len(events)}개")
        st.markdown(month_heatmap_html(anchor, events),unsafe_allow_html=True)
        
    elif view == "주":
        first = week_start(anchor)
        end = first + timedelta(days=7)
        events = events_in_range(first, end)
        total = sum(completed_minutes([e for e in events if e['date']==(first+timedelta(days=i)).isoformat()]) for i in range(7))
        st.markdown(f"**{first:%Y-%m-%d} ~ {(end-timedelta(days=1)):%Y-%m-%d}** · 완료 {fmt_hours(total)}")
        st.markdown(heatmap_html(first, events, days=7),unsafe_allow_html=True)
        
    else:
        first = anchor
        events = events_in_range(first, first+timedelta(days=1))
        total = completed_minutes(events)
        st.markdown(f"**{anchor:%Y-%m-%d} ({WEEKDAYS[anchor.weekday()]})** · 완료 {fmt_hours(total)}")
        st.markdown(heatmap_html(anchor, events, days=1), unsafe_allow_html=True)
    # 홈에서는 달력만 표시합니다. 상세 일정 목록과 등록/수정 폼은 학습전략에만 표시합니다.
    if show_event_list:
        if events:
            with st.expander(f"📋 선택한 {view}의 일정 {len(events)}건", expanded=(view=="일")):
                st.dataframe([{"날짜":e["date"],"시간":f'{e["start"]}~{e["end"]}',
                              "학습 내용":e["title"],"유형":e["category"],"상태":e["status"]} for e in events],
                             hide_index=True, use_container_width=True)
        else:
            st.caption("이 기간에는 등록한 학습 일정이 없습니다.")
    if not editable:
        return
    with st.expander("＋ 학습 일정 등록", expanded=False):
        with st.form(f"{prefix}_add", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1: chosen_date = st.date_input("학습 날짜", value=anchor, key=f"{prefix}_add_date")
            with col2: start = st.time_input("시작", value=time(19, 0), step=900, key=f"{prefix}_add_start")
            with col3: end = st.time_input("종료", value=time(20, 0), step=900, key=f"{prefix}_add_end")
            title = st.text_input("학습 내용", placeholder="예: RAG 청킹 원리 복습", max_chars=150, key=f"{prefix}_add_title")
            category, status = st.columns(2)
            with category: what = st.selectbox("학습 유형", CATEGORIES, key=f"{prefix}_add_category")
            with status: done = st.selectbox("진행 상태", ["계획", "완료"], key=f"{prefix}_add_status")
            added = st.form_submit_button("일정 저장", type="primary", use_container_width=True)
        if added:
            if not title.strip(): st.warning("학습 내용을 적어 주세요.")
            elif not chosen_date: st.warning("학습 날짜를 선택해 주세요.")
            elif end <= start: st.warning("종료 시간은 시작 시간보다 뒤여야 합니다. 자정 넘는 일정은 날짜별로 나눠 등록하세요.")
            elif len(S.study_events) >= 1000: st.warning("한 세션에 최대 1,000개의 일정을 등록할 수 있습니다.")
            else:
                S.study_events.append({"id":uuid.uuid4().hex[:12],"date":chosen_date.isoformat(),
                                       "start":start.strftime("%H:%M"),"end":end.strftime("%H:%M"),
                                       "title":title.strip(),"category":what,"status":done})
                S.calendar_anchor = chosen_date
                st.rerun()
    if events:
        with st.expander("✎ 기존 일정 수정 · 삭제"):
            ids = {f"{e['date']} {e['start']}~{e['end']} · {e['title']} ({e['id'][:4]})":e["id"] for e in events}
            selected_name = st.selectbox("수정할 일정", list(ids), key=f"{prefix}_event_choice")
            selected = next(e for e in S.study_events if e["id"] == ids[selected_name])
            event_key = selected["id"]
            with st.form(f"{prefix}_edit_{event_key}"):
                col1,col2,col3 = st.columns(3)
                with col1: edit_date = st.date_input("날짜", value=date.fromisoformat(selected["date"]), key=f"{prefix}_date_{event_key}")
                with col2: edit_start = st.time_input("시작", value=time.fromisoformat(selected["start"]), key=f"{prefix}_start_{event_key}")
                with col3: edit_end = st.time_input("종료", value=time.fromisoformat(selected["end"]), key=f"{prefix}_end_{event_key}")
                edit_title = st.text_input("내용", value=selected["title"], key=f"{prefix}_title_{event_key}")
                x,y=st.columns(2)
                with x: edit_category = st.selectbox("유형", CATEGORIES, index=CATEGORIES.index(selected["category"]), key=f"{prefix}_category_{event_key}")
                with y: edit_status = st.selectbox("상태", ["계획", "완료"], index=["계획", "완료"].index(selected["status"]), key=f"{prefix}_status_{event_key}")
                save,delete = st.columns(2)
                with save: do_save = st.form_submit_button("수정 저장", type="primary", use_container_width=True)
                with delete: do_delete = st.form_submit_button("이 일정 삭제", use_container_width=True)
            if do_delete:
                S.study_events = [e for e in S.study_events if e["id"] != event_key]
                st.rerun()
            if do_save:
                if not edit_title.strip(): st.warning("내용을 적어 주세요.")
                elif not edit_date: st.warning("날짜를 선택해 주세요.")
                elif edit_end <= edit_start: st.warning("종료 시간은 시작 시간보다 뒤여야 합니다.")
                else:
                    selected.update({"date":edit_date.isoformat(), "start":edit_start.strftime("%H:%M"),
                                     "end":edit_end.strftime("%H:%M"), "title":edit_title.strip(),
                                     "category":edit_category, "status":edit_status})
                    S.calendar_anchor = edit_date
                    st.rerun()




# [UI-L01] 개인 학습시간 입력 → 학습 영역별 우선순위 및 콘텐츠 추천 (모델 호출 없음)
SKILL_CHECKS = [
    "Python 변수와 자료형을 설명할 수 있다",
    "조건문과 반복문을 혼자 작성할 수 있다",
    "함수를 정의하고 호출할 수 있다",
    "pandas로 데이터를 읽고 처리할 수 있다",
    "분류와 회귀의 차이를 설명할 수 있다",
    "모델 결과를 내 말로 설명할 수 있다",
]
LEARNING_TOPICS = {
    "개념 학습": "Python·통계·AI 기본 개념과 모르는 용어 정리",
    "코드 실습": "pandas 전처리·함수 작성·예제 변형하여 실행",
    "복습": "그날의 오류를 다시 해결하고 한 문장으로 설명",
    "프로젝트 준비": "요구사항·RAG 검색·데모·발표 흐름 정리",
}

def learning_allocation(hours, checked):
    """약한 역량에 비중을 두고 주간 학습시간을 30분 단위로 정확히 배분."""
    units = int(round(float(hours) * 2))
    weights = {"개념 학습":24, "코드 실습":38, "복습":22, "프로젝트 준비":16}
    if not all(checked[:3]):
        weights["개념 학습"] += 14
        weights["프로젝트 준비"] -= 6
    if len(checked)>3 and not checked[3]:
        weights["코드 실습"] += 16
    if len(checked)>5 and not checked[5]:
        weights["복습"] += 11
    weight_sum = sum(weights.values())
    raw = {k: units*w/weight_sum for k,w in weights.items()}
    floor = {k:int(v) for k,v in raw.items()}
    leftover = units-sum(floor.values())
    order = sorted(raw, key=lambda k: raw[k]-floor[k], reverse=True)
    for k in order[:leftover]: floor[k]+=1
    return {k:floor[k]/2 for k in weights}

def recommend_daily_hours(hours):
    """월~일 30분 단위 배분. 요일별 합계=주간 목표."""
    units=int(round(float(hours)*2))
    weights=[1,1,1,1,1,1.5,1.5]
    raw=[units*w/sum(weights) for w in weights]
    vals=[int(v) for v in raw]
    for idx in sorted(range(7),key=lambda i: raw[i]-vals[i],reverse=True)[:units-sum(vals)]: vals[idx]+=1
    return {day:vals[i]/2 for i,day in enumerate(WEEKDAYS)}

def learning_priorities(checked):
    mapping = ["Python 변수·자료형", "조건문·반복문", "함수·입출력", "pandas 전처리",
               "분류와 회귀 개념", "결과 해석·발표"]
    return [label for label,ok in zip(mapping,checked) if not ok]

def safe_backup():
    """개인 정보 유출을 피하기 위해 PDF·대화·API 키는 백업에 포함하지 않습니다."""
    keys = ["level", "weekly_hours", "goal", "days", "study_events", "study_logs",
            "menu_order", "answer_format", "answer_tone", "tts_model", "tts_voice",
            "tts_speed", "stt_model", "theme_mode", "chat_height", "calendar_view", "next_week_focus"]
    data = {k:S[k] for k in keys}
    data["study_checks"] = {str(i):bool(S.get(f"execute_{i}", False)) for i in range(5)}
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def restore_backup(data):
    """허용한 설정만 가져오며 예외·큰 파일은 제한합니다."""
    if len(data)>1024*1024: raise ValueError("백업 파일은 1MB 이하만 허용합니다.")
    obj = json.loads(data.decode("utf-8-sig"))
    if not isinstance(obj,dict): raise ValueError("JSON 객체 형식이어야 합니다.")
    options = {
        "level": ("기초", "초급", "중급"),
        "answer_format": ("간결", "표준", "상세"),
        "answer_tone": ("차분한", "다정한", "엄격한", "자신감을 주는", "격려하는 코치"),
        "tts_model": TTS_MODELS, "tts_voice": ALL_VOICES,
        "stt_model": STT_MODELS, "theme_mode": ("시스템", "라이트", "다크"),
        "calendar_view": ("월", "주", "일"),
    }
    for field, allowed in options.items():
        if obj.get(field) in allowed: S[field]=obj[field]
    if isinstance(obj.get("goal"),str): S.goal=obj["goal"][:150]
    if isinstance(obj.get("next_week_focus"),str): S.next_week_focus=obj["next_week_focus"][:300]
    if isinstance(obj.get("weekly_hours"),(int,float)):
        S.weekly_hours=int(min(30,max(1,obj["weekly_hours"])))
    if isinstance(obj.get("chat_height"),(int,float)):
        S.chat_height=int(min(960,max(240,obj["chat_height"])))
    if isinstance(obj.get("tts_speed"),(int,float)): S.tts_speed=min(2.0,max(0.5,float(obj["tts_speed"])))
    days = obj.get("days")
    if isinstance(days,dict) and all(isinstance(days.get(k),(int,float)) and 0<=days[k]<=12 for k in WEEKDAYS):
        S.days={k:float(days[k]) for k in WEEKDAYS}
    evs=obj.get("study_events",[])
    if isinstance(evs,list):
        valid=[]
        for e in evs[:1000]:
            try:
                date.fromisoformat(e["date"])
                if e.get("category") not in CATEGORIES or e.get("status") not in ("계획","완료"): continue
                if _minutes(e["end"]) <= _minutes(e["start"]): continue
                if not isinstance(e.get("title"),str): continue
                valid.append({"id":uuid.uuid4().hex[:12],"date":e["date"],"start":e["start"],
                              "end":e["end"],"title":e["title"][:150],"category":e["category"],"status":e["status"]})
            except (ValueError,KeyError,TypeError,AttributeError): continue
        S.study_events=valid
    if isinstance(obj.get("study_logs"),list):
        S.study_logs=[x for x in obj["study_logs"][:200] if isinstance(x,dict)]
    order=obj.get("menu_order")
    if isinstance(order,list):
        # 5차 백업의 문의 메뉴는 6차에서 제거하되 나머지 순서는 유지합니다.
        cleaned=[x for x in order if x in DEFAULT_MENU]
        if set(cleaned)==set(DEFAULT_MENU) and len(cleaned)==len(DEFAULT_MENU):
            S.menu_order=["AI에게 질문하기"]+[x for x in cleaned if x!="AI에게 질문하기"]
    checks=obj.get("study_checks",{})
    if isinstance(checks,dict):
        for i in range(5):
            S[f"execute_{i}"]=bool(checks.get(str(i),False))
    # 기존 선택 위젯의 상태가 백업값을 가리지 않도록 초기화합니다.
    for day in WEEKDAYS: S.pop(f"day_{day}",None)
# [셀 05] AI 채팅: 추천 질문, 출처, 크기 조절, TTS, 후속 질문

def followups_for(question):
    """정해진 후보에서 선택하므로 후속 질문 생성으로 새로운 사실을 만들지 않습니다."""
    q = question.lower()
    if any(x in q for x in ("출석", "수료", "지각", "결석")):
        return ["학교 수업 때문에 빠져도 출석 인정되나요?", "수료 기준 80%와 출석 권고 100%는 어떻게 다른가요?"]
    if any(x in q for x in ("훈련장려금", "지원금", "내일배움카드", "자기부담")):
        return ["훈련장려금과 실업급여를 동시에 받을 수 있나요?", "2026년 K-DT 자기부담금 면제 대상은 누구인가요?"]
    if any(x in q for x in ("취업", "포트폴리오", "면접")):
        return ["DX 컨설턴트에게 필요한 포트폴리오 요소는 무엇인가요?", "취업 지원 프로그램에는 무엇이 있나요?"]
    if any(x in q for x in ("미니프로젝트", "빅프로젝트", "rag")):
        return ["미니프로젝트와 빅프로젝트는 어떻게 다른가요?", "프로젝트를 포트폴리오로 정리하는 방법은 무엇인가요?"]
    return ["공식 안내와 선배 후기는 어떻게 구분하나요?", "AIVLE School 학습 계획은 어떻게 세우나요?"]


def render_message_history(prefix="full"):
    if not S.messages:
        st.caption("추천 질문을 선택하거나 아래에서 직접 질문해 보세요.")
    last_assistant = max((i for i,m in enumerate(S.messages) if m["role"]=="assistant"), default=-1)
    for i,msg in enumerate(S.messages):
        with st.chat_message(msg["role"], avatar="🎓" if msg["role"] == "user" else "🌿"):
            displayed = tone_render(strip_display_citations(msg["content"])) if msg["role"]=="assistant" else msg["content"]
            st.markdown(displayed)
            if msg["role"] != "assistant":
                continue
            srcs = msg.get("sources", [])
            if srcs:
                with st.expander(f"📚 근거 보기 ({len(srcs)}개)", expanded=False):
                    original_name, original_bytes = active_document()
                    used_document = msg.get("document_name") or (srcs[0].get("name") if srcs else None)
                    if original_bytes and original_name == used_document:
                        st.download_button("📄 원문 PDF 다운로드", original_bytes,
                            file_name=original_name or "aivle_source.pdf", mime="application/pdf",
                            key=f"original_{prefix}_{i}")
                    else:
                        st.caption("답변에 사용한 PDF가 현재 선택된 문서와 다릅니다. 사이드바에서 해당 PDF를 다시 선택해 주세요.")
                    for j,src in enumerate(srcs,1):
                        label = f"{src.get('name','백서')} · "
                        label += f"{src.get('page') or '미상'}쪽 · {src.get('section','본문')}"
                        types = src.get("source_types", [])
                        readable_types = " / ".join(types) if types else "자료 유형 확인 필요"
                        ids = ", ".join(src.get("ids",[])) or "근거 번호 없음"
                        excerpt = src.get("excerpt", "")
                        # 원문 페이지 전체가 아니라 RAG가 사용한 청크 발췌임을 명시
                        card = ("<div class='evidence-card'>"
                            f"<div><strong>{html.escape(label)}</strong></div>"
                            f"<div>출처 성격: {html.escape(readable_types)}</div>"
                            f"<div>원문 근거 ID: {html.escape(ids)}</div>"
                            f"<div class='evidence-excerpt'>{html.escape(excerpt)}</div>"
                            "</div>")
                        st.markdown(card, unsafe_allow_html=True)
            else:
                st.caption("현재 답변에 표시할 수 있는 검색 근거가 없습니다.")
            setting=json.dumps([displayed,S.tts_model,S.tts_voice,float(S.tts_speed)],ensure_ascii=False)
            speech_key=hashlib.sha256(setting.encode("utf-8")).hexdigest()[:22]
            if st.button("🔊 답변 듣기",key=f"listen_{prefix}_{i}",help="요청할 때만 TTS API를 사용합니다"):
                if not get_api_key():
                    st.warning("OPENAI_API_KEY가 필요합니다.")
                else:
                    try:
                        with st.spinner("선택한 설정으로 음성 생성 중..."):
                            S.audio_responses[speech_key] = synthesize_answer(displayed,get_api_key(),
                                model=S.tts_model,voice=S.tts_voice,speed=S.tts_speed)
                    except Exception as exc:
                        st.error(f"음성 변환 실패: {type(exc).__name__}. 모델과 목소리를 확인해 주세요.")
            if speech_key in S.audio_responses:
                st.audio(S.audio_responses[speech_key],format="audio/mp3")
            c1,c2=st.columns(2)
            with c1:
                if st.button("👍 도움이 됐어요",key=f"fb_yes_{prefix}_{i}"):
                    S.feedback[i]="helpful"
                    st.toast("피드백을 기록했어요.")
            with c2:
                if st.button("⚠️ 근거가 맞지 않아요",key=f"fb_no_{prefix}_{i}"):
                    S.feedback[i]="incorrect"
                    st.toast("근거 확인 요청으로 기록했어요.")
            if i==last_assistant:
                st.caption("🔎 관련 후속 질문")
                cols=st.columns(2)
                for j,q in enumerate(followups_for(msg.get("question",""))):
                    with cols[j]:
                        if st.button(q,key=f"follow_{prefix}_{i}_{j}",use_container_width=True):
                            submit_question(q)
                            rerun_after_question(prefix)


def render_voice_question(prefix):
    with st.expander("🎙️ 음성으로 질문하기",expanded=False):
        st.caption("녹음 → 한국어 음성 인식 → 문장 확인 후 전송")
        audio=st.audio_input("질문 녹음",key=f"mic_{prefix}")
        if audio is None: return
        raw=audio.getvalue()
        digest=hashlib.sha256(raw).hexdigest()
        if S.get(f"voice_digest_{prefix}")!=digest:
            S[f"voice_digest_{prefix}"]=digest
            S[f"voice_edit_{prefix}"]=""
            if not get_api_key(): st.warning("음성 인식에는 API 키가 필요합니다.")
            else:
                try:
                    with st.spinner("음성을 텍스트로 변환하는 중..."):
                        S[f"voice_edit_{prefix}"]=transcribe_audio(raw,get_api_key(),model=S.stt_model)
                except Exception as exc: st.error(f"음성 인식 실패 ({type(exc).__name__}).")
        if S.get(f"voice_edit_{prefix}"):
            st.text_area("인식한 질문 (수정 가능)",key=f"voice_edit_{prefix}",height=80)
            if st.button("이 음성 질문 전송",key=f"voice_send_{prefix}",type="primary"):
                submit_question(S.get(f"voice_edit_{prefix}",""))
                rerun_after_question(prefix)


def export_conversation():
    rows=["AIVLE Guide | 내 질문 기록",""]
    for m in S.messages:
        who="나" if m["role"]=="user" else "AIVLE Guide"
        content=m["content"] if m["role"]=="user" else tone_render(strip_display_citations(m["content"]))
        rows.extend([f"[{who}]",content,""])
        if m["role"]=="assistant" and m.get("sources"):
            rows.append("검색 근거: " + " / ".join(
                f"{s.get('name','백서')} {s.get('page') or '?'}쪽" for s in m['sources'][:5]))
            rows.append("")
    return "\n".join(rows)


def render_recommendations(prefix, compact=False):
    with st.expander("✨ 추천 질문 · 펼쳐보기 / 접기", expanded=(prefix=="full")):
        with st.container(key=f"recs_{prefix}"):
            cols=st.columns(2)
            for i,q in enumerate(QUESTIONS[:4] if compact else QUESTIONS[:6]):
                with cols[i%2]:
                    if st.button(q,key=f"rec_{prefix}_{i}",use_container_width=True):
                        submit_question(q)
                        rerun_after_question(prefix)


def render_chat_input(prefix):
    with st.form(f"form_{prefix}",clear_on_submit=True):
        field,send=st.columns([6,1],vertical_alignment="center")
        with field:
            question=st.text_input("질문",placeholder="에이블스쿨에 대해 질문해 주세요",
                                   label_visibility="collapsed",key=f"text_{prefix}")
        with send: sent=st.form_submit_button("전송",type="primary",use_container_width=True)
        if sent and question.strip():
            submit_question(question)
            rerun_after_question(prefix)
    render_voice_question(prefix)


def render_top_five(prefix="full"):
    top=top_questions()
    # 최소 5개 서로 다른 질문이 실제 집계될 때까지는 인기 순위를 주장하지 않습니다.
    if len(top)<5:
        title="추천 FAQ · 질문 기록이 아직 적어요"
        ranked=[(q,None) for q in QUESTIONS[:5]]
    else:
        title="많이 묻는 질문 TOP 5 · 서버에 기록된 횟수"
        ranked=top[:5]
    st.caption(title)
    with st.container(key="aivle_popular"):
        for i,(q,count) in enumerate(ranked):
            col,_=st.columns([9,1])
            with col:
                if st.button(f"{i+1}. {q}",key=f"popular_{prefix}_{i}",use_container_width=True):
                    submit_question(q)
                    rerun_after_question(prefix)
            if count is not None:
                with _:
                    st.caption(f"{count}회")
    


def render_popular_questions(prefix="full", expanded=True):
    with st.expander("☰ 많이 묻는 질문 TOP 5", expanded=expanded):
        render_top_five(prefix)


@st.dialog("💬 AIVLE Guide AI 도우미",width="large")
def chatbot_dialog():
    
    render_recommendations("popup",compact=True)
    render_popular_questions("popup", expanded=False)
    with chat_history_container():
        render_message_history("popup")
    render_chat_input("popup")
    c1,c2=st.columns(2)
    with c1:
        if st.button("↗ 전체 화면 열기",key="dialog_open_full",use_container_width=True):
            navigate("AI에게 질문하기")
    with c2:
        if st.button("🗑️ 대화 초기화",key="dialog_clear",use_container_width=True):
            S.messages,S.audio_responses=[],{}
            st.rerun()
# [셀 06] 사이드바 / 홈 / 에이블스쿨 안내 / 노하우 / 학습전략 / 설정 / 챗봇
# 기존 백서 기반 기능을 유지하면서 메뉴를 간소화합니다.
with st.sidebar:
    st.image(LOGO_URL, width=145)
    st.caption("백서 기반 학습 도우미")
    st.divider()
    with st.container(key="nav_ai"):
        if st.button("💬 AI에게 질문하기", key="nav_ai_button", use_container_width=True):
            navigate("AI에게 질문하기")
    for page in S.menu_order:
        if page == "AI에게 질문하기" or page not in DEFAULT_MENU:
            continue
        if st.button(f"{MENU_ICON[page]}  {page}", key=f"nav_{page}",
                     type="primary" if S.page==page else "secondary",use_container_width=True):
            navigate(page)
    st.divider()
    document_upload()
    st.divider()
    st.markdown("[AIVLE School 공식 홈페이지](https://aivle.kt.co.kr/)")
    

if S.page == "홈":
    # 카드 자체의 상단이 잘리던 문제를 없애기 위해 홈 소개는 HTML 카드 대신 제목/문장으로 처리.
    st.caption("KT AIVLE SCHOOL  |  AIVLE GUIDE")
    st.title("궁금한 건 묻고, 배운 건 기록하세요")
    st.write("에이블스쿨 통합 백서를 바탕으로 질문의 근거를 찾고, 나의 학습시간을 한눈에 살펴보는 AI 학습 도우미입니다.")
    
    if st.button("💬 AI에게 질문하기",type="primary",key="home_ai_start",use_container_width=True):
        navigate("AI에게 질문하기")
    st.divider()
    with st.container(border=True, key="home_time_panel"):
        st.subheader("나의 학습 시간")
        
        render_schedule("home", editable=False, show_stats=False, show_event_list=False)
    if st.button("📚 학습전략에서 일정 관리하기",key="home_schedule_manage"):
        navigate("학습전략")

elif S.page == "에이블스쿨이란?":
    st.title("🎓 에이블스쿨이란?")
    st.write("KT AIVLE School은 AI와 DX 분야의 실무 역량을 기르는 교육 프로그램입니다.")
    st.subheader("트랙별 특징")
    st.table({"구분":["중심 역할","학습과 활동","주요 산출물"],
              "AI 개발자":["AI 서비스 구현","데이터·모델·API 개발","모델·서비스 프로토타입"],
              "DX 컨설턴트":["기업 디지털 전환 제안","고객 문제 분석·서비스 설계","문제정의·분석·제안서"]})
    st.markdown("**기초 학습 → 미니프로젝트 → 빅프로젝트 → 진로·취업 준비**")
    st.subheader("주요 학습 경험")
    for title,desc in [
        ("온라인 기반 실습", "강의·실습 플랫폼에서 Python·데이터 분석·AI 등을 학습합니다."),
        ("현직 전문가 피드백", "직무 관점의 코칭과 발표 피드백을 학습에 활용합니다."),
        ("팀 프로젝트", "문제 정의부터 분석·구현·제안까지 협업합니다.")]:
        with st.expander(title):
            st.write(desc)
    st.caption("교육 운영 방식과 혜택은 지원 기수의 공식 모집공고를 최종 확인하세요.")
    st.link_button("공식 프로그램 안내", "https://aivle.kt.co.kr/home/main/programMain?mcd=HM02001000")

elif S.page == "노하우":
    st.title("💡 경험과 학습 노하우")
    t1,t2=st.tabs(["선배들의 후기", "10기 프로젝트 구경하기"])
    with t1:
        
        track=st.selectbox("트랙",["전체","DX 컨설턴트","AI 개발자"],key="review_track")
        reviews=[
          ("7기","DX 컨설턴트","고객 데이터 분석과 제안 경험", "고객 군집화·서비스 제안 사례를 돌아봅니다.", "이 프로젝트의 분석/발표 흐름을 내 포트폴리오와 비교해 볼 수 있습니다.","https://puffero.tistory.com/17"),
          ("8기","DX 컨설턴트","기획·협업 도구 활용", "RFP·WBS·스토리보드 등의 산출물 사례를 살펴봅니다.", "팀 단위 역할과 문제 정의 과정에서 쓸 수 있는 도구를 확인해 보세요.", "https://aivleview.tistory.com/29"),
          ("9기","DX 컨설턴트","AI 서비스 실습 기록", "개인비서·문서기반 검색 챗봇 사례를 참고합니다.", "서비스 화면만이 아니라 RAG 근거와 검증 과정을 남겨 보세요.", "https://hyerong.tistory.com/"),
          ("4기","AI 개발자","수어 인식·웹 서비스 연계", "인식 모델을 사용자용 서비스로 연결한 사례를 살펴봅니다.", "모델의 역할과 사용자가 경험하는 기능을 함께 설명해 보세요.", "https://for-ahyun.tistory.com/45"),
        ]
        for cohort,major,topic,experience,tip,link in reviews:
            if track not in ("전체",major): continue
            with st.expander(f"{cohort} · {major} | {topic}"):
                st.write(f"**경험 요약(블로그/백서 참고):** {experience}")
                st.write(f"**학습 적용 아이디어(서비스 제안):** {tip}")
                
                st.link_button("원문 후기 열기",link)
    with t2:
        project=st.radio("프로젝트",["미니프로젝트","빅프로젝트"],horizontal=True)
        if project=="미니프로젝트":
            with st.container(border=True):
                st.markdown("**10기 DX 4차 | RAG 기반 AIVLE 학습 도우미**")
                st.write("**해결 과제:** 흩어진 AIVLE 정보·후기를 문서 근거와 함께 찾도록 돕기")
                st.write("**기술:** PDF 로딩, 청킹, 임베딩, Chroma, LangChain, Streamlit")
                st.write("**기능:** 백서 PDF 업로드 · 자동 벡터화 · 출처가 있는 채팅")
                st.write("**산출물:** 통합 백서, 노트북 코드, 보고서 및 시연")
                
        else:
            st.info("10기 빅프로젝트의 공개 검증 자료와 시연 영상이 아직 이 파일에 포함되어 있지 않습니다. 확인되지 않은 결과는 게시하지 않습니다.")
        

elif S.page == "학습전략":
    st.title("📚 학습전략")
    guide, timetable = st.tabs(["기초 학습 가이드", "시간표 설정"])
    with guide:
        st.markdown("**추천 학습 순서**")
        for title, detail in [
            ("Python 기초", "변수와 자료형 → 조건문 → 반복문 → 함수"),
            ("데이터 분석", "pandas 데이터 정제 → 시각화 → 해석"),
            ("AI 학습", "회귀·분류 → 모델 평가 → 딥러닝의 기초"),
            ("프로젝트", "문제 정의 → 구현 → 검증 → 발표"),
        ]:
            with st.expander(title):
                st.write(detail)
        if st.button("이 학습 주제로 질문하기", key="study_chat", type="primary"):
            navigate("AI에게 질문하기")
    with timetable:
        render_schedule("strategy", editable=True, show_stats=False)

elif S.page == "환경설정":
    st.title("⚙️ 환경설정")
    # Streamlit 폼은 저장 버튼을 누르기 전까지 기존 적용값을 변경하지 않습니다.
    with st.form("aivle_settings", clear_on_submit=False):
        st.subheader("답변 스타일")
        fmt_options = ["간결", "표준", "상세"]
        tone_options = ["자신감을 주는", "다정한", "차분한", "엄격한", "격려하는 코치"]
        answer_format = st.selectbox("답변 분량", fmt_options,
            index=fmt_options.index(S.answer_format) if S.answer_format in fmt_options else 1)
        answer_tone = st.selectbox("답변 태도", tone_options,
            index=tone_options.index(S.answer_tone) if S.answer_tone in tone_options else 0)
        st.divider()
        st.subheader("음성 답변")
        model_options=list(TTS_MODELS)
        tts_model = st.selectbox("음성 합성 모델", model_options,
            index=model_options.index(S.tts_model) if S.tts_model in model_options else 0)
        # 모델을 변경하더라도 같은 폼 안에서 모든 목소리를 고를 수 있게 유지하고 저장 시 검증합니다.
        voice_options=list(ALL_VOICES)
        tts_voice = st.selectbox("목소리", voice_options,
            index=voice_options.index(S.tts_voice) if S.tts_voice in voice_options else 0)
        tts_speed = st.slider("음성 속도", 0.5, 2.0, float(S.tts_speed), 0.1)
        stt_options=list(STT_MODELS)
        stt_model = st.selectbox("음성 인식 모델", stt_options,
            index=stt_options.index(S.stt_model) if S.stt_model in stt_options else 0)
        st.divider()
        st.subheader("화면 설정")
        chat_height = st.slider("대화 영역 높이(px)", 300, 900,
            int(min(900,max(300,S.chat_height))), 50)
        theme_options = ["시스템", "라이트", "다크"]
        theme_mode = st.radio("화면 모드", theme_options,
            index=theme_options.index(S.theme_mode) if S.theme_mode in theme_options else 0,
            horizontal=True)
        save_settings = st.form_submit_button("설정 저장", type="primary", use_container_width=True)
    if save_settings:
        # 저장할 때만 반영하므로 드롭다운 항목을 한 번 클릭하면 그대로 저장됩니다.
        S.answer_format = answer_format
        S.answer_tone = answer_tone
        S.tts_model = tts_model
        S.tts_voice = tts_voice if tts_model == "gpt-4o-mini-tts" or tts_voice in CLASSIC_VOICES else "alloy"
        S.tts_speed = float(tts_speed)
        S.stt_model = stt_model
        S.chat_height = int(chat_height)
        S.theme_mode = theme_mode
        st.toast("설정이 저장되었습니다.")
        st.rerun()
    st.divider()
    st.subheader("사이드바 메뉴 순서")
    if "menu_draft" not in S or set(S.menu_draft) != set(DEFAULT_MENU):
        S.menu_draft = list(S.menu_order)
    menu=[x for x in S.menu_draft if x!="AI에게 질문하기" and x in DEFAULT_MENU]
    if menu:
        selected = st.selectbox("이동할 메뉴", menu, key="menu_reorder_choice")
        up_col, down_col, reset_col = st.columns(3)
        with up_col: up = st.button("↑ 위로", use_container_width=True)
        with down_col: down = st.button("↓ 아래로", use_container_width=True)
        with reset_col: reset = st.button("기본 순서", use_container_width=True)
        if reset:
            S.menu_draft = list(DEFAULT_MENU)
            st.rerun()
        if up or down:
            idx = menu.index(selected)
            target = idx + (-1 if up else 1)
            if 0 <= target < len(menu):
                menu[idx], menu[target] = menu[target], menu[idx]
                S.menu_draft = ["AI에게 질문하기"] + menu
                st.rerun()
        st.write(" → ".join(S.menu_draft))
        if st.button("메뉴 순서 저장", key="save_menu_order", type="primary", use_container_width=True):
            S.menu_order = list(S.menu_draft)
            st.toast("메뉴 순서가 저장되었습니다.")
            st.rerun()
    st.divider()
    st.subheader("학습 데이터 백업")
    st.download_button("JSON 백업 다운로드", safe_backup(), file_name="aivle_study_backup.json",
        mime="application/json", use_container_width=True)
    saved=st.file_uploader("백업 JSON 불러오기", type=["json"], key="study_backup_upload")
    if saved is not None and st.button("백업 복원", type="primary"):
        try:
            restore_backup(saved.getvalue())
            S.menu_draft = list(S.menu_order)
            st.toast("백업을 복원했습니다.")
            st.rerun()
        except Exception as exc:
            st.error(f"백업 파일을 확인해 주세요 ({type(exc).__name__}).")

elif S.page == "AI에게 질문하기":
    st.title("💬 AI에게 질문하기")
    name,_=active_document()
    if name:
        st.caption(f"현재 검색 문서: {name} · 문서 변경과 업로드는 왼쪽 사이드바에서 가능합니다.")
    else:
        st.info("왼쪽 사이드바에서 백서 PDF를 업로드하거나 기본 백서를 선택해 주세요.")
    render_popular_questions("full",expanded=True)
    render_recommendations("full",compact=False)
    st.divider()
    with chat_history_container():
        render_message_history("full")
    render_chat_input("full")
    x,y=st.columns(2)
    with x:
        if S.messages:
            st.download_button("📥 대화 기록 TXT 저장",export_conversation().encode("utf-8-sig"),
                file_name="aivle_guide_conversation.txt",mime="text/plain",use_container_width=True)
    with y:
        if st.button("🗑️ 대화 초기화",key="full_clear",use_container_width=True):
            S.messages,S.audio_responses=[],{}
            st.rerun()
    

if S.page!="AI에게 질문하기":
    with st.container(key="chat_float"):
        if st.button("AI",key="float_chat_button",help="AI 도우미 열기"):
            chatbot_dialog()
