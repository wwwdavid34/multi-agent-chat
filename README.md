# AI Multi-Agent Discussion Panel

LangGraph + FastAPI backend with a Vite/React frontend for running multi-agent discussions that persist across a thread ID.

## Backend (FastAPI + LangGraph)

1. `conda activate magent`
2. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`, `PG_CONN_STR`, and optional `USE_IN_MEMORY_CHECKPOINTER=1` for local tests.
3. `cd backend`
4. Install Python deps once: `pip install -e '.[dev]'`
5. Run the API: `uvicorn main:app --reload`

Tests (use in-memory saver):
```
cd backend
USE_IN_MEMORY_CHECKPOINTER=1 pytest
```

## Frontend (Vite + React)

1. `cd frontend`
2. `cp .env.example .env` and point `VITE_API_BASE_URL` to the FastAPI server
3. `npm install`
4. `npm run dev` (serves at http://localhost:5173 by default)

The frontend lets you pick a thread ID, ask questions, and view panelist responses plus the moderator summary. Keep the same thread ID to maintain context across turns.
