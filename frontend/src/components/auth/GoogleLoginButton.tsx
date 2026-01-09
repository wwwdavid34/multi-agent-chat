/**
 * GoogleLoginButton - Google OAuth login button using Google Identity Services
 *
 * This component:
 * 1. Loads the Google Identity Services SDK from CDN
 * 2. Renders the official Google Sign-In button
 * 3. Handles the OAuth callback
 * 4. Passes the ID token to AuthContext for verification
 */

import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { GOOGLE_CLIENT_ID } from "../../contexts/AuthContext";

// Extend Window interface to include Google Identity Services
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: GoogleIdConfiguration) => void;
          renderButton: (
            parent: HTMLElement,
            options: GoogleButtonConfiguration
          ) => void;
          prompt: () => void;
        };
      };
    };
  }
}

interface GoogleIdConfiguration {
  client_id: string;
  callback: (response: GoogleCallbackResponse) => void;
  auto_select?: boolean;
  cancel_on_tap_outside?: boolean;
}

interface GoogleCallbackResponse {
  credential: string; // JWT ID token
  select_by?: string;
}

interface GoogleButtonConfiguration {
  type?: "standard" | "icon";
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  text?: "signin_with" | "signup_with" | "continue_with" | "signin";
  shape?: "rectangular" | "pill" | "circle" | "square";
  logo_alignment?: "left" | "center";
  width?: number;
  locale?: string;
}

export function GoogleLoginButton() {
  const { login } = useAuth();
  const buttonRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Check if Google Client ID is configured
    if (!GOOGLE_CLIENT_ID) {
      setError(
        "Google OAuth not configured. Set VITE_GOOGLE_CLIENT_ID in your .env file."
      );
      return;
    }

    // Load Google Identity Services SDK
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;

    script.onload = () => {
      if (!window.google) {
        setError("Failed to load Google Identity Services");
        return;
      }

      // Initialize Google Identity Services
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      // Render the Google Sign-In button
      if (buttonRef.current) {
        window.google.accounts.id.renderButton(buttonRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "signin_with",
          shape: "rectangular",
          logo_alignment: "left",
        });
      }
    };

    script.onerror = () => {
      setError("Failed to load Google login. Check your internet connection.");
    };

    document.body.appendChild(script);

    // Cleanup
    return () => {
      document.body.removeChild(script);
    };
  }, []);

  /**
   * Handle Google OAuth callback
   */
  const handleGoogleResponse = async (response: GoogleCallbackResponse) => {
    setIsLoading(true);
    setError(null);

    try {
      // Pass Google ID token to backend for verification
      await login(response.credential);

      // Success - AuthContext will update isAuthenticated state
      console.log("Google login successful");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Google login failed";
      setError(message);
      console.error("Google login error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Google Sign-In Button Container */}
      <div ref={buttonRef} className="google-signin-button" />

      {/* Loading State */}
      {isLoading && (
        <div className="text-sm text-gray-600 dark:text-gray-400">
          Signing in...
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="max-w-md p-4 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400 rounded-lg">
          {error}
        </div>
      )}

      {/* Help Text */}
      {!error && !isLoading && (
        <div className="max-w-md text-center text-sm text-gray-600 dark:text-gray-400">
          Sign in with your Google account to access your conversations and
          settings
        </div>
      )}
    </div>
  );
}
