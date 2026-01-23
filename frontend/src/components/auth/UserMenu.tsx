/**
 * UserMenu - User profile dropdown with logout and settings
 * For guests: shows login button
 * For authenticated users: shows profile dropdown with settings, import, logout
 */

import React, { useState, useRef, useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import { LogOut, User, Settings, Upload, Moon, Sun, Shield } from "lucide-react";
import { GoogleLoginButton } from "./GoogleLoginButton";
import { useTheme } from "../theme-provider";

interface UserMenuProps {
  onOpenSettings?: () => void;
  onImportThread?: () => void;
  onOpenAdmin?: () => void;
}

export function UserMenu({ onOpenSettings, onImportThread, onOpenAdmin }: UserMenuProps) {
  const { user, isAuthenticated, logout, isAdmin } = useAuth();
  const { theme, setTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        setShowLoginModal(false);
      }
    }

    if (isOpen || showLoginModal) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen, showLoginModal]);

  // Guest user - show sign in button and theme toggle
  if (!isAuthenticated) {
    return (
      <>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowLoginModal(true)}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 transition-colors text-sm font-medium"
          >
            <User className="w-4 h-4" />
            Sign in
          </button>
          <button
            onClick={toggleTheme}
            className="p-2.5 rounded-lg hover:bg-muted/60 transition-colors"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Moon className="w-4 h-4 text-muted-foreground" />
            ) : (
              <Sun className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
        </div>

        {/* Login Modal */}
        {showLoginModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 backdrop-blur-sm">
            <div
              ref={modalRef}
              className="bg-background rounded-2xl shadow-2xl max-w-md w-full mx-4 p-8 border border-border"
            >
              <div className="text-center mb-6">
                <h2 className="text-2xl font-bold tracking-tight">Welcome</h2>
                <p className="mt-2 text-muted-foreground text-sm">
                  Sign in to save your conversations and access them anywhere
                </p>
              </div>

              <GoogleLoginButton />

              <div className="mt-6 text-center">
                <button
                  onClick={() => setShowLoginModal(false)}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Continue as guest
                </button>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  // Authenticated user
  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.email?.[0].toUpperCase() || "U";

  return (
    <div className="relative" ref={menuRef}>
      {/* User Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted/60 transition-colors w-full"
        title={user?.email}
      >
        {user?.picture_url ? (
          <img
            src={user.picture_url}
            alt={user.name || user.email}
            className="w-8 h-8 rounded-full"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-accent text-accent-foreground flex items-center justify-center text-sm font-medium">
            {initials}
          </div>
        )}
        <span className="flex-1 text-left text-sm font-medium text-foreground truncate">
          {user?.name || user?.email?.split("@")[0]}
        </span>
        <svg
          className={`w-4 h-4 text-muted-foreground transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute left-0 bottom-full mb-2 w-full bg-background rounded-lg shadow-lg border border-border z-50">
          {/* User Info */}
          <div className="px-4 py-3 border-b border-border">
            <div className="flex items-center gap-3">
              {user?.picture_url ? (
                <img
                  src={user.picture_url}
                  alt={user.name || user.email}
                  className="w-10 h-10 rounded-full"
                />
              ) : (
                <div className="w-10 h-10 rounded-full bg-accent text-accent-foreground flex items-center justify-center text-sm font-medium">
                  {initials}
                </div>
              )}
              <div className="flex-1 min-w-0">
                {user?.name && (
                  <p className="text-sm font-medium text-foreground truncate">
                    {user.name}
                  </p>
                )}
                <p className="text-xs text-muted-foreground truncate">
                  {user?.email}
                </p>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-1">
            {onOpenSettings && (
              <button
                onClick={() => {
                  setIsOpen(false);
                  onOpenSettings();
                }}
                className="w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-muted/60 flex items-center gap-3"
              >
                <Settings className="w-4 h-4 text-muted-foreground" />
                Panel Settings
              </button>
            )}

            {onImportThread && (
              <button
                onClick={() => {
                  setIsOpen(false);
                  onImportThread();
                }}
                className="w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-muted/60 flex items-center gap-3"
              >
                <Upload className="w-4 h-4 text-muted-foreground" />
                Import Thread
              </button>
            )}

            {/* Admin Panel - only for admins */}
            {isAdmin && onOpenAdmin && (
              <button
                onClick={() => {
                  setIsOpen(false);
                  onOpenAdmin();
                }}
                className="w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-muted/60 flex items-center gap-3"
              >
                <Shield className="w-4 h-4 text-muted-foreground" />
                Admin Panel
              </button>
            )}

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-muted/60 flex items-center gap-3"
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4 text-muted-foreground" />
              ) : (
                <Moon className="w-4 h-4 text-muted-foreground" />
              )}
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </button>
          </div>

          {/* Logout */}
          <div className="border-t border-border py-1">
            <button
              onClick={() => {
                setIsOpen(false);
                logout();
              }}
              className="w-full px-4 py-2.5 text-left text-sm text-destructive hover:bg-destructive/10 flex items-center gap-3"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
