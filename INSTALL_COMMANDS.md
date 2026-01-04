# Quick Installation Commands

Copy and paste these commands to install dependencies properly.

## Standard Installation (Recommended)

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python3.10 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate
# On Windows: venv\Scripts\activate

# 4. Upgrade pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# 5. Install all dependencies (including AG2 and asyncpg)
pip install -e .

# 6. Install development tools (tests)
pip install -e ".[dev]"
```

**Done!** You now have all dependencies including AG2 and asyncpg.

---

## Verify Installation

```bash
# Test all imports
python3 -c "
import fastapi
import langgraph
import ag2
import asyncpg
print('✅ All core dependencies installed!')
print(f'   AG2 version: {ag2.__version__}')
print(f'   asyncpg version: {asyncpg.__version__}')
"

# Test debate modules
python3 -c "
from debate.service import AG2DebateService
from debate.persistence import PostgresDebateStorage
from debate.orchestrator import DebateOrchestrator
print('✅ All debate modules loaded successfully!')
"
```

---

## Update Existing Installation

If you already have the project installed and need to update:

```bash
cd backend
source venv/bin/activate

# Update all packages
pip install -e . --upgrade

# Verify AG2 is installed
python3 -c "import ag2; print(f'AG2: {ag2.__version__}')"
python3 -c "import asyncpg; print(f'asyncpg: {asyncpg.__version__}')"
```

---

## Docker Installation

```bash
# Build Docker image with all dependencies
docker build -t multi-agent-chat .

# Run with environment variables
docker run -e DEBATE_ENGINE=ag2 -e OPENAI_API_KEY=your_key multi-agent-chat

# Or use Docker Compose
docker-compose up --build
```

---

## Minimal Installation (LangGraph Only, No AG2)

If you don't want AG2:

```bash
cd backend

# Edit pyproject.toml and remove this line:
# "ag2>=0.3.0",

# Then install
python3.10 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## Development Setup

```bash
cd backend
python3.10 -m venv venv
source venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -e .
pip install -e ".[dev]"

# Run tests
pytest tests/test_ag2_debate.py -v
pytest tests/test_feature_flag.py -v
```

---

## Troubleshooting Installation

### If asyncpg fails to install:

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql-client libpq-dev
pip install asyncpg>=0.29.0
```

**macOS:**
```bash
brew install postgresql
pip install asyncpg>=0.29.0
```

**Windows:**
```bash
# Pre-built wheels usually work
pip install asyncpg>=0.29.0
```

### If AG2 fails to import:

```bash
# Reinstall with force
pip install --no-cache-dir -e . --force-reinstall

# Verify
python3 -c "import ag2; print(ag2.__version__)"
```

### If virtual environment issues:

```bash
# Use specific Python version
python3.10 -m venv venv --upgrade

# Or recreate
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## Environment Setup

```bash
cd backend

# Copy environment template (if exists)
cp .env.example .env

# Or create new .env with required variables:
cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key_here
PG_CONN_STR=postgresql://user:password@localhost:5432/debate_db
TAVILY_API_KEY=your_tavily_api_key_here
DEBATE_ENGINE=ag2
EOF

# Verify .env is loaded
python3 -c "from config import get_openai_api_key; print('✓ Config loaded')"
```

---

## Running the Server

```bash
cd backend
source venv/bin/activate

# Start server
python3 main.py

# You should see:
# ================================================================================
# 🔵 DEBATE ENGINE: AG2 (New Backend)
# or
# 🟢 DEBATE ENGINE: LangGraph (Legacy Backend)
# ================================================================================
```

---

## Testing Installation

```bash
cd backend
source venv/bin/activate

# Quick test
python3 -c "
print('Testing imports...')
import fastapi; print('✓ FastAPI')
import langgraph; print('✓ LangGraph')
import ag2; print('✓ AG2')
import asyncpg; print('✓ asyncpg')
from debate.service import AG2DebateService; print('✓ AG2DebateService')
print('✅ All imports successful!')
"

# Run full test suite
pytest tests/test_ag2_debate.py tests/test_feature_flag.py -v
```

---

## Dependency Versions

Current versions in pyproject.toml:

```
Core Framework:
- fastapi>=0.111
- uvicorn[standard]>=0.30

LLM Providers:
- langchain-openai>=0.1.7
- langchain-google-genai>=1.0.4
- langchain-anthropic>=0.1.15
- langchain-community>=0.3.0
- langchain-tavily>=0.2.0

Orchestration:
- langgraph>=0.2.39
- langgraph-checkpoint-postgres>=0.1.0
- ag2>=0.3.0

Database:
- psycopg[binary]>=3.1
- asyncpg>=0.29.0

Utilities:
- python-dotenv>=1.0
- httpx>=0.27
- tavily-python>=0.3.0

Development (optional):
- pytest>=8.2
- pytest-asyncio>=0.23
```

---

## One-Line Installation

If you prefer a single command (after navigating to backend):

```bash
python3.10 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -e . && pip install -e ".[dev]" && echo "✅ Installation complete!"
```

---

## Next Steps

1. **Verify**: Run `python3 -c "import ag2; import asyncpg; print('OK')"`
2. **Configure**: Set environment variables in `.env`
3. **Start**: Run `python3 main.py`
4. **Test**: Make a request to the API
5. **Check Logs**: Look for 🔵 or 🟢 in startup output

For detailed information, see:
- `INSTALLATION_GUIDE.md` - Complete guide with troubleshooting
- `LOGGING_GUIDE.md` - Understanding log output
- `QUICK_ENGINE_CHECK.md` - Visual reference for engine identification
