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
            st.success(f"Signed in as {data['username']} ({data['role']})")
        except Exception as exc:
            st.error(str(exc))


def upload_page() -> None:
    require_login()
    st.header("Upload Documents")
    with st.form("upload-form"):
        uploaded_file = st.file_uploader("Document", type=["pdf", "docx", "txt", "md", "markdown", "csv"])
        title = st.text_input("Title")
        allowed_roles = st.multiselect(
            "Allowed roles",
            options=["admin", "manager", "employee", "guest"],
            default=["employee"],
        )
        allowed_user_ids = st.text_input("Allowed user IDs (comma-separated, optional)")
        submitted = st.form_submit_button("Upload")
    if submitted and uploaded_file:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {
            "title": title,
            "allowed_roles": ",".join(allowed_roles),
            "allowed_user_ids": allowed_user_ids,
        }
        try:
            result = request_json("POST", "/documents/upload", headers=api_headers(), files=files, data=data)
            st.success(f"Uploaded {result['document']['filename']} with {result['chunks_created']} chunks")
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
    question = st.text_area("Question", height=120)
    col_a, col_b = st.columns([1, 1])
    top_k = col_a.slider("Top K", min_value=1, max_value=20, value=5)
    model = col_b.text_input("Model", value="auto")
    if st.button("Ask", type="primary") and question.strip():
        try:
            result = request_json(
                "POST",
                "/chat",
                headers=api_headers(),
                json={"question": question, "top_k": top_k, "model": model},
            )
            render_answer(result)
        except Exception as exc:
            st.error(str(exc))


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
    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Evidence", result["evidence_score"])
    metric_b.metric("Groundedness", result["groundedness_score"])
    metric_c.metric("Latency (ms)", result["latency_ms"])

    with st.expander("Citations", expanded=True):
        for citation in result.get("citations", []):
            st.markdown(f"**{citation['filename']}** | page {citation.get('page_number') or 'n/a'}")
            st.caption(f"doc {citation['document_id']} | chunk {citation['chunk_id']}")
            st.write(citation["quoted_text"])

    with st.expander("Retrieved chunks"):
        st.dataframe(result.get("retrieved_chunks", []), use_container_width=True)


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
            st.rerun()
    page = st.radio(
        "Navigation",
        ["Login", "Upload Documents", "Chat", "Evaluation", "Admin Logs"],
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

