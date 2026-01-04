# LLM Model Names Guide

## Current Error Diagnosis

Your debate is failing because panelist models are invalid:

```
❌ gemini-2.5-flash   → Does NOT exist
❌ claude-3-5-haiku-20241022 → Model exists but API key may be missing
```

## Valid Model Names by Provider

### OpenAI (✓ Recommended for AG2)

Most reliable and consistent with AG2.

```json
{
  "panelists": [
    {
      "id": "gpt4",
      "name": "GPT-4 Expert",
      "provider": "openai",
      "model": "gpt-4o"
    }
  ],
  "provider_keys": {
    "openai": "sk-proj-..."
  }
}
```

**Available OpenAI Models:**

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| `gpt-4o` | Medium | Higher | Best all-around, most capable |
| `gpt-4o-mini` | Fast | Lower | Quick debates, cost-effective |
| `gpt-4-turbo` | Medium | Higher | Complex reasoning |
| `gpt-3.5-turbo` | Fast | Low | Basic discussions |

**Minimum Recommended:** `gpt-4o-mini` (fast + capable)

---

### Google Gemini (⚠️ Fix Model Name)

**Current Issue:** `gemini-2.5-flash` doesn't exist

```json
{
  "panelists": [
    {
      "id": "gemini",
      "name": "Gemini Analyst",
      "provider": "google",
      "model": "gemini-2.0-flash"  // ✓ Correct
    }
  ],
  "provider_keys": {
    "google": "AIza..."
  }
}
```

**Available Google Gemini Models:**

| Model | Speed | Status | Notes |
|-------|-------|--------|-------|
| `gemini-2.0-flash` | Fast | Current | Latest, recommended |
| `gemini-1.5-flash` | Fast | Active | Still works |
| `gemini-1.5-pro` | Medium | Active | More capable |
| `gemini-pro` | Medium | Legacy | Older version |

**What to Change:**
```
OLD: "model": "gemini-2.5-flash"
NEW: "model": "gemini-2.0-flash"
```

---

### Anthropic Claude (⚠️ Check API Key)

**Current Issue:** Model name is correct but `CLAUDE_API_KEY` might not be set

```json
{
  "panelists": [
    {
      "id": "claude",
      "name": "Claude Analyst",
      "provider": "anthropic",
      "model": "claude-3-5-haiku-20241022"  // ✓ Correct
    }
  ],
  "provider_keys": {
    "anthropic": "sk-ant-..."
  }
}
```

**Available Claude Models:**

| Model | Speed | Capability | Cost |
|-------|-------|-----------|------|
| `claude-3-5-sonnet-20241022` | Medium | Highest | Higher |
| `claude-3-5-haiku-20241022` | Fast | Good | Lower |
| `claude-3-opus-20240229` | Slow | Highest | Highest |

**Setup in .env:**

```bash
# Method 1: CLAUDE_API_KEY
CLAUDE_API_KEY=sk-ant-v1-xxxxx

# Method 2: ANTHROPIC_API_KEY
ANTHROPIC_API_KEY=sk-ant-v1-xxxxx

# Use ONE of the above (not both)
```

---

## Recommended Panel Configurations

### Simple: Single Provider (Fastest)

```json
{
  "panelists": [
    {
      "id": "gpt1",
      "name": "GPT-4 Expert",
      "provider": "openai",
      "model": "gpt-4o-mini"
    },
    {
      "id": "gpt2",
      "name": "GPT-4 Analyst",
      "provider": "openai",
      "model": "gpt-4o"
    }
  ],
  "provider_keys": {
    "openai": "sk-proj-..."
  }
}
```

**Pros:** Fast, reliable, one API key
**Cons:** Only one perspective

### Balanced: Multiple Providers (Recommended)

```json
{
  "panelists": [
    {
      "id": "gpt",
      "name": "GPT-4",
      "provider": "openai",
      "model": "gpt-4o-mini"
    },
    {
      "id": "claude",
      "name": "Claude",
      "provider": "anthropic",
      "model": "claude-3-5-haiku-20241022"
    },
    {
      "id": "gemini",
      "name": "Gemini",
      "provider": "google",
      "model": "gemini-2.0-flash"
    }
  ],
  "provider_keys": {
    "openai": "sk-proj-...",
    "anthropic": "sk-ant-...",
    "google": "AIza..."
  }
}
```

**Pros:** Diverse perspectives, balanced
**Cons:** Requires 3 API keys, slightly slower

### Advanced: Different Models (Specialized)

```json
{
  "panelists": [
    {
      "id": "fast",
      "name": "Quick Thinker",
      "provider": "openai",
      "model": "gpt-4o-mini"
    },
    {
      "id": "deep",
      "name": "Deep Analyst",
      "provider": "openai",
      "model": "gpt-4o"
    },
    {
      "id": "creative",
      "name": "Creative Mind",
      "provider": "google",
      "model": "gemini-2.0-flash"
    }
  ],
  "provider_keys": {
    "openai": "sk-proj-...",
    "google": "AIza..."
  }
}
```

---

## Troubleshooting Model Errors

### Error: "model does not exist"

```
Error code: 404 - The model `gemini-2.5-flash` does not exist
```

**Fix:**
1. Check model name in your request
2. Verify against valid models list above
3. Use correct spelling (models are case-sensitive)

**Common Mistakes:**
- ❌ `gemini-2.5-flash` → ✓ `gemini-2.0-flash`
- ❌ `gpt-4` → ✓ `gpt-4o`
- ❌ `claude-haiku` → ✓ `claude-3-5-haiku-20241022`

### Error: "You do not have access to it"

```
Error code: 404 - you do not have access to it
```

**Fix:**
1. Verify you have API key for that provider
2. Check API key is correct in `provider_keys`
3. Verify API key has access to that specific model
4. Check API key permissions in provider dashboard

### Error: "Authentication failed" (401)

```
Error code: 401 - Unauthorized
```

**Fix:**
1. Verify API key is set correctly
2. Check for typos in the key
3. Regenerate API key if needed
4. Ensure key has proper permissions

### Error: "Rate limit exceeded" (429)

```
Error code: 429 - Too many requests
```

**Fix:**
1. Wait before retrying
2. Use cheaper/faster models (e.g., `gpt-4o-mini`)
3. Reduce number of panelists
4. Check provider's rate limit documentation

---

## How to Get API Keys

### OpenAI

1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Copy and add to `.env`:
   ```bash
   OPENAI_API_KEY=sk-proj-xxxxx
   ```

### Google Gemini

1. Go to https://ai.google.dev/tutorials/setup
2. Click "Get API Key"
3. Create or select project
4. Copy and add to `.env`:
   ```bash
   GEMINI_API_KEY=AIza...
   ```

### Anthropic Claude

1. Go to https://console.anthropic.com/
2. Create API key
3. Copy and add to `.env`:
   ```bash
   CLAUDE_API_KEY=sk-ant-xxxxx
   ```
   OR
   ```bash
   ANTHROPIC_API_KEY=sk-ant-xxxxx
   ```

---

## Testing Your Setup

### Test Single Panelist

```bash
curl -X POST http://localhost:8000/ask-stream \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "test-gpt",
    "question": "What is AI?",
    "panelists": [
      {
        "id": "test",
        "name": "Test Agent",
        "provider": "openai",
        "model": "gpt-4o-mini"
      }
    ],
    "provider_keys": {
      "openai": "YOUR_OPENAI_API_KEY"
    }
  }'
```

**Expected output:**
```
🔵 [AG2-EVENT] Test Agent responded (XX words)
🔵 [AG2-EVENT] Debate round 1 complete
```

### Test Multiple Panelists

```bash
curl -X POST http://localhost:8000/ask-stream \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "test-multi",
    "question": "What is AI?",
    "panelists": [
      {"id": "gpt", "name": "GPT", "provider": "openai", "model": "gpt-4o-mini"},
      {"id": "gemini", "name": "Gemini", "provider": "google", "model": "gemini-2.0-flash"}
    ],
    "provider_keys": {
      "openai": "YOUR_OPENAI_API_KEY",
      "google": "YOUR_GEMINI_API_KEY"
    }
  }'
```

---

## Quick Reference Card

```
OPENAI:
✓ gpt-4o
✓ gpt-4o-mini ← Recommended
✓ gpt-4-turbo
✓ gpt-3.5-turbo

GEMINI:
✓ gemini-2.0-flash ← Use this (NOT gemini-2.5-flash)
✓ gemini-1.5-flash
✓ gemini-1.5-pro

CLAUDE:
✓ claude-3-5-sonnet-20241022
✓ claude-3-5-haiku-20241022 ← Recommended
✓ claude-3-opus-20240229

ERROR FIXES:
- Model not found? → Check model name spelling
- No access? → Check API key and permissions
- 401? → Verify API key is correct
- 429? → Wait and try again
```

---

## Summary

**To fix your current issue:**

1. **Change Gemini model:**
   ```
   gemini-2.5-flash → gemini-2.0-flash
   ```

2. **Add Claude API key to .env:**
   ```bash
   CLAUDE_API_KEY=sk-ant-xxxxx
   ```

3. **Or use only OpenAI (simplest):**
   ```json
   "panelists": [
     {"id": "gpt", "name": "GPT-4", "provider": "openai", "model": "gpt-4o-mini"}
   ]
   ```

4. **Restart server and test:**
   ```bash
   python3 main.py
   ```

You should then see panelists responding with AG2 backend! 🔵
