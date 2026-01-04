# Installation Guide: Dependency Management

## Overview

The refactor adds **AG2** as a new optional debate backend alongside the existing LangGraph backend. Both backends can coexist in the same installation.

### New Dependency Added
- **ag2>=0.3.0** - AutoGen framework for alternative debate orchestration
- **asyncpg>=0.29.0** - Async PostgreSQL driver (for AG2 PostgreSQL storage)

### Required Python Version
- **Python 3.10+** (as specified in pyproject.toml)

---

## Quick Start: Installation

### 1. Fresh Installation (Recommended)

```bash
# Clone the repository
git clone <repository>
cd multi-agent-chat

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies (including new AG2)
pip install -e .

# Install optional development dependencies
pip install -e ".[dev]"
```

### 2. Update Existing Installation

```bash
# Activate your existing environment
source venv/bin/activate

# Upgrade to latest dependencies
pip install --upgrade pip setuptools wheel

# Update all packages (including new AG2)
pip install -e . --upgrade

# Verify installation
python3 -c "import ag2; print(f'AG2 version: {ag2.__version__}')"
```

### 3. Install Only Core Dependencies (Skip AG2)

If you only want LangGraph and don't need AG2:

```bash
# Edit pyproject.toml and remove ag2>=0.3.0 from dependencies
# Then install normally:
pip install -e .
```

---

## Detailed Dependency Installation

### Option A: Full Installation (Recommended)

```bash
# Install with all dependencies including AG2
pip install -e .
```

**What gets installed:**
- FastAPI 0.111+
- Uvicorn with standard extras
- LangChain ecosystem (OpenAI, Google, Anthropic, Community, Tavily)
- LangGraph and PostgreSQL checkpointing
- psycopg3 (PostgreSQL driver)
- AG2 0.3.0+ (NEW)
- asyncpg for async database access (see below)
- Python-dotenv
- httpx
- Tavily Python SDK

### Option B: Development Installation

```bash
# Install core + development tools (pytest, asyncio testing)
pip install -e ".[dev]"
```

**Additional packages:**
- pytest>=8.2
- pytest-asyncio>=0.23

### Option C: Minimal Installation (LangGraph Only)

If you want to keep using only LangGraph without AG2:

```bash
# Remove ag2>=0.3.0 from pyproject.toml dependencies list
# Then run:
pip install -e .
```

---

## Adding asyncpg Dependency (Important for AG2)

The AG2 backend with PostgreSQL storage requires asyncpg. You have two options:

### Option 1: Add to pyproject.toml (Recommended)

Edit `pyproject.toml` and add asyncpg to dependencies:

```toml
dependencies = [
    # ... existing dependencies ...
    "ag2>=0.3.0",
    "asyncpg>=0.29.0",  # Add this line
]
```

Then reinstall:

```bash
pip install -e . --upgrade
```

### Option 2: Install asyncpg Separately

```bash
pip install asyncpg>=0.29.0
```

### Verify asyncpg Installation

```bash
python3 -c "import asyncpg; print(f'asyncpg version: {asyncpg.__version__}')"
```

---

## Verification Steps

After installation, verify all components are working:

### 1. Check Python Version

```bash
python3 --version
# Should output: Python 3.10.x or higher
```

### 2. Verify Core Dependencies

```bash
python3 -c "
import fastapi
import uvicorn
import langchain
import langgraph
print('✓ FastAPI:', fastapi.__version__)
print('✓ Uvicorn:', uvicorn.__version__)
print('✓ LangChain:', langchain.__version__)
print('✓ LangGraph:', langgraph.__version__)
"
```

### 3. Verify LLM Provider Dependencies

```bash
python3 -c "
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
print('✓ LangChain providers installed')
"
```

### 4. Verify AG2 Installation

```bash
python3 -c "
import ag2
print(f'✓ AG2 version: {ag2.__version__}')
"
```

### 5. Verify asyncpg (for AG2 PostgreSQL storage)

```bash
python3 -c "
import asyncpg
print(f'✓ asyncpg version: {asyncpg.__version__}')
"
```

### 6. Full System Check

```bash
cd backend
python3 -c "
print('🟦 Checking core modules...')
import fastapi; print('✓ FastAPI')
import langchain; print('✓ LangChain')
import langgraph; print('✓ LangGraph')

print('\n🟦 Checking AG2...')
import ag2; print('✓ AG2')
import asyncpg; print('✓ asyncpg')

print('\n🟦 Checking debate modules...')
from debate.service import AG2DebateService; print('✓ AG2DebateService')
from debate.persistence import PostgresDebateStorage; print('✓ PostgresDebateStorage')
from debate.orchestrator import DebateOrchestrator; print('✓ DebateOrchestrator')

print('\n✅ All dependencies verified!')
"
```

---

## Environment Setup

### 1. Create .env File

```bash
cd backend
cp .env.example .env  # If available
# or create new .env
```

### 2. Required Environment Variables

```bash
# .env file
OPENAI_API_KEY=your_openai_key
PG_CONN_STR=postgresql://user:password@localhost/debate_db
TAVILY_API_KEY=your_tavily_key

# Optional: Enable AG2 backend
DEBATE_ENGINE=ag2

# Optional: Use in-memory storage for testing
USE_IN_MEMORY_CHECKPOINTER=1
```

### 3. Load Environment

```bash
# Automatically loaded by python-dotenv
python3 main.py
```

---

## Docker Installation

### Dockerfile Setup

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for asyncpg
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Setup

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DEBATE_ENGINE: ag2
      PG_CONN_STR: postgresql://user:password@postgres:5432/debate_db
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: debate_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Build and Run

```bash
docker-compose up --build
```

---

## Troubleshooting Installation

### Issue: "ModuleNotFoundError: No module named 'ag2'"

**Solution:**
```bash
# Reinstall with AG2
pip install -e . --upgrade

# Verify
python3 -c "import ag2; print(ag2.__version__)"
```

### Issue: "ModuleNotFoundError: No module named 'asyncpg'"

**Solution:**
```bash
# Install asyncpg separately
pip install asyncpg>=0.29.0

# Or update pyproject.toml and reinstall
pip install -e . --upgrade
```

### Issue: "asyncpg requires PostgreSQL development headers"

**Solution (Linux - Ubuntu/Debian):**
```bash
sudo apt-get install postgresql-client libpq-dev
pip install asyncpg>=0.29.0
```

**Solution (macOS):**
```bash
brew install postgresql
pip install asyncpg>=0.29.0
```

**Solution (Windows):**
```bash
# Download PostgreSQL from postgresql.org
# Or use pip's pre-built wheels (usually automatic)
pip install asyncpg>=0.29.0
```

### Issue: "Python version requirements not met"

**Solution:**
```bash
# Check your Python version
python3 --version

# If < 3.10, install Python 3.10+
# Then create virtual environment with correct version
python3.10 -m venv venv
source venv/bin/activate
pip install -e .
```

### Issue: "Compilation error when installing asyncpg"

**Solution:**
```bash
# Use pre-built wheels (recommended)
pip install --only-binary asyncpg asyncpg>=0.29.0

# Or install development headers first
# Linux: sudo apt-get install python3-dev libpq-dev
# macOS: brew install postgresql python3
```

---

## Dependency Management Best Practices

### 1. Use Virtual Environments

```bash
# Create
python3.10 -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Always work inside the virtual environment
```

### 2. Freeze Dependencies for Production

```bash
# Generate requirements.txt for reproducible builds
pip freeze > requirements-frozen.txt

# Later: install from frozen file
pip install -r requirements-frozen.txt
```

### 3. Keep Dependencies Updated

```bash
# Check for outdated packages
pip list --outdated

# Update a specific package
pip install --upgrade ag2

# Update all packages
pip install --upgrade -e .
```

### 4. Monitor Security

```bash
# Check for known vulnerabilities
pip install safety
safety check

# Or use pip-audit
pip install pip-audit
pip-audit
```

---

## Switching Between Backends

### Use AG2 (New Backend)

```bash
# Install all dependencies (includes AG2)
pip install -e .

# Enable AG2
export DEBATE_ENGINE=ag2

# Run server
python3 main.py
```

### Use LangGraph (Legacy Backend)

```bash
# Install all dependencies (LangGraph included)
pip install -e .

# Use default (LangGraph)
unset DEBATE_ENGINE
# or explicitly:
export DEBATE_ENGINE=langgraph

# Run server
python3 main.py
```

---

## Dependency Size Reference

Approximate disk space usage:

```
Core dependencies (without AG2):
├── FastAPI ecosystem: ~10 MB
├── LangChain ecosystem: ~150 MB
├── LangGraph: ~20 MB
└── PostgreSQL drivers: ~5 MB
Total: ~185 MB

AG2 (additional):
├── AG2 framework: ~30 MB
└── asyncpg: ~2 MB
Total: ~32 MB

Full installation: ~217 MB
```

---

## Complete Installation Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] `pip install -e .` completed successfully
- [ ] `pip install -e ".[dev]"` for development (optional)
- [ ] All verification checks passed
- [ ] `.env` file configured with API keys
- [ ] Database (PostgreSQL) running (if using AG2)
- [ ] Can import all modules: `ag2`, `asyncpg`, `langgraph`, etc.
- [ ] Logging shows correct engine at startup (🔵 or 🟢)
- [ ] Tests passing: `pytest tests/test_ag2_debate.py`

---

## Next Steps

After installation:

1. **Start the backend:**
   ```bash
   python3 main.py
   ```

2. **Check startup logs:**
   ```
   🔵 DEBATE ENGINE: AG2 (New Backend)
   or
   🟢 DEBATE ENGINE: LangGraph (Legacy Backend)
   ```

3. **Run tests:**
   ```bash
   pytest tests/test_ag2_debate.py -v
   ```

4. **Try a request:**
   ```bash
   curl -X POST http://localhost:8000/ask-stream \
     -H "Content-Type: application/json" \
     -d '{"thread_id":"test","question":"Hello AI","panelists":[]}'
   ```

For detailed usage, see:
- `LOGGING_GUIDE.md` - Understanding log output
- `QUICK_ENGINE_CHECK.md` - Quick visual reference
- `REFACTOR_SUMMARY.md` - Complete refactor details
