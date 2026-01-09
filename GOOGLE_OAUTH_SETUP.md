# Google OAuth Authentication - Setup Guide

This guide walks you through setting up Google OAuth authentication for the multi-agent chat application.

## Overview

We're adding:
- Google OAuth login
- User-specific conversation isolation
- Encrypted per-user API key storage
- Thread migration from localStorage

**Estimated setup time:** 30-40 minutes

## Part 1: Google Cloud Console Setup (15-20 minutes)

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" → "New Project"
3. Project name: `multi-agent-chat` (or your choice)
4. Click "Create"
5. Note your Project ID

### Step 2: Enable Required APIs

1. Navigate to **APIs & Services** → **Library**
2. Search for "People API"
3. Click "Enable"

### Step 3: Configure OAuth Consent Screen

1. Navigate to **APIs & Services** → **OAuth consent screen**
2. Select user type:
   - **External**: For any Google account (recommended)
   - **Internal**: Only for Google Workspace users
3. Click "Create"

**Fill in App Information:**
- **App name**: `Multi-Agent Chat Panel`
- **User support email**: Your email address
- **App logo**: Optional (skip for now)
- **Application home page**: `http://localhost:5173` (for development)
- **Authorized domains**: Leave empty for localhost development
- **Developer contact email**: Your email address

4. Click "Save and Continue"

**Scopes:**
1. Click "Add or Remove Scopes"
2. Select these scopes:
   - `openid` (automatically included)
   - `...auth/userinfo.email`
   - `...auth/userinfo.profile`
3. Click "Update" → "Save and Continue"

**Test users (if in Testing mode):**
1. Click "Add Users"
2. Add your Gmail address
3. Add any other Gmail accounts that will test the app (max 100)
4. Click "Save and Continue"
5. Click "Back to Dashboard"

### Step 4: Create OAuth 2.0 Client ID

1. Navigate to **APIs & Services** → **Credentials**
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Web application**
4. Name: `Multi-Agent Chat Web Client`

**Authorized JavaScript origins:**
```
http://localhost:5173
http://localhost:8000
```

**Authorized redirect URIs:**
```
http://localhost:5173
http://localhost:8000
```

5. Click "Create"
6. **IMPORTANT:** Copy your Client ID - you'll need it next
   - Format: `123456789-abc123def456.apps.googleusercontent.com`

### Step 5: Add Production URLs (Optional - for deployment)

When deploying to production:
1. Go back to your OAuth client ID
2. Add production URLs to **Authorized JavaScript origins**:
   ```
   https://chat.yourdomain.com
   https://yourdomain.com
   ```
3. Add to **Authorized redirect URIs**:
   ```
   https://chat.yourdomain.com
   https://yourdomain.com
   ```
4. Click "Save"

## Part 2: Generate Security Keys (5 minutes)

### Step 1: Generate JWT Secret

```bash
# Generate 64-character hex secret for JWT tokens
openssl rand -hex 32
```

Copy the output - you'll add this to `.env` as `JWT_SECRET_KEY`

### Step 2: Generate Encryption Master Key

```bash
# Generate encryption key for API key storage
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

Copy the output - you'll add this to `.env` as `ENCRYPTION_MASTER_KEY`

## Part 3: Configure Environment Variables (5 minutes)

### Backend Environment (.env)

Edit or create `backend/.env`:

```bash
# Existing database connection
PG_CONN_STR=postgresql://user:password@localhost:5432/multi_agent_panel

# Google OAuth (from Step 4 above)
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com

# JWT Secret (from Part 2, Step 1)
JWT_SECRET_KEY=your_64_character_hex_secret_here

# Encryption Master Key (from Part 2, Step 2)
ENCRYPTION_MASTER_KEY=your_base64_encoded_key_here

# CORS (for development)
FRONTEND_URL=http://localhost:5173

# Optional: For production
# FRONTEND_URL=https://chat.yourdomain.com
```

### Frontend Environment (frontend/.env)

Create `frontend/.env`:

```bash
# Google OAuth (same Client ID as backend)
VITE_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com

# API base URL (development)
VITE_API_BASE_URL=http://localhost:8000

# Optional: For production
# VITE_API_BASE_URL=https://yourdomain.com
```

## Part 4: Run Database Migration (2 minutes)

```bash
# From project root
cd /home/david/Documents/projects/multi-agent-chat

# Load environment variables
export $(grep -v '^#' backend/.env | xargs)

# Run migration
psql $PG_CONN_STR < backend/migrations/001_add_auth_tables.sql
```

**Expected output:**
```
CREATE TABLE
CREATE INDEX
...
NOTICE: ✓ users table created
NOTICE: ✓ user_threads table created
NOTICE: ✓ thread_migrations table created
```

**Verify migration:**
```bash
psql $PG_CONN_STR -c "\dt" | grep users
```

Should show:
- `users`
- `user_threads`
- `thread_migrations`

## Part 5: Install Dependencies (3 minutes)

### Backend Dependencies

```bash
cd backend

# Add to pyproject.toml (already done in code)
# Then install:
poetry install
# or
pip install google-auth==2.25.2 PyJWT==2.8.0 cryptography==41.0.7
```

### Frontend Dependencies

```bash
cd frontend

# Install jwt-decode for token parsing
npm install jwt-decode
# or
pnpm add jwt-decode
```

## Part 6: Start the Application (2 minutes)

### Terminal 1: Start Backend

```bash
cd backend
uvicorn main:app --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Terminal 2: Start Frontend

```bash
cd frontend
npm run dev
```

Expected output:
```
VITE ready in XXX ms
➜  Local:   http://localhost:5173/
```

## Part 7: Test Authentication (5 minutes)

### Step 1: Open Application

1. Navigate to `http://localhost:5173`
2. You should see a **"Sign in with Google"** button

### Step 2: Test Login

1. Click "Sign in with Google"
2. Select your Google account
3. Grant permissions (email, profile)
4. You should be redirected back to the app
5. Check browser console (F12) for:
   ```
   User logged in: {id: "...", email: "your@gmail.com", name: "..."}
   ```

### Step 3: Verify Database

```bash
psql $PG_CONN_STR -c "SELECT email, name, created_at FROM users;"
```

Should show your user account.

### Step 4: Test Thread Isolation

1. Create a new conversation thread
2. Log out
3. Log in with a different Google account (must be in test users)
4. Verify you DON'T see the first user's thread

## Troubleshooting

### Error: "redirect_uri_mismatch"

**Cause:** Authorized redirect URIs don't match your app's URL

**Fix:**
1. Go to Google Cloud Console → Credentials
2. Edit your OAuth client ID
3. Add `http://localhost:5173` to **Authorized JavaScript origins**
4. Add `http://localhost:5173` to **Authorized redirect URIs**
5. Save and wait 5 minutes for changes to propagate

### Error: "Access blocked: This app's request is invalid"

**Cause:** OAuth consent screen not configured

**Fix:**
1. Go to Google Cloud Console → OAuth consent screen
2. Complete all required fields
3. Add your email to test users (if in Testing mode)

### Error: "Invalid client"

**Cause:** GOOGLE_CLIENT_ID mismatch or not set

**Fix:**
1. Verify `backend/.env` has correct `GOOGLE_CLIENT_ID`
2. Verify `frontend/.env` has correct `VITE_GOOGLE_CLIENT_ID`
3. Restart both backend and frontend

### Error: "Token verification failed"

**Cause:** Backend can't verify Google token

**Fix:**
1. Ensure `google-auth` is installed: `pip show google-auth`
2. Check backend logs for detailed error
3. Verify internet connection (backend needs to contact Google)

### Database connection error

**Cause:** `PG_CONN_STR` not set or database doesn't exist

**Fix:**
```bash
# Check if database exists
psql -l | grep multi_agent_panel

# If not, create it
createdb multi_agent_panel

# Verify connection
psql $PG_CONN_STR -c "SELECT version();"
```

### Migration already exists error

**Cause:** Migration was already run (this is safe!)

**Fix:**
- Migration is idempotent - you can safely ignore this
- Or verify tables exist: `psql $PG_CONN_STR -c "\dt"`

## Security Checklist

Before deploying to production:

- [ ] OAuth consent screen published (not in Testing mode)
- [ ] Domain verified in Google Search Console
- [ ] Production URLs added to OAuth client
- [ ] `JWT_SECRET_KEY` is random and secure (64+ characters)
- [ ] `ENCRYPTION_MASTER_KEY` is secure and backed up
- [ ] Environment variables NOT committed to git
- [ ] HTTPS enabled on frontend
- [ ] CORS restricted to specific frontend origin
- [ ] Database backups configured

## Next Steps

After authentication is working:

1. **Add API key storage**: Users can store their OpenAI/Anthropic keys
2. **Test thread migration**: Existing localStorage threads should migrate on first login
3. **Add user menu**: Profile dropdown with logout button
4. **Monitor logs**: Check for any authentication errors
5. **Deploy to production**: Follow production security checklist above

## Support

- **Plan file**: `/home/david/.claude/plans/composed-swimming-twilight.md`
- **Migration README**: `backend/migrations/README.md`
- **Google OAuth docs**: https://developers.google.com/identity/protocols/oauth2

## Summary

You've successfully set up:
- ✅ Google Cloud project with OAuth
- ✅ OAuth consent screen configured
- ✅ OAuth client ID created
- ✅ Security keys generated
- ✅ Environment variables configured
- ✅ Database migrated with user tables
- ✅ Application dependencies installed

You're ready to start using Google OAuth authentication!
