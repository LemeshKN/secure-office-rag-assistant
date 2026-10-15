import json
import os
from typing import Any

import requests
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


st.set_page_config(page_title="Enterprise RAG Agent Platform", layout="wide")


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


def login_page() -> None:
    st.header("Login")
    with st.form("login-form"):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", value="admin123")
        submitted = st.form_submit_button("Sign in")
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
            st.success(f"Signed in as {data['username']} ({data['role']})")
        except Exception as exc:
            st.error(str(exc))


def upload_page() -> None:
    require_login()
    st.header("Upload Documents")
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


    with st.form("upload-form"):
        uploaded_file = st.file_uploader("Document", type=["pdf", "docx", "txt", "md", "markdown", "csv"])
        title = st.text_input("Title")
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
        submitted = st.form_submit_button("Upload")

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

    st.subheader("Accessible Documents")
    try:
        docs = request_json("GET", "/documents", headers=api_headers())
        st.dataframe(docs, use_container_width=True)
    except Exception as exc:
        st.info(str(exc))


def chat_page() -> None:
    require_login()
    st.header("Chat")

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

        if st.button("+ New chat", use_container_width=True):
            st.session_state["conversation_id"] = None
            st.rerun()

        st.subheader("My conversations")

        if not conversations:
            st.caption("No saved conversations yet.")

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
                with st.expander("Sources", expanded=False):
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
                            snippet = snippet[:180].rstrip() + "…"

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
    st.header("Evaluation")
    question = st.text_area("Evaluation question", height=120)
    expected_doc_ids = st.text_input("Expected document IDs (comma-separated, optional)")
    if st.button("Run evaluation", type="primary") and question.strip():
        doc_ids = [int(item.strip()) for item in expected_doc_ids.split(",") if item.strip()]
        payload = {"question": question, "expected_doc_ids": doc_ids or None}
        try:
            result = request_json("POST", "/evaluate/query", headers=api_headers(), json=payload)
            render_answer(result)
            st.metric("Retrieval precision", result.get("retrieval_precision"))
        except Exception as exc:
            st.error(str(exc))


def admin_logs_page() -> None:
    require_login()
    st.header("Admin Logs")
    try:
        logs = request_json("GET", "/logs", headers=api_headers())
        st.dataframe(logs, use_container_width=True)
    except Exception as exc:
        st.error(str(exc))


def render_answer(result: dict[str, Any]) -> None:
    if result.get("warning"):
        st.warning(result["warning"])

    st.subheader("Answer")
    st.write(result["answer"])

    citations = result.get("citations", [])
    if citations:
        with st.expander("Sources", expanded=False):
            for citation in result.get("citations", []):
                filename = citation.get("filename", "Unknown document")
                score = citation.get("score")
                score_text = f" | score: {score:.3f}" if isinstance(score, (int, float)) else ""

                st.markdown(f"**{filename}**{score_text}")

                snippet = citation.get("quoted_text", "") or ""
                if len(snippet) > 180:
                    snippet = snippet[:180].rstrip() + "…"

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
        st.info("Sign in before using this page.")
        st.stop()


with st.sidebar:
    st.title("Enterprise RAG")
    if st.session_state.get("token"):
        st.caption(f"{st.session_state.get('username')} | {st.session_state.get('role')}")
        if st.button("Sign out"):
            st.session_state.clear()
            st.session_state["page"] = "Login"
            st.rerun()

    page = st.radio(
        "Navigation",
        ["Login", "Upload Documents", "Chat", "Evaluation", "Admin Logs"],
        key="page",
    )

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

