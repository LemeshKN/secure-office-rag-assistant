# Enterprise RAG Agent Platform

An internal AI assistant. Employees upload company documents, ask questions, and get answers based only on documents they are allowed to access.

---

## 1. How It Works

1. You upload a document.
2. The system splits it into chunks and stores them for search.
3. When you ask a question, the system retrieves the most relevant chunks.
4. The AI writes an answer using only those chunks.
5. The answer shows source citations and relevance scores.

---

## 2. Access Control

Each user sees only their own conversations. You can share a document in three ways:

| Sharing method | Who can access the document |
|---|---|
| Allowed roles | Every user with the selected role |
| Allowed user IDs | Only the selected users |
| Share with my manager | Only the uploader's assigned manager |

**Example:** Lemesh uploads `project-schedule.txt` and selects **Share with my manager**. Amit, Lemesh's manager, can ask questions about it. Priya cannot, unless someone shares it with her directly.

---

## 3. User Hierarchy

```text
Admin
├── HR
└── Manager
      └── Lemesh

Priya (Developer, no assigned manager)
```

- **Admin** manages the system and views admin logs.
- **Lemesh** reports to **Amit**, the Manager.
- **Priya** has no manager. She can receive document access through user-specific sharing.

---

## 4. Features

- Login with JWT tokens
- Upload PDF, DOCX, TXT, Markdown, and CSV files
- Question answering with source citations and relevance scores
- Conversation history
- Sharing by role, user ID, or manager
- Streamed chat responses
- Evaluation page for retrieval quality
- Admin query logs

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Database | SQLite with SQLAlchemy |
| Vector database | ChromaDB |
| Authentication | JWT bearer tokens |
| AI workflow | LangGraph |
| LLM providers | Mock, OpenAI-compatible, Ollama, Anthropic, Gemini |

---

## 6. Project Structure

```text
enterprise-rag-agent-platform/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── ingestion/
│   │   ├── rag/
│   │   ├── retrieval/
│   │   ├── main.py
│   │   └── models.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── streamlit_app.py
│   ├── requirements.txt
│   └── Dockerfile
├── sample_documents/
├── docs/
│   └── DEPLOYMENT.md
├── docker-compose.yml
└── README.md
```

---

## 7. Sample Documents

| File | Tests |
|---|---|
| `company-leave-policy.txt` | General policy questions |
| `hr-onboarding-guide.txt` | HR-role access |
| `private-project-notes.txt` | Private document isolation |
| `project-schedule.txt` | Manager sharing |

---

## 8. Local Setup

**Prerequisites:** Python 3.11, pip, Git

**Backend:**

```powershell
cd backend
python -m venv .venv311
.\.venv311\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**

```powershell
cd frontend
python -m venv .venv311
.\.venv311\Scripts\activate
pip install -r requirements.txt
```

---

## 9. Environment Variables

Copy the example file and fill in your values:

```powershell
copy .env.example .env
```

Example settings:

```text
DATABASE_URL=sqlite:///./data/app.db
LLM_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_BASE_URL=
JWT_SECRET_KEY=change-this-in-production
```

Never commit real API keys, passwords, or JWT secrets to Git. In production, store secrets in environment variables or a secret manager.

---

## 10. Run the Application

**Backend** (terminal 1):

```powershell
cd backend
.\.venv311\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`

**Frontend** (terminal 2):

```powershell
cd frontend
.\.venv311\Scripts\activate
streamlit run streamlit_app.py --server.port 8501
```

- App: `http://localhost:8501`

---

## 11. Docker

```powershell
docker compose up --build
```

To stop:

```powershell
docker compose down
```

---

## 12. Using the App

**Sign in:** Enter your username and password, then click **Sign in**.

**Upload a document:**

1. Open **Upload Documents**.
2. Select a file and enter a title.
3. Choose sharing options: allowed roles, specific users, or **Share with my manager**.
4. Click **Upload**.

**Ask a question:**

1. Open **Chat**.
2. Select or create a conversation.
3. Enter your question.
4. Open **Sources** to see the referenced documents and scores.

---

## 13. Evaluation

The **Evaluation** page checks whether the system retrieves the correct document for a question.

**Retrieval precision** = correct retrieved chunks / total retrieved chunks

**Example:** If 4 of 5 retrieved chunks come from the expected document, precision is 4 / 5 = 0.8.

### Run an evaluation

1. Sign in and open **Upload Documents** to find the ID of the document you want to test.
2. Open **Evaluation**.
3. Enter a question in **Question**.
4. Enter the expected document ID in **Expected document IDs**.
5. Click **Run evaluation**.
6. Review the answer, citations, and precision score.

### Worked example

Upload `company-leave-policy.txt`. If its ID is `9`:

| Field | Value |
|---|---|
| Question | How many paid leave days do employees receive per year? |
| Expected document IDs | `9` |
| Expected result | Retrieval precision of 0.8 or higher |

### Test questions

| Document | Question |
|---|---|
| `company-leave-policy.txt` | How many paid leave days do employees receive per year? |
| `company-leave-policy.txt` | How far in advance must leave requests be submitted? |
| `project-schedule.txt` | When is the MapleBridge project checkpoint scheduled? |
| `hr-onboarding-guide.txt` | What must new employees complete on their first day? |
| `private-project-notes.txt` | When is the internal budget review scheduled? |

Evaluation measures retrieval only. Check the final answer wording yourself.

---

## 14. Privacy Test Checklist

| Test | Expected result |
|---|---|
| User A uploads a private document | Only User A can query it |
| User A shares a document with User B by ID | User B can query it |
| User A shares a document with a role | Only that role can query it |
| User A shares with their manager | Only the assigned manager can query it |
| User B tries to access User A's chat | Access denied |
| User without a manager selects manager sharing | Upload is rejected |
| Unrelated question | System refuses due to insufficient evidence |

---

## 15. Production Recommendations

- Use PostgreSQL instead of SQLite.
- Deploy behind HTTPS with a reverse proxy such as Nginx.
- Restrict CORS to your frontend domain.
- Store uploaded files in encrypted or cloud storage.
- Enable database backups and monitor logs.
- Rotate JWT secrets regularly.
- Limit admin access to authorized staff.

---

## 16. Troubleshooting

| Problem | Fix |
|---|---|
| Backend does not start | Check the virtual environment and installed requirements |
| Frontend cannot connect | Confirm the backend is running on port 8000 |
| Upload returns 404 | Confirm `POST /documents/upload` appears at `/docs` |
| No answer returned | Check that your user has access to the relevant documents |
| Streaming does not appear | Refresh Streamlit and confirm the streaming endpoint is available |
| Docker fails | Confirm Docker Desktop is running and ports are free |