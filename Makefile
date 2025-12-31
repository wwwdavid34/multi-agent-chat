.PHONY: help start start-backend start-frontend dev install install-backend install-frontend test clean

# Default conda environment
CONDA_ENV = magent

help:
	@echo "Multi-Agent Chat - Available commands:"
	@echo ""
	@echo "  make start          - Start both backend and frontend in parallel"
	@echo "  make dev            - Alias for 'make start'"
	@echo "  make start-backend  - Start only the backend server"
	@echo "  make start-frontend - Start only the frontend dev server"
	@echo ""
	@echo "  make install        - Install all dependencies (backend + frontend)"
	@echo "  make install-backend - Install backend dependencies"
	@echo "  make install-frontend - Install frontend dependencies"
	@echo ""
	@echo "  make test           - Run backend tests"
	@echo "  make test-watch     - Run backend tests in watch mode"
	@echo ""
	@echo "  make clean          - Clean build artifacts and caches"
	@echo ""
	@echo "Note: Ensure conda environment '$(CONDA_ENV)' is available"

# Start both backend and frontend in parallel
start:
	@echo "Starting backend and frontend..."
	@trap 'kill 0' INT; \
	(cd backend && conda run -n $(CONDA_ENV) uvicorn main:app --reload --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

# Alias for start
dev: start

# Start only backend
start-backend:
	@echo "Starting backend on http://localhost:8000..."
	cd backend && conda run -n $(CONDA_ENV) uvicorn main:app --reload --port 8000

# Start only frontend
start-frontend:
	@echo "Starting frontend on http://localhost:5173..."
	cd frontend && npm run dev

# Install all dependencies
install: install-backend install-frontend
	@echo "All dependencies installed!"

# Install backend dependencies
install-backend:
	@echo "Installing backend dependencies..."
	cd backend && conda run -n $(CONDA_ENV) pip install -e '.[dev]'

# Install frontend dependencies
install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Run backend tests
test:
	@echo "Running backend tests..."
	cd backend && conda run -n $(CONDA_ENV) pytest -v

# Run backend tests in watch mode
test-watch:
	@echo "Running backend tests in watch mode..."
	cd backend && conda run -n $(CONDA_ENV) pytest -v --looponfail

# Clean build artifacts and caches
clean:
	@echo "Cleaning build artifacts..."
	rm -rf backend/__pycache__ backend/.pytest_cache backend/**/__pycache__
	rm -rf frontend/node_modules/.vite frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete!"
