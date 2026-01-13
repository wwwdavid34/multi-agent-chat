/**
 * AuthContext - Authentication state management with Google OAuth
 *
 * Provides:
 * - User login/logout
 * - JWT token management
 * - API key storage (encrypted in backend)
 * - Thread migration from localStorage
 */

import React, { createContext, useState, useEffect, ReactNode } from "react";
import { jwtDecode } from "jwt-decode";

// Get API base URL from environment or use relative URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ??
  `${window.location.protocol}//${window.location.hostname}:8000`;

// Get Google Client ID from environment
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// ============================================================================
// Types
// ============================================================================

export interface User {
  id: string;
  email: string;
  name: string | null;
  picture_url: string | null;
}

export interface JWTPayload {
  user_id: string;
  email: string;
  exp: number;
  iat: number;
}

export interface ThreadInfo {
  thread_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthContextType {
  // State
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Auth methods
  login: (googleToken: string) => Promise<void>;
  logout: () => void;

  // API key management
  saveApiKeys: (keys: Record<string, string>) => Promise<void>;
  getApiKeys: () => Promise<Record<string, string>>;

  // Thread management
  migrateThreads: (threadIds: string[], metadata?: any) => Promise<void>;
  fetchThreads: () => Promise<ThreadInfo[]>;
}

// ============================================================================
// Context
// ============================================================================

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================================================
// Provider Component
// ============================================================================

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // =========================================================================
  // Initialize auth state from localStorage
  // =========================================================================

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem("auth_token");

      if (storedToken) {
        try {
          // Decode token to check expiration
          const decoded = jwtDecode<JWTPayload>(storedToken);

          // Check if token is expired
          const now = Date.now() / 1000;
          if (decoded.exp < now) {
            // Token expired - clear it
            localStorage.removeItem("auth_token");
            setIsLoading(false);
            return;
          }

          // Token is valid - restore session
          setAccessToken(storedToken);

          // Fetch full user info from backend
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              Authorization: `Bearer ${storedToken}`,
            },
          });

          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
          } else {
            // Token is invalid on backend - clear everything
            localStorage.removeItem("auth_token");
            setAccessToken(null);
            setUser(null);
          }
        } catch (err) {
          console.error("Failed to restore session:", err);
          localStorage.removeItem("auth_token");
          setAccessToken(null);
          setUser(null);
        }
      }

      setIsLoading(false);
    };

    initAuth();
  }, []);

  // =========================================================================
  // Login with Google
  // =========================================================================

  const login = async (googleToken: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/google`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token: googleToken }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Login failed");
      }

      const data = await response.json();

      // Store token and user data
      setAccessToken(data.access_token);
      setUser(data.user);
      localStorage.setItem("auth_token", data.access_token);

      console.log(`User logged in: ${data.user.email}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      console.error("Login error:", err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // =========================================================================
  // Logout
  // =========================================================================

  const logout = () => {
    setUser(null);
    setAccessToken(null);
    setError(null);
    localStorage.removeItem("auth_token");
    // Clear user-specific data to prevent data bleeding to guests
    localStorage.removeItem("threads");
    localStorage.removeItem("conversations");
    localStorage.removeItem("threadId");
    // NOTE: Keep threads_migrated flag - threads are already on server
    // When user logs back in, they'll be restored from server, not re-migrated
    console.log("User logged out, cleared user data");
  };

  // =========================================================================
  // Save API keys (encrypted on backend)
  // =========================================================================

  const saveApiKeys = async (keys: Record<string, string>) => {
    if (!accessToken) {
      throw new Error("Not authenticated");
    }

    const response = await fetch(`${API_BASE_URL}/auth/keys`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ keys }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to save API keys");
    }

    console.log("API keys saved successfully");
  };

  // =========================================================================
  // Get API keys (decrypted from backend)
  // =========================================================================

  const getApiKeys = async (): Promise<Record<string, string>> => {
    if (!accessToken) {
      throw new Error("Not authenticated");
    }

    const response = await fetch(`${API_BASE_URL}/auth/keys`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to retrieve API keys");
    }

    const data = await response.json();
    return data.keys;
  };

  // =========================================================================
  // Migrate threads from localStorage to user account
  // =========================================================================

  const migrateThreads = async (threadIds: string[], metadata?: any) => {
    if (!accessToken) {
      throw new Error("Not authenticated");
    }

    if (threadIds.length === 0) {
      return; // Nothing to migrate
    }

    const response = await fetch(`${API_BASE_URL}/auth/migrate-threads`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        thread_ids: threadIds,
        metadata,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Thread migration failed");
    }

    const data = await response.json();
    console.log(
      `Threads migrated: ${data.migrated_count} migrated, ${data.skipped_count} skipped`
    );
  };

  // =========================================================================
  // Fetch user's threads from server
  // =========================================================================

  const fetchThreads = async (): Promise<ThreadInfo[]> => {
    if (!accessToken) {
      throw new Error("Not authenticated");
    }

    const response = await fetch(`${API_BASE_URL}/auth/threads`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to fetch threads");
    }

    const data = await response.json();
    return data.threads;
  };

  // =========================================================================
  // Context value
  // =========================================================================

  const value: AuthContextType = {
    user,
    accessToken,
    isAuthenticated: !!user && !!accessToken,
    isLoading,
    error,
    login,
    logout,
    saveApiKeys,
    getApiKeys,
    migrateThreads,
    fetchThreads,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ============================================================================
// Export Google Client ID for use in GoogleLoginButton
// ============================================================================

export { GOOGLE_CLIENT_ID };
