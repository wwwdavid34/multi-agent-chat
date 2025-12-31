import os
import sys
from pathlib import Path


# Ensure backend modules (e.g. panel_graph.py) are importable even when running pytest from repo root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Avoid requiring real credentials / services during import-time initialization.
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("USE_IN_MEMORY_CHECKPOINTER", "1")

