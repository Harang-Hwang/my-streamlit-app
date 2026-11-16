import hashlib
import sqlite3
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="AIVLE Guide | 에이블스쿨 학습 도우미", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp {background:#F8FBFA;}
[data-testid="stSidebar"] {background:#EDF7F3;}
h1,h2,h3 {color:#174F48;}
.hero {background:linear-gradient(110deg,#D9F2E8,#F7FCFA); border:1px solid #C5E1D5; border-radius:22px; padding:34px 36px; margin:8px 0 24px;}
.hero .eyebrow {color:#287E6A;letter-spacing:2px;font-size:12px;font-weight:750;}
.hero h1 {margin:12px 0;color:#174F48;font-size:34px;}
.hero p {color:#557269;font-size:16px;line-height:1.75;}
.feature {background:white;border:1px solid #D9E9E2;border-radius:16px;padding:21px;min-height:140px;}
.feature strong {color:#1B5D4C;font-size:16px;}
/* 사이드바 라디오: 동그란 선택 버튼을 숨기고 일반 내비게이션 메뉴처럼 표현 */
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {gap:5px;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {border-radius:10px;padding:9px 12px;background:transparent;transition:background .2s;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:#DAEEE4;}
[data-testid="stSidebar"] [data-testid="stRadio"] label [data-testid="stWidgetLabel"] {display:none;}
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {display:none;}
[data-testid="stSidebar"] [data-testid="stRadio"] label p {font-weight:600;color:#24574C;font-size:14px;}
/* 페이지 전환용 플로팅 버튼: 이모지만 노출, 아래에서 약간 위로 */
.st-key-floating_chat {position:fixed;right:30px;bottom:112px;z-index:9999;width:56px;}
.st-key-floating_chat button {width:56px!important;height:56px!important;min-height:56px!important;border-radius:50%!important;background:#166B57!important;color:white!important;border:none!important;font-size:24px!important;box-shadow:0 7px 20px rgba(20,71,57,.25)!important;padding:0!important;}
.st-key-floating_chat button:hover {background:#105846!important;}
/* 보라색 포인트를 최소화하고 테마와 정렬 */
button[kind="primary"], button[data-testid="stBaseButton-primary"] {background-color:#17745F!important;border-color:#17745F!important;}
[data-testid="stFileUploader"] {border-color:#AFCFC1;}
</style>
""", unsafe_allow_html=True)

S = st.session_state
if "page" not in S: S.page = "홈"
if "messages" not in S: S.messages = []
if "doc_hash" not in S: S.doc_hash = None
if "doc_name" not in S: S.doc_name = None
if "pending_question" not in S: S.pending_question = None

MENU = ["홈", "에이블스쿨이란?", "공지사항", "노하우", "학습전략", "문의", "AI에게 질문하기"]
LABELS = ["🏠  홈", "🎓  에이블스쿨이란?", "📢  공지사항", "💡  노하우", "📚  학습전략", "✉️  문의", "💬  AI에게 질문하기"]
RECOMMENDATIONS = [
    "비전공자도 에이블스쿨에 지원할 수 있나요?",
    "AI 개발자와 DX 컨설턴트는 무엇이 다른가요?",
    "미니프로젝트와 빅프로젝트는 어떻게 다른가요?",
    "7·8·9기 DX 미니프로젝트는 몇 차까지 진행됐나요?",
    "에이블스쿨은 어떤 취업 지원을 제공하나요?",
]

# 질문 통계는 데모용 로컬 DB입니다. 서버 재시작 시 보존되지 않을 수 있습니다.
DB_FILE = Path("/tmp/aivle_guide_qcounts.sqlite3")
def add_question_count(question):
    clean = " ".join(question.strip().split())[:200]
    if not clean: return
    with sqlite3.connect(DB_FILE, timeout=10) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS qcounts (question TEXT PRIMARY KEY, count INTEGER NOT NULL)")
        conn.execute("INSERT INTO qcounts(question,count) VALUES (?,1) ON CONFLICT(question) DO UPDATE SET count=count+1", (clean,))
def get_top_five():
    try:
        with sqlite3.connect(DB_FILE, timeout=10) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS qcounts (question TEXT PRIMARY KEY, count INTEGER NOT NULL)")
            return conn.execute("SELECT question,count FROM qcounts ORDER BY count DESC, question ASC LIMIT 5").fetchall()
    except sqlite3.Error:
        return []

def change_page(page):
    S.page = page
    S.nav_radio = LABELS[MENU.index(page)]
    st.rerun()

def receive_pdf(file):
    if file is None:
        if S.doc_hash is not None:
            S.doc_hash = None
            S.doc_name = None
            S.messages = []
        return
    digest = hashlib.sha256(file.getvalue()).hexdigest()
    if S.doc_hash != digest:
        S.doc_hash = digest
        S.doc_name = file.name
        S.messages = []
        # TODO (2일차): 여기서 파일을 임시 PDF로 저장 후 rag_pipeline(filepath) 호출
        # 이전 PDF의 체인을 폐기하고 새 파일에 맞는 RAG 체인을 생성/보관

def ask(question):
    question = question.strip()
    if not question: return
    S.messages.append({"role":"user", "content":question})
    add_question_count(question)
    # TODO (2일차): 아래 답변을 st.session_state.rag_chain.invoke({"input":question})로 교체
    answer = ("**AIVLE Guide UI 시연 답변입니다.**\n\n"
              "현재는 화면/질문 기능을 확인하는 프로토타입이에요. "
              "내일 PDF 자동 벡터화와 RAG를 연결하면 업로드한 백서에 근거해 답변합니다.\n\n"
              "*현재 답변은 실제 문서 검색 결과가 아닙니다.*")
    S.messages.append({"role":"assistant", "content":answer})

with st.sidebar:
    st.markdown("## 🎓 AIVLE Guide")
    st.caption("KT 에이블스쿨 학습 길잡이")
    st.divider()
    selected_label = st.radio("메뉴", LABELS, index=MENU.index(S.page), label_visibility="collapsed", key="nav_radio")
    selected_page = MENU[LABELS.index(selected_label)]
    if selected_page != S.page:
        S.page = selected_page
        st.rerun()
    st.divider()
    st.caption("지원 · 교육 · 프로젝트 · 취업")
    st.markdown("[KT AIVLE School 공식 홈페이지](https://aivle.kt.co.kr/)")

if S.page == "홈":
    st.markdown("""<div class='hero'><div class='eyebrow'>KT AIVLE SCHOOL</div>
        <h1>이제 AI는 기본, DX는 필수.</h1>
        <p>AI·Cloud Native 기반 기업 실무형 AI/DX 인재양성 프로그램.<br>
        자기주도적인 학습과 실무형 프로젝트로 문제 해결 역량을 키웁니다.</p></div>""", unsafe_allow_html=True)
    st.subheader("에이블스쿨만의 학습 경험")
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown('<div class="feature"><strong>🌐 비대면 실습 환경</strong><p>전국에서 참여할 수 있는 온라인 학습·실습 플랫폼을 제공합니다.</p></div>', unsafe_allow_html=True)
    with c2: st.markdown('<div class="feature"><strong>🧑‍🏫 현직 전문가 코칭</strong><p>KT AI/DX 실무 전문가에게 일하는 방식과 문제 해결 과정을 배웁니다.</p></div>', unsafe_allow_html=True)
    with c3: st.markdown('<div class="feature"><strong>🛠 실전 프로젝트</strong><p>과제 발굴부터 서비스 구현 또는 제안서 제작까지 경험합니다.</p></div>', unsafe_allow_html=True)
    st.write("")
    st.subheader("우리가 키우는 네 가지 역량")
    st.markdown("**Self-motivation** 자기주도 학습　 ·　 **Practical** 실무 실행력　 ·　 **Excellence** 전문성　 ·　 **Collaboration** 소통과 협업")
    st.info("지원 자격, 교육 운영과 혜택은 기수별로 달라질 수 있으므로 공식 모집 안내를 확인하세요.")
    st.link_button("공식 홈페이지 자세히 보기", "https://aivle.kt.co.kr/home/main/introMain?mcd=HM01001000")
    st.caption("내용 출처: KT AIVLE School 공식 홈페이지의 프로그램 소개·특징·교육과정 안내를 요약·재구성했습니다.")

elif S.page == "에이블스쿨이란?":
    st.title("🎓 에이블스쿨이란?")
    st.write("KT AIVLE School은 고용노동부 K-Digital Training과 함께 청년을 기업 실무형 AI/DX 인재로 양성하는 교육 프로그램입니다.")
    st.markdown("### 프로그램이 추구하는 방향")
    st.markdown("- **문제 발굴:** 실제 산업·고객 문제를 찾아내기\n- **방법 학습:** 데이터, AI, 클라우드, 컨설팅 도구 익히기\n- **End-to-end 경험:** 문제 정의부터 구현·제안까지 수행하기")
    left,right = st.columns(2)
    with left:
        st.markdown("#### AI 개발자 트랙")
        st.write("데이터와 모델, AI 서비스 개발·배포 등 구현 중심의 경험을 쌓습니다.")
    with right:
        st.markdown("#### DX 컨설턴트 트랙")
        st.write("기업과 고객의 문제를 이해하고 AI/DX 솔루션을 설계·제안하는 경험을 쌓습니다.")
    st.link_button("공식 프로그램 구성 확인", "https://aivle.kt.co.kr/home/main/programMain?mcd=HM02001000")

elif S.page == "공지사항":
    st.title("📢 공지사항")
    st.info("현재는 공지 모음 UI입니다. 실시간 공지를 자동으로 가져오지는 않습니다.")
    with st.expander("모집 일정 및 지원 안내", expanded=True):
        st.write("지원 자격과 모집 일정은 해당 기수의 공식 공고에서 확인해 주세요.")
    with st.expander("교육 운영 및 프로젝트 안내"):
        st.write("정확한 교육 일정, 프로젝트 안내, 출결 규정은 해당 기수 운영 공지가 우선입니다.")
    st.link_button("공식 AIVLE 사이트에서 확인", "https://aivle.kt.co.kr/")

elif S.page == "노하우":
    st.title("💡 에이블러 노하우")
    t1,t2 = st.tabs(["1. 선배들의 후기", "2. 10기 프로젝트 구경하기"])
    with t1:
        st.markdown("### 선배들이 알려준 성장 방법")
        st.markdown("- 개념을 이해한 뒤 실제 코드와 결과물로 검증해 보세요.\n- 팀원과 오류 해결 과정을 나누고 발표로 정리해 보세요.\n- 짧은 미니프로젝트도 포트폴리오에 활용할 수 있도록 기록하세요.")
        st.caption("백서의 선배 조언을 요약한 내용입니다.")
        st.link_button("공식 교육생 후기 보러 가기", "https://aivle.kt.co.kr/home/main/aiDxMain?mcd=HM02002000")
    with t2:
        st.markdown("### 10기 프로젝트 사례")
        st.markdown("**4차 미니프로젝트 — RAG 기반 AIVLE School 학습 도우미**")
        st.write("AIVLE School 백서를 만들고, 이를 검색해 질문에 답하는 웹 학습 도우미를 구축합니다.")
        st.caption("다른 프로젝트의 사진·영상·개별 결과물은 팀에서 검증한 자료를 확보한 뒤 추가하세요.")

elif S.page == "학습전략":
    st.title("📚 학습전략")
    for title,desc in [
        ("01. 매일 짧게 복습하기", "핵심 개념과 오류 원인을 복기하고 다시 실행합니다."),
        ("02. 프로젝트마다 요구사항 먼저 읽기", "최종 제출물, 필수 기능, 일정, 팀 역할을 먼저 확인합니다."),
        ("03. 역할과 의사결정 공유하기", "구현 담당이 달라도 입력·출력 형식과 테스트 질문을 통일합니다."),
        ("04. 결과물을 포트폴리오로 정리하기", "문제, 본인 역할, 해결 방법, 결과, 한계를 기록합니다."),
    ]:
        with st.expander(title, expanded=title.startswith("01")): st.write(desc)
    st.caption("백서의 학습 조언을 바탕으로 구성한 실천 예시입니다.")

elif S.page == "문의":
    st.title("✉️ 문의")
    st.write("에이블스쿨 일반 질문은 'AI에게 질문하기' 메뉴를 이용하세요.")
    st.warning("이 화면은 문의 접수 서버와 연결되어 있지 않습니다. 개인정보를 입력하지 마세요.")
    st.link_button("공식 FAQ로 이동", "https://aivle.kt.co.kr/home/brd/faq/main?mcd=MC00000056")

elif S.page == "AI에게 질문하기":
    st.title("💬 AI에게 질문하기")
    st.caption("백서를 업로드하고 학습 도우미에게 질문해 보세요. 현재 답변은 RAG 연결 전 시연용입니다.")
    with st.expander("📄 학습 백서 PDF 업로드", expanded=S.doc_hash is None):
        uploaded = st.file_uploader("학습할 백서 PDF를 선택하세요", type=["pdf"], key="chat_pdf")
        receive_pdf(uploaded)
        if uploaded is not None:
            st.success(f"{uploaded.name} 업로드 완료 (현재는 벡터화 전)")
        else:
            st.info("PDF 업로드를 테스트할 수 있습니다. 실제 자동 벡터화는 내일 연결할 예정입니다.")
    left,right = st.columns([3,1], gap="large")
    with left:
        st.markdown("### 대화")
        if not S.messages:
            st.info("질문을 입력하거나 아래 추천 질문을 선택해 보세요.")
        with st.container(height=350, border=True):
            for msg in S.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
        # 질문창 아래에 추천 질문을 배치하기 위해 form + text_input 사용
        with st.form("chat_form", clear_on_submit=True):
            typed = st.text_input("질문 입력", placeholder="에이블스쿨에 대해 궁금한 점을 적어주세요")
            sent = st.form_submit_button("질문 보내기", type="primary", use_container_width=True)
        if sent and typed.strip():
            ask(typed)
            st.rerun()
        st.markdown("**✨ 추천 질문**")
        rcols = st.columns(2)
        for idx, item in enumerate(RECOMMENDATIONS):
            with rcols[idx%2]:
                if st.button(item, key=f"recommend_{idx}", use_container_width=True):
                    ask(item)
                    st.rerun()
        if st.button("🗑️ 대화 초기화", key="clear_history"):
            S.messages = []
            st.rerun()
    with right:
        st.markdown("### 🔥 인기 질문 TOP 5")
        top = get_top_five()
        if top:
            for i,(q,count) in enumerate(top,1):
                st.markdown(f"**{i}. {q}**")
                st.caption(f"질문 {count}회")
        else:
            st.caption("아직 누적 질문이 없습니다.")
        st.divider()
        st.caption("현재 순위는 앱 서버의 시연용 집계입니다. 서버 재시작 시 초기화될 수 있습니다.")

# 챗봇 이모지 플로팅 버튼: 팝업이 아니라 독립 페이지로 이동
if S.page != "AI에게 질문하기":
    with st.container(key="floating_chat"):
        if st.button("💬", key="floating_chat_button", help="AI 질문 페이지 열기"):
            change_page("AI에게 질문하기")
