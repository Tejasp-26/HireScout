# HireScout

**AI resume screening for recruiters.** Drop in a pile of resumes and HireScout turns them into structured, searchable candidate profiles, then ranks them against any job description, with the skill gaps spelled out.

Built with FastAPI, React, Google Gemini, FAISS and sentence-transformers.

---

## What it does

| | |
|---|---|
| **Resume ingestion** | Drag-and-drop PDF upload or automatic import from a Google Drive folder. Duplicates are caught by file hash *and* by email. |
| **LLM resume parsing** | Gemini extracts a structured profile: contact details, title, years of experience, skills, work history, education and a summary. It returns typed JSON against a Pydantic schema. If no API key is set, a rule-based parser takes over. |
| **Semantic search** | Search in plain English ("backend engineer who has worked with streaming data"). Profiles are embedded with `all-MiniLM-L6-v2` and searched with FAISS (cosine similarity). |
| **Job matching** | Paste a job description and Gemini extracts required skills, nice-to-haves and minimum experience. Every candidate gets a 0–100 match score with matched/missing skills. Optionally, Gemini writes a one-line rationale for the top matches. |
| **AI assistant** | A RAG chat: the question is embedded, the closest candidates are retrieved, and Gemini answers using only their profiles. |
| **Dashboard** | Real analytics: top skills, imports over time, experience distribution, parsing/import stats. |
| **Auth** | JWT login, bcrypt password hashing, `admin` / `recruiter` roles. Every API route is protected. |

## How matching works

```
score = 0.5 × required-skill coverage
      + 0.3 × semantic similarity (JD vs. candidate profile)
      + 0.1 × experience vs. minimum
      + 0.1 × nice-to-have coverage
```

Signals that don't apply (for example a JD with no minimum years) are dropped and the remaining weights are renormalised. Skills are compared through an alias table, so `ReactJS`, `react.js` and `React` count as the same skill, and so do `k8s` and `Kubernetes`. Recruiters can edit the extracted requirements and re-rank.

## Architecture

```
React + Vite + Tailwind  ──REST/JWT──▶  FastAPI
                                          │
            ┌─────────────────────────────┼──────────────────────────────┐
            ▼                             ▼                              ▼
   SQLite / PostgreSQL           FAISS index (on disk)            Google Gemini
   candidates, jobs, users,      ids = candidate ids,             structured parsing,
   ingestion logs                cosine over MiniLM vectors       JD analysis, RAG chat
            ▲
            │  ingestion pipeline: validate → dedupe → extract text → parse → store → index → log
   PDF upload  ·  Google Drive (service account, background sync)
```

```
backend/
  app/
    main.py              FastAPI app, CORS, startup (DB + index)
    config.py            all settings from env / .env
    models.py            SQLAlchemy models: User, Candidate, Job, IngestionLog
    schemas.py           Pydantic request/response models
    security.py          bcrypt, JWT, auth dependencies
    routers/             auth, candidates, resumes, jobs, assistant, analytics
    services/
      ingestion.py       one pipeline for every resume source
      pdf_text.py        PDF → text (repairs "L E T T E R - S P A C E D" exports)
      resume_parser.py   Gemini structured extraction + fallback
      heuristic_parser.py  regex/rule-based parser
      skills.py          ~150-skill vocabulary with aliases
      vector_index.py    FAISS + sentence-transformers
      matching.py        requirement extraction, scoring, AI rationale
      drive_sync.py      Google Drive background import
      llm.py             Gemini client wrapper
  scripts/create_user.py
  tests/                 pytest (offline: no model download, no API key)
frontend/
  src/pages/             Dashboard, Candidates, CandidateDetail, Jobs, JobDetail, Import, Assistant, Login
  src/components/        Layout, shared UI
  src/lib/               axios client, auth context
```

## Run it locally

**Requirements:** Python 3.11+, Node 20+.

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then set SECRET_KEY and (optionally) GEMINI_API_KEY
python -m scripts.create_user --email you@example.com --name "Your Name" --role admin
uvicorn app.main:app --reload
```

The API runs on http://localhost:8000, with interactive docs at http://localhost:8000/docs.
With no `DATABASE_URL`, data lives in `backend/data/` (SQLite, uploaded PDFs, search index).
The first start downloads the ~90 MB embedding model.

A free Gemini API key is available at https://aistudio.google.com/apikey. Without one, everything still works with rule-based parsing and keyword-based requirement extraction, and the assistant returns search results without a written answer.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env              # VITE_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:5173 and sign in with the user you created.

### 3. Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The tests run fully offline. They use a hashing stand-in for the embedding model and generate their own PDFs.

## Optional: Google Drive auto-import

1. In Google Cloud Console, create a project, enable the **Google Drive API** and create a **service account**. Download its JSON key.
2. Share your resumes folder with the service account's email (`…@….iam.gserviceaccount.com`). **Viewer** access is enough.
3. Set `GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/key.json` and `GOOGLE_DRIVE_FOLDER_ID=<id from the folder URL>` in `backend/.env`.
4. Click **Sync now** on the Import page. Files already imported are skipped without being downloaded again.

A service account is used instead of a user OAuth token because it never expires and needs no browser login, so it works unattended on a server.

## API overview

All routes except `/auth/login` and `/health` require `Authorization: Bearer <token>`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Get a JWT |
| GET | `/auth/me` | Current user |
| GET/POST | `/auth/users` | List / create users (admin) |
| GET | `/candidates?q=&skill=&page=` | Keyword-filtered, paginated list |
| GET | `/search?q=` | Semantic search |
| GET/DELETE | `/candidates/{id}` | Profile / delete |
| GET | `/candidates/{id}/resume` | Download original PDF |
| POST | `/candidates/{id}/reparse` | Re-run parsing (e.g. after adding a Gemini key) |
| POST | `/resumes/upload` | Import one PDF |
| GET | `/resumes/logs` | Import history |
| GET/POST | `/resumes/drive-sync` | Drive sync status / start |
| GET/POST | `/jobs` | List / create (extracts requirements) |
| GET/PATCH/DELETE | `/jobs/{id}` | View / edit requirements / delete |
| GET | `/jobs/{id}/matches?explain=5` | Ranked candidates (+ AI rationale for top N) |
| POST | `/assistant/chat` | RAG chat over candidates |
| GET | `/analytics` | Dashboard data |

## Deploying

- **Backend:** any host that runs a Python web process (Render, Railway, Fly.io). Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL` to a managed Postgres (Neon/Supabase free tiers work), plus `SECRET_KEY`, `GEMINI_API_KEY` and `CORS_ORIGINS=<your frontend URL>`. Mount a persistent disk at `DATA_DIR` so uploaded PDFs survive redeploys. The search index rebuilds itself from the database if it's missing.
- **Frontend:** Vercel or Netlify. Set `VITE_API_URL` to the backend URL. `vercel.json` already handles SPA routing.

## Roadmap

- Candidate pipeline stages (new → shortlisted → interview → offer) and recruiter notes
- DOCX resume support and OCR for scanned PDFs
- Background job queue for large batch imports
- Email outreach templates generated from match results

## Privacy note

Resumes contain personal data. Use your own or synthetic resumes for demos, and never commit real candidate files. `backend/data/` is git-ignored for this reason.
