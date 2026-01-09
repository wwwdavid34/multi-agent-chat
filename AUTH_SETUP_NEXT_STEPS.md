# Authentication Setup - Next Steps

## ✅ What's Already Done

1. **Database Migration** ✅
   - Users, threads, and migration tables created
   - User ID columns added to existing tables
   - 9 indexes created for performance

2. **Security Keys Generated** ✅
   - JWT Secret: `babd3be9dc59b8f5e40d9b7d8ab2bd97c233e8fa2562ab1bca46da81982ee8c4`
   - Encryption Key: `NYKqMQ9HvQjmM63sFTFmVqHQMbK44gtTfdXotwGTn4s=`
   - Both added to `backend/.env`

3. **Environment Files Configured** ✅
   - `backend/.env` updated with auth variables
   - `frontend/.env` created with placeholders

4. **Code Implementation** ✅
   - Backend authentication service complete
   - Frontend login components ready
   - API endpoints secured

---

## 📋 Remaining Steps (15-20 minutes)

### Step 1: Set Up Google OAuth (15 minutes)

**Go to Google Cloud Console:**
1. Visit https://console.cloud.google.com
2. Create new project (or select existing)
3. Name: `multi-agent-chat`

**Enable API:**
1. Go to **APIs & Services** → **Library**
2. Search for "People API"
3. Click **Enable**

**Configure OAuth Consent Screen:**
1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type
3. Click **Create**
4. Fill in:
   - App name: `Multi-Agent Chat Panel`
   - User support email: (your email)
   - Developer contact email: (your email)
5. Click **Save and Continue**
6. Scopes: Click **Add or Remove Scopes**
   - Select: `openid`, `email`, `profile`
   - Click **Update** → **Save and Continue**
7. Test users: Click **Add Users**
   - Add your Gmail address
   - Click **Save and Continue**
8. Click **Back to Dashboard**

**Create OAuth Client ID:**
1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Name: `Multi-Agent Chat Web Client`
5. **Authorized JavaScript origins:** Add these:
   ```
   http://localhost:5173
   http://localhost:8000
   ```
6. **Authorized redirect URIs:** Add these:
   ```
   http://localhost:5173
   http://localhost:8000
   ```
7. Click **Create**
8. **COPY YOUR CLIENT ID** - it looks like:
   ```
   123456789-abc123def456.apps.googleusercontent.com
   ```

### Step 2: Update Environment Files (2 minutes)

**Update `backend/.env`:**
```bash
# Replace this line:
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com

# With your actual Client ID:
GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
```

**Update `frontend/.env`:**
```bash
# Replace this line:
VITE_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com

# With your actual Client ID (SAME as backend):
VITE_GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
```

### Step 3: Install Dependencies (3 minutes)

**Backend:**
```bash
cd backend
pip install google-auth PyJWT cryptography
# or if using poetry:
poetry install
```

**Frontend:**
```bash
cd frontend
npm install
```

### Step 4: Test the Application (5 minutes)

**Terminal 1 - Start Backend:**
```bash
cd backend
uvicorn main:app --reload
```

**Look for this in the output:**
```
🔐 AUTHENTICATION: Enabled (Google OAuth + JWT)
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```

**Open Browser:**
```
http://localhost:5173
```

**What you should see:**
1. Login screen with "Sign in with Google" button
2. Click the button
3. Google account picker appears
4. After login → Chat interface loads
5. All your existing threads are preserved

---

## 🧪 Testing Checklist

- [ ] Backend starts with "AUTHENTICATION: Enabled" message
- [ ] Frontend shows Google login button
- [ ] Can click login button and see Google account picker
- [ ] After selecting account, redirected to chat interface
- [ ] Existing conversations are visible
- [ ] Can create new conversations
- [ ] Can log out (add logout button to UI if needed)
- [ ] Can log in with different Google account (sees different data)

---

## 🔍 Troubleshooting

### Backend shows "AUTHENTICATION: Disabled"
**Cause:** Environment variables not loaded

**Fix:**
```bash
# Stop the backend (Ctrl+C)
# Verify .env file has Google Client ID
cat backend/.env | grep GOOGLE_CLIENT_ID
# Should NOT show "YOUR_CLIENT_ID_HERE"

# Restart backend
cd backend
uvicorn main:app --reload
```

### Frontend shows "Google OAuth not configured"
**Cause:** Frontend environment variable not set

**Fix:**
```bash
# Stop frontend (Ctrl+C)
# Verify .env file
cat frontend/.env | grep VITE_GOOGLE_CLIENT_ID
# Should NOT show "YOUR_CLIENT_ID_HERE"

# Restart frontend
cd frontend
npm run dev
```

### "redirect_uri_mismatch" Error
**Cause:** Authorized redirect URIs don't match

**Fix:**
1. Go to Google Cloud Console → Credentials
2. Edit your OAuth client ID
3. Ensure these are in **Authorized JavaScript origins**:
   - `http://localhost:5173`
   - `http://localhost:8000`
4. Save and wait 5 minutes for changes to propagate

### "Access blocked: This app's request is invalid"
**Cause:** OAuth consent screen not fully configured

**Fix:**
1. Go to Google Cloud Console → OAuth consent screen
2. Ensure all required fields are filled
3. Add your email to test users list
4. Save changes

### Google Login Button Doesn't Appear
**Cause:** Network issue or script loading failure

**Fix:**
1. Open browser console (F12)
2. Check for errors
3. Verify internet connection
4. Try refreshing the page

---

## 📖 Full Documentation

- **Setup Guide:** `GOOGLE_OAUTH_SETUP.md` - Complete step-by-step guide
- **Migration Guide:** `backend/migrations/README.md` - Database migration docs
- **Implementation Plan:** `/home/david/.claude/plans/composed-swimming-twilight.md`

---

## 🎉 What You Get After Setup

✅ **Google OAuth Login** - Secure authentication with Google accounts
✅ **User Isolation** - Each user sees only their conversations
✅ **Encrypted API Keys** - Store OpenAI/Anthropic keys per-user
✅ **Thread Migration** - Existing localStorage threads automatically claimed
✅ **Multi-Device Support** - Access your conversations from anywhere
✅ **JWT Sessions** - 7-day token expiry with automatic refresh

---

## 🚀 Ready to Go!

1. Complete Google OAuth setup (15 min)
2. Update both .env files with Client ID (2 min)
3. Install dependencies (3 min)
4. Start backend and frontend (1 min)
5. Test login flow (2 min)

**Total time:** ~25 minutes

Let me know if you run into any issues!
