# AI Multi-Agent Discussion Panel

A multi-engine AI debate platform powered by **AG2 (AutoGen)** and LangGraph, with FastAPI backend and React frontend. Run multi-agent discussions with streaming responses, multi-provider support (OpenAI, Gemini, Claude, Grok), and persistent conversation threads.

## What's New in v0.7.0 (Development)

### Human-in-the-Loop Debate Modes
- **Autonomous Mode**: Panelists debate without interruption until consensus or max rounds
- **Supervised Mode**: Debate pauses after each round for user review, voting, and optional input
- **Participatory Mode**: Users can inject messages, @mention panelists, and guide the discussion

### Adversarial Stance Assignment
Real debate team logic for diverse positions:
- **Even panelists**: Half PRO, half CON (e.g., 4 panelists = 2 PRO, 2 CON)
- **Odd panelists**: Half PRO, half CON, last is Devil's Advocate (e.g., 3 panelists = 1 PRO, 1 CON, 1 Devil's Advocate)
- **Devil's Advocate**: Strictly NEUTRAL critic who challenges BOTH sides equally

### Response Compartmentalization
Prevents "groupthink" in Round 1:
- Panelists generate initial responses **independently** without seeing each other
- Responses are added to shared context only AFTER all panelists have responded
- Subsequent rounds use normal debate context where panelists see and respond to each other

### Debate Quality Evaluation
- **Stance Extraction**: Tracks FOR/AGAINST/CONDITIONAL/NEUTRAL positions per round
- **Argument Parsing**: Identifies claims, evidence, challenges, and concessions
- **Responsiveness Scoring**: Measures how well panelists address opponent arguments
- **Live Scoring**: Real-time scoreboard showing debate performance

### Enhanced UI
- **Live Stance Display**: Color-coded stance badges during debate (FOR=green, AGAINST=red, NEUTRAL=gray)
- **Role Indicators**: Shows assigned debate roles (PRO/CON/DEVIL'S ADVOCATE)
- **Prominent User Input**: Clear "Your Turn" interface when debate pauses
- **Debate Scoreboard**: Rankings with score breakdowns

## Previous Releases

### v0.6.0
- **AG2 Engine Support**: Added AG2 (AutoGen v0.3.0+) as the primary debate engine alongside LangGraph
- **Multi-Provider Support**: Full support for OpenAI, Google Gemini, Anthropic Claude, and xAI Grok
- **Enhanced UX**: Improved panelist naming validation and regenerate UI consistency

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

### Backend (FastAPI + AG2/LangGraph)

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

---

## Architecture

### Debate Flow
```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Debate Orchestrator (AG2 GroupChat)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Round 0: Independent Generation                 │   │
│  │  • Panelist 1 (PRO) → generates alone           │   │
│  │  • Panelist 2 (CON) → generates alone           │   │
│  │  • Panelist 3 (DEVIL) → generates alone         │   │
│  │  • All responses added to context together      │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Round 1+: Debate with Context                   │   │
│  │  • Each panelist sees all previous responses    │   │
│  │  • Stance tracking & scoring per round          │   │
│  │  • Supervised mode pauses for user input        │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Moderation Phase                                │   │
│  │  • Consensus check or max rounds reached        │   │
│  │  • Generate final summary                       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
     │
     ▼
  SSE Stream → Frontend (real-time updates)
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `DebateOrchestrator` | `backend/debate/orchestrator.py` | Phase-based state machine for debate control |
| `AG2DebateService` | `backend/debate/service.py` | Service layer, SSE event streaming |
| `StanceExtractor` | `backend/debate/evaluators.py` | LLM-based stance classification |
| `DebateScorer` | `backend/debate/scoring.py` | Points-based debate scoring |
| `DebateViewer` | `frontend/src/components/DebateViewer.tsx` | Debate UI with scoreboard |
| `StanceIndicator` | `frontend/src/components/StanceIndicator.tsx` | Stance badges display |

### Debate Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `autonomous` | Runs to completion without pauses | Quick answers, background processing |
| `supervised` | Pauses after each round for review | Quality control, voting on arguments |
| `participatory` | User can inject messages each round | Interactive discussions, guided debates |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ask-stream` | POST | Start debate with SSE streaming |
| `/resume-debate/{thread_id}` | POST | Resume paused debate |
| `/storage-info` | GET | Check persistence mode |
| `/initial-keys` | GET | Get available API keys |

### SSE Event Types

| Event | Data | Description |
|-------|------|-------------|
| `status` | `{message}` | Progress updates |
| `panelist_response` | `{panelist, response}` | Individual panelist output |
| `stance_extracted` | `{panelist, stance, confidence}` | Stance classification result |
| `roles_assigned` | `{roles}` | PRO/CON/DEVIL assignments |
| `debate_round` | `{round}` | Complete round data |
| `score_update` | `{panelist, round_total, cumulative_total}` | Scoring events |
| `debate_paused` | `{thread_id, panel_responses}` | Supervised mode pause |
| `result` | `{summary, panel_responses}` | Final debate result |

---

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional - Multi-provider support
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
XAI_API_KEY=...

# Database
PG_CONN_STR=postgresql://...
USE_IN_MEMORY_CHECKPOINTER=1  # For local testing

# JWT Auth (optional)
JWT_SECRET=...
```

### Debate Settings (Frontend)

- **Debate Mode**: autonomous / supervised / participatory
- **Max Rounds**: 1-10 (default: 3)
- **Stance Mode**: adversarial (default) / free

---

## Development

### Running Tests
```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

### Code Structure
```
multi-agent-chat/
├── backend/
│   ├── debate/
│   │   ├── orchestrator.py  # Debate state machine
│   │   ├── service.py       # AG2 service wrapper
│   │   ├── evaluators.py    # Quality evaluation
│   │   ├── scoring.py       # Debate scoring
│   │   ├── state.py         # TypedDict definitions
│   │   └── agents.py        # AG2 agent factory
│   ├── main.py              # FastAPI app
│   └── config.py            # Environment config
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main application
│   │   ├── api.ts           # API client
│   │   └── components/
│   │       ├── DebateViewer.tsx
│   │       ├── DebateScoreboard.tsx
│   │       └── StanceIndicator.tsx
│   └── package.json
├── Makefile
├── start.sh
└── README.md
```
