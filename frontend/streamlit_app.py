import json
import os
from typing import Any

import requests
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


st.set_page_config(
    page_title="Enterprise RAG Agent Platform",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — Premium Dark Glassmorphism Theme
# ─────────────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Global Reset ─────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"], .main,
[data-testid="stApp"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #07070e !important;
    color: #e2e8f0 !important;
}

/* ── Animated gradient background ─────────────────────────────────────── */
[data-testid="stApp"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 60% at 10% 20%, rgba(124,58,237,.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 90% 80%, rgba(59,130,246,.08) 0%, transparent 60%),
        radial-gradient(ellipse 50% 40% at 50% 50%, rgba(236,72,153,.06) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
    animation: bgPulse 12s ease-in-out infinite alternate;
}

@keyframes bgPulse {
    0%   { opacity: .7; }
    100% { opacity: 1; }
}

/* ── Scrollbar ────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(124,58,237,.35); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(124,58,237,.55); }

/* ── Sidebar ──────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d1a 0%, #111128 100%) !important;
    border-right: 1px solid rgba(124,58,237,.15) !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
    background: linear-gradient(135deg, #a78bfa, #7c3aed, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
    font-size: 1.5rem !important;
    letter-spacing: -0.03em;
}

[data-testid="stSidebar"] .stRadio > label {
    font-weight: 600 !important;
    font-size: .75rem !important;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: rgba(226,232,240,.45) !important;
}

[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    padding: 10px 16px !important;
    border-radius: 10px !important;
    margin-bottom: 4px !important;
    transition: all .2s ease !important;
    border: 1px solid transparent !important;
    font-weight: 500 !important;
}

[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
    background: rgba(124,58,237,.1) !important;
    border-color: rgba(124,58,237,.25) !important;
}

[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"],
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[aria-checked="true"] {
    background: rgba(124,58,237,.15) !important;
    border-color: rgba(124,58,237,.4) !important;
}

/* ── Sidebar buttons ──────────────────────────────────────────────────── */
[data-testid="stSidebar"] .stButton > button {
    border: 1px solid rgba(124,58,237,.25) !important;
    border-radius: 10px !important;
    background: rgba(124,58,237,.08) !important;
    color: #c4b5fd !important;
    font-weight: 600 !important;
    font-size: .85rem !important;
    transition: all .25s ease !important;
    padding: 8px 16px !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(124,58,237,.2) !important;
    border-color: rgba(124,58,237,.5) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(124,58,237,.2) !important;
}

/* ── Main headers ─────────────────────────────────────────────────────── */
.main [data-testid="stMarkdownContainer"] h1 {
    font-weight: 800 !important;
    font-size: 2rem !important;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: .5rem !important;
}

.main [data-testid="stMarkdownContainer"] h2 {
    font-weight: 700 !important;
    font-size: 1.35rem !important;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #c4b5fd, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.main [data-testid="stMarkdownContainer"] h3 {
    font-weight: 600 !important;
    color: #94a3b8 !important;
    font-size: 1.1rem !important;
}

/* ── Glass Card ───────────────────────────────────────────────────────── */
.glass-card {
    background: rgba(15, 15, 30, .55);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(124, 58, 237, .12);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 20px;
    transition: border-color .3s ease, box-shadow .3s ease;
}

.glass-card:hover {
    border-color: rgba(124, 58, 237, .28);
    box-shadow: 0 8px 40px rgba(124, 58, 237, .08);
}

/* ── Hero Section ─────────────────────────────────────────────────────── */
.hero-section {
    text-align: center;
    padding: 60px 20px 40px;
}

.hero-section h1 {
    font-size: 2.8rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #f8fafc 0%, #a78bfa 50%, #7c3aed 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 12px !important;
    line-height: 1.15;
}

.hero-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 100px;
    background: rgba(124, 58, 237, .12);
    border: 1px solid rgba(124, 58, 237, .25);
    color: #c4b5fd;
    font-size: .78rem;
    font-weight: 600;
    letter-spacing: .04em;
    margin-bottom: 20px;
}

.hero-subtitle {
    color: #64748b;
    font-size: 1.05rem;
    line-height: 1.7;
    max-width: 520px;
    margin: 0 auto;
}

/* ── Stat Cards ───────────────────────────────────────────────────────── */
.stat-card {
    background: rgba(15, 15, 30, .55);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(124, 58, 237, .1);
    border-radius: 14px;
    padding: 22px;
    text-align: center;
    transition: all .3s ease;
}

.stat-card:hover {
    border-color: rgba(124, 58, 237, .3);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(124, 58, 237, .1);
}

.stat-icon {
    font-size: 1.8rem;
    margin-bottom: 8px;
}

.stat-label {
    font-size: .72rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: .08em;
    font-weight: 600;
}

.stat-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #e2e8f0;
}

/* ── Forms ────────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: rgba(15, 15, 30, .45) !important;
    backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(124, 58, 237, .12) !important;
    border-radius: 16px !important;
    padding: 28px !important;
}

/* ── Text Inputs ──────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(15, 15, 30, .6) !important;
    border: 1px solid rgba(124, 58, 237, .18) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .9rem !important;
    padding: 12px 16px !important;
    transition: all .25s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(124, 58, 237, .5) !important;
    box-shadow: 0 0 0 3px rgba(124, 58, 237, .1) !important;
}

.stTextInput label, .stTextArea label, .stSelectbox label,
.stMultiSelect label, .stFileUploader label, .stCheckbox label {
    font-weight: 600 !important;
    font-size: .82rem !important;
    color: #94a3b8 !important;
    letter-spacing: .02em;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
.main .stButton > button {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: .88rem !important;
    padding: 10px 24px !important;
    transition: all .25s ease !important;
    border: 1px solid rgba(124, 58, 237, .3) !important;
    background: rgba(124, 58, 237, .1) !important;
    color: #c4b5fd !important;
}

.main .stButton > button:hover {
    background: rgba(124, 58, 237, .2) !important;
    border-color: rgba(124, 58, 237, .5) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(124, 58, 237, .15) !important;
}

.main .stButton > button[kind="primary"],
.main button[data-testid="stFormSubmitButton"] > button,
.main .stFormSubmitButton > button {
    background: linear-gradient(135deg, #7c3aed, #6366f1) !important;
    border: none !important;
    color: #fff !important;
    box-shadow: 0 4px 16px rgba(124, 58, 237, .25) !important;
}

.main .stButton > button[kind="primary"]:hover,
.main button[data-testid="stFormSubmitButton"] > button:hover,
.main .stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #6d28d9, #4f46e5) !important;
    box-shadow: 0 6px 28px rgba(124, 58, 237, .35) !important;
    transform: translateY(-2px);
}

[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #7c3aed, #6366f1) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    padding: 10px 28px !important;
    box-shadow: 0 4px 16px rgba(124, 58, 237, .25) !important;
    transition: all .25s ease !important;
}

[data-testid="stFormSubmitButton"] > button:hover {
    background: linear-gradient(135deg, #6d28d9, #4f46e5) !important;
    box-shadow: 0 6px 28px rgba(124, 58, 237, .35) !important;
    transform: translateY(-2px);
}

/* ── Chat ─────────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: rgba(15, 15, 30, .4) !important;
    border: 1px solid rgba(124, 58, 237, .08) !important;
    border-radius: 14px !important;
    padding: 16px 20px !important;
    margin-bottom: 12px !important;
    backdrop-filter: blur(10px) !important;
    animation: msgSlideIn .35s ease-out;
}

[data-testid="stChatMessage"][data-testid*="user"] {
    border-color: rgba(59, 130, 246, .12) !important;
}

@keyframes msgSlideIn {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}

[data-testid="stChatInput"] > div {
    background: rgba(15, 15, 30, .6) !important;
    border: 1px solid rgba(124, 58, 237, .2) !important;
    border-radius: 14px !important;
    transition: border-color .25s ease !important;
}

[data-testid="stChatInput"] > div:focus-within {
    border-color: rgba(124, 58, 237, .5) !important;
    box-shadow: 0 0 0 3px rgba(124, 58, 237, .08) !important;
}

[data-testid="stChatInput"] textarea {
    font-family: 'Inter', sans-serif !important;
    color: #e2e8f0 !important;
}

/* ── Expander ─────────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: rgba(15, 15, 30, .3) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: .85rem !important;
    color: #94a3b8 !important;
}

details {
    border: 1px solid rgba(124, 58, 237, .1) !important;
    border-radius: 12px !important;
    background: rgba(15, 15, 30, .3) !important;
}

/* ── Dataframe ────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(124, 58, 237, .1) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* ── Metrics ──────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(15, 15, 30, .45) !important;
    border: 1px solid rgba(124, 58, 237, .1) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

[data-testid="stMetricLabel"] {
    font-weight: 600 !important;
    color: #94a3b8 !important;
    font-size: .78rem !important;
    text-transform: uppercase;
    letter-spacing: .06em;
}

[data-testid="stMetricValue"] {
    font-weight: 700 !important;
    color: #e2e8f0 !important;
}

/* ── File Uploader ────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] > div {
    border: 2px dashed rgba(124, 58, 237, .2) !important;
    border-radius: 14px !important;
    background: rgba(15, 15, 30, .3) !important;
    transition: all .25s ease !important;
}

[data-testid="stFileUploader"] > div:hover {
    border-color: rgba(124, 58, 237, .4) !important;
    background: rgba(124, 58, 237, .05) !important;
}

/* ── Multiselect ──────────────────────────────────────────────────────── */
.stMultiSelect > div > div {
    background: rgba(15, 15, 30, .6) !important;
    border: 1px solid rgba(124, 58, 237, .18) !important;
    border-radius: 10px !important;
}

/* ── Alert boxes ──────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    backdrop-filter: blur(10px) !important;
    font-weight: 500 !important;
}

/* ── Divider ──────────────────────────────────────────────────────────── */
hr {
    border-color: rgba(124, 58, 237, .1) !important;
}

/* ── Caption ──────────────────────────────────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #64748b !important;
    font-size: .82rem !important;
}

/* ── Hide Streamlit branding ──────────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ── Tabs ─────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(15, 15, 30, .4);
    border-radius: 12px;
    padding: 4px;
    border: 1px solid rgba(124, 58, 237, .1);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: .85rem !important;
    color: #64748b !important;
    padding: 8px 20px !important;
    transition: all .2s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #c4b5fd !important;
    background: rgba(124, 58, 237, .08) !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(124, 58, 237, .15) !important;
    color: #c4b5fd !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: #7c3aed !important;
}

/* ── Checkbox ─────────────────────────────────────────────────────────── */
.stCheckbox label span {
    font-weight: 500 !important;
    color: #94a3b8 !important;
}

/* ── Success / Error ──────────────────────────────────────────────────── */
.stSuccess {
    background: rgba(16, 185, 129, .08) !important;
    border: 1px solid rgba(16, 185, 129, .2) !important;
}

.stError {
    background: rgba(239, 68, 68, .08) !important;
    border: 1px solid rgba(239, 68, 68, .2) !important;
}

/* ── Page transition animation ────────────────────────────────────────── */
.main .block-container {
    animation: pageIn .4s ease-out;
    padding-top: 2rem !important;
}

@keyframes pageIn {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Selectbox ────────────────────────────────────────────────────────── */
.stSelectbox > div > div {
    background: rgba(15, 15, 30, .6) !important;
    border: 1px solid rgba(124, 58, 237, .18) !important;
    border-radius: 10px !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# API helpers (unchanged logic)
# ─────────────────────────────────────────────────────────────────────────────

def api_headers() -> dict[str, str]:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


@st.cache_resource
def backend_session() -> requests.Session:
    return requests.Session()


def request_json(method: str, path: str, **kwargs: Any) -> Any:
    response = backend_session().request(method, f"{BACKEND_URL}{path}", timeout=120, **kwargs)
    if response.status_code >= 400:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except Exception:
            pass
        raise RuntimeError(detail)
    return response.json()


# ─────────────────────────────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────────────────────────────

def login_page() -> None:
    col_left, col_center, col_right = st.columns([1, 1.5, 1])
    with col_center:
        st.markdown(
            """
            <div class="hero-section">
                <div class="hero-badge">🔐 SECURE · ENTERPRISE · AI</div>
                <h1>Enterprise RAG<br>Agent Platform</h1>
                <p class="hero-subtitle">
                    Intelligent document analysis powered by advanced retrieval-augmented
                    generation. Sign in to access your secure workspace.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login-form"):
            st.markdown("#### 🔑 Sign In")
            username = st.text_input("Username", value="admin", placeholder="Enter username")
            password = st.text_input("Password", type="password", value="admin123", placeholder="Enter password")
            submitted = st.form_submit_button("Sign in →", use_container_width=True)

        if submitted:
            try:
                data = request_json(
                    "POST",
                    "/auth/login",
                    data={"username": username, "password": password},
                )
                st.session_state["token"] = data["access_token"]
                st.session_state["username"] = data["username"]
                st.session_state["role"] = data["role"]
                st.session_state["user_id"] = data.get("user_id")
                st.session_state["page"] = "Chat"
                st.rerun()
            except Exception as exc:
                st.error(f"⚠️ {exc}")

        st.markdown("---")
        feat_cols = st.columns(3)
        features = [
            ("🔍", "Smart Search", "AI-powered document retrieval"),
            ("🛡️", "Role-Based Access", "Enterprise-grade security"),
            ("💬", "Chat Interface", "Natural language queries"),
        ]
        for col, (icon, title, desc) in zip(feat_cols, features):
            with col:
                st.markdown(
                    f"""
                    <div class="stat-card">
                        <div class="stat-icon">{icon}</div>
                        <div class="stat-value" style="font-size:1rem;">{title}</div>
                        <div class="stat-label" style="margin-top:4px;">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def upload_page() -> None:
    require_login()
    st.markdown("# 📄 Upload Documents")
    st.caption("Upload and manage documents for your RAG knowledge base")

    try:
        manager_info = request_json(
            "GET",
            "/auth/me/manager",
            headers=api_headers(),
        )
        has_manager = manager_info.get("has_manager", False)
    except Exception:
        has_manager = False

    try:
        users = request_json(
            "GET",
            "/auth/users",
            headers=api_headers(),
        )
    except Exception:
        users = []

    user_options = {
        user["username"]: user["id"]
        for user in users
        if user["id"] != st.session_state.get("user_id")
    }

    upload_col, docs_col = st.columns([1, 1], gap="large")

    with upload_col:
        st.markdown("### ⬆️ New Upload")
        with st.form("upload-form"):
            uploaded_file = st.file_uploader(
                "Choose a document",
                type=["pdf", "docx", "txt", "md", "markdown", "csv"],
                help="Supported formats: PDF, DOCX, TXT, MD, CSV",
            )
            title = st.text_input("Document title", placeholder="e.g. Q4 Financial Report")
            allowed_roles = st.multiselect(
                "Allowed roles",
                options=["admin", "agent_developer", "developer", "hr"],
                default=[],
                help="Select roles only when sharing with everyone in those roles.",
            )
            selected_usernames = st.multiselect(
                "Share with specific people",
                options=list(user_options.keys()),
                default=[],
                help="Select individual users who should access this document.",
            )
            share_with_manager = False
            if has_manager:
                share_with_manager = st.checkbox(
                    "Share with my manager",
                    value=False,
                    help="Give your assigned manager access to this document.",
                )
            else:
                st.info(
                    "You do not have an assigned manager, so manager sharing is unavailable."
                )
            submitted = st.form_submit_button("Upload Document →", use_container_width=True)

        if submitted and uploaded_file:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            selected_user_ids = [
                str(user_options[username])
                for username in selected_usernames
            ]
            data = {
                "title": title,
                "allowed_roles": ",".join(allowed_roles),
                "allowed_user_ids": ",".join(selected_user_ids),
                "share_with_manager": str(share_with_manager).lower(),
            }

            try:
                result = request_json("POST", "/documents/upload", headers=api_headers(), files=files, data=data)
                if share_with_manager:
                    st.success(
                        f"✅ {uploaded_file.name} uploaded and shared with your manager."
                    )
                else:
                    st.success(
                        f"✅ {uploaded_file.name} uploaded with {result['chunks_created']} chunks."
                    )
            except Exception as exc:
                st.error(f"⚠️ {exc}")

    with docs_col:
        st.markdown("### 📋 Accessible Documents")
        try:
            docs = request_json("GET", "/documents", headers=api_headers())
            if docs:
                st.dataframe(docs, use_container_width=True, height=450)
            else:
                st.info("No documents found. Upload your first document to get started.")
        except Exception as exc:
            st.info(str(exc))


def chat_page() -> None:
    require_login()

    username = st.session_state.get("username")

    if st.session_state.get("chat_owner") != username:
        st.session_state["chat_owner"] = username
        st.session_state["conversation_id"] = None

    try:
        conversations = request_json(
            "GET",
            "/conversations",
            headers=api_headers(),
        )
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    def open_conversation(conversation_id):
        st.session_state["conversation_id"] = conversation_id

    def remove_conversation(conversation_id):
        try:
            request_json(
                "DELETE",
                f"/conversations/{conversation_id}",
                headers=api_headers(),
            )
        except Exception as exc:
            st.session_state["delete_error"] = str(exc)
            return

        if st.session_state.get("conversation_id") == conversation_id:
            st.session_state["conversation_id"] = None

    # ── Sidebar conversation list ──────────────────────────────────────────
    with st.sidebar:
        st.divider()

        if st.button("✨ New Chat", use_container_width=True):
            st.session_state["conversation_id"] = None
            st.rerun()

        st.markdown(
            "<p style='font-size:.72rem;font-weight:700;color:rgba(226,232,240,.4);"
            "text-transform:uppercase;letter-spacing:.1em;margin:16px 0 8px;'>History</p>",
            unsafe_allow_html=True,
        )

        if not conversations:
            st.caption("No conversations yet")

        for conversation in conversations:
            conv_id = conversation["id"]
            title = " ".join(conversation["title"].split())
            label = title if len(title) <= 24 else title[:23] + "..."

            title_col, delete_col = st.columns([5, 1])

            with title_col:
                st.button(
                    label,
                    key=f"conversation_{username}_{conv_id}",
                    help=title,
                    use_container_width=True,
                    on_click=open_conversation,
                    args=(conv_id,),
                )

            with delete_col:
                st.button(
                    "×",
                    key=f"delete_{username}_{conv_id}",
                    help="Permanently delete this conversation",
                    use_container_width=True,
                    on_click=remove_conversation,
                    args=(conv_id,),
                )

        delete_error = st.session_state.pop("delete_error", None)
        if delete_error:
            st.error(delete_error)

    # ── Chat area ──────────────────────────────────────────────────────────
    conversation_id = st.session_state.get("conversation_id")
    messages = []

    if conversation_id is not None:
        try:
            messages = request_json(
                "GET",
                f"/conversations/{conversation_id}/messages",
                headers=api_headers(),
            )
        except Exception as exc:
            st.session_state["conversation_id"] = None
            st.error(str(exc))
            st.stop()

    if not messages:
        st.markdown(
            """
            <div style="text-align:center; padding:80px 20px 40px;">
                <div style="font-size:3.5rem; margin-bottom:16px;">💬</div>
                <h2 style="font-weight:700; color:#e2e8f0; font-size:1.5rem; margin-bottom:8px;">
                    Start a Conversation
                </h2>
                <p style="color:#64748b; font-size:.95rem; max-width:400px; margin:0 auto;">
                    Ask questions about your accessible documents. The AI will search
                    through your knowledge base to provide accurate, cited answers.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for message in messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

                citations = message.get("citations", [])
                if citations:
                    with st.expander(f"📎 Sources ({len(citations)})", expanded=False):
                        for citation in citations:
                            filename = citation.get("filename", "Unknown document")
                            score = citation.get("score")
                            score_text = (
                                f" · score: {score:.3f}"
                                if isinstance(score, (int, float))
                                else ""
                            )

                            st.markdown(f"**📄 {filename}**{score_text}")

                            snippet = citation.get("quoted_text", "") or ""
                            if len(snippet) > 180:
                                snippet = snippet[:180].rstrip() + "…"

                            if snippet:
                                st.caption(snippet)

    question = st.chat_input("Ask a question about your documents...")

    if question and question.strip():
        try:
            if conversation_id is None:
                conversation = request_json(
                    "POST",
                    "/conversations",
                    headers=api_headers(),
                )
                conversation_id = conversation["id"]
                st.session_state["conversation_id"] = conversation_id

            with st.chat_message("user"):
                st.write(question)

            answer_box = st.empty()
            full_answer = ""

            with requests.post(
                f"{BACKEND_URL}/conversations/{conversation_id}/messages/stream",
                headers=api_headers(),
                json={
                    "question": question,
                    "top_k": 5,
                    "model": "auto",
                },
                stream=True,
                timeout=120,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue

                    payload = json.loads(line.removeprefix("data: "))

                    if payload.get("type") == "token":
                        full_answer += payload["content"]
                        answer_box.write(full_answer)

                    elif payload.get("type") == "done":
                        break

        except Exception as exc:
            st.error(f"⚠️ {exc}")
        else:
            st.rerun()


def evaluation_page() -> None:
    require_login()
    st.markdown("# 📊 Evaluation")
    st.caption("Test retrieval quality and answer accuracy")

    eval_col, result_col = st.columns([1, 1], gap="large")

    with eval_col:
        st.markdown("### 🧪 Run Test")
        question = st.text_area(
            "Evaluation question",
            height=120,
            placeholder="Enter a question to evaluate against your knowledge base...",
        )
        expected_doc_ids = st.text_input(
            "Expected document IDs",
            placeholder="e.g. 1, 2, 5 (comma-separated, optional)",
        )
        run_btn = st.button("Run Evaluation →", type="primary", use_container_width=True)

    if run_btn and question.strip():
        doc_ids = [int(item.strip()) for item in expected_doc_ids.split(",") if item.strip()]
        payload = {"question": question, "expected_doc_ids": doc_ids or None}
        try:
            result = request_json("POST", "/evaluate/query", headers=api_headers(), json=payload)
            with result_col:
                st.markdown("### 📈 Results")
                render_answer(result)
                st.metric("Retrieval Precision", result.get("retrieval_precision"))
        except Exception as exc:
            st.error(f"⚠️ {exc}")


def admin_logs_page() -> None:
    require_login()
    st.markdown("# 🔒 Admin Logs")
    st.caption("Monitor system activity and audit trail")
    try:
        logs = request_json("GET", "/logs", headers=api_headers())
        if logs:
            st.dataframe(logs, use_container_width=True, height=600)
        else:
            st.info("No logs available yet.")
    except Exception as exc:
        st.error(f"⚠️ {exc}")


def render_answer(result: dict[str, Any]) -> None:
    if result.get("warning"):
        st.warning(result["warning"])

    st.markdown("#### 💡 Answer")
    st.write(result["answer"])

    citations = result.get("citations", [])
    if citations:
        with st.expander(f"📎 Sources ({len(citations)})", expanded=False):
            for citation in result.get("citations", []):
                filename = citation.get("filename", "Unknown document")
                score = citation.get("score")
                score_text = f" · score: {score:.3f}" if isinstance(score, (int, float)) else ""

                st.markdown(f"**📄 {filename}**{score_text}")

                snippet = citation.get("quoted_text", "") or ""
                if len(snippet) > 180:
                    snippet = snippet[:180].rstrip() + "…"

                if snippet:
                    st.caption(snippet)

    if st.session_state.get("role") == "admin":
        with st.expander("🔧 Debug Details", expanded=False):
            metric_a, metric_b, metric_c = st.columns(3)
            metric_a.metric("Evidence", result["evidence_score"])
            metric_b.metric("Groundedness", result["groundedness_score"])
            metric_c.metric("Latency (ms)", result["latency_ms"])

            st.caption("Retrieved chunks")
            st.dataframe(
                result.get("retrieved_chunks", []),
                use_container_width=True,
            )


def require_login() -> None:
    if not st.session_state.get("token"):
        st.info("🔒 Please sign in to access this page.")
        st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar Navigation
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("# 🔮 Enterprise RAG")

    if st.session_state.get("token"):
        role_badge = st.session_state.get("role", "user")
        user = st.session_state.get("username", "")
        st.markdown(
            f"""
            <div style="
                background: rgba(124,58,237,.08);
                border: 1px solid rgba(124,58,237,.15);
                border-radius: 10px;
                padding: 10px 14px;
                margin-bottom: 12px;
            ">
                <div style="font-weight:600; color:#e2e8f0; font-size:.88rem;">
                    👤 {user}
                </div>
                <div style="
                    display:inline-block;
                    padding:2px 8px;
                    border-radius:6px;
                    background:rgba(124,58,237,.15);
                    color:#a78bfa;
                    font-size:.7rem;
                    font-weight:600;
                    text-transform:uppercase;
                    letter-spacing:.05em;
                    margin-top:4px;
                ">{role_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚪 Sign out", use_container_width=True):
            st.session_state.clear()
            st.session_state["page"] = "Login"
            st.rerun()

    page = st.radio(
        "Navigation",
        ["Login", "Upload Documents", "Chat", "Evaluation", "Admin Logs"],
        key="page",
        format_func=lambda x: {
            "Login": "🔑  Sign In",
            "Upload Documents": "📄  Documents",
            "Chat": "💬  Chat",
            "Evaluation": "📊  Evaluation",
            "Admin Logs": "🔒  Admin Logs",
        }.get(x, x),
    )

# ─────────────────────────────────────────────────────────────────────────────
# Page Router
# ─────────────────────────────────────────────────────────────────────────────

if page == "Login":
    login_page()
elif page == "Upload Documents":
    upload_page()
elif page == "Chat":
    chat_page()
elif page == "Evaluation":
    evaluation_page()
else:
    admin_logs_page()
