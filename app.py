"""AIVLE Guide: Streamlit multi-page UI + optional PDF RAG.
UI prototype works without OpenAI API key. Full Q&A requires configured key and PDF.
"""
import csv
import hashlib
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
    "study_checks": {}, "study_logs": [],
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


@st.cache_resource(show_spinner="PDF에서 참고 내용을 추출하고 벡터화하는 중...")
def build_retriever(file_bytes, file_hash, api_key):
    """해시가 같으면 재임베딩하지 않음. 파일별 컬렉션 분리."""
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_chroma import Chroma

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        pdf_path = tmp.name
    try:
        docs = PyMuPDFLoader(pdf_path).load()
    finally:
        os.unlink(pdf_path)
    if not docs:
        raise ValueError("PDF에서 텍스트를 읽지 못했습니다.")
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    ).split_documents(docs)
    if not chunks:
        raise ValueError("문서에서 검색 가능한 내용이 없습니다.")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
    vectordb = Chroma.from_documents(
        documents=chunks, embedding=embeddings,
        collection_name=f"aivle_{file_hash[:22]}"
    )
    return vectordb.as_retriever(search_kwargs={"k":6}), len(docs), len(chunks)


def active_document():
    if S.source_choice == "기본 백서" and DEFAULT_PDF.exists():
        return DEFAULT_PDF.name, DEFAULT_PDF.read_bytes()
    if S.source_choice == "첨부 PDF" and S.pdf_bytes:
        return S.pdf_name, S.pdf_bytes
    return None, None


def answer_question(question):
    document_name, pdf_bytes = active_document()
    key = get_api_key()
    if pdf_bytes is None:
        return ("현재 선택된 백서가 없습니다. **AI에게 질문하기**에서 PDF를 업로드한 후 질문해 주세요.\n\n"
                "※ 아직 문서를 검색하지 않았습니다."), []
    if not key:
        return ("**UI 미리보기 모드입니다.** PDF는 업로드되었지만 AI 답변을 생성하려면 "
                "Streamlit Cloud의 앱 설정 → Secrets에 `OPENAI_API_KEY`를 등록해야 합니다.\n\n"
                "※ 현재는 실제 RAG 답변이 아닙니다."), []
    from langchain_openai import ChatOpenAI
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    retriever, _, _ = build_retriever(pdf_bytes, digest, key)
    docs = retriever.invoke(question)
    context_parts = []
    sources = []
    for idx, doc in enumerate(docs, 1):
        page = doc.metadata.get("page")
        page_num = page + 1 if isinstance(page, int) else None
        section = doc.metadata.get("section") or "본문"
        excerpt = " ".join(doc.page_content.strip().split())[:200]
        context_parts.append(f"[자료 {idx} | {document_name} | {page_num or '미상'}페이지]\n{doc.page_content}")
        sources.append({"name":document_name, "page":page_num, "section":section, "excerpt":excerpt})
    prompt = (
        "당신은 KT AIVLE School 백서 기반 FAQ 학습 도우미입니다.\n"
        "제공된 문서에 근거하여 한국어로 답하세요. 기수·트랙·시점을 혼동하지 마세요.\n"
        "백서의 공식 안내, 선배 개인 후기, 학습 권고를 구분하세요.\n"
        "문서에 근거가 없으면 확인할 수 없다고 답하세요. 출처 페이지를 임의로 만들지 마세요.\n"
        "개인 출결 인정, 지원금, 평가, 수료 판정은 운영 담당자에게 확인하도록 안내하세요.\n"
        "학습 계획에 관한 제안은 '개인 학습 권고안'이라고 구분하세요.\n\n"
        f"[문서 발췌]\n{'\n\n'.join(context_parts)}\n\n[질문]\n{question}"
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=key)
    result = llm.invoke(prompt)
    return result.content, sources


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
            S.messages = []
        st.caption(f"✅ {uploaded.name} · 파일 확인 완료")
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
    name, content = active_document()
    if name and content:
        if get_api_key():
            st.success(f"선택한 문서: {name} · 질문 시 자동 분석")
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
                            st.caption(src["excerpt"])
                            st.caption("원문은 업로드한 PDF의 해당 페이지에서 확인해 주세요.")
                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button("👍 도움이 됐어요", key=f"fb_yes_{i}"):
                        S.feedback[i] = "helpful"
                        st.toast("피드백 감사합니다!")
                with c2:
                    if st.button("⚠️ 근거가 맞지 않아요", key=f"fb_no_{i}"):
                        S.feedback[i] = "incorrect"
                        st.toast("검토 의견을 기록했어요. (현재 세션에만 저장)")


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
    st.caption("FAQ 기반 간편 대화 · 더 큰 화면은 '전체 화면 열기'를 눌러주세요.")
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
            st.rerun()


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
    st.caption("백서를 기반으로 모집·교육·운영 질문에 답하는 FAQ 학습 도우미")
    with st.expander("📎 학습 백서 업로드 / 답변 자료 선택", expanded=S.pdf_bytes is None):
        document_upload("full")
    a,b = st.columns([3,1],gap="large")
    with a:
        with st.container(height=380,border=True):
            render_message_history()
        render_questions("full",compact=False)
        if st.button("🗑️ 대화 초기화",key="full_clear"):
            S.messages = []
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
