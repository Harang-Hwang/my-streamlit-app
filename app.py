# [셀 03] UI 디자인/CSS/메뉴/세션/질문 데이터 | Ctrl+F로 [수정 포인트 ...] 검색
"""AIVLE Guide: Streamlit multi-page UI + optional PDF RAG.
UI prototype works without OpenAI API key. Full Q&A requires configured key and PDF.
"""
import csv
import hashlib
import re
import io
import os
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="AIVLE Guide | 에이블스쿨 학습 도우미",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp {background:#F8FBFA;}
[data-testid="stSidebar"] {background:#ECF6F1;}
h1,h2,h3 {color:#174F48;}
.hero {background:linear-gradient(110deg,#DAF2E8,#F8FCFA);border:1px solid #C8E2D5;
       border-radius:19px;padding:31px 35px;margin:4px 0 22px;}
.hero small {color:#287E6A;letter-spacing:2px;font-weight:700;}
.hero h1 {margin:9px 0;font-size:34px;}
.hero p {color:#4B6D62;font-size:16px;line-height:1.65;}
.panel {border:1px solid #D5E8DD;border-radius:15px;background:white;padding:18px;min-height:116px;}
.panel strong {color:#155942;}
.muted {font-size:13px;color:#678477;}
/* 라디오 내비게이션을 없애고 버튼만 쓰므로 선택 동그라미가 생기지 않습니다. */
[data-testid="stSidebar"] .stButton button {text-align:left;justify-content:flex-start;
  background:transparent;border:0;border-radius:8px;box-shadow:none;color:#1E584B;
  font-weight:600;padding:10px 13px;min-height:41px;}
[data-testid="stSidebar"] .stButton button:hover {background:#D7ECE0;color:#104B3B;}
[data-testid="stSidebar"] .stButton button[kind="primary"] {background:#D1E9DC!important;
  color:#13583F!important;border-left:3px solid #148465!important;}
button[kind="primary"],button[data-testid="stBaseButton-primary"] {
 background:#17745F!important;border-color:#17745F!important;color:white!important;}
/* 우측 하단 플로팅 이모지 버튼: 기존 112px에서 78px로 내리고, 크기는 키우고 그림자는 줄임 */
.st-key-chat_float {position:fixed;right:25px;bottom:78px;z-index:9998;width:62px;}
.st-key-chat_float button {width:62px!important;height:62px!important;min-height:62px!important;
 border:0!important;border-radius:50%!important;background:#146D57!important;
 color:white!important;font-size:33px!important;padding:0!important;
 box-shadow:0 3px 9px rgba(16,58,44,.15)!important;}
.st-key-chat_float button:hover {background:#115941!important;transform:translateY(-1px);}
/* 채팅 및 인기 질문에 쓰이는 작은 안내 */
.helper {padding:11px 14px;background:#E9F5EF;border-radius:11px;color:#275846;font-size:13px;}
</style>
""", unsafe_allow_html=True)

S = st.session_state
for key, default in {
    "page": "홈", "messages": [], "pdf_hash": None, "pdf_name": None,
    "pdf_bytes": None, "source_choice": "첨부 PDF", "feedback": {},
    "weekly_hours": 8, "level": "기초", "goal": "Python·데이터 분석 기초 익히기",
    "days": {"월":1.0,"화":1.0,"수":1.0,"목":1.0,"금":1.0,"토":2.0,"일":1.0},
    "study_checks": {}, "study_logs": [], "audio_responses": {},
}.items():
    if key not in S:
        S[key] = default

MENU = ["홈", "에이블스쿨이란?", "공지사항", "노하우", "학습전략", "문의"]
MENU_ICON = {"홈":"🏠", "에이블스쿨이란?":"🎓", "공지사항":"📢", "노하우":"💡", "학습전략":"📚", "문의":"✉️"}
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
FOLLOW_UP = ["공식 안내와 선배 후기는 어떻게 구분하나요?", "프로젝트를 준비하는 팁을 알려주세요.", "학습 계획은 어떻게 세우나요?"]
DB = Path(tempfile.gettempdir()) / "aivle_guide_qcounts_v2.sqlite3"
DEFAULT_PDF = Path(__file__).parent / "AIVLE School 백서.pdf"


def navigate(page):
    # 위젯 key를 바꾸지 않고 독립 세션 상태만 변경: WidgetAlreadyInstantiatedError 방지
    S.page = page
    st.rerun()


def count_question(q):
    q = " ".join(q.strip().split())[:200]
    if not q:
        return
    try:
        with sqlite3.connect(DB, timeout=10) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS counts (q TEXT PRIMARY KEY, n INTEGER NOT NULL)")
            conn.execute("INSERT INTO counts(q,n) VALUES (?,1) ON CONFLICT(q) DO UPDATE SET n=n+1", (q,))
    except sqlite3.Error:
        pass


def top_questions():
    try:
        with sqlite3.connect(DB, timeout=10) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS counts (q TEXT PRIMARY KEY, n INTEGER NOT NULL)")
            return conn.execute("SELECT q,n FROM counts ORDER BY n DESC, q LIMIT 5").fetchall()
    except sqlite3.Error:
        return []


def get_api_key():
    # GitHub/Colab 토큰은 앱 코드에 쓰지 않음. Streamlit Secrets에만 OPENAI_API_KEY 설정.
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        return key
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        # Secrets를 아직 등록하지 않은 UI 미리보기에서도 앱이 실행되도록 처리
        return ""


# [셀 04] PDF 저장/벡터화 캐시/RAG 호출/질문 저장 | Ctrl+F로 [수정 포인트 ...] 검색
# [UI/핵심 연결] RAG는 rag_core.py, 음성은 voice_core.py에 각각 모듈화했습니다.
from rag_core import rag_pipeline
from voice_core import transcribe_audio, synthesize_answer


@st.cache_resource(show_spinner="백서를 분석하고 검색 인덱스를 생성하는 중...", max_entries=4)
def build_retriever(file_bytes, file_hash, api_key, document_name):
    """[교안 46쪽 필수] PDF bytes를 임시 .pdf 경로로 저장 → rag_pipeline(path)에 전달.

    Streamlit은 클릭마다 앱을 다시 실행하지만, 같은 파일 해시에는 캐시된
    RAG 객체를 재사용합니다. 문서를 바꾸면 새 해시로 재임베딩됩니다.
    """
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as temp:
        temp.write(file_bytes)
        pdf_path = temp.name
    try:
        rag = rag_pipeline(pdf_path, api_key)
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
    rag.document_name = document_name
    return rag

def active_document():
    if S.source_choice == "기본 백서" and DEFAULT_PDF.exists():
        return DEFAULT_PDF.name, DEFAULT_PDF.read_bytes()
    if S.source_choice == "첨부 PDF" and S.pdf_bytes:
        return S.pdf_name, S.pdf_bytes
    return None, None


def answer_question(question):
    """활성 백서로 검색 후 출처와 함께 반환합니다 (UI와 RAG의 접점)."""
    document_name, pdf_bytes = active_document()
    if pdf_bytes is None:
        return "먼저 **📄 PDF 백서 업로드**에서 자료를 등록해 주세요.", []
    api_key = get_api_key()
    if not api_key:
        return ("OpenAI 연결 정보가 없어 실제 RAG 답변을 만들 수 없습니다. "
                "Streamlit Cloud → Settings → Secrets에 `OPENAI_API_KEY`를 등록해 주세요.", [])
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    rag = build_retriever(pdf_bytes, digest, api_key, document_name)
    result = rag.ask(question)
    return result.answer, result.sources

def submit_question(question):
    question = question.strip()
    if not question:
        return
    S.messages.append({"role":"user", "content":question})
    count_question(question)
    try:
        response, sources = answer_question(question)
    except Exception as exc:
        response = f"문서 검색 또는 답변 생성 중 오류가 발생했습니다: `{type(exc).__name__}`. API 키·PDF·설치 패키지를 확인해 주세요."
        sources = []
    S.messages.append({"role":"assistant", "content":response, "sources":sources})


def document_upload(key_suffix):
    st.markdown("**📄 백서 문서 선택**")
    uploaded = st.file_uploader("PDF 업로드", type=["pdf"], key=f"upload_{key_suffix}")
    if uploaded is not None:
        content = uploaded.getvalue()
        digest = hashlib.sha256(content).hexdigest()
        if digest != S.pdf_hash:
            S.pdf_hash = digest
            S.pdf_bytes = content
            S.pdf_name = uploaded.name
            S.source_choice = "첨부 PDF"
            # 같은 페이지의 선택 위젯이 기본 PDF를 계속 가리키지 않도록 교정
            S[f"source_{key_suffix}"] = "첨부 PDF"
            S.messages = []
            S.audio_responses = {}
        st.caption(f"✅ {uploaded.name} · PDF 업로드 완료")
    options = ["첨부 PDF"]
    if DEFAULT_PDF.exists():
        options.insert(0, "기본 백서")
    # 선택값을 key가 없는 독립 선택 위젯에서 관리
    selected = st.selectbox("답변에 사용할 자료", options,
                            index=options.index(S.source_choice) if S.source_choice in options else 0,
                            key=f"source_{key_suffix}")
    if selected != S.source_choice:
        S.source_choice = selected
        S.messages = []
        S.audio_responses = {}
    name, content = active_document()
    if name and content:
        if get_api_key():
            try:
                digest = hashlib.sha256(content).hexdigest()
                rag = build_retriever(content, digest, get_api_key(), name)
                st.success(f"✅ 검색 준비 완료 · {name} · {rag.page_count}개 페이지 객체 · {rag.chunk_count}개 청크")
            except Exception as exc:
                st.error(f"PDF 벡터화 실패: {type(exc).__name__}. API 키와 PDF 파일을 확인해 주세요.")
        else:
            st.info(f"선택한 문서: {name} · AI 연결 전 UI 테스트 모드")
    else:
        st.info("기본 백서 파일이 없으면 PDF를 업로드해 주세요.")
    st.caption("업로드 자료는 이 화면의 답변 자료로 사용됩니다. 개인·민감정보가 있는 문서는 업로드하지 마세요.")


def rerun_after_question(prefix):
    # st.dialog는 fragment이므로 질문 전송 후에도 창이 닫히지 않도록 합니다.
    if prefix == "popup":
        st.rerun(scope="fragment")
    else:
        st.rerun()


# [셀 05] 채팅 UI/음성 질문/음성 답변/대화 저장 | Ctrl+F로 [수정 포인트 ...] 검색
def render_message_history():
    if not S.messages:
        st.info("추천 질문을 누르거나 직접 질문해 보세요.")
    for i, msg in enumerate(S.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                srcs = msg.get("sources", [])
                if srcs:
                    with st.expander(f"📚 근거 보기 ({len(srcs)}개 검색 조각)"):
                        original_name, original_bytes = active_document()
                        if original_bytes:
                            st.download_button("📄 원문 PDF 열기/저장", data=original_bytes,
                                               file_name=original_name or "source.pdf", mime="application/pdf",
                                               key=f"original_{i}")
                        for j, src in enumerate(srcs, 1):
                            page_label = f"{src['page']}페이지" if src["page"] else "페이지 미상"
                            st.markdown(f"**{j}. {src['name']} · {page_label} · {src['section']}**")
                            if src.get("ids"):
                                st.caption("백서 근거 번호(발췌에서 검출): " + ", ".join(src["ids"]))
                            st.caption(src["excerpt"])
                            st.caption("원문은 업로드한 PDF의 해당 페이지에서 확인해 주세요.")
                # [추가 기능] 3차 AI 개인비서의 TTS를 가져와 답변을 음성으로 재생합니다.
                speech_key = hashlib.sha256(msg["content"].encode("utf-8")).hexdigest()[:20]
                if st.button("🔊 답변 듣기", key=f"listen_{i}", help="요청할 때만 TTS API를 사용합니다"):
                    if not get_api_key():
                        st.warning("OPENAI_API_KEY가 필요합니다.")
                    else:
                        try:
                            with st.spinner("음성 답변을 생성하는 중..."):
                                S.audio_responses[speech_key] = synthesize_answer(msg["content"], get_api_key())
                        except Exception as exc:
                            st.error(f"음성 변환에 실패했습니다 ({type(exc).__name__}).")
                if speech_key in S.audio_responses:
                    st.audio(S.audio_responses[speech_key], format="audio/mp3")
                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button("👍 도움이 됐어요", key=f"fb_yes_{i}"):
                        S.feedback[i] = "helpful"
                        st.toast("피드백 감사합니다!")
                with c2:
                    if st.button("⚠️ 근거가 맞지 않아요", key=f"fb_no_{i}"):
                        S.feedback[i] = "incorrect"
                        st.toast("검토 의견을 기록했어요. (현재 세션에만 저장)")


# [추가 기능/수정 포인트 UI-V1] Streamlit 기본 마이크 녹음 + 3차 프로젝트 Whisper(STT)
def render_voice_question(prefix):
    """음성 입력은 문자로 변환한 뒤 사용자가 확인하고 전송하도록 합니다."""
    with st.expander("🎙️ 음성으로 질문하기", expanded=False):
        st.caption("마이크 녹음 → 한국어 음성 인식 → 문장 확인·수정 → 백서 RAG 질문")
        audio = st.audio_input("질문을 녹음해 주세요", key=f"mic_{prefix}")
        if audio is None:
            return
        raw = audio.getvalue()
        voice_digest = hashlib.sha256(raw).hexdigest()
        if S.get(f"voice_digest_{prefix}") != voice_digest:
            S[f"voice_digest_{prefix}"] = voice_digest
            S[f"voice_edit_{prefix}"] = ""
            if not get_api_key():
                st.warning("음성 인식에는 OpenAI API 키가 필요합니다.")
            else:
                try:
                    with st.spinner("한국어 음성을 텍스트로 변환하는 중..."):
                        S[f"voice_edit_{prefix}"] = transcribe_audio(raw, get_api_key())
                except Exception as exc:
                    st.error(f"음성 인식 중 오류가 발생했습니다 ({type(exc).__name__}). 다시 녹음해 주세요.")
        if S.get(f"voice_edit_{prefix}"):
            st.text_area("인식한 질문 (전송 전 수정 가능)", key=f"voice_edit_{prefix}", height=75)
            if st.button("이 음성 질문 전송", key=f"voice_send_{prefix}", type="primary"):
                submit_question(S.get(f"voice_edit_{prefix}", ""))
                rerun_after_question(prefix)


def export_conversation():
    """[추가 기능] 개인 대화 기록을 UTF-8 텍스트로 내보냅니다. 서버 DB에는 저장하지 않습니다."""
    items = ["AIVLE Guide | 나의 학습 질문 기록", ""]
    for message in S.messages:
        title = "나" if message["role"] == "user" else "AIVLE Guide"
        items.extend([f"[{title}]", message["content"], ""])
        if message["role"] == "assistant" and message.get("sources"):
            used = message["sources"][:5]
            items.append("검색 근거: " + " / ".join(
                f"{x.get('id','D?')} {x['name']} PDF {x.get('page') or '?'}쪽" for x in used))
            items.append("")
    return "\n".join(items)

def render_questions(prefix, compact=False):
    # 질문 입력창 옆의 클립 아이콘으로도 문서를 업로드/선택할 수 있습니다.
    input_col, attach_col = st.columns([9, 1], vertical_alignment="center")
    with input_col:
        with st.form(f"form_{prefix}", clear_on_submit=True):
            field, send_col = st.columns([5, 1], vertical_alignment="center")
            with field:
                question = st.text_input("질문", placeholder="에이블스쿨에 대해 질문해 주세요",
                                         label_visibility="collapsed", key=f"text_{prefix}")
            with send_col:
                sent = st.form_submit_button("전송", type="primary", use_container_width=True)
            if sent and question.strip():
                submit_question(question)
                rerun_after_question(prefix)
    with attach_col:
        with st.popover("📎", help="백서 PDF 첨부", use_container_width=True):
            document_upload(f"attach_{prefix}")
    render_voice_question(prefix)
    st.caption("✨ 추천 질문")
    options = QUESTIONS[:4] if compact else QUESTIONS
    cols = st.columns(2)
    for j, q in enumerate(options):
        with cols[j % 2]:
            if st.button(q, key=f"{prefix}_rec_{j}", use_container_width=True):
                submit_question(q)
                rerun_after_question(prefix)
    if S.messages:
        st.caption("🔎 관련 후속 질문")
        for j, q in enumerate(FOLLOW_UP[:2]):
            if st.button(q, key=f"{prefix}_follow_{j}"):
                submit_question(q)
                rerun_after_question(prefix)


def render_top_five():
    top = top_questions()
    if not top:
        st.caption("아직 질문 기록이 없어 추천 FAQ를 보여줍니다.")
        top = [(q, None) for q in QUESTIONS[:5]]
    else:
        st.caption("현재 앱 서버에 기록된 질문 기준 · 서버 재시작 시 초기화될 수 있음")
    for i, (question, count) in enumerate(top[:5], 1):
        st.markdown(f"**{i}. {question}**")
        if count is not None:
            st.caption(f"{count}회 질문")


@st.dialog("💬 AIVLE Guide AI 도우미", width="large")
def chatbot_dialog():
    st.caption("통합 백서 PDF에 근거하는 질문·답변 · 큰 화면은 '전체 화면 열기'")
    with st.expander("📄 학습 백서 업로드 / 자료 변경", expanded=False):
        document_upload("dialog")
    with st.container(height=280, border=True):
        render_message_history()
    render_questions("popup", compact=True)
    with st.expander("🔥 많이 묻는 질문 TOP 5"):
        render_top_five()
    c1,c2 = st.columns(2)
    with c1:
        if st.button("↗ 전체 화면 열기", key="open_full_chat", use_container_width=True):
            navigate("AI에게 질문하기")
    with c2:
        if st.button("🗑️ 대화 초기화", key="popup_clear", use_container_width=True):
            S.messages = []
            S.audio_responses = {}
            st.rerun()


# [셀 06] 사이드바 및 전체 페이지 디자인 | Ctrl+F로 [수정 포인트 ...] 검색
with st.sidebar:
    st.markdown("## 🎓 AIVLE Guide")
    st.caption("에이블스쿨 학습·정보 길잡이")
    st.divider()
    for page in MENU:
        if st.button(f"{MENU_ICON[page]}  {page}", key=f"nav_{page}",
                     type="primary" if S.page == page else "secondary",
                     use_container_width=True):
            navigate(page)
    st.divider()
    if st.button("💬 AI에게 질문하기", key="nav_chat", use_container_width=True):
        navigate("AI에게 질문하기")
    st.caption("지원 · 교육 · 프로젝트 · 진로")
    st.markdown("[KT AIVLE School 공식 홈페이지](https://aivle.kt.co.kr/)")

if S.page == "홈":
    st.markdown("""<div class="hero"><small>KT AIVLE SCHOOL</small>
      <h1>AI와 DX, 내일의 가능성을 만나다</h1>
      <p>KT AIVLE School은 AI·데이터·클라우드를 활용해 실제 기업의 문제를 해결하는 경험을 쌓는
      실무형 인재양성 프로그램입니다. 기초 학습부터 미니프로젝트, 빅프로젝트, 진로 준비까지 이어집니다.</p>
      </div>""", unsafe_allow_html=True)
    a,b,c = st.columns(3)
    with a:
        if st.button("🎓 교육과정 안내", use_container_width=True): navigate("에이블스쿨이란?")
    with b:
        if st.button("📚 나만의 학습전략", use_container_width=True): navigate("학습전략")
    with c:
        if st.button("💬 AI 도우미 시작", type="primary", use_container_width=True): navigate("AI에게 질문하기")
    st.write("")
    st.subheader("에이블스쿨의 주요 학습 경험")
    a,b,c = st.columns(3)
    for col, head, desc in [
        (a,"🌐 온라인 중심 실습", "강의·실습 플랫폼에서 기초 개념을 익히고 직접 적용합니다."),
        (b,"🧑‍🏫 현직 전문가 피드백", "기업 실무 관점의 코칭과 발표 피드백으로 결과물을 다듬습니다."),
        (c,"🛠️ 팀 기반 프로젝트", "문제 정의에서 분석·구현·제안까지 협업을 경험합니다.")
    ]:
        with col:
            st.markdown(f'<div class="panel"><strong>{head}</strong><p>{desc}</p></div>', unsafe_allow_html=True)
    st.write("")
    left,right = st.columns([1,1], gap="large")
    with left:
        st.subheader("📢 주요 안내")
        st.info("현재 공지 영역은 안내 예시입니다. 모집·교육 일정은 반드시 해당 기수의 공식 공지를 확인하세요.")
        st.markdown("- **모집:** 지원 자격·모집 일정 확인\n- **교육:** 운영 공지·교육 자료 확인\n- **프로젝트:** 과제별 제출 기한·형식 확인")
        if st.button("공지사항 메뉴 보기", use_container_width=True): navigate("공지사항")
    with right:
        st.subheader("🔥 자주 묻는 질문 TOP 5")
        render_top_five()
    st.caption("안내 내용: KT AIVLE School 공식 프로그램 소개·학습 환경을 바탕으로 재구성. 실시간 공지 연동은 미구현.")

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
    st.subheader("학습 환경·지원")
    st.markdown("- 온라인 중심 학습·실습\n- 현직 전문가 코칭 및 프로젝트 피드백\n- 취업 관련 컨설팅·잡페어 등 안내\n- 세부 혜택·채용 우대는 모집 기수와 공고에 따라 달라질 수 있음")
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
    pre,plan,check = st.tabs(["① 사전학습", "② 개인 학습계획", "③ 실행점검"])
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
        st.caption("체크 결과와 학습 기록은 세션 기반입니다. 새로 접속하면 사라질 수 있으니 CSV로 백업하세요.")
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

elif S.page == "AI에게 질문하기":
    st.title("💬 AI에게 질문하기")
    st.caption("PDF 업로드 → 자동 청킹·임베딩·Chroma 검색 → 백서 근거 기반 답변")
    st.info("📄 백서 PDF를 등록하고 질문해 보세요. 답변은 문서의 근거를 찾아 작성하며, "
            "각 답변에서 출처·PDF 페이지를 확인할 수 있습니다.")
    with st.expander("📎 학습 백서 업로드 / 답변 자료 선택", expanded=S.pdf_bytes is None):
        document_upload("full")
    a,b = st.columns([3,1],gap="large")
    with a:
        with st.container(height=380,border=True):
            render_message_history()
        render_questions("full",compact=False)
        if S.messages:
            st.download_button("📥 대화 기록 TXT 저장", export_conversation().encode("utf-8-sig"),
                               file_name="aivle_guide_conversation.txt", mime="text/plain",
                               key="save_chat", use_container_width=True)
        if st.button("🗑️ 대화 초기화",key="full_clear"):
            S.messages = []
            S.audio_responses = {}
            st.rerun()
    with b:
        st.subheader("🔥 많이 묻는 질문 TOP 5")
        render_top_five()
        st.divider()
        st.caption("답변의 근거는 검색된 문서의 PDF 페이지 및 근거 문장으로 표시됩니다. 표준 항목명 정보가 없는 PDF는 '본문'으로 표시합니다.")

# 모든 일반 페이지에 이모지 전용 플로팅 버튼 유지. 내비게이션 위젯 상태 수정 없음.
if S.page != "AI에게 질문하기":
    with st.container(key="chat_float"):
        if st.button("💬", key="float_chat_button", help="AI 도우미 열기"):
            chatbot_dialog()
