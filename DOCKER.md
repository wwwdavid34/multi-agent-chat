# Docker Deployment Guide

This guide explains how to run the AI Multi-Agent Discussion Panel using Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose V2+
- At least one LLM provider API key (OpenAI required, others optional)

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.docker.example .env.docker
   ```

2. **Edit `.env.docker` and set your API keys:**
   ```bash
   # Required
   OPENAI_API_KEY=sk-your-actual-key-here

   # Optional: Add other provider keys as needed
   GEMINI_API_KEY=your-gemini-key
   CLAUDE_API_KEY=your-claude-key
   ```

3. **Set a secure database password:**
   ```bash
   POSTGRES_PASSWORD=your-secure-password-here
   ```

4. **Build and start the services:**
   ```bash
   docker-compose --env-file .env.docker up --build
   ```

5. **Access the application:**
   - Open your browser to: http://localhost:8000
   - The FastAPI backend serves the React frontend automatically
   - API docs available at: http://localhost:8000/docs

## Services

The Docker Compose setup includes:

### Application (`app`)
- FastAPI backend + React frontend (built with Vite)
- Exposed on port 8000 (configurable via `APP_PORT`)
- Automatically connects to PostgreSQL for conversation persistence

### PostgreSQL (`postgres`)
- Database for LangGraph checkpointing
- Exposed on port 5432 (configurable via `POSTGRES_PORT`)
- Data persisted in Docker volume `postgres_data`

## Configuration

### Environment Variables

Edit `.env.docker` to configure:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_DB` | No | `multi_agent_panel` | Database name |
| `POSTGRES_USER` | No | `panel_user` | Database username |
| `POSTGRES_PASSWORD` | Yes | `changeme` | Database password (change this!) |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port on host |
| `APP_PORT` | No | `8000` | Application port on host |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `GEMINI_API_KEY` | No | - | Google Gemini API key |
| `CLAUDE_API_KEY` | No | - | Anthropic Claude API key |
| `GROK_API_KEY` | No | - | xAI Grok API key |
| `USE_IN_MEMORY_CHECKPOINTER` | No | `0` | Set to `1` to disable PostgreSQL |

### Special Characters in Passwords

The application automatically URL-encodes special characters in the PostgreSQL password, so you can use special characters like `@`, `#`, `$`, etc. without manual encoding.

### API Key Prefilling

When you configure API keys in `.env.docker`, they will be automatically prefilled in the web interface settings panel. This provides a better user experience by:

- Automatically loading keys from environment variables on first use
- Allowing easy verification of which keys are configured
- Storing keys in browser localStorage after first load
- User-entered keys take precedence over environment keys

**How it works:**
1. Set API keys in `.env.docker` (e.g., `OPENAI_API_KEY=sk-...`)
2. Start the application with Docker Compose
3. Open the web interface and click "Settings"
4. API keys will be automatically populated from environment variables
5. You can toggle visibility and copy keys using the eye and copy buttons

**Note:** Keys are only sent from the backend to frontend on initial page load. User modifications in the UI are stored in browser localStorage and won't be overwritten by environment variables.

## Common Commands

### Start services in background
```bash
docker-compose --env-file .env.docker up -d
```

### View logs
```bash
docker-compose logs -f app
docker-compose logs -f postgres
```

### Stop services
```bash
docker-compose down
```

### Stop and remove volumes (deletes all data)
```bash
docker-compose down -v
```

### Rebuild after code changes
```bash
docker-compose --env-file .env.docker up --build
```

## Troubleshooting

### Frontend not loading
- Check that the build completed successfully: `docker-compose logs app | grep frontend`
- Verify the frontend dist directory exists in the container:
  ```bash
  docker-compose exec app ls -la /app/frontend/dist
  ```

### Database connection errors
- Ensure PostgreSQL is healthy: `docker-compose ps`
- Check the connection string encoding: `docker-compose logs app | grep "Falling back"`
- Verify password doesn't have issues: Update `POSTGRES_PASSWORD` in `.env.docker`

### Port already in use
- Change `APP_PORT` or `POSTGRES_PORT` in `.env.docker`
- Or stop the conflicting service

### API keys not working
- Ensure no quotes around keys in `.env.docker`
- Check for extra whitespace
- Verify keys are valid by testing with the provider's API

## Development

For local development without Docker, see the main [README.md](README.md).

### Using in-memory checkpointer
For testing without PostgreSQL persistence:

```bash
# In .env.docker
USE_IN_MEMORY_CHECKPOINTER=1
```

Then you can comment out or remove the `postgres` service from `docker-compose.yml`.

## Production Deployment

For production use:

1. **Security:**
   - Use strong, random passwords for `POSTGRES_PASSWORD`
   - Store `.env.docker` securely (add to `.gitignore`)
   - Consider using Docker secrets instead of environment variables
   - Update CORS settings in `main.py` to restrict origins

2. **Scaling:**
   - Add nginx as a reverse proxy
   - Use managed PostgreSQL (AWS RDS, GCP Cloud SQL, etc.)
   - Consider horizontal scaling with load balancing

3. **Monitoring:**
   - Add health check endpoints
   - Set up logging aggregation
   - Monitor database connections and performance

## Data Persistence

Conversation history is stored in the `postgres_data` Docker volume. To backup:

```bash
docker-compose exec postgres pg_dump -U panel_user multi_agent_panel > backup.sql
```

To restore:

```bash
docker-compose exec -T postgres psql -U panel_user multi_agent_panel < backup.sql
```
