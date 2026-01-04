# Quick Engine Check: Visual Reference

## What You'll See at Startup

Copy the startup output and paste it here to identify which engine is running:

### ✅ AG2 Backend is ENABLED

Look for this pattern in your startup logs:

```
================================================================================
🔵 DEBATE ENGINE: AG2 (New Backend)
================================================================================
✓ AG2 backend is ENABLED
✓ Using feature-flag based routing
✓ Lazy initialization on first request
================================================================================
```

**Confirmed**: AG2 is active (blue circle 🔵)

---

### ✅ LangGraph Backend is ACTIVE (Default)

Look for this pattern in your startup logs:

```
================================================================================
🟢 DEBATE ENGINE: LangGraph (Legacy Backend)
================================================================================
✓ LangGraph backend is ACTIVE (default)
✓ Storage mode: checkpointer
================================================================================
```

**Confirmed**: LangGraph is active (green circle 🟢)

---

## What You'll See During a Debate

### When Using AG2

```
================================================================================
🔵 [DEBATE] Using AG2 backend for thread: abc123def456
   Question: What is the future of AI?
   Mode: debate | Rounds: 3
================================================================================
```

**Pattern**: 🔵 = AG2 is handling this request

### When Using LangGraph

```
================================================================================
🟢 [DEBATE] Using LangGraph backend for thread: abc123def456
   Question: What is the future of AI?
   Mode: debate | Rounds: 3
================================================================================
```

**Pattern**: 🟢 = LangGraph is handling this request

---

## Quick Grep Commands

### Check which engine is active

```bash
# See startup engine info
grep "DEBATE ENGINE:" /var/log/application.log

# Expected output (one of these):
# 🔵 DEBATE ENGINE: AG2 (New Backend)
# 🟢 DEBATE ENGINE: LangGraph (Legacy Backend)
```

### Count AG2 vs LangGraph requests

```bash
# Count AG2 debates
grep -c "🔵 \[DEBATE\]" /var/log/application.log

# Count LangGraph debates
grep -c "🟢 \[DEBATE\]" /var/log/application.log
```

### See all events for a specific thread

```bash
# Show all logs for thread abc123def456
grep "abc123def456" /var/log/application.log
```

### Find errors

```bash
# Show all errors
grep "🟥" /var/log/application.log
```

---

## Color/Emoji Quick Reference

| Symbol | Meaning | Backend |
|--------|---------|---------|
| 🔵 | AG2 action/event | AG2 (New) |
| 🟢 | LangGraph action/event | LangGraph (Legacy) |
| 🟦 | AG2 initialization | AG2 (Service init) |
| 🟥 | Error | Both |
| ✓ | Success | Both |

---

## Common Log Patterns

### AG2 Service Starting Up

```
🟦 [AG2-SERVICE] Initialized with PostgreSQL storage
🟦 [AG2-SERVICE] AG2 debate service ready
```

→ **Confirms**: AG2 service initialized successfully

### AG2 Debate Starting

```
🔵 [AG2] Initializing AG2 debate service for thread: xyz
🔵 [AG2] Service initialized, starting event stream for thread: xyz
```

→ **Confirms**: AG2 is processing this request

### AG2 Events Flowing

```
🔵 [AG2-EVENT] Status: Panel is discussing...
🔵 [AG2-EVENT] Claude responded (25 words)
🔵 [AG2-EVENT] GPT-4 responded (32 words)
🔵 [AG2-EVENT] Debate round 1 complete
🔵 [AG2-EVENT] Stream complete (12 events total)
```

→ **Confirms**: AG2 is streaming events successfully

### LangGraph Events

```
🟢 [LANGGRAPH] Initializing LangGraph service for thread: xyz
🟢 [LANGGRAPH] Event stream started for thread: xyz
```

→ **Confirms**: LangGraph is processing this request

---

## How to Switch Engines

### Enable AG2 (Blue 🔵)

```bash
export DEBATE_ENGINE=ag2
python3 main.py
```

Then restart and check logs for: `🔵 DEBATE ENGINE: AG2`

### Use LangGraph (Green 🟢)

```bash
export DEBATE_ENGINE=langgraph
python3 main.py
# or just don't set the variable (defaults to langgraph)
```

Then restart and check logs for: `🟢 DEBATE ENGINE: LangGraph`

---

## Testing Your Setup

### 1. Start the backend

```bash
python3 main.py
```

### 2. Watch for startup message

```
🔵 DEBATE ENGINE: AG2 (New Backend)
   or
🟢 DEBATE ENGINE: LangGraph (Legacy Backend)
```

### 3. Make a test request

```bash
curl -X POST http://localhost:8000/ask-stream \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "test-123",
    "question": "Hello AI",
    "panelists": []
  }'
```

### 4. Watch the logs

You should see:
- `🔵 [DEBATE]` or `🟢 [DEBATE]` message
- Engine initialization logs
- Event streaming logs
- Final completion message

---

## Troubleshooting

### I don't see any startup message

**Problem**: Logs might be elsewhere or logging is disabled

**Solution**:
```bash
# Run with explicit logging to console
python3 main.py 2>&1 | tee console.log
```

Then look at `console.log` for the startup message.

### I see 🟢 but want to use AG2 (🔵)

**Problem**: LangGraph is active (default)

**Solution**:
```bash
# Set environment variable
export DEBATE_ENGINE=ag2

# Restart the backend
python3 main.py

# Look for startup logs with 🔵
```

### I see 🔵 but want to use LangGraph (🟢)

**Problem**: AG2 is enabled

**Solution**:
```bash
# Unset the variable or explicitly set to langgraph
unset DEBATE_ENGINE
# or
export DEBATE_ENGINE=langgraph

# Restart the backend
python3 main.py

# Look for startup logs with 🟢
```

### I see 🟥 errors

**Problem**: Error occurred during debate

**Solution**: Look at the full error message:
```bash
# See error details
grep "🟥" /var/log/application.log

# Check AG2 service initialization
grep "🟦 \[AG2-SERVICE\]" /var/log/application.log
```

---

## Docker/Kubernetes Quick Check

### Check logs in Docker

```bash
# See all logs
docker logs container-name

# See logs with AG2 marker
docker logs container-name | grep "🔵"

# See logs with LangGraph marker
docker logs container-name | grep "🟢"

# See startup message only
docker logs container-name | grep "DEBATE ENGINE"
```

### Check logs in Kubernetes

```bash
# See logs
kubectl logs pod-name

# See AG2 logs
kubectl logs pod-name | grep "🔵"

# Watch logs in real-time
kubectl logs -f pod-name | grep "DEBATE\|ENGINE"
```

---

## One-Line Summary

**To know which engine is running:**

```bash
# Look for the startup message - it clearly shows which engine is active
grep "DEBATE ENGINE" /var/log/application.log

# Blue 🔵 = AG2 (New)
# Green 🟢 = LangGraph (Legacy/Default)
```

That's it! The logs tell you exactly which engine is running.
