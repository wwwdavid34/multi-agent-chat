# AI Multi-Agent Discussion Panel

LangGraph + FastAPI backend with a Vite/React frontend for running multi-agent discussions that persist across a thread ID.

## Quick Start

### Prerequisites
1. Ensure conda environment `magent` exists and is activated
2. Copy `backend/.env.example` to `backend/.env` and configure required variables

### Easy Startup (Recommended)

**Option 1: Using Makefile**
```bash
make start          # Start both backend and frontend
make start-backend  # Start only backend
make start-frontend # Start only frontend
make help          # Show all available commands
```

**Option 2: Using bash script**
```bash
./start.sh         # Start both (default)
./start.sh backend # Start only backend
./start.sh frontend # Start only frontend
```

### First-time Setup
```bash
make install  # Install all dependencies (backend + frontend)
```

---

## Manual Setup

### Backend (FastAPI + LangGraph)

1. `conda activate magent`
2. `cd backend`
3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`, `PG_CONN_STR`, and optional `USE_IN_MEMORY_CHECKPOINTER=1` for local tests.
4. Install Python deps once: `pip install -e '.[dev]'`
5. Run the API: `uvicorn main:app --reload`

Tests:
```bash
make test        # Run all tests
make test-watch  # Run tests in watch mode
```

Or manually (use in-memory saver):
```bash
cd backend
USE_IN_MEMORY_CHECKPOINTER=1 pytest
```

## Frontend (Vite + React)

1. `cd frontend`
2. `cp .env.example .env` and point `VITE_API_BASE_URL` to the FastAPI server
3. `npm install`
4. `npm run dev` (serves at http://localhost:5173 by default)

The frontend lets you pick a thread ID, ask questions, and view panelist responses plus the moderator summary. Keep the same thread ID to maintain context across turns.
