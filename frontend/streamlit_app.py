import json
import os
from typing import Any

import requests
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


st.set_page_config(
    page_title="Enterprise RAG Agent Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — Clean Professional Dark Theme
# ─────────────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"], .main,
[data-testid="stApp"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #0c0c14 !important;
    color: #d1d5db !important;
}

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,.3); border-radius: 10px; }

/* ── Sidebar ──────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #101018 !important;
    border-right: 1px solid rgba(255,255,255,.06) !important;
}

[data-testid="stSidebar"] .stRadio > label {
    font-weight: 600 !important;
    font-size: .7rem !important;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: rgba(255,255,255,.3) !important;
}

[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    padding: 9px 14px !important;
    border-radius: 8px !important;
    margin-bottom: 2px !important;
    transition: all .15s ease !important;
    border: 1px solid transparent !important;
    font-weight: 500 !important;
    font-size: .88rem !important;
    color: #9ca3af !important;
}

[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
    background: rgba(255,255,255,.04) !important;
    color: #e5e7eb !important;
}

[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"],
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[aria-checked="true"] {
    background: rgba(99,102,241,.1) !important;
    border-color: rgba(99,102,241,.2) !important;
    color: #e5e7eb !important;
}

[data-testid="stSidebar"] .stButton > button {
    border: 1px solid rgba(255,255,255,.08) !important;
    border-radius: 8px !important;
    background: rgba(255,255,255,.03) !important;
    color: #9ca3af !important;
    font-weight: 500 !important;
    font-size: .85rem !important;
    transition: all .15s ease !important;
    padding: 8px 14px !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,.06) !important;
    border-color: rgba(255,255,255,.12) !important;
    color: #e5e7eb !important;
}

/* ── Headers ──────────────────────────────────────────────────────────── */
.main [data-testid="stMarkdownContainer"] h1 {
    font-weight: 700 !important;
    font-size: 1.6rem !important;
    letter-spacing: -0.02em;
    color: #f3f4f6 !important;
    margin-bottom: 4px !important;
}

.main [data-testid="stMarkdownContainer"] h2 {
    font-weight: 600 !important;
    font-size: 1.15rem !important;
    color: #e5e7eb !important;
}

.main [data-testid="stMarkdownContainer"] h3 {
    font-weight: 600 !important;
    font-size: 1rem !important;
    color: #9ca3af !important;
}

/* ── Forms ────────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: rgba(255,255,255,.02) !important;
    border: 1px solid rgba(255,255,255,.06) !important;
    border-radius: 12px !important;
    padding: 24px !important;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,.03) !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: 8px !important;
    color: #e5e7eb !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .88rem !important;
    padding: 10px 14px !important;
    transition: border-color .15s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(99,102,241,.5) !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,.08) !important;
}

.stTextInput label, .stTextArea label, .stSelectbox label,
.stMultiSelect label, .stFileUploader label, .stCheckbox label {
    font-weight: 500 !important;
    font-size: .82rem !important;
    color: #9ca3af !important;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
.main .stButton > button {
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: .85rem !important;
    padding: 9px 20px !important;
    transition: all .15s ease !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    background: rgba(255,255,255,.04) !important;
    color: #d1d5db !important;
}

.main .stButton > button:hover {
    background: rgba(255,255,255,.07) !important;
    border-color: rgba(255,255,255,.15) !important;
}

[data-testid="stFormSubmitButton"] > button {
    background: #4f46e5 !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    transition: all .15s ease !important;
}

[data-testid="stFormSubmitButton"] > button:hover {
    background: #4338ca !important;
}

/* ── Chat ─────────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,.02) !important;
    border: 1px solid rgba(255,255,255,.05) !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
    margin-bottom: 10px !important;
}

[data-testid="stChatInput"] > div {
    background: rgba(255,255,255,.03) !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: 10px !important;
    transition: border-color .15s ease !important;
}

[data-testid="stChatInput"] > div:focus-within {
    border-color: rgba(99,102,241,.4) !important;
}

[data-testid="stChatInput"] textarea {
    font-family: 'Inter', sans-serif !important;
    color: #e5e7eb !important;
}

/* ── Expander ─────────────────────────────────────────────────────────── */
details {
    border: 1px solid rgba(255,255,255,.06) !important;
    border-radius: 8px !important;
    background: rgba(255,255,255,.02) !important;
}

/* ── Dataframe ────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,.06) !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}

/* ── Metrics ──────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,.02) !important;
    border: 1px solid rgba(255,255,255,.06) !important;
    border-radius: 8px !important;
    padding: 14px !important;
}

[data-testid="stMetricLabel"] {
    font-weight: 500 !important;
    color: #6b7280 !important;
    font-size: .78rem !important;
}

[data-testid="stMetricValue"] {
    font-weight: 600 !important;
    color: #e5e7eb !important;
}

/* ── File Uploader ────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] > div {
    border: 1px dashed rgba(255,255,255,.12) !important;
    border-radius: 10px !important;
    background: rgba(255,255,255,.02) !important;
}

[data-testid="stFileUploader"] > div:hover {
    border-color: rgba(255,255,255,.2) !important;
}

/* ── Multiselect / Selectbox ──────────────────────────────────────────── */
.stMultiSelect > div > div,
.stSelectbox > div > div {
    background: rgba(255,255,255,.03) !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: 8px !important;
}

/* ── Alert ────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-weight: 500 !important;
}

hr { border-color: rgba(255,255,255,.06) !important; }

.stCaption, [data-testid="stCaptionContainer"] {
    color: #6b7280 !important;
    font-size: .8rem !important;
}

/* ── Hide branding ────────────────────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

.main .block-container {
    padding-top: 2rem !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# API helpers
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
    col_left, col_center, col_right = st.columns([1.2, 1, 1.2])
    with col_center:
        st.markdown("")
        st.markdown("")
        st.markdown("## Enterprise RAG Platform")
        st.caption("Sign in to access your secure workspace")

        with st.form("login-form"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password", value="admin123")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

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
                st.error(str(exc))


def upload_page() -> None:
    require_login()
    st.markdown("# Upload Documents")
    st.caption("Upload and manage documents for your knowledge base")

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
        st.markdown("### New Upload")
        with st.form("upload-form"):
            uploaded_file = st.file_uploader(
                "Choose a document",
                type=["pdf", "docx", "txt", "md", "markdown", "csv"],
                help="Supported: PDF, DOCX, TXT, MD, CSV",
            )
            title = st.text_input("Document title")
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
            submitted = st.form_submit_button("Upload", use_container_width=True)

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
                        f"{uploaded_file.name} uploaded and shared with your manager."
                    )
                else:
                    st.success(
                        f"{uploaded_file.name} uploaded with {result['chunks_created']} chunks."
                    )
            except Exception as exc:
                st.error(str(exc))

    with docs_col:
        st.markdown("### Accessible Documents")
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

    with st.sidebar:
        st.divider()

        if st.button("New chat", use_container_width=True):
            st.session_state["conversation_id"] = None
            st.rerun()

        st.caption("HISTORY")

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
                    "x",
                    key=f"delete_{username}_{conv_id}",
                    help="Delete this conversation",
                    use_container_width=True,
                    on_click=remove_conversation,
                    args=(conv_id,),
                )

        delete_error = st.session_state.pop("delete_error", None)
        if delete_error:
            st.error(delete_error)

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
        st.caption("Ask a question about your accessible documents.")

    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

            citations = message.get("citations", [])
            if citations:
                with st.expander(f"Sources ({len(citations)})", expanded=False):
                    for citation in citations:
                        filename = citation.get("filename", "Unknown document")
                        score = citation.get("score")
                        score_text = (
                            f" | score: {score:.3f}"
                            if isinstance(score, (int, float))
                            else ""
                        )

                        st.markdown(f"**{filename}**{score_text}")

                        snippet = citation.get("quoted_text", "") or ""
                        if len(snippet) > 180:
                            snippet = snippet[:180].rstrip() + "..."

                        if snippet:
                            st.caption(snippet)

    question = st.chat_input("Ask a question...")

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
            st.error(str(exc))
        else:
            st.rerun()


def evaluation_page() -> None:
    require_login()
    st.markdown("# Evaluation")
    st.caption("Test retrieval quality and answer accuracy")

    eval_col, result_col = st.columns([1, 1], gap="large")

    with eval_col:
        st.markdown("### Run Test")
        question = st.text_area(
            "Evaluation question",
            height=120,
            placeholder="Enter a question to evaluate...",
        )
        expected_doc_ids = st.text_input(
            "Expected document IDs",
            placeholder="e.g. 1, 2, 5 (comma-separated, optional)",
        )
        run_btn = st.button("Run evaluation", type="primary", use_container_width=True)

    if run_btn and question.strip():
        doc_ids = [int(item.strip()) for item in expected_doc_ids.split(",") if item.strip()]
        payload = {"question": question, "expected_doc_ids": doc_ids or None}
        try:
            result = request_json("POST", "/evaluate/query", headers=api_headers(), json=payload)
            with result_col:
                st.markdown("### Results")
                render_answer(result)
                st.metric("Retrieval precision", result.get("retrieval_precision"))
        except Exception as exc:
            st.error(str(exc))


def admin_logs_page() -> None:
    require_login()
    st.markdown("# Admin Logs")
    st.caption("System activity and audit trail")
    try:
        logs = request_json("GET", "/logs", headers=api_headers())
        if logs:
            st.dataframe(logs, use_container_width=True, height=600)
        else:
            st.info("No logs available yet.")
    except Exception as exc:
        st.error(str(exc))


def render_answer(result: dict[str, Any]) -> None:
    if result.get("warning"):
        st.warning(result["warning"])

    st.markdown("#### Answer")
    st.write(result["answer"])

    citations = result.get("citations", [])
    if citations:
        with st.expander(f"Sources ({len(citations)})", expanded=False):
            for citation in result.get("citations", []):
                filename = citation.get("filename", "Unknown document")
                score = citation.get("score")
                score_text = f" | score: {score:.3f}" if isinstance(score, (int, float)) else ""

                st.markdown(f"**{filename}**{score_text}")

                snippet = citation.get("quoted_text", "") or ""
                if len(snippet) > 180:
                    snippet = snippet[:180].rstrip() + "..."

                if snippet:
                    st.caption(snippet)

    if st.session_state.get("role") == "admin":
        with st.expander("Debug details", expanded=False):
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
        st.info("Please sign in to access this page.")
        st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar Navigation
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Enterprise RAG")

    if st.session_state.get("token"):
        username = st.session_state.get("username", "")
        role = st.session_state.get("role", "")
        st.caption(f"{username} / {role}")
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.session_state["page"] = "Login"
            st.rerun()

    page = st.radio(
        "Navigation",
        ["Login", "Upload Documents", "Chat", "Evaluation", "Admin Logs"],
        key="page",
        format_func=lambda x: {
            "Login": "Sign In",
            "Upload Documents": "Documents",
            "Chat": "Chat",
            "Evaluation": "Evaluation",
            "Admin Logs": "Admin Logs",
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
