# Test Google OAuth Authentication

## ✅ Setup Complete!

Everything is now configured and ready to test:

- ✅ Database migration completed
- ✅ Security keys generated
- ✅ Google Client ID configured
- ✅ Backend dependencies installed
- ✅ Frontend dependencies installed

---

## 🚀 Start the Application

### Terminal 1: Start Backend

```bash
cd /home/david/Documents/projects/multi-agent-chat/backend
conda activate magent
uvicorn main:app --reload
```

**Look for this output:**
```
🔐 AUTHENTICATION: Enabled (Google OAuth + JWT)
```

If you see "AUTHENTICATION: Disabled", check that your `.env` file has the Google Client ID set.

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
================================================================================
🟢 DEBATE ENGINE: LangGraph (Legacy Backend)
================================================================================
✓ LangGraph backend is ACTIVE (default)
✓ Storage mode: PostgreSQL
🔐 AUTHENTICATION: Enabled (Google OAuth + JWT)
================================================================================
INFO:     Application startup complete.
```

---

### Terminal 2: Start Frontend

```bash
cd /home/david/Documents/projects/multi-agent-chat/frontend
npm run dev
```

**Expected output:**
```
  VITE v5.4.1  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

---

## 🧪 Test the Authentication Flow

### Step 1: Open the Application

Open your browser and navigate to:
```
http://localhost:5173
```

### Step 2: Login Screen

You should see:
- ✅ "Multi-Agent Chat Panel" heading
- ✅ "Sign in to access your conversations" message
- ✅ "Sign in with Google" button

**If you see an error:**
- "Google OAuth not configured" → Frontend .env file not loaded correctly
- Check that `frontend/.env` has the correct Client ID
- Restart the frontend (Ctrl+C and run `npm run dev` again)

### Step 3: Click "Sign in with Google"

The Google account picker should appear:
- ✅ Shows your Google account(s)
- ✅ Click on an account to sign in

**If nothing happens:**
- Open browser console (F12)
- Check for JavaScript errors
- Verify internet connection (Google SDK needs to load)

### Step 4: Grant Permissions

Google will ask for permissions:
- ✅ Email address
- ✅ Basic profile info
- ✅ Click "Allow" or "Continue"

**If you see "Access blocked":**
- Your email needs to be added as a test user in Google Cloud Console
- Go to: OAuth consent screen → Test users → Add users
- Add your Gmail address
- Try logging in again

### Step 5: Verify Successful Login

After login, you should:
- ✅ See the chat interface (not the login screen)
- ✅ See your existing conversations in the sidebar
- ✅ Be able to create new conversations
- ✅ See your name/email in the UI (if we add a user menu)

**Check browser console (F12):**
```
User logged in: your-email@gmail.com
Migrated X threads to user account
```

**Check backend terminal:**
```
INFO: User created: your-email@gmail.com
```
or
```
INFO: User logged in: your-email@gmail.com
```

---

## 🔍 Verification Checklist

- [ ] Backend starts with "AUTHENTICATION: Enabled"
- [ ] Frontend loads at http://localhost:5173
- [ ] Login screen appears
- [ ] "Sign in with Google" button is visible
- [ ] Clicking button shows Google account picker
- [ ] After selecting account, redirected to chat interface
- [ ] Existing conversations are visible
- [ ] Can create new conversations
- [ ] Browser console shows "User logged in"
- [ ] Backend logs show user creation/login

---

## 🎯 Test Multi-User Isolation

To verify that users see different conversations:

### Test 1: Create conversations with User A
1. Log in with your Google account
2. Create a new conversation
3. Add some messages
4. Note the thread ID/name

### Test 2: Log in with User B
1. Log out (or use incognito window)
2. Go to http://localhost:5173
3. Log in with a DIFFERENT Google account (must be in test users)
4. You should NOT see User A's conversations
5. Create a new conversation as User B

### Test 3: Verify isolation
1. Log back in as User A
2. You should see ONLY User A's conversations
3. User B's conversations should NOT be visible

---

## 🐛 Troubleshooting

### Backend Issues

**"AUTHENTICATION: Disabled" message:**
```bash
# Check environment variables
cd backend
conda activate magent
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print('GOOGLE_CLIENT_ID:', os.getenv('GOOGLE_CLIENT_ID'))"
```

Should output:
```
GOOGLE_CLIENT_ID: 118540861678-fnmfu7n9a1qs3emnap8opch0eorlhf7s.apps.googleusercontent.com
```

If it shows `None` or `YOUR_CLIENT_ID_HERE`, edit `backend/.env` and restart.

**ImportError for google-auth, PyJWT, or cryptography:**
```bash
# Verify packages are installed
conda run -n magent pip list | grep -E "google-auth|PyJWT|cryptography"
```

Should show:
```
cryptography                  41.0.7
google-auth                   2.47.0
PyJWT                         2.8.0
```

If missing, reinstall:
```bash
conda activate magent
pip install google-auth PyJWT cryptography
```

### Frontend Issues

**"Google OAuth not configured" error:**
```bash
# Check frontend .env
cat frontend/.env | grep VITE_GOOGLE_CLIENT_ID
```

Should output:
```
VITE_GOOGLE_CLIENT_ID=118540861678-fnmfu7n9a1qs3emnap8opch0eorlhf7s.apps.googleusercontent.com
```

If incorrect, edit `frontend/.env` and restart frontend.

**Google button doesn't appear:**
- Check browser console for errors
- Verify internet connection (needs to load Google SDK)
- Try hard refresh (Ctrl+Shift+R)

**"redirect_uri_mismatch" error:**
- Your OAuth client needs these authorized origins:
  - `http://localhost:5173`
  - `http://localhost:8000`
- Go to Google Cloud Console → Credentials → Edit OAuth client
- Add the origins if missing
- Wait 5 minutes for changes to take effect

### Database Issues

**"User not found" after login:**
```bash
# Check if user was created in database
cd /home/david/Documents/projects/multi-agent-chat
python3 -c "
import asyncio
import sys
sys.path.insert(0, 'backend')
from config import get_pg_conn_str
import asyncpg

async def check_users():
    conn = await asyncpg.connect(get_pg_conn_str())
    users = await conn.fetch('SELECT id, email, created_at FROM users ORDER BY created_at DESC LIMIT 5')
    print('Recent users:')
    for u in users:
        print(f'  - {u[\"email\"]} (created: {u[\"created_at\"]})')
    await conn.close()

asyncio.run(check_users())
"
```

---

## 📊 Database Verification

To check that user data is being stored correctly:

```python
# Run this in Python (conda activate magent first)
python3 /home/david/Documents/projects/multi-agent-chat/verify_migration.py
```

Should show all auth tables are created.

---

## ✨ Success Indicators

Your authentication is working when you see:

1. **Backend startup:**
   ```
   🔐 AUTHENTICATION: Enabled (Google OAuth + JWT)
   ```

2. **Frontend login screen:**
   - Google Sign-in button appears
   - Clicking it shows Google account picker

3. **After login:**
   - Chat interface loads
   - Existing threads visible
   - Can create new conversations

4. **Browser console:**
   ```
   User logged in: your-email@gmail.com
   ```

5. **Backend logs:**
   ```
   INFO: User created: your-email@gmail.com
   ```
   or
   ```
   INFO: User logged in: your-email@gmail.com
   ```

---

## 🎉 Next Steps After Testing

Once authentication is working:

1. **Add logout button** - Create a user menu component with logout
2. **Display user info** - Show user name/email in the UI
3. **Test API key storage** - Save provider keys per-user
4. **Production deployment** - Update OAuth origins for your domain
5. **Add user profile page** - Manage settings, API keys, etc.

---

## 📝 Documentation

- **Full setup guide:** `GOOGLE_OAUTH_SETUP.md`
- **Next steps:** `AUTH_SETUP_NEXT_STEPS.md`
- **Implementation plan:** `/home/david/.claude/plans/composed-swimming-twilight.md`

---

**Happy testing! 🚀**
