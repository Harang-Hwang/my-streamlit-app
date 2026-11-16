import hashlib
import sqlite3
from collections import Counter
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
.stApp { background: #F8FBFA; }
[data-testid="stSidebar"] { background: #EAF5F1; }
h1, h2, h3 { color: #174F48; }
.intro-banner {
    background: linear-gradient(115deg, #DDF3EA, #F6FCF9);
    border: 1px solid #CDE4DA; border-radius: 22px;
    padding: 34px; margin: 5px 0 24px;
}
.kicker { font-size: 12px; letter-spacing: 2px; color: #287B68; font-weight: 750; }
.intro-banner h1 { font-size: 34px; margin: 12px 0; }
.intro-banner p { color: #526D65; font-size: 16px; }
.feature {
    background: white; border: 1px solid #DEEAE4;
    border-radius: 16px; padding: 22px; min-height: 135px;
}
.feature-title { color: #17564A; font-weight: 750; font-size: 17px; margin-bottom: 9px; }
.muted { color: #637A70; font-size: 13px; }
div.stButton > button { border-radius: 12px; }
/* 챗봇 실행 배너: 화면 오른쪽 아래에 고정 */
.st-key-chat_launcher {
    position: fixed; right: 27px; bottom: 23px;
    z-index: 100000; width: auto;
}
.st-key-chat_launcher [data-testid="stPopover"] > button {
    border-radius: 30px !important;
    background: #176B59 !important; color: white !important;
    border: 1px solid #176B59 !important;
    box-shadow: 0 7px 22px rgba(15, 70, 54, .22);
    padding: 13px 24px !important;
    font-weight: 700 !important;
}
/* 챗봇은 Streamlit 팝오버로 열림 (디바이스 폭에 따라 위치 조정) */
</style>
""", unsafe_allow_html=True)

S = st.session_state
if "messages" not in S:
    S.messages = []
if "document_id" not in S:
    S.document_id = None
if "last_question" not in S:
    S.last_question = None

RECOMMENDATIONS = [
    "비전공자도 에이블스쿨에 지원할 수 있나요?",
    "AI 개발자와 DX 컨설턴트는 어떤 차이가 있나요?",
    "7·8·9기 DX 미니프로젝트는 몇 차까지 진행했나요?",
    "에이블스쿨에서 취업 지원은 어떻게 받나요?",
    "미니프로젝트와 빅프로젝트는 어떻게 다른가요?",
]

# 앱 서버가 재시작하면 집계가 초기화될 수 있는 데모 통계.
# 사용자별 대화 기록을 저장하지 않고 질문 텍스트/횟수만 저장함.
DB_FILE = Path("/tmp/aivle_guide_questions.sqlite3")

def init_db():
    with sqlite3.connect(DB_FILE, timeout=10) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS question_counts (
            question TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0
        )""")

def track_question(question):
    clean = " ".join(question.strip().split())[:200]
    if not clean:
        return
    try:
        with sqlite3.connect(DB_FILE, timeout=10) as conn:
            conn.execute("""INSERT INTO question_counts(question, count) VALUES (?,1)
                ON CONFLICT(question) DO UPDATE SET count = count + 1""", (clean,))
    except sqlite3.Error:
        pass  # 통계 기능 오류가 대화를 중단시키지 않게 처리

def top_questions():
    try:
        with sqlite3.connect(DB_FILE, timeout=10) as conn:
            return conn.execute("""SELECT question, count FROM question_counts
                ORDER BY count DESC, question ASC LIMIT 5""").fetchall()
    except sqlite3.Error:
        return []

init_db()

def ask(question):
    question = question.strip()
    if not question:
        return
    S.messages.append({"role": "user", "content": question})
    track_question(question)
    # TODO: 내일 연결 — 아래 answer를 RAG 체인 호출 결과로 교체
    answer = (
        "**AIVLE Guide UI 시연 답변입니다.**\n\n"
        "현재는 화면 구성과 대화 흐름을 확인하는 프로토타입이에요. "
        "내일 PDF 업로드 → 자동 벡터화 → RAG 검색 기능을 연결하면 "
        "실제 통합 백서에 근거해 답변할 예정입니다.\n\n"
        "*현재 답변은 백서 검색 결과가 아닙니다.*"
    )
    S.messages.append({"role": "assistant", "content": answer})
    S.last_question = question

with st.sidebar:
    st.markdown("## 🎓 AIVLE Guide")
    st.caption("에이블스쿨을 알아보는 가장 쉬운 방법")
    st.divider()
    page = st.radio(
        "메뉴",
        ["홈", "에이블스쿨이란?", "공지사항", "노하우", "학습전략", "문의"],
        label_visibility="collapsed",
        key="page_menu",
    )
    st.divider()
    st.markdown("**📄 학습 백서 업로드**")
    uploaded = st.file_uploader("PDF 선택", type=["pdf"], key="uploaded_pdf")
    if uploaded is not None:
        digest = hashlib.sha256(uploaded.getvalue()).hexdigest()
        if S.document_id != digest:
            S.document_id = digest
            S.messages = []
        st.success("PDF 업로드 완료")
        st.caption(uploaded.name)
        st.caption("UI 시연 단계: 아직 벡터화되지 않았습니다.")
    else:
        if S.document_id is not None:
            S.document_id = None
            S.messages = []
        st.caption("내일 RAG 파이프라인 연결 예정")
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        S.messages = []
        st.rerun()

if page == "홈":
    st.markdown("""<div class="intro-banner">
        <div class="kicker">AIVLE SCHOOL · LEARNING GUIDE</div>
        <h1>당신의 가능성을 여는, AIVLE School 🎓</h1>
        <p>지원과 선발부터 프로젝트, 선배 경험, 취업 준비까지.<br>
        에이블스쿨에 관한 정보를 쉽고 편하게 살펴보세요.</p>
        </div>""", unsafe_allow_html=True)
    st.subheader("에이블스쿨, 무엇을 배울까요?")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="feature"><div class="feature-title">🤖 AI·데이터</div>데이터 분석과 AI 기술을 학습하고 실제 문제에 적용해요.</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="feature"><div class="feature-title">🤝 팀 프로젝트</div>미니프로젝트와 빅프로젝트를 통해 실무 문제 해결을 경험해요.</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="feature"><div class="feature-title">🚀 진로 준비</div>포트폴리오, 면접, 잡페어 등 취업 준비 활동을 접해요.</div>', unsafe_allow_html=True)
    st.info("오른쪽 아래 **💬 AI 도우미에게 질문하기** 버튼을 눌러 챗봇을 열어보세요.")

elif page == "에이블스쿨이란?":
    st.title("🎓 에이블스쿨이란?")
    st.write("KT AIVLE School은 AI·데이터·DX 역량을 실무 프로젝트와 연결하는 청년 대상 교육 프로그램입니다.")
    st.markdown("### 주요 트랙")
    left, right = st.columns(2)
    with left:
        st.markdown("#### AI 개발자")
        st.write("AI 모델, 데이터, API, 서비스 구현 등 개발·검증 중심의 프로젝트를 경험합니다.")
    with right:
        st.markdown("#### DX 컨설턴트")
        st.write("산업·고객 문제를 분석하고 AI·클라우드 활용 방안과 DX 전략을 설계·제안합니다.")
    st.markdown("### 교육의 큰 흐름")
    st.markdown("기초 역량 학습 → 미니프로젝트 → 빅프로젝트 → 진로 연계")
    st.caption("설명은 업로드한 개인 백서 내용을 간추린 UI 시안이며, 최신 모집 조건은 공식 공고에서 확인해야 합니다.")

elif page == "공지사항":
    st.title("📢 공지사항")
    st.info("현재는 UI 시안입니다. 실제 공지사항은 아직 자동 연동되지 않았습니다.")
    with st.expander("공지 01 · 모집 및 지원 일정", expanded=True):
        st.write("모집 일정과 지원 자격은 기수별 공식 모집 공고를 기준으로 확인하세요.")
    with st.expander("공지 02 · 교육 운영 안내"):
        st.write("프로젝트 일정, 출석, 교육 장소 등의 최신 정보는 운영 공지를 확인하세요.")
    st.link_button("AIVLE School 공식 사이트", "https://aivle.kt.co.kr")

elif page == "노하우":
    st.title("💡 에이블러의 노하우")
    t1, t2 = st.tabs(["1. 선배들의 후기", "2. 10기 프로젝트 구경하기"])
    with t1:
        st.subheader("선배들이 전하는 경험과 조언")
        st.markdown("- 이론을 이해하는 것과 직접 구현하는 것은 다릅니다.\n- 미니프로젝트의 경험이 빅프로젝트에서 다시 활용됩니다.\n- 팀원과 오류를 해결하고, 발표하며 배운 것을 정리하세요.")
        st.caption("개인 백서의 '선배의 12가지 조언'을 요약한 내용입니다.")
    with t2:
        st.subheader("10기 프로젝트 둘러보기")
        st.markdown("**4차 미니프로젝트 · RAG 기반 AIVLE School 학습 도우미**")
        st.write("에이블스쿨 백서를 제작하고, 문서를 검색해 답하는 학습 도우미를 구축합니다.")
        st.info("다른 10기 프로젝트 소개 카드·사진·영상은 조별 자료 확보 후 추가할 수 있습니다.")

elif page == "학습전략":
    st.title("📚 학습전략")
    st.write("에이블스쿨을 준비하거나 수강할 때 실천할 수 있는 학습 방법을 정리했습니다.")
    for title, desc in [
        ("01 · 복습과 실습", "강의 내용을 다시 확인하고 작은 단위로 직접 구현해 보세요."),
        ("02 · 팀 협업", "역할을 나누되 오류 해결 과정과 의사결정 근거를 공유하세요."),
        ("03 · 프로젝트 기록", "문제 정의, 사용한 도구, 본인 역할, 검증 결과를 남겨두세요."),
        ("04 · 발표·취업 연결", "프로젝트의 목적과 본인의 기여를 설명하는 연습을 하세요."),
    ]:
        with st.expander(title, expanded=(title.startswith("01"))):
            st.write(desc)
    st.caption("학습전략은 백서의 선배 조언을 토대로 재구성한 일반적 제안입니다.")

else:
    st.title("✉️ 문의")
    st.write("에이블스쿨에 관한 일반적인 궁금증은 오른쪽 아래 AI 도우미에 질문해 보세요.")
    st.warning("현재 문의 양식은 접수 시스템과 연결되지 않습니다. 개인정보는 입력하지 마세요.")
    st.link_button("공식 FAQ 확인하기", "https://aivle.kt.co.kr/home/brd/faq/main?mcd=MC00000056")

# 페이지와 무관하게 유지되는 우측 하단 챗봇 진입 버튼
with st.container(key="chat_launcher"):
    with st.popover("💬 AI 도우미에게 질문하기", use_container_width=False):
        st.markdown("### 🎓 AIVLE 챗봇")
        st.caption("통합 백서 기반 답변은 내일 연결할 예정입니다.")
        with st.container(height=245, border=True):
            if not S.messages:
                st.info("궁금한 내용을 질문하거나 추천 질문을 선택하세요!")
            for msg in S.messages[-12:]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        # 질문창 아래에 추천 질문 표시
        with st.form("chat_question_form", clear_on_submit=True):
            typed = st.text_input("질문 입력", placeholder="궁금한 점을 입력해 주세요...")
            submitted = st.form_submit_button("질문 보내기", use_container_width=True)
        if submitted and typed.strip():
            ask(typed)
            st.rerun()
        st.caption("✨ 추천 질문")
        cols = st.columns(2)
        for i, recommendation in enumerate(RECOMMENDATIONS):
            with cols[i % 2]:
                if st.button(recommendation, key=f"chat_rec_{i}", use_container_width=True):
                    ask(recommendation)
                    st.rerun()
        with st.expander("📊 가장 많이 질문한 내용 TOP 5"):
            st.caption("이 앱 서버의 질문 횟수 기준 · 서버 재시작 시 초기화될 수 있습니다.")
            rows = top_questions()
            if not rows:
                st.write("아직 질문 기록이 없습니다.")
            else:
                for rank, (q, count) in enumerate(rows, start=1):
                    st.write(f"{rank}. **{q}** · {count}회")
        if st.button("대화 내용 지우기", key="chat_clear", use_container_width=True):
            S.messages = []
            st.rerun()
