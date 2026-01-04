# Debate Engine Logging Guide

## Quick Check: How to Know Which Engine is Running

### 1. **At Startup (Console Output)**

When the backend starts, you'll see clear indicators:

#### If AG2 is Enabled:
```
================================================================================
🔵 DEBATE ENGINE: AG2 (New Backend)
================================================================================
✓ AG2 backend is ENABLED
✓ Using feature-flag based routing
✓ Lazy initialization on first request
================================================================================
```

#### If LangGraph is Active (Default):
```
================================================================================
🟢 DEBATE ENGINE: LangGraph (Legacy Backend)
================================================================================
✓ LangGraph backend is ACTIVE (default)
✓ Storage mode: checkpointer
================================================================================
```

### 2. **Per-Request (When a Debate Starts)**

Each debate request shows which engine is handling it:

#### AG2 Backend:
```
================================================================================
🔵 [DEBATE] Using AG2 backend for thread: abc123def456
   Question: What is the future of artificial intelligence?
   Mode: debate | Rounds: 3
================================================================================
🔵 [AG2] Initializing AG2 debate service for thread: abc123def456
🔵 [AG2] Service initialized, starting event stream for thread: abc123def456
🔵 [AG2-SERVICE] Initialized with PostgreSQL storage
🔵 [AG2-SERVICE] AG2 debate service ready
```

#### LangGraph Backend:
```
================================================================================
🟢 [DEBATE] Using LangGraph backend for thread: abc123def456
   Question: What is the future of artificial intelligence?
   Mode: debate | Rounds: 3
================================================================================
🟢 [LANGGRAPH] Initializing LangGraph service for thread: abc123def456
🟢 [LANGGRAPH] Event stream started for thread: abc123def456
```

## Log Markers and Meanings

### Visual Indicators

| Marker | Meaning | Backend |
|--------|---------|---------|
| 🔵 | AG2 backend event/action | AG2 |
| 🟢 | LangGraph backend event/action | LangGraph |
| 🟦 | AG2 service initialization | AG2 |
| 🟥 | Error condition | Both |
| ✓ | Success/confirmation | Both |

### Log Prefixes

| Prefix | Context |
|--------|---------|
| `[DEBATE]` | Debate engine selection and request routing |
| `[AG2]` | AG2 service initialization and operations |
| `[AG2-SERVICE]` | AG2 service storage configuration |
| `[AG2-EVENT]` | AG2 event streaming (status, responses, rounds, results) |
| `[LANGGRAPH]` | LangGraph backend operations |
| `[EVENT_STREAM]` | LangGraph event streaming |

## Detailed Event Logs (AG2 Backend)

When running with AG2, you'll see event-level logging:

### During Debate Execution

```
🔵 [AG2-EVENT] Status: Panel is discussing...
🔵 [AG2-EVENT] Claude responded (25 words)
🔵 [AG2-EVENT] GPT-4 responded (32 words)
🔵 [AG2-EVENT] Debate round 1 complete
🔵 [AG2-EVENT] Status: Moderating the discussion...
🔵 [AG2-EVENT] Debate complete - Final result received
🔵 [AG2-EVENT] Stream complete (15 events total)
```

### Interpreting AG2 Events

```
[AG2-EVENT] Type of event and details
├── Status updates: "Panel is discussing...", "Searching the web...", etc.
├── Panelist responses: "Agent-name responded (XX words)"
├── Debate rounds: "Debate round N complete"
├── Results: "Debate complete - Final result received"
├── Errors: "Error: [error message]"
└── Completion: "Stream complete (N events total)"
```

## Log Levels Configuration

### Current Configuration (INFO level shown by default)

The backend uses Python's standard logging with these levels:

| Level | Example Events | Visibility |
|-------|---|-----------|
| **DEBUG** | Individual panelist responses, status updates | Detailed debugging |
| **INFO** | Debate start, rounds, results, service init | Normal operation (default) |
| **WARNING** | Timeouts, config issues | Potential problems |
| **ERROR** | Service failures, exceptions | Serious issues |

### To See More Detailed Logs

Set logging level to DEBUG:

```bash
# In your environment or systemd service file
export LOG_LEVEL=DEBUG

# Or in Python before starting
python3 -c "import logging; logging.basicConfig(level=logging.DEBUG)" && python3 main.py
```

### To See Less Verbose Output

Set logging level to WARNING:

```bash
export LOG_LEVEL=WARNING
```

## Complete Log Trace Example

### Starting the Server

```
INFO - Application startup complete
INFO - ================================================================================
INFO - 🔵 DEBATE ENGINE: AG2 (New Backend)
INFO - ================================================================================
INFO - ✓ AG2 backend is ENABLED
INFO - ✓ Using feature-flag based routing
INFO - ✓ Lazy initialization on first request
INFO - ================================================================================
```

### Making a Request

```
INFO - ================================================================================
INFO - 🔵 [DEBATE] Using AG2 backend for thread: test-thread-001
INFO -    Question: What is machine learning?
INFO -    Mode: debate | Rounds: 3
INFO - ================================================================================
INFO - 🔵 [AG2] Initializing AG2 debate service for thread: test-thread-001
INFO - 🔵 [AG2] Service initialized, starting event stream for thread: test-thread-001
INFO - 🟦 [AG2-SERVICE] Initialized with PostgreSQL storage
INFO - 🟦 [AG2-SERVICE] AG2 debate service ready
```

### During Debate

```
DEBUG - 🔵 [AG2-EVENT] Status: Panel is discussing...
DEBUG - 🔵 [AG2-EVENT] Claude responded (28 words)
DEBUG - 🔵 [AG2-EVENT] GPT-4 responded (35 words)
DEBUG - 🔵 [AG2-EVENT] Gemini responded (42 words)
INFO - 🔵 [AG2-EVENT] Debate round 1 complete
INFO - 🔵 [AG2-EVENT] Debate complete - Final result received
INFO - 🔵 [AG2-EVENT] Stream complete (12 events total)
```

## Environment Variables for Debugging

### Enable AG2 Backend

```bash
export DEBATE_ENGINE=ag2
python3 main.py
```

Result: All debates will use AG2 backend with detailed 🔵 logs.

### Use LangGraph Backend (Default)

```bash
unset DEBATE_ENGINE
# or
export DEBATE_ENGINE=langgraph
python3 main.py
```

Result: All debates will use LangGraph backend with 🟢 logs.

### Use In-Memory Storage (Testing)

```bash
export USE_IN_MEMORY_CHECKPOINTER=1
export DEBATE_ENGINE=ag2
python3 main.py
```

Result: AG2 with in-memory storage, useful for testing without database.

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
export DEBATE_ENGINE=ag2
python3 main.py
```

Result: Very detailed logs including individual event logging.

## Docker / Kubernetes Deployment

### Docker Run

```bash
docker run -e DEBATE_ENGINE=ag2 -e LOG_LEVEL=INFO your-image
```

### Docker Compose

```yaml
services:
  api:
    environment:
      DEBATE_ENGINE: ag2
      LOG_LEVEL: INFO
```

### Kubernetes

```yaml
env:
- name: DEBATE_ENGINE
  value: "ag2"
- name: LOG_LEVEL
  value: "INFO"
```

## Troubleshooting with Logs

### Issue: Can't tell which engine is running

**Solution**: Look for startup logs:
- 🔵 = AG2 is enabled
- 🟢 = LangGraph is active

```bash
tail -50 /path/to/logs | grep "DEBATE ENGINE"
```

### Issue: AG2 backend not initializing

**Solution**: Look for 🔵 [AG2] error logs:

```bash
tail -100 /path/to/logs | grep "🔵\|🟥"
```

Common issues:
- `🟥 [AG2-SERVICE] Failed to initialize` - Check PostgreSQL connection
- `🟥 [AG2] Error in AG2 debate stream` - Check AG2 dependencies

### Issue: Slow event streaming

**Solution**: Check for timeout logs:

```bash
tail -200 /path/to/logs | grep "timeout\|ERROR"
```

### Issue: Storage errors

**Solution**: Check storage initialization logs:

```bash
tail -50 /path/to/logs | grep "AG2-SERVICE.*storage\|database\|PostgreSQL"
```

Expected:
- ✓ `🟦 [AG2-SERVICE] Initialized with PostgreSQL storage`
- ✓ `🟦 [AG2-SERVICE] Initialized with IN-MEMORY storage`

## Log File Locations

### Development

```bash
# Console output (if running directly)
python3 main.py

# Check logs in Docker
docker logs container-name
```

### Production

Typically in:
```
/var/log/application.log
/var/log/debates.log
journalctl -u your-service
```

### Configuration Location

Update logging configuration in your Python logging setup:

```python
# In main.py or logging config file
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/debates.log'),
        logging.StreamHandler()  # Console
    ]
)
```

## Monitoring Dashboard Quick Checks

### To verify AG2 is being used:

```bash
# Count AG2 events
grep -c "🔵 \[DEBATE\]" /var/log/debates.log

# Count LangGraph events
grep -c "🟢 \[DEBATE\]" /var/log/debates.log
```

### To track success rate:

```bash
# Successful completions
grep -c "Stream complete" /var/log/debates.log

# Error count
grep -c "🟥 \[AG2-EVENT\] Error" /var/log/debates.log
```

### To find slow debates:

```bash
# Look for timeouts
grep "timeout\|Timeout" /var/log/debates.log

# Check debate duration in logs
grep "🔵 \[DEBATE\]" /var/log/debates.log  # Start times
grep "Stream complete" /var/log/debates.log  # End times
```

## Summary Checklist

- [x] Can see startup engine selection (🔵 AG2 or 🟢 LangGraph)
- [x] Can see which engine handles each request
- [x] Can identify AG2 events by 🔵 markers
- [x] Can identify errors by 🟥 markers
- [x] Can set environment variables to switch engines
- [x] Can enable DEBUG logging for detailed traces
- [x] Know where to look for logs in your deployment

For questions or issues, check the logs first - they'll tell you exactly what's happening!
