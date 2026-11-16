import streamlit as st

st.set_page_config(page_title="AIVLE Guide | 에이블스쿨 학습 도우미", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
.stApp {background:#F8FBFA;}
[data-testid="stSidebar"] {background:#EAF5F1;}
h1,h2,h3 {color:#174F48;}
.hero {background:linear-gradient(120deg,#E1F3ED,#F6FBF9);border:1px solid #CEE4DA;border-radius:20px;padding:26px 28px;margin:4px 0 24px;}
.eyebrow {font-size:12px;font-weight:700;letter-spacing:2px;color:#277E6C;}
.hero h1 {font-size:32px;margin:12px 0 10px;}
.hero p {color:#526E65;margin:0;font-size:15px;}
.note {background:white;border:1px solid #DBE8E2;border-radius:12px;padding:12px 16px;color:#517067;font-size:13px;}
div.stButton > button {border-radius:12px;border:1px solid #BBD9CE;background:#FFFFFF;color:#205A4F;min-height:47px;width:100%;white-space:normal;}
div.stButton > button:hover {background:#E1F3EB;border-color:#77B69C;color:#174F48;}
</style>""", unsafe_allow_html=True)

S = st.session_state
if "messages" not in S: S.messages = []
if "pending_question" not in S: S.pending_question = None
if "doc_id" not in S: S.doc_id = None

RECOMMENDATIONS = [
    "비전공자도 에이블스쿨에 지원할 수 있나요?",
    "AI 개발자와 DX 컨설턴트는 무엇이 다른가요?",
    "7·8·9기 DX 미니프로젝트는 각각 몇 차까지 진행했나요?",
    "에이블스쿨의 취업 지원은 어떤 것이 있나요?",
]

with st.sidebar:
    st.markdown("## 🎓 AIVLE Guide")
    st.caption("나의 에이블스쿨 AI 길잡이")
    st.divider()
    st.subheader("📄 백서 관리")
    uploaded_file = st.file_uploader("AIVLE School 백서 PDF를 선택하세요", type=["pdf"], key="pdf_upload")
    if uploaded_file is not None:
        import hashlib
        current_id = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
        if S.doc_id != current_id:
            S.doc_id = current_id
            S.messages = []
        st.success("PDF 업로드 완료")
        st.caption(f"📎 {uploaded_file.name}")
        st.info("현재는 UI 프로토타입으로, PDF 내용 검색은 내일 RAG 연결 후 활성화됩니다.")
    else:
        if S.doc_id is not None:
            S.doc_id = None
            S.messages = []
        st.info("PDF 업로드 기능 테스트 가능")
    st.divider()
    st.subheader("📚 주요 안내 주제")
    st.markdown("지원·선발  ·  교육·혜택  ·  미니/빅프로젝트  ·  취업·진로")
    st.divider()
    if st.button("🗑️ 대화 초기화", key="clear_chat"):
        S.messages = []
        S.pending_question = None
        st.rerun()
    st.caption("KT AIVLE School | 4차 미니프로젝트 UI 시안")

st.markdown("""<div class="hero"><div class="eyebrow">AIVLE SCHOOL · YOUR LEARNING COMPANION</div><h1>무엇이 궁금한가요? 👋</h1><p>지원 자격부터 프로젝트와 진로까지, 에이블스쿨의 정보를 한눈에 살펴보세요.</p></div>""", unsafe_allow_html=True)
st.markdown("#### ✨ 이런 질문은 어떠세요?")
cols = st.columns(2, gap="medium")
for idx, question in enumerate(RECOMMENDATIONS):
    with cols[idx % 2]:
        if st.button(question, key=f"recommend_{idx}"):
            S.pending_question = question

st.divider()
if not S.messages:
    st.markdown('<div class="note">💡 추천 질문을 누르거나 아래 채팅창에 직접 질문해 보세요. 현재 답변은 테스트용 안내 문구입니다.</div>', unsafe_allow_html=True)

for message in S.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("에이블스쿨에 대해 질문해 주세요...")
question = S.pending_question or user_input
if question:
    S.pending_question = None
    with st.chat_message("user"):
        st.markdown(question)
    S.messages.append({"role":"user", "content":question})
    # TODO: 내일 실제 체인 연결 후 아래 answer만 교체
    answer = ("**AIVLE Guide UI 테스트 답변입니다.**\n\n"
              "현재는 화면과 버튼 동작을 확인하는 프로토타입입니다. "
              "내일 PDF 업로드 → 벡터화 → RAG 검색을 연결하면 업로드한 백서를 근거로 답변할 수 있습니다.\n\n"
              "*현재 답변은 백서 검색 결과가 아닙니다.*")
    with st.chat_message("assistant"):
        st.markdown(answer.replace("\n", "\n"))
    S.messages.append({"role":"assistant", "content":answer.replace("\n", "\n")})
