# [셀 03] 공통 UI, 디자인, 사용자 설정, 질문 데이터
"""AIVLE Guide 3차 추가수정본 — 간결한 UI와 월·주·일 학습 캘린더."""
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
DEFAULT_MENU = ["AI에게 질문하기", "홈", "에이블스쿨이란?", "공지사항", "노하우", "학습전략", "문의", "환경설정"]
LOGO_URL = "https://raw.githubusercontent.com/Jangrae/img/master/aivle.png"
DEFAULTS = {
    "page": "홈", "messages": [], "pdf_hash": None, "pdf_name": None,
    "pdf_bytes": None, "source_choice": "첨부 PDF", "feedback": {},
    "weekly_hours": 8, "level": "기초", "goal": "Python·데이터 분석 기초 익히기",
    "days": {"월":1.0,"화":1.0,"수":1.0,"목":1.0,"금":1.0,"토":2.0,"일":1.0},
    "study_checks": {}, "study_logs": [], "study_events": [],
    "calendar_anchor": today_kst(), "calendar_view": "월", "audio_responses": {},
    "answer_format": "표준", "answer_tone": "차분한", "tts_model": "gpt-4o-mini-tts",
    "tts_voice": "marin", "tts_speed": 1.0, "stt_model": "whisper-1",
    "theme_mode": "시스템", "menu_order": list(DEFAULT_MENU), "chat_height": 500,
}
for key, default in DEFAULTS.items():
    if key not in S:
        S[key] = default

# [UI-S01] Streamlit의 정적 테마를 재설정하는 대신 앱 전체 색을 CSS로 전환합니다.
# 시스템 선택 시 브라우저/OS의 prefers-color-scheme을 따릅니다.
LIGHT = {"bg":"#F8FBFA", "side":"#ECF6F1", "surface":"#FFFFFF", "text":"#203F38",
         "sub":"#537568", "border":"#D5E8DD", "hero_a":"#DAF2E8", "hero_b":"#F8FCFA",
         "lightbtn":"#E8F4EC", "soft":"#F0F8F4"}
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
[data-testid="stMainBlockContainer"] {max-width:1220px!important;padding-top:1.7rem!important;padding-bottom:3rem!important;}
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
/* 플로팅 버튼: 작아진 원형, 이모지 대신 가독성 높은 AI 표기 */
.st-key-chat_float {position:fixed;right:25px;bottom:25px;z-index:9998;width:64px;}
.st-key-chat_float button,.st-key-chat_float button:hover,.st-key-chat_float button:focus {
 width:64px!important;height:64px!important;min-height:64px!important;
 border:0!important;border-radius:50%!important;background:#146F58!important;
 color:#FFFFFF!important;font-size:23px!important;font-weight:850!important;letter-spacing:-.03em;
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
</style>""", unsafe_allow_html=True)


MENU_ICON = {"AI에게 질문하기":"💬", "홈":"🏠", "에이블스쿨이란?":"🎓",
             "공지사항":"📢", "노하우":"💡", "학습전략":"📚", "문의":"✉️", "환경설정":"⚙️"}
QUESTIONS = [
    "비전공자도 에이블스쿨에 지원할 수 있나요?",
    "AI 개발자와 DX 컨설턴트는 무엇이 다른가요?",
    "미니프로젝트와 빅프로젝트는 어떻게 다른가요?",
    "7·8·9기 DX 미니프로젝트는 몇 차까지 진행됐나요?",
    "취업 지원 프로그램에는 무엇이 있나요?",
    "출석인정요청은 언제까지 가능한가요?",
    "국민내일배움카드가 없어도 지원할 수 있나요?",
    "훈련장려금 11만 6천 원과 30만 원은 왜 다른가요?",
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


def tone_render(text):
    """근거 답변 본문은 공통으로 보존하고 문장 앞의 안내 어조만 바꿉니다.

    모든 톤은 동일한 RAG 답변과 동일한 출처를 공유하므로 사실 내용은 달라지지 않습니다.
    """
    openers = {
        "차분한": "",
        "다정한": "차근차근 함께 살펴볼게요.\n\n",
        "엄격한": "확인된 근거와 조건을 중심으로 정리합니다.\n\n",
        "자신감을 주는": "좋아요. 중요한 내용을 하나씩 짚어볼게요.\n\n",
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
    S.messages.append({"role":"assistant", "content":response, "sources":sources, "question":question})


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
            st.success(f"검색 준비 완료 · {rag.chunk_count}개 청크")
        except Exception as exc:
            st.error(f"PDF 벡터화 실패 ({type(exc).__name__}).")
    else:
        st.caption("API 키 미설정 · 화면 미리보기 모드")
    st.caption("업로드 문서는 현재 사용자 세션에서 사용합니다. 민감정보 업로드는 피하세요.")


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
            # 완료 기준 0 / 30분 / 1시간 / 2시간 / 3시간 / 4시간 이상
            level = (0 if minutes == 0 else 1 if minutes < 30 else 2 if minutes < 60
                     else 3 if minutes < 120 else 4 if minutes < 180 else 5)
            shades = ["var(--guide-surface)", "rgba(28,141,105,.16)",
                      "rgba(28,141,105,.29)", "rgba(28,141,105,.44)",
                      "rgba(20,115,87,.68)", "#12664F"]
            bg = shades[level]
            color = "#FFFFFF" if level >= 4 else "var(--guide-text)"
            classes = ("other-month " if day.month != month else "") + ("today-cell" if day == today else "")
            plan_count = sum(e.get("status") != "완료" for e in day_events)
            tooltip = (f"{day:%Y-%m-%d} / 완료 {fmt_hours(minutes)} / "
                       f"계획 {plan_count}건")
            if day_events:
                tooltip += " / " + " · ".join(f"{e['start']}~{e['end']} {e['title']} ({e['status']})" for e in day_events[:5])
            note = f'<span class="day-total">{fmt_hours(minutes)}</span>' if minutes else ""
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
            label = f'<span>{used}분</span>' if used else ""
            row.append(f'<td title="{tooltip}" style="background:{background};color:{ink}">{label}</td>')
        row.append('</tr>')
        rows.append(''.join(row))
    rows.append('</tbody>')
    minimum = 'min-width:560px;' if days==7 else 'min-width:250px;'
    return '<div class="guide-heatmap-wrap"><table class="guide-heatmap" style="'+minimum+'">' + ''.join(rows) + '</table></div>'


def render_schedule(prefix, editable=True):
    """홈과 학습전략이 같은 S.study_events, 달력 날짜와 보기 모드를 공유합니다."""
    options = ["월", "주", "일"]
    key_view = f"{prefix}_schedule_view"
    # 서로 다른 페이지에서 번갈아 볼 때도 마지막 선택 보기 유지
    if S.get(key_view) != S.calendar_view:
        S[key_view] = S.calendar_view
    def view_changed():
        # Streamlit 버전에 따라 선택된 항목을 다시 누르면 None이 될 수 있어 월을 기본값으로 복원합니다.
        S.calendar_view = S.get(key_view) or "월"
    st.segmented_control("시간표 보기", options, key=key_view, on_change=view_changed)
    view = S.calendar_view
    nav_a, nav_b, nav_c, picker = st.columns([1, 1, 1, 3], vertical_alignment="bottom")
    with nav_a:
        prev = st.button("‹ 이전", key=f"{prefix}_previous", use_container_width=True)
    with nav_b:
        now = st.button("오늘", key=f"{prefix}_today", use_container_width=True)
    with nav_c:
        following = st.button("다음 ›", key=f"{prefix}_next", use_container_width=True)
    if prev or following:
        S.calendar_anchor = shift_calendar(S.calendar_anchor, view, -1 if prev else 1)
    elif now:
        S.calendar_anchor = today_kst()
    date_key = f"{prefix}_jump_date"
    if S.get(date_key) != S.calendar_anchor:
        S[date_key] = S.calendar_anchor
    def changed_date():
        S.calendar_anchor = S[date_key]
    with picker:
        st.date_input("기준 날짜", key=date_key, on_change=changed_date)
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
        a,b,c = st.columns(3)
        a.metric("완료한 학습", fmt_hours(total))
        b.metric("공부한 날짜", f"{distinct}일")
        c.metric("등록 일정", f"{len(events)}개")
        st.markdown(month_heatmap_html(anchor, events),unsafe_allow_html=True)
        st.caption("'완료'로 표시한 학습시간만 색에 반영됩니다. 날짜 위에 마우스를 올려 일정을 확인하고, 일 보기에서 세부 내용을 볼 수 있어요.")
    elif view == "주":
        first = week_start(anchor)
        end = first + timedelta(days=7)
        events = events_in_range(first, end)
        total = sum(completed_minutes([e for e in events if e['date']==(first+timedelta(days=i)).isoformat()]) for i in range(7))
        st.markdown(f"**{first:%Y-%m-%d} ~ {(end-timedelta(days=1)):%Y-%m-%d}** · 완료 {fmt_hours(total)}")
        st.markdown(heatmap_html(first, events, days=7),unsafe_allow_html=True)
        st.caption("각 칸은 해당 시간대에 실제 완료한 학습 분량입니다. 흐린 칸도 마우스를 올리면 계획된 일정을 확인할 수 있어요.")
    else:
        first = anchor
        events = events_in_range(first, first+timedelta(days=1))
        total = completed_minutes(events)
        st.markdown(f"**{anchor:%Y-%m-%d} ({WEEKDAYS[anchor.weekday()]})** · 완료 {fmt_hours(total)}")
        st.markdown(heatmap_html(anchor, events, days=1), unsafe_allow_html=True)
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



def safe_backup():
    """개인 정보 유출을 피하기 위해 PDF·대화·API 키는 백업에 포함하지 않습니다."""
    keys = ["level", "weekly_hours", "goal", "days", "study_events", "study_logs",
            "menu_order", "answer_format", "answer_tone", "tts_model", "tts_voice",
            "tts_speed", "stt_model", "theme_mode", "chat_height", "calendar_view"]
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
    if isinstance(order,list) and set(order)==set(DEFAULT_MENU) and len(order)==len(DEFAULT_MENU):
        S.menu_order=["AI에게 질문하기"]+[x for x in order if x!="AI에게 질문하기"]
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
        st.info("위의 추천 질문을 누르거나 아래에서 직접 질문해 보세요.")
    last_assistant = max((i for i,m in enumerate(S.messages) if m["role"]=="assistant"), default=-1)
    for i,msg in enumerate(S.messages):
        with st.chat_message(msg["role"]):
            displayed = tone_render(msg["content"]) if msg["role"]=="assistant" else msg["content"]
            st.markdown(displayed)
            if msg["role"]!="assistant": continue
            srcs=msg.get("sources",[])
            if srcs:
                with st.expander(f"📚 근거 보기 ({len(srcs)}개 검색 근거)"):
                    original_name,original_bytes=active_document()
                    if original_bytes:
                        st.download_button("📄 원문 PDF 저장", data=original_bytes,
                            file_name=original_name or "source.pdf",mime="application/pdf",key=f"src_download_{prefix}_{i}")
                    for j,src in enumerate(srcs,1):
                        page_label=f"{src['page']}페이지" if src.get('page') else "페이지 미상"
                        title=f"{j}. {src.get('name','백서')} · {page_label} · {src.get('section','본문')}"
                        ids=", ".join(src.get("ids",[])) or "표시된 근거 번호 없음"
                        excerpt=src.get("excerpt","")
                        card=("<div class='evidence-card'>"
                              f"<div><strong>{html.escape(title)}</strong></div>"
                              f"<div>원문 근거 번호: {html.escape(ids)}</div>"
                              f"<div class='evidence-excerpt'>{html.escape(excerpt)}</div>"
                              "<div>상세 내용은 PDF 원문에서 확인하세요.</div></div>")
                        st.markdown(card,unsafe_allow_html=True)
            # [UI-C02] 음성 설정(모델·목소리·배속)과 톤이 캐시 키에 포함됩니다.
            setting=json.dumps([displayed,S.tts_model,S.tts_voice,float(S.tts_speed)],ensure_ascii=False)
            speech_key=hashlib.sha256(setting.encode("utf-8")).hexdigest()[:22]
            if st.button("🔊 답변 듣기",key=f"listen_{prefix}_{i}",help="필요할 때만 TTS API를 호출합니다"):
                if not get_api_key(): st.warning("OPENAI_API_KEY가 필요합니다.")
                else:
                    try:
                        with st.spinner("선택한 설정으로 음성 생성 중..."):
                            S.audio_responses[speech_key]=synthesize_answer(displayed,get_api_key(),
                                model=S.tts_model,voice=S.tts_voice,speed=S.tts_speed)
                    except Exception as exc:
                        st.error(f"음성 변환 실패: {type(exc).__name__}. 음성 모델·목소리를 확인해 주세요.")
            if speech_key in S.audio_responses:
                st.audio(S.audio_responses[speech_key],format="audio/mp3")
            c1,c2=st.columns(2)
            with c1:
                if st.button("👍 도움이 됐어요",key=f"fb_yes_{prefix}_{i}"):
                    S.feedback[i]="helpful"; st.toast("피드백 감사합니다!")
            with c2:
                if st.button("⚠️ 근거가 맞지 않아요",key=f"fb_no_{prefix}_{i}"):
                    S.feedback[i]="incorrect"; st.toast("현재 세션에 의견을 기록했어요.")
            # [UI-C03] 관련 질문은 답변 카드 내부의 마지막, 답변 듣기 아래 위치합니다.
            if i==last_assistant:
                st.caption("🔎 이 답변에 이어서 물어보기")
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
        content=m["content"] if m["role"]=="user" else tone_render(m["content"])
        rows.extend([f"[{who}]",content,""])
        if m["role"]=="assistant" and m.get("sources"):
            rows.append("검색 근거: " + " / ".join(
                f"{s.get('id','D?')} {s.get('name','백서')} {s.get('page') or '?'}쪽" for s in m['sources'][:5]))
            rows.append("")
    return "\n".join(rows)


def render_recommendations(prefix,compact=False):
    # 추천 질문은 열기/닫기가 가능한 접이식 영역입니다.
    with st.expander("✨ 추천 질문", expanded=True):
        with st.container(key=f"recs_{prefix}"):
            cols=st.columns(2)
            for i,q in enumerate(QUESTIONS[:4] if compact else QUESTIONS):
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


def render_top_five():
    top=top_questions()
    if not top:
        st.caption("아직 질문이 없어 추천 FAQ로 대신 표시합니다.")
        top=[(q,None) for q in QUESTIONS[:5]]
    else:
        st.caption("앱 서버에 기록된 질문 횟수 기준이며 서버 재시작 시 초기화될 수 있습니다.")
    for i,(q,count) in enumerate(top[:5],1):
        st.markdown(f"**{i}. {q}**")
        if count is not None: st.caption(f"{count}회 질문")


def render_popular_questions():
    with st.expander("☰ 많이 묻는 질문 TOP 5", expanded=False):
        render_top_five()


@st.dialog("💬 AIVLE Guide AI 도우미",width="large")
def chatbot_dialog():
    st.caption("백서 근거 중심 AI 도우미 · 문서 업로드는 왼쪽 사이드바에서 진행")
    render_recommendations("popup",compact=True)
    with st.container(height=int(S.chat_height),border=True):
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
# [셀 06] 사이드바 / 홈 / 나머지 페이지 / 환경설정 / AI 채팅
# [UI-P01] AI 메뉴는 최상단 고정, 나머지 목차는 환경설정에서 순서 변경할 수 있습니다.
with st.sidebar:
    st.image(LOGO_URL, use_container_width=True)
    st.caption("AIVLE School 학습 · 정보 길잡이")
    st.divider()
    with st.container(key="nav_ai"):
        if st.button("💬 AI에게 질문하기",key="nav_ai_button",use_container_width=True):
            navigate("AI에게 질문하기")
    for page in S.menu_order:
        if page == "AI에게 질문하기": continue
        if st.button(f"{MENU_ICON[page]}  {page}",key=f"nav_{page}",
                     type="primary" if S.page==page else "secondary",use_container_width=True):
            navigate(page)
    st.divider()
    # [UI-P02] 유일한 PDF 업로더 위치. 드래그앤드롭 기본 지원.
    document_upload()
    st.divider()
    # 인기 질문은 AI 채팅 페이지에서 확인할 수 있습니다.
    st.markdown("[KT AIVLE School 공식 홈페이지](https://aivle.kt.co.kr/)")

if S.page == "홈":
    st.markdown("""<div class="hero"><small>KT AIVLE SCHOOL</small>
      <h1>AI와 DX, 내일의 가능성을 만나다</h1>
      <p>KT AIVLE School은 AI·데이터·클라우드를 활용해 실제 기업의 문제를 해결하는 경험을 쌓는
      실무형 인재양성 프로그램입니다. 기초 학습부터 프로젝트, 진로 준비까지 이어집니다.</p>
      </div>""",unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    with c1:
        if st.button("🎓 교육과정 안내",use_container_width=True): navigate("에이블스쿨이란?")
    with c2:
        if st.button("📚 나만의 학습전략",use_container_width=True): navigate("학습전략")
    with c3:
        if st.button("💬 AI 도우미 시작",type="primary",use_container_width=True): navigate("AI에게 질문하기")
    st.divider()
    st.subheader("나의 학습 계획")
    # 학습전략의 목표·실행점검·시간표 데이터와 실시간 동기화합니다.
    completed_checks=sum(bool(S.get(f"execute_{i}",False)) for i in range(5))
    a,b,c = st.columns(3)
    a.metric("이번 주 목표", f"{S.weekly_hours}시간")
    b.metric("학습 수준", S.level)
    c.metric("실행 점검", f"{completed_checks}/5")
    st.caption(f"학습 목표: {S.goal}")
    if S.study_logs:
        last=S.study_logs[-1]
        st.caption(f"최근 실행 기록 · {last.get('날짜','')} · {last.get('실제시간',0)}시간 학습 · 실습 {last.get('실습완료',0)}개")
    render_schedule("home",editable=True)
    st.caption("시간표와 기록은 현재 세션에 저장됩니다. 장기 보관은 환경설정의 JSON 백업을 이용하세요.")


elif S.page == "에이블스쿨이란?":
    st.title("🎓 에이블스쿨이란?")
    st.write("KT AIVLE School은 AI와 디지털 전환(DX) 분야의 실무 역량을 키우는 교육 프로그램입니다.")
    st.subheader("교육 목적")
    st.markdown("산업·고객의 문제를 이해하고, 데이터·AI·클라우드 기술을 활용해 서비스나 실행 전략으로 연결하는 능력을 기르는 데 중점을 둡니다.")
    st.subheader("트랙 비교")
    st.table({"구분":["중심 역할","주요 학습·활동","대표 산출물"],
              "AI 개발자":["AI 서비스 구현","데이터·모델·API·서비스 개발","모델 성능 검증, 웹 서비스 구현"],
              "DX 컨설턴트":["기업 DX 과제 설계·제안","고객 문제 분석, 서비스 설계, 솔루션 제안","분석 근거, 제안서, 프로토타입"]})
    st.subheader("교육의 큰 흐름")
    st.markdown("**기초 역량 학습 → 미니프로젝트 → 빅프로젝트 → 진로·취업 준비**")
    st.subheader("에이블스쿨의 주요 학습 경험")
    a,b,c=st.columns(3)
    for col,head,desc in [
        (a,"🌐 온라인 중심 실습","강의·실습 플랫폼에서 기초 개념을 익히고 적용합니다."),
        (b,"🧑‍🏫 현직 전문가 피드백","기업 실무 관점의 코칭과 발표 피드백을 반영합니다."),
        (c,"🛠️ 팀 기반 프로젝트","문제 정의에서 분석·구현·제안까지 협업합니다."),
    ]:
        with col:
            st.markdown(f'<div class="panel"><strong>{head}</strong><p>{desc}</p></div>',unsafe_allow_html=True)
    st.subheader("학습 환경·지원")
    st.markdown("- 비대면 중심 수업 및 실습\n- 취업 컨설팅·잡페어 등 진로 지원\n- 세부 혜택과 채용 우대는 모집 기수별 공고 확인")
    st.link_button("공식 프로그램 안내", "https://aivle.kt.co.kr/home/main/programMain?mcd=HM02001000")

elif S.page == "공지사항":
    st.title("📢 공지사항")
    st.warning("실시간 공지 API에 연결되어 있지 않습니다. 아래 항목은 분류·확인 경로를 위한 안내이며 실제 게시일과 변경 사항은 공식 공지를 기준으로 확인해야 합니다.")
    section = st.selectbox("공지 분류", ["전체", "모집", "교육", "프로젝트", "행정"])
    notices = [
        ("모집", "지원 자격 및 모집 일정", "해당 모집 기수", "공식 게시일 확인", "최신 모집공고의 변경 여부 확인"),
        ("교육", "학습 과정과 교육 운영", "소속 기수", "운영 공지 확인", "교육 방식·운영 시간 확인"),
        ("프로젝트", "프로젝트 수행 및 제출", "소속 기수", "강의실 공지 확인", "과제 마감·파일 형식 확인"),
        ("행정", "출결·지원금·수료 관련 문의", "개인별 상이", "운영 공지 확인", "개별 판정은 담당자 확인"),
    ]
    for category,title,cohort,posted,change in notices:
        if section != "전체" and section != category:
            continue
        with st.expander(f"[{category}] {title}", expanded=False):
            st.write(f"**적용 기수:** {cohort}")
            st.write(f"**게시일:** {posted}")
            st.write(f"**확인할 변경 사항:** {change}")
    st.link_button("AIVLE School 공식 홈페이지", "https://aivle.kt.co.kr/")

elif S.page == "노하우":
    st.title("💡 에이블러 노하우")
    t1,t2 = st.tabs(["1. 선배들의 후기", "2. 10기 프로젝트 구경하기"])
    with t1:
        st.info("아래 조언은 공개된 교육생 후기와 백서에서 재구성한 내용으로, 공식 평가 기준이나 운영 규정이 아닙니다.")
        filter_track = st.selectbox("트랙", ["전체", "DX 컨설턴트", "AI 개발자"], key="review_track")
        reviews = [
            ("7기", "DX 컨설턴트", "미니프로젝트", "고객 데이터 분석에서 서비스 제안으로 확장한 경험", "스마트 횡단보도 제안·고객 군집화 후기를 참고", "https://puffero.tistory.com/17"),
            ("8기", "DX 컨설턴트", "협업과 기획", "RFP·WBS·스토리보드를 활용한 서비스 기획 경험", "요구사항과 산출물의 연결을 중요하게 살펴보기", "https://aivleview.tistory.com/29"),
            ("9기", "DX 컨설턴트", "AI 서비스", "AI 개인비서·백서 검색 챗봇 등 서비스 구현 사례", "구현뿐 아니라 발표와 업무 맥락을 설명하기", "https://hyerong.tistory.com/"),
            ("4기", "AI 개발자", "서비스 개발", "수어 이미지 인식 모델과 웹 서비스 연계 과제", "모델을 실제 사용자 화면으로 연결해 보기", "https://for-ahyun.tistory.com/45"),
        ]
        for cohort,track,topic,experience,advice,link in reviews:
            if filter_track != "전체" and filter_track != track:
                continue
            with st.expander(f"{cohort} · {track} | {topic}"):
                st.write("**학습·협업 경험:**", experience)
                st.write("**후배에게 주는 조언:**", advice)
                st.caption("작성일: 원문에서 확인 필요 · 개인 공개 후기 기반 재구성")
                st.link_button("후기 원문", link)
    with t2:
        kind = st.segmented_control("프로젝트 유형", ["미니프로젝트", "빅프로젝트"], default="미니프로젝트")
        if kind == "미니프로젝트":
            st.markdown("### 10기 DX 4차 미니프로젝트 — RAG 학습 도우미")
            st.markdown("- **문제:** AIVLE School 정보와 선배 경험이 흩어져 있음\n- **기술:** PDF 로딩, 텍스트 분할, 임베딩, Chroma, RAG, Streamlit\n- **주요 기능:** 백서 업로드, 문서 검색, 근거 기반 질의응답\n- **결과물:** 통합 백서 PDF, 웹 앱, 결과 보고서")
            st.caption("교육 제공 자료를 기반으로 작성한 10기 진행 중 과제. 팀별 시연 링크·영상은 공개 가능 여부를 확인한 뒤 추가하세요.")
        else:
            st.info("10기 빅프로젝트는 이 자료에서 구체적인 최종 결과를 확인할 수 없습니다. 수행 후 공개 허가를 받은 결과물·시연 영상·팀 회고를 추가하세요.")
        st.caption("미공개 프로젝트 산출물이나 내부 교육자료를 허가 없이 외부에 공개하지 마세요.")

elif S.page == "학습전략":
    st.title("📚 학습전략 · 나만의 학습 도우미")
    st.caption("통합 백서의 '개인 학습 계획과 실행 점검' 항목을 활용하기 위한 화면 초안입니다. 아래 배분과 체크리스트는 개인 학습 권고안이며 공식 성적·수료 판정과 무관합니다.")
    pre,plan,timetable,check = st.tabs(["① 사전학습", "② 개인 학습계획", "③ 시간표 설정", "④ 실행점검"])
    with pre:
        st.subheader("학습 순서 가이드")
        for head,desc in [
            ("1. Python 기초", "변수·자료형 → 조건문 → 반복문 → 함수 → 간단한 파일 처리"),
            ("2. 데이터 분석", "pandas DataFrame, 결측치 처리, 그룹별 집계, 시각화"),
            ("3. 머신러닝", "데이터의 규칙을 학습해 분류·예측하는 방법. 학습/평가 데이터 구분, 지표 해석"),
            ("4. 딥러닝", "여러 층의 신경망을 활용해 복잡한 패턴을 학습하는 방법. 모델 구조와 과적합 이해"),
            ("5. 프로젝트 실습", "예제를 수정하고 오류를 직접 해결하며 결과를 설명해 보기"),
        ]:
            with st.expander(head): st.write(desc)
        st.subheader("내 기초역량 자가 점검")
        skills = ["Python 변수와 자료형을 설명할 수 있다", "조건문과 반복문을 혼자 작성할 수 있다",
                  "함수를 정의하고 호출할 수 있다", "pandas로 데이터를 읽고 처리할 수 있다",
                  "분류와 회귀의 차이를 설명할 수 있다", "모델 결과를 내 말로 설명할 수 있다"]
        for i,label in enumerate(skills):
            st.checkbox(label, key=f"skill_{i}")
        missing = [s for i,s in enumerate(skills) if not S.get(f"skill_{i}", False)]
        if missing:
            st.info("다음 주 보완 제안: " + ", ".join(missing[:3]))
        else:
            st.success("기초 항목을 모두 체크했어요. 실제 예제를 혼자 실행하며 점검해 보세요.")
        st.markdown("**참고 학습 자료:** [Python 공식 튜토리얼](https://docs.python.org/ko/3/tutorial/) · [pandas 사용자 가이드](https://pandas.pydata.org/docs/user_guide/index.html) · 통합 백서의 학습전략 항목")
    with plan:
        st.info("이 계획은 개인 학습 권고안입니다. 정규 교육 시간표·출석 규정과는 별개입니다.")
        a,b = st.columns(2)
        with a:
            S.level = st.selectbox("현재 수준", ["기초", "초급", "중급"], index=["기초","초급","중급"].index(S.level))
            S.weekly_hours = st.slider("주간 학습 가능 시간", 1, 30, S.weekly_hours, 1)
        with b:
            S.goal = st.text_input("이번 주 학습 목표", value=S.goal)
        ratio = {"개념 학습":0.25, "코드 실습":0.40, "복습":0.20, "프로젝트 준비":0.15}
        st.markdown("#### 추천 시간 배분")
        st.table({"영역":list(ratio.keys()), "권고 시간(시간)":[round(S.weekly_hours*r,1) for r in ratio.values()]})
        st.caption("배분 비율: 개념 25% · 코드 실습 40% · 복습 20% · 프로젝트 준비 15% (서비스가 제안하는 기본값)")
        st.markdown("#### 요일별 시간 조정")
        cols = st.columns(7)
        days = {}
        for col,day in zip(cols,["월","화","수","목","금","토","일"]):
            with col:
                days[day] = st.number_input(day, min_value=0.0,max_value=12.0,
                                             value=float(S.days.get(day,0.0)),step=0.5,key=f"day_{day}")
        S.days = days
        total = sum(days.values())
        st.caption(f"요일별 계획 합계: {total:.1f}시간 / 설정한 주간 가능 시간: {S.weekly_hours}시간")
        if abs(total-S.weekly_hours)>0.01:
            st.warning("요일별 계획 합계와 주간 가능 시간이 달라요. 시간을 조정해 주세요.")
        if st.button("📋 내 계획 복사", key="copyplan"):
            st.code(f"학습 수준: {S.level}\n목표: {S.goal}\n주간 권고 학습: {S.weekly_hours}시간\n"+" / ".join(f"{k} {v:g}h" for k,v in days.items()), language="text")
    with timetable:
        st.subheader("🗓️ 나의 날짜·시간별 학습 일정")
        st.caption("홈과 연결된 같은 시간표입니다. 여기서 변경하면 홈에도 즉시 반영됩니다.")
        render_schedule("strategy",editable=True)
    with check:
        st.subheader("실행점검 체크리스트")
        points = ["예제를 혼자 다시 실행할 수 있다", "코드와 결과를 내 말로 설명할 수 있다",
                  "이번 주 복습을 완료했다", "발생한 오류와 해결 과정을 기록했다", "남은 질문을 정리했다"]
        for i,p in enumerate(points):
            st.checkbox(p,key=f"execute_{i}")
        st.divider()
        with st.form("weekly_log",clear_on_submit=True):
            actual = st.number_input("이번 주 실제 학습 시간",min_value=0.0,max_value=100.0,step=0.5)
            completed = st.number_input("완료한 실습 수",min_value=0,step=1)
            errors = st.text_area("해결한 오류 / 남은 질문",height=80)
            submitted = st.form_submit_button("이번 주 기록 저장",type="primary")
            if submitted:
                S.study_logs.append({"날짜":date.today().isoformat(),"계획시간":S.weekly_hours,
                                     "실제시간":actual,"실습완료":completed,"메모":errors})
                st.success("현재 브라우저 세션에 기록했어요.")
        if S.study_logs:
            st.dataframe(S.study_logs,use_container_width=True,hide_index=True)
            last = S.study_logs[-1]
            if last["실제시간"]<last["계획시간"]:
                st.info("다음 주에는 미완료 학습 시간을 조정하고, 가장 중요한 개념 1개부터 복습해 보세요.")
            else:
                st.success("이번 주 계획 시간을 달성했어요. 다음 주에는 새 예제를 혼자 구현해 보세요.")
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer,fieldnames=["날짜","계획시간","실제시간","실습완료","메모"])
            writer.writeheader()
            writer.writerows(S.study_logs)
            st.download_button("학습 기록 CSV 다운로드",buffer.getvalue().encode("utf-8-sig"),
                               file_name="aivle_study_log.csv",mime="text/csv")
        st.caption("기록은 세션에 저장됩니다. 환경설정의 JSON 백업으로 시간표·목표·실행기록을 함께 보관할 수 있습니다.")
    if st.button("💬 이 학습 주제로 질문하기", type="primary"):
        navigate("AI에게 질문하기")

elif S.page == "문의":
    st.title("✉️ 문의")
    st.markdown("**일반 모집·교육 정보**는 AI FAQ 챗봇으로 물어볼 수 있습니다. **개인별 행정 판단**은 담당자의 확인이 필요합니다.")
    a,b = st.columns(2)
    with a:
        st.markdown("### 🤖 일반 안내")
        st.write("모집·교육과정·프로젝트·선배 경험 등 문서 기반 질문")
        if st.button("챗봇 질문하기",use_container_width=True): navigate("AI에게 질문하기")
    with b:
        st.markdown("### 🧑‍💼 운영 담당자 확인")
        st.write("개인 출결 인정, 지원금 지급, 성적·평가, 수료 판정 등")
        st.link_button("공식 FAQ 및 문의 경로", "https://aivle.kt.co.kr/home/brd/faq/main?mcd=MC00000056")
    st.markdown("### 문의 내용 정리 도우미")
    category = st.selectbox("문의 유형",["출결", "지원금", "평가", "수료", "기타"])
    details = st.text_area("확인하고 싶은 내용",placeholder="민감한 개인정보 없이 문의 요점을 적어 주세요.")
    if st.button("문의 문안 생성"):
        if details.strip():
            st.code(f"안녕하세요. 에이블스쿨 운영 관련하여 문의드립니다.\n문의 유형: {category}\n문의 내용: {details.strip()}\n확인 부탁드립니다. 감사합니다.",language="text")
        else:
            st.warning("문의 요점을 먼저 입력해 주세요.")
    st.caption("이 화면은 메시지를 자동 발송하지 않습니다. 운영 담당자의 공식 연락처를 통해 직접 문의해 주세요.")


elif S.page == "환경설정":
    st.title("⚙️ 환경설정")
    st.caption("답변 근거의 사실 내용은 유지하면서 표시 형식, 말투, 음성, 화면 모드, 메뉴 순서를 조정합니다.")
    a,b,c=st.tabs(["💬 답변 스타일", "🔊 음성 · 화면", "↕️ 메뉴 · 데이터 백업"])
    with a:
        st.subheader("답변 형식")
        fmt=["간결", "표준", "상세"]
        S.answer_format=st.selectbox("답변 분량/구성",fmt,index=fmt.index(S.answer_format) if S.answer_format in fmt else 1)
        st.caption("간결: 핵심 중심 · 표준: 근거와 예외 · 상세: 조건 비교 및 세부 설명")
        st.subheader("답변 태도")
        tones=["차분한", "다정한", "엄격한", "자신감을 주는", "격려하는 코치"]
        S.answer_tone=st.selectbox("말투와 분위기",tones,index=tones.index(S.answer_tone) if S.answer_tone in tones else 0)
        st.info("말투를 바꿔도 RAG 본문과 출처는 동일하게 유지합니다. 답변 위에 붙는 안내 어조만 바뀌므로 사실관계가 달라지지 않습니다.")
        st.markdown("**적용 미리보기**")
        st.markdown(tone_render("백서에서 확인한 사실과 출처를 근거로 답변합니다. [D1]"))
    with b:
        st.subheader("음성 답변 설정")
        models=list(TTS_MODELS)
        S.tts_model=st.selectbox("음성 합성 모델 (TTS)",models,
            index=models.index(S.tts_model) if S.tts_model in models else 0)
        voices=list(ALL_VOICES if S.tts_model=="gpt-4o-mini-tts" else CLASSIC_VOICES)
        if S.tts_voice not in voices: S.tts_voice="alloy"
        S.tts_voice=st.selectbox("음성 목소리",voices,index=voices.index(S.tts_voice))
        S.tts_speed=st.slider("음성 답변 속도 (배속)",min_value=0.5,max_value=2.0,
            value=float(S.tts_speed),step=0.1)
        S.stt_model=st.selectbox("음성 질문 인식 모델 (STT)",list(STT_MODELS),
            index=list(STT_MODELS).index(S.stt_model) if S.stt_model in STT_MODELS else 0)
        st.caption("음성 답변은 '🔊 답변 듣기'를 클릭할 때만 생성됩니다. 설정 변경 후 새로 듣기를 누르면 변경한 속도·목소리로 생성합니다.")
        st.caption("현재 음성 합성 API 모델은 향후 변경될 수 있으므로 장기 배포 시 공식 API 문서를 확인하세요.")
        st.divider()
        st.subheader("채팅 화면")
        S.chat_height=st.slider("대화 영역 높이 (px)", min_value=300, max_value=900,
                                value=int(min(900,max(300,S.chat_height))),step=50)
        st.caption("AI에게 질문하기 페이지와 플로팅 AI 채팅창에 공통 적용됩니다.")
        st.divider()
        st.subheader("화면 모드")
        theme=["시스템","라이트","다크"]
        chosen=st.radio("테마",theme,index=theme.index(S.theme_mode) if S.theme_mode in theme else 0,horizontal=True)
        if chosen!=S.theme_mode:
            S.theme_mode=chosen
            st.rerun()
        st.caption("시스템 모드는 사용자의 브라우저/운영체제 다크모드 선호 설정을 따릅니다. 기본 Streamlit 컴포넌트의 내부 스타일은 배포 환경에 따라 일부 다를 수 있습니다.")
    with c:
        st.subheader("사이드바 목차 순서")
        st.caption("요청에 따라 'AI에게 질문하기'는 항상 첫 번째로 고정합니다. 나머지 메뉴는 위/아래 버튼으로 이동할 수 있습니다.")
        menu=[x for x in S.menu_order if x!="AI에게 질문하기"]
        selected=st.selectbox("이동할 메뉴",menu,key="menu_reorder_choice")
        col1,col2,col3=st.columns(3)
        with col1: up=st.button("↑ 위로",use_container_width=True)
        with col2: down=st.button("↓ 아래로",use_container_width=True)
        with col3: reset=st.button("기본 순서",use_container_width=True)
        if reset:
            S.menu_order=list(DEFAULT_MENU); st.rerun()
        if up or down:
            idx=menu.index(selected)
            target=idx+(-1 if up else 1)
            if 0<=target<len(menu):
                menu[idx],menu[target]=menu[target],menu[idx]
                S.menu_order=["AI에게 질문하기"]+menu
                st.rerun()
        st.markdown("**현재 순서**")
        st.write("  →  ".join(f"{i+1}. {x}" for i,x in enumerate(S.menu_order)))
        st.divider()
        st.subheader("나의 학습 계획 · 설정 백업")
        st.caption("시간표/개인 목표/실행기록/환경설정만 저장합니다. PDF, 질문 대화, API 키는 백업에 포함되지 않습니다.")
        st.download_button("📦 JSON 백업 저장",data=safe_backup(),
            file_name="aivle_my_study_backup.json",mime="application/json",use_container_width=True)
        restore_file=st.file_uploader("이전에 저장한 JSON 백업 불러오기",type=["json"],key="study_backup_upload")
        if restore_file is not None and st.button("백업 내용 복원",type="primary"):
            try:
                restore_backup(restore_file.getvalue())
                st.success("개인 계획과 설정을 불러왔습니다.")
                st.rerun()
            except Exception as exc:
                st.error(f"백업 파일을 확인해 주세요 ({type(exc).__name__}).")

elif S.page == "AI에게 질문하기":
    st.title("💬 AI에게 질문하기")
    name,_=active_document()
    st.caption("백서 근거 기반 RAG 질의응답 · PDF 변경/업로드는 왼쪽 사이드바에서만 가능합니다.")
    st.info(f"현재 백서: {name}" if name else "📄 왼쪽 사이드바에서 백서 PDF를 드래그해 업로드해 주세요.")
    # 추천 질문과 많이 묻는 질문을 모두 이 페이지에서 펼쳐 볼 수 있습니다.
    render_recommendations("full",compact=False)
    render_popular_questions()
    st.divider()
    with st.container(height=int(S.chat_height),border=True):
        render_message_history("full")
    render_chat_input("full")
    col1,col2=st.columns(2)
    with col1:
        if S.messages:
            st.download_button("📥 대화 기록 TXT 저장",export_conversation().encode("utf-8-sig"),
                file_name="aivle_guide_conversation.txt",mime="text/plain",use_container_width=True)
    with col2:
        if st.button("🗑️ 대화 초기화",key="full_clear",use_container_width=True):
            S.messages,S.audio_responses=[],{}
            st.rerun()
    st.caption("근거 보기는 PDF 페이지와 원문 구역을 표시합니다. 중요 운영 규정은 원문과 담당자 안내로 최종 확인하세요.")

# 일반 페이지에서만 큰 플로팅 버튼 활성화
if S.page!="AI에게 질문하기":
    with st.container(key="chat_float"):
        if st.button("AI",key="float_chat_button",help="AI 도우미 열기"):
            chatbot_dialog()
