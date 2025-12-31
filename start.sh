#!/bin/bash

# Multi-Agent Chat startup script
# Usage: ./start.sh [backend|frontend|both|help]

CONDA_ENV="magent"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${BLUE}Multi-Agent Chat - Startup Script${NC}"
    echo ""
    echo "Usage: ./start.sh [command]"
    echo ""
    echo "Commands:"
    echo "  both (default) - Start both backend and frontend in parallel"
    echo "  backend        - Start only the backend server"
    echo "  frontend       - Start only the frontend dev server"
    echo "  help           - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./start.sh              # Start everything"
    echo "  ./start.sh backend      # Start only backend"
    echo "  ./start.sh frontend     # Start only frontend"
}

start_backend() {
    echo -e "${GREEN}Starting backend on http://localhost:8000...${NC}"
    cd backend && conda run -n $CONDA_ENV uvicorn main:app --reload --port 8000
}

start_frontend() {
    echo -e "${GREEN}Starting frontend on http://localhost:5173...${NC}"
    cd frontend && npm run dev
}

start_both() {
    echo -e "${GREEN}Starting backend and frontend in parallel...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
    echo ""

    # Start both processes in background
    (cd backend && conda run -n $CONDA_ENV uvicorn main:app --reload --port 8000) &
    BACKEND_PID=$!

    (cd frontend && npm run dev) &
    FRONTEND_PID=$!

    # Trap Ctrl+C and kill both processes
    trap "echo -e '\n${YELLOW}Stopping servers...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

    # Wait for both processes
    wait
}

# Main command handler
case "${1:-both}" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    both|"")
        start_both
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        echo -e "${YELLOW}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
