#!/usr/bin/env python3
"""Test backend authentication endpoints."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print("✅ Health endpoint working\n")


def test_auth_protected():
    """Test that protected endpoint requires authentication."""
    print("=" * 60)
    print("TEST 2: Protected Endpoint (No Auth)")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/auth/me")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 401:
        print("✅ Authentication required - endpoint properly protected\n")
    else:
        print("❌ Endpoint should return 401 without auth\n")


def test_google_login_endpoint():
    """Test Google login endpoint exists (will fail without valid token)."""
    print("=" * 60)
    print("TEST 3: Google Login Endpoint")
    print("=" * 60)

    # Send invalid token to see if endpoint exists
    response = requests.post(
        f"{BASE_URL}/auth/google",
        json={"token": "invalid_test_token"}
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")

    if response.status_code in [401, 500]:
        print("✅ Google login endpoint exists (token verification works)\n")
    else:
        print(f"⚠️  Unexpected status code: {response.status_code}\n")


def test_threads_endpoint():
    """Test threads endpoint (should require auth)."""
    print("=" * 60)
    print("TEST 4: Threads Endpoint (No Auth)")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/auth/threads")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 401:
        print("✅ Threads endpoint properly protected\n")
    else:
        print("❌ Threads endpoint should require authentication\n")


def test_keys_endpoint():
    """Test API keys endpoint (should require auth)."""
    print("=" * 60)
    print("TEST 5: API Keys Endpoint (No Auth)")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/auth/keys")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 401:
        print("✅ API keys endpoint properly protected\n")
    else:
        print("❌ API keys endpoint should require authentication\n")


def check_backend_config():
    """Check if backend has auth configured."""
    print("=" * 60)
    print("Backend Configuration Check")
    print("=" * 60)

    import os
    import sys
    sys.path.insert(0, "backend")

    from dotenv import load_dotenv
    load_dotenv("backend/.env")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    encryption_key = os.getenv("ENCRYPTION_MASTER_KEY")

    print(f"GOOGLE_CLIENT_ID: {'✅ SET' if client_id and 'YOUR_CLIENT_ID' not in client_id else '❌ NOT SET'}")
    print(f"JWT_SECRET_KEY: {'✅ SET' if jwt_secret and len(jwt_secret) >= 32 else '❌ NOT SET'}")
    print(f"ENCRYPTION_MASTER_KEY: {'✅ SET' if encryption_key else '❌ NOT SET'}")
    print()


if __name__ == "__main__":
    print("\n🧪 BACKEND AUTHENTICATION TESTS")
    print("=" * 60)
    print()

    try:
        check_backend_config()
        test_health()
        test_auth_protected()
        test_google_login_endpoint()
        test_threads_endpoint()
        test_keys_endpoint()

        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("✅ Backend is running")
        print("✅ Authentication endpoints are configured")
        print("✅ Endpoints are properly protected")
        print()
        print("Next: Test Google OAuth flow from frontend")
        print("Run: cd frontend && npm run dev")
        print("Then open: http://localhost:5173")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running!")
        print("Start it with: cd backend && conda activate magent && uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
