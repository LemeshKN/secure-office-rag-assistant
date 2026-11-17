import json
import os
import time
from typing import Any
import pandas as pd

import requests
import streamlit as st
import altair as alt

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


# Render returns 502/503 while the backend is waking up or restarting,
# so retry a few times before reporting the backend as unavailable.
RETRY_STATUS_CODES = (502, 503)
RETRY_WAITS_SECONDS = (3, 6, 12, 20)


class BackendError(RuntimeError):
    """A backend failure with a message that is safe to show to the user."""


def sign_out(message: str | None = None) -> None:
    st.session_state.clear()
    if message:
        st.session_state["flash"] = message
    st.rerun()


def backend_request(method: str, path: str, retry: bool = True, **kwargs: Any) -> requests.Response:
    url = f"{BACKEND_URL}{path}"
    waits = (*RETRY_WAITS_SECONDS, None) if retry else (None,)
    for wait in waits:
        try:
            response = backend_session().request(method, url, timeout=120, **kwargs)
        except requests.ReadTimeout:
            raise BackendError("The backend took too long to respond. Please try again.")
        except requests.ConnectionError:
            if wait is None:
                raise BackendError("Could not connect to the backend. Please try again in a minute.")
        except requests.RequestException as exc:
            raise BackendError(f"Request to the backend failed: {exc.__class__.__name__}")
        else:
            if response.status_code not in RETRY_STATUS_CODES or wait is None:
                return response
        time.sleep(wait)
    raise AssertionError("unreachable")


def error_message(response: requests.Response) -> str:
    if response.status_code in (502, 503, 504):
        return (
            f"Backend is unavailable (HTTP {response.status_code}). "
            "It may be starting up; please try again in a minute."
        )
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, list):  # FastAPI validation errors
        detail = "; ".join(
            str(item.get("msg", item)) if isinstance(item, dict) else str(item) for item in detail
        )
    return str(detail) if detail else f"Request failed (HTTP {response.status_code})."


def check_response(response: requests.Response, path: str) -> None:
    if response.status_code == 401 and path != "/auth/login" and st.session_state.get("token"):
        message = "Your session has expired. Please sign in again."
        sign_out(message)
        raise BackendError(message)  # st.rerun() is a no-op inside widget callbacks
    if response.status_code >= 400:
        raise BackendError(error_message(response))


def request_json(method: str, path: str, **kwargs: Any) -> Any:
    response = backend_request(method, path, **kwargs)
    check_response(response, path)
    try:
        return response.json()
    except ValueError:
        raise BackendError("The backend returned an unexpected response. Please try again.")


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

        flash = st.session_state.pop("flash", None)
        if flash:
            st.warning(flash)

        with st.form("login-form"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password", value="admin123")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            if not username.strip() or not password:
                st.error("Please enter both username and password.")
                return
            try:
                with st.spinner("Signing in..."):
                    data = request_json(
                        "POST",
                        "/auth/login",
                        data={"username": username.strip(), "password": password},
                    )
                token = data["access_token"]
            except BackendError as exc:
                st.error(str(exc))
                return
            except (KeyError, TypeError):
                st.error("The backend returned an unexpected login response. Please try again.")
                return
            st.session_state["token"] = token
            st.session_state["username"] = data.get("username", username.strip())
            st.session_state["role"] = data.get("role", "")
            st.session_state["user_id"] = data.get("user_id")
            st.rerun()


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

MODEL_CHOICES = [
    "auto",
    "mock-small",
    "mock-large",
    "gemini/gemini-3.5-flash-lite",
    "gemini/gemini-3.8-flash",
]

def money(value: Any) -> str:
    return f"${float(value or 0):.4f}"


def load_cost_profile() -> dict:
    try:
        return request_json("GET", "/cost/me", headers=api_headers())
    except Exception:
        return {"projects": []}


def chat_options() -> dict:
    """Project and model dropdowns. Called inside the sidebar."""
    profile = load_cost_profile()
    projects = {p["name"]: p["id"] for p in profile.get("projects", [])}
    st.caption("COST SETTINGS")
    project_name = st.selectbox("Project", ["No project", *projects], key="chat_project")
    model = st.selectbox("Model", MODEL_CHOICES, key="chat_model")
    budget = profile.get("user_budget")
    if budget:
        st.caption(f"Your budget left this month: {money(budget['remaining_amount'])}")
    return {"project_id": projects.get(project_name), "model": model}


def request_body(question: str, settings: dict, approved: bool | None = None) -> dict:
    body = {
        "question": question,
        "top_k": settings["top_k"],
        "model": settings["model"],
        "project_id": settings["project_id"],
        "max_output_tokens": settings["max_output_tokens"],
    }
    if approved is not None:
        body["approved"] = approved
    return body


def run_stream(question: str, settings: dict, approved: bool) -> None:
    """Send the question to the stream route. Handles both reply types."""
    conversation_id = st.session_state.get("conversation_id")
    if conversation_id is None:
        conversation_id = request_json("POST", "/conversations", headers=api_headers())["id"]
        st.session_state["conversation_id"] = conversation_id

    with st.chat_message("user"):
        st.write(question)
    answer_box = st.empty()
    full_answer = ""

    path = f"/conversations/{conversation_id}/messages/stream"
    # No retry: the backend saves the message before streaming, so a retry could duplicate it.
    response = backend_request(
        "POST", path, retry=False, headers=api_headers(),
        json=request_body(question, settings, approved), stream=True,
    )
    with response:
        check_response(response, path)

        # A stopped request (warn without approval, or block) comes back as JSON.
        if "application/json" in response.headers.get("content-type", ""):
            st.session_state["pending"] = {
                "question": question, "settings": settings, "card": response.json(),
            }
            return

        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            try:
                payload = json.loads(line.removeprefix("data: "))
            except ValueError:
                continue
            if payload.get("type") == "token":
                full_answer += payload.get("content", "")
                answer_box.write(full_answer)
            elif payload.get("type") == "done":
                break
    st.session_state.pop("pending", None)


def attempt(question: str, settings: dict) -> None:
    """Estimate first. Allow runs at once. Anything else stores a card and waits."""
    estimate = request_json(
        "POST", "/cost/estimate", headers=api_headers(), json=request_body(question, settings)
    )
    if estimate["decision"] == "allow":
        run_stream(question, settings, approved=False)
    else:
        st.session_state["pending"] = {"question": question, "settings": settings, "card": estimate}


def guarded(action, *args) -> None:
    try:
        action(*args)
    except BackendError as exc:
        st.error(str(exc))
        return
    except requests.RequestException:
        st.error("Connection to the backend was lost. Please refresh the chat.")
        return
    st.rerun()

def plain(text: str) -> str:
    """Stop Streamlit from reading $ as math."""
    return text.replace("$", "\\$")

def render_card(box, pending: dict) -> str | None:
    """Draw the decision card. Returns accept, run, cancel or None."""
    card = pending["card"]
    decision = card.get("decision", "warn")
    recs = card.get("recommendations", [])
    can_accept = decision != "block" and any(r.get("suggested") for r in recs)
    action = None

    with box.container():
        with st.chat_message("user"):
            st.write(pending["question"])
        with st.container(border=True):
            reason = card.get("reason", "")
            if decision == "block":
                st.error(f"Blocked. {plain(reason)}")
            elif decision == "warn":
                st.warning(f"Warning. {plain(reason)}")
            else:
                st.info(plain(reason))

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Estimated cost", money(card.get("estimated_cost")))
            c2.metric("Input tokens", card.get("input_tokens", 0))
            c3.metric("Output limit", card.get("output_tokens", 0))
            remaining = card.get("lowest_remaining")
            scope = card.get("limiting_scope") or "none"
            c4.metric(f"Lowest budget left ({scope})", money(remaining) if remaining is not None else "n/a")
            st.caption(f"Priced as {card.get('priced_as', 'unknown')}")

            if recs:
                st.markdown("**Recommendations**")
                for rec in recs:
                    st.markdown(f"- {plain(rec['message'])}")

            buttons = st.columns(3)
            if decision == "block":
                st.caption("The server does not run blocked requests.")
                if buttons[0].button("Cancel", key="card_cancel"):
                    action = "cancel"
            else:
                if can_accept and buttons[0].button("Accept recommendation", key="card_accept", type="primary"):
                    action = "accept"
                if buttons[1].button("Run anyway", key="card_run"):
                    action = "run"
                if buttons[2].button("Cancel", key="card_cancel"):
                    action = "cancel"
    return action


def handle_card_action(action: str, pending: dict) -> None:
    settings = pending["settings"]
    if action == "cancel":
        st.session_state.pop("pending", None)
        st.rerun()
    elif action == "run":
        guarded(run_stream, pending["question"], settings, True)
    elif action == "accept":
        changes: dict = {}
        for rec in pending["card"].get("recommendations", []):
            changes.update(rec.get("suggested", {}))
        # The server recalculates the estimate for the new settings.
        guarded(attempt, pending["question"], {**settings, **changes})

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
        st.session_state.pop("pending", None)

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
            st.session_state.pop("pending", None)
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

        st.divider()
        options = chat_options()

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

    pending = st.session_state.get("pending")
    card_box = st.empty()
    question = st.chat_input("Ask a question...")

    if question and question.strip():
        st.session_state.pop("pending", None)
        card_box.empty()
        settings = {**options, "top_k": 5, "max_output_tokens": None}
        guarded(attempt, question.strip(), settings)
    elif pending:
        action = render_card(card_box, pending)
        if action:
            card_box.empty()
            handle_card_action(action, pending)


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

    if run_btn and not question.strip():
        st.warning("Please enter a question to evaluate.")
    elif run_btn:
        try:
            doc_ids = [int(item.strip()) for item in expected_doc_ids.split(",") if item.strip()]
        except ValueError:
            st.error("Expected document IDs must be comma-separated numbers, e.g. 1, 2, 5.")
            return
        payload = {"question": question, "expected_doc_ids": doc_ids or None}
        try:
            result = request_json("POST", "/evaluate/query", headers=api_headers(), json=payload)
            if result.get("stopped"):
                with result_col:
                    st.warning(result.get("reason", "This request was stopped by the cost policy."))
                return
            
            with result_col:
                st.markdown("### Results")
                render_answer(result)
                st.metric("Retrieval precision", result.get("retrieval_precision"))
        except Exception as exc:
            st.error(str(exc))


def admin_logs_page() -> None:
    require_login()
    require_admin_role()
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

def cost_chart(frame: pd.DataFrame, x: str, kind: str) -> None:
    """Fixed chart with a labelled y axis in US cents."""
    frame = frame.assign(cents=frame["cost"] * 100)
    base = alt.Chart(frame).encode(
        x=alt.X(f"{x}:N", title=None, sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("cents:Q", title="Cost (US cents)", axis=alt.Axis(format=".3f", grid=True)),
        tooltip=[x, alt.Tooltip("cents:Q", title="cents", format=".4f"), "requests"],
    )
    chart = base.mark_bar(color="#6366f1") if kind == "bar" else base.mark_line(color="#6366f1", point=True)
    st.altair_chart(chart.properties(height=300), use_container_width=True)


def breakdown(rows: list[dict], label: str) -> None:
    if not rows:
        st.info("No usage in this period.")
        return
    frame = pd.DataFrame(rows)
    cost_chart(frame, label, "bar")
    st.dataframe(frame, use_container_width=True, hide_index=True)


def trend_chart(rows: list[dict]) -> None:
    if not rows:
        st.info("No usage in this period.")
        return
    cost_chart(pd.DataFrame(rows), "period", "line")

def cost_dashboard_page() -> None:
    require_login()
    require_admin_role()
    st.markdown("# Cost Dashboard")
    st.caption("Spend comes from saved usage records. Actual cost is tokens used times the model price.")

    period = st.radio("Period", ["This month", "All time"], horizontal=True)
    params = {"this_month": "true"} if period == "This month" else None

    def fetch(path: str, filtered: bool = True) -> Any:
        return request_json(
            "GET", f"/cost/admin/{path}", headers=api_headers(), params=params if filtered else None
        )

    try:
        summary = fetch("summary")
        compare = fetch("estimated-vs-actual")
        by_department = fetch("by-department")
        by_user = fetch("by-user")
        by_project = fetch("by-project")
        by_model = fetch("by-model")
        daily = fetch("trend/daily")
        monthly = fetch("trend/monthly")
        budgets = fetch("budgets", filtered=False)
        top_users = fetch("top-users")
        top_conversations = fetch("top-conversations")
    except Exception as exc:
        st.error(str(exc))
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Total spend", money(summary["actual_cost"]))
    m2.metric("Requests", summary["requests"])
    m3.metric("Tokens", f"{summary['total_tokens']:,}")

    st.markdown("### Estimated vs actual")
    e1, e2, e3 = st.columns(3)
    e1.metric("Estimated", money(compare["estimated_cost"]))
    e2.metric("Actual", money(compare["actual_cost"]))
    percent = compare.get("difference_percent")
    e3.metric(
        "Difference (actual minus estimated)",
        money(compare["difference"]),
        delta=f"{percent:+.1f}%" if percent is not None else None,
        delta_color="inverse",
    )

    st.markdown("### Cost breakdown")
    tab_dept, tab_user, tab_project, tab_model = st.tabs(["Department", "User", "Project", "Model"])
    with tab_dept:
        breakdown(by_department, "department")
    with tab_user:
        breakdown(by_user, "username")
    with tab_project:
        breakdown(by_project, "project")
    with tab_model:
        breakdown(by_model, "model")

    st.markdown("### Trends")
    daily_col, monthly_col = st.columns(2)
    with daily_col:
        st.caption("Daily")
        trend_chart(daily)
    with monthly_col:
        st.caption("Monthly")
        trend_chart(monthly)

    st.markdown("### Budget utilization")
    st.dataframe(
        pd.DataFrame(budgets),
        use_container_width=True,
        hide_index=True,
        column_config={
            "utilization_percent": st.column_config.ProgressColumn(
                "utilization %", min_value=0, max_value=100, format="%.1f%%"
            )
        },
    )

    left, right = st.columns(2)
    with left:
        st.markdown("### Top expensive users")
        st.dataframe(pd.DataFrame(top_users), use_container_width=True, hide_index=True)
    with right:
        st.markdown("### Top expensive conversations")
        st.dataframe(pd.DataFrame(top_conversations), use_container_width=True, hide_index=True)

def seat_page() -> None:
    require_login()
    require_admin_role()
    st.markdown("# Seat Utilization")
    st.caption("Demo data only. Upload a CSV of AI seats to find unused and low-use seats.")

    try:
        path = "/cost/admin/seats/sample"
        sample = backend_request("GET", path, headers=api_headers())
        check_response(sample, path)
        st.download_button("Download sample CSV", sample.content, "seats_sample.csv", "text/csv")
    except BackendError as exc:
        st.error(str(exc))

    p1, p2 = st.columns(2)
    standard = p1.number_input("Standard seat price (USD per month)", min_value=0.0, value=20.0, step=1.0)
    premium = p2.number_input("Premium seat price (USD per month)", min_value=0.0, value=30.0, step=1.0)
    uploaded = st.file_uploader("Seat CSV", type=["csv"])

    if st.button("Analyze seats", type="primary"):
        if uploaded is None:
            st.warning("Choose a CSV file first.")
        else:
            try:
                st.session_state["seat_result"] = request_json(
                    "POST", "/cost/admin/seats/analyze", headers=api_headers(),
                    files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")},
                    data={"standard_price": standard, "premium_price": premium},
                )
            except BackendError as exc:
                st.session_state.pop("seat_result", None)
                st.error(str(exc))

    result = st.session_state.get("seat_result")
    if not result:
        return

    m = result["metrics"]
    st.caption(f"Active means last active within 30 days of {result['as_of']} and at least 1 message.")
    a1, a2, a3 = st.columns(3)
    a1.metric("Seats purchased", m["seats_purchased"])
    a2.metric("Seats assigned", m["seats_assigned"])
    a3.metric("Active users", m["active_users"])
    b1, b2, b3 = st.columns(3)
    b1.metric("Inactive assigned users", m["inactive_assigned"])
    b2.metric("Unused paid seats", m["unused_seats"])
    b3.metric("Premium seats to downgrade", m["downgrade_candidates"])
    st.metric("Potential monthly saving", f"${m['potential_monthly_saving']:,.2f}")

    st.markdown("### How the saving adds up")
    st.dataframe(
        pd.DataFrame(result["saving_breakdown"]).rename(
            columns={"reason": "Reason", "seats": "Seats", "saving": "Saving (USD)"}
        ),
        use_container_width=True, hide_index=True,
    )
    st.markdown("### All seats")
    st.dataframe(pd.DataFrame(result["seats"]), use_container_width=True, hide_index=True)

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

def require_admin_role() -> None:
    if st.session_state.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar Navigation
# ─────────────────────────────────────────────────────────────────────────────

PAGE_LABELS = {
    "Chat": "Chat",
    "Upload Documents": "Documents",
    "Evaluation": "Evaluation",
    "Admin Logs": "Admin Logs",
    "Cost Dashboard": "Cost Dashboard",
    "Seat Utilization": "Seat Utilization",
}
ADMIN_PAGES = {"Admin Logs", "Cost Dashboard", "Seat Utilization"}

with st.sidebar:
    st.markdown("### Enterprise RAG")

    # Signed-out users only see the login page; signed-in users never see it.
    if st.session_state.get("token"):
        username = st.session_state.get("username", "")
        role = st.session_state.get("role", "")
        st.caption(f"{username} / {role}")
        if st.button("Sign out", use_container_width=True):
            sign_out()

        visible_pages = [p for p in PAGE_LABELS if p not in ADMIN_PAGES or role == "admin"]
        page = st.radio(
            "Navigation",
            visible_pages,
            key="nav_page",
            format_func=PAGE_LABELS.get,
        )
        
    else:
        page = "Login"

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
elif page == "Cost Dashboard":
    cost_dashboard_page()
elif page == "Seat Utilization":
    seat_page()
else:
    admin_logs_page()