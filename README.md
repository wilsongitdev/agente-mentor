# CV Analyzer – Multi-Agent AI Learning Path Platform

A production-ready multi-agent system that analyses CVs and generates personalised
learning paths using **LangGraph**, **FastAPI**, **Firebase**, **FAISS**, and a
modern **React** frontend.

---

## Architecture Overview

```
PDF Upload
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                  LangGraph Pipeline                  │
│                                                     │
│  ┌──────────────┐    ┌──────────────────┐           │
│  │  Agent 1     │───►│    Agent 2        │           │
│  │  PDF Parser  │    │  Skill Extractor  │           │
│  │  pdfplumber  │    │  (LLM: GPT/Claude)│           │
│  └──────────────┘    └────────┬─────────┘           │
│                               │                     │
│  ┌──────────────┐    ┌────────▼─────────┐           │
│  │  Agent 4     │◄───│    Agent 3        │           │
│  │ Learning Path│    │  Course Matcher   │           │
│  │  Generator   │    │  (FAISS + Firebase│           │
│  └──────┬───────┘    └──────────────────┘           │
│         │                                           │
└─────────┼───────────────────────────────────────────┘
          │
          ▼
    Firebase (persist)
          │
          ▼
    FastAPI Response ──► React Frontend
```

---

## Tech Stack

| Layer           | Technology                          |
|----------------|-------------------------------------|
| Orchestration   | LangGraph 0.1.x                    |
| LLM             | OpenAI GPT-4o-mini OR AWS Bedrock Claude |
| Embeddings      | OpenAI text-embedding-3-small       |
| PDF Parsing     | pdfplumber + PyMuPDF + unstructured |
| Vector Store    | FAISS (or Chroma)                   |
| NoSQL DB        | Firebase Realtime Database          |
| API             | FastAPI + Uvicorn                   |
| Frontend        | React 18 + Vite + Tailwind CSS      |
| Environment     | Miniconda + Python 3.11             |

---

## Project Structure

```
notebook-analizer/
├── backend/
│   ├── agents/
│   │   ├── pdf_parser_agent.py       # Agent 1: PDF → text
│   │   ├── skill_extraction_agent.py # Agent 2: text → skills (LLM)
│   │   ├── course_matching_agent.py  # Agent 3: skills → courses (FAISS)
│   │   └── learning_path_agent.py    # Agent 4: courses → roadmap (LLM)
│   ├── api/
│   │   ├── main.py                   # FastAPI app
│   │   └── routes/
│   │       ├── cv.py                 # POST /upload-cv
│   │       └── learning_path.py      # GET /learning-path/:id
│   ├── core/
│   │   ├── graph.py                  # LangGraph StateGraph definition
│   │   └── state.py                  # Shared AgentState TypedDict
│   ├── config/
│   │   └── settings.py               # Pydantic-settings configuration
│   ├── db/
│   │   └── seed_courses.py           # Firebase + FAISS seeding script
│   ├── prompts/
│   │   ├── skill_extraction.py       # LLM prompt for Agent 2
│   │   └── learning_path.py          # LLM prompt for Agent 4
│   ├── schemas/                      # Pydantic models
│   ├── services/
│   │   ├── pdf_service.py
│   │   ├── llm_service.py
│   │   ├── firebase_service.py
│   │   └── vector_store_service.py
│   ├── utils/logger.py
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CVUpload.jsx
│   │   │   ├── SkillsDisplay.jsx
│   │   │   ├── LearningPath.jsx
│   │   │   └── LoadingSpinner.jsx
│   │   ├── pages/
│   │   │   ├── HomePage.jsx
│   │   │   └── ResultsPage.jsx
│   │   └── services/api.js
│   ├── package.json
│   └── vite.config.js
├── environment.yml
└── README.md
```

---

## Setup Guide

### 1 – Create Conda Environment

```bash
conda env create -f environment.yml
conda activate cv-analyzer
```

### 2 – Configure Environment Variables

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
```

Minimum required values:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
FIREBASE_CREDENTIALS_PATH=./config/firebase_credentials.json
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com
```

### 3 – Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create a project → Enable **Realtime Database**
3. Go to **Project Settings → Service Accounts → Generate new private key**
4. Save the downloaded JSON as `backend/config/firebase_credentials.json`
5. Set `FIREBASE_DATABASE_URL` in your `.env`

### 4 – Seed Courses into Firebase + Build Vector Index

```bash
cd backend
python db/seed_courses.py
```

This uploads 20 curated courses to Firebase and builds the FAISS index at `./db/faiss_index`.

### 5 – Run the Backend

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 6 – Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: http://localhost:5173

---

## API Reference

### `POST /api/v1/upload-cv`
Upload a PDF CV. Returns `session_id` immediately; processing runs in background.

**Request:** `multipart/form-data` with `file` field (PDF, max 10 MB)

**Response:**
```json
{
  "session_id": "uuid",
  "filename": "my-cv.pdf",
  "status": "processing",
  "message": "CV received. Analysis started…"
}
```

### `GET /api/v1/job-status/{session_id}`
Poll for pipeline status.

**Response:**
```json
{ "status": "processing" }         // still running
{ "status": "completed", "learning_path": { ... } }
{ "status": "failed", "errors": [ "..." ] }
```

### `GET /api/v1/learning-path/{session_id}`
Retrieve the completed learning path (also persisted in Firebase).

### `POST /api/v1/index-courses`
Trigger a background re-index of all courses from Firebase → FAISS.

---

## Supported LLM Providers

### OpenAI (default)
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### AWS Bedrock (Claude)
```env
LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

---

## Extending the System

### Add a new course
Edit `backend/db/seed_courses.py` → `COURSE_CATALOG` and re-run the seed script.

### Swap Vector DB: FAISS → Chroma
```env
VECTOR_STORE_TYPE=chroma
CHROMA_PERSIST_DIR=./db/chroma
```

### Add a new agent
1. Create `backend/agents/my_agent.py` with a `my_agent_node(state) → dict` function
2. Register it in `backend/core/graph.py`
3. Add output fields to `backend/core/state.py`

### Scale to microservices
Replace the in-memory `_job_status` dict with **Redis** and deploy each agent as a
separate service communicating via a message queue (e.g. SQS / RabbitMQ).

---

## Possible Improvements

| Area | Suggestion |
|------|-----------|
| Auth | Add JWT authentication to the API |
| Caching | Redis for job results + LLM response caching |
| Queue | Celery / SQS for async background tasks |
| Multi-language | Detect CV language and adjust prompts |
| Streaming | Stream LLM output to the frontend via SSE |
| Observability | LangSmith tracing for the LangGraph pipeline |
| Tests | Pytest + mocked LLM for unit/integration testing |
| Docker | Dockerfile + docker-compose for one-command startup |
