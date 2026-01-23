# Multi-stage build for AI Multi-Agent Discussion Panel
# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build frontend for production
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/pyproject.toml ./
COPY backend/*.py ./
COPY backend/auth/ ./auth/
COPY backend/routers/ ./routers/
COPY backend/debate/ ./debate/
COPY backend/migrations/ ./migrations/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy built frontend from frontend-builder stage
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Expose port (Cloud Run uses PORT env var)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Run the application (uses PORT env var for Cloud Run compatibility)
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
