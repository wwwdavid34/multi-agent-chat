import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
/**
 * UserMenu - User profile dropdown with logout and settings
 * For guests: shows login button
 * For authenticated users: shows profile dropdown with settings, import, logout
 */
import { useState, useRef, useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import { LogOut, User, Settings, Upload, Moon, Sun } from "lucide-react";
import { GoogleLoginButton } from "./GoogleLoginButton";
import { useTheme } from "../theme-provider";
export function UserMenu({ onOpenSettings, onImportThread }) {
    const { user, isAuthenticated, logout } = useAuth();
    const { theme, setTheme } = useTheme();
    const [isOpen, setIsOpen] = useState(false);
    const [showLoginModal, setShowLoginModal] = useState(false);
    const menuRef = useRef(null);
    const modalRef = useRef(null);
    const toggleTheme = () => {
        setTheme(theme === "dark" ? "light" : "dark");
    };
    // Close menu when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setIsOpen(false);
            }
            if (modalRef.current && !modalRef.current.contains(event.target)) {
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
        return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "flex items-center gap-2", children: [_jsxs("button", { onClick: () => setShowLoginModal(true), className: "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 transition-colors text-sm font-medium", children: [_jsx(User, { className: "w-4 h-4" }), "Sign in"] }), _jsx("button", { onClick: toggleTheme, className: "p-2.5 rounded-lg hover:bg-muted/60 transition-colors", "aria-label": "Toggle theme", children: theme === "dark" ? (_jsx(Moon, { className: "w-4 h-4 text-muted-foreground" })) : (_jsx(Sun, { className: "w-4 h-4 text-muted-foreground" })) })] }), showLoginModal && (_jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 backdrop-blur-sm", children: _jsxs("div", { ref: modalRef, className: "bg-background rounded-2xl shadow-2xl max-w-md w-full mx-4 p-8 border border-border", children: [_jsxs("div", { className: "text-center mb-6", children: [_jsx("h2", { className: "text-2xl font-bold tracking-tight", children: "Welcome" }), _jsx("p", { className: "mt-2 text-muted-foreground text-sm", children: "Sign in to save your conversations and access them anywhere" })] }), _jsx(GoogleLoginButton, {}), _jsx("div", { className: "mt-6 text-center", children: _jsx("button", { onClick: () => setShowLoginModal(false), className: "text-sm text-muted-foreground hover:text-foreground transition-colors", children: "Continue as guest" }) })] }) }))] }));
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
    return (_jsxs("div", { className: "relative", ref: menuRef, children: [_jsxs("button", { onClick: () => setIsOpen(!isOpen), className: "flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted/60 transition-colors w-full", title: user?.email, children: [user?.picture_url ? (_jsx("img", { src: user.picture_url, alt: user.name || user.email, className: "w-8 h-8 rounded-full" })) : (_jsx("div", { className: "w-8 h-8 rounded-full bg-accent text-accent-foreground flex items-center justify-center text-sm font-medium", children: initials })), _jsx("span", { className: "flex-1 text-left text-sm font-medium text-foreground truncate", children: user?.name || user?.email?.split("@")[0] }), _jsx("svg", { className: `w-4 h-4 text-muted-foreground transition-transform ${isOpen ? "rotate-180" : ""}`, fill: "none", stroke: "currentColor", viewBox: "0 0 24 24", children: _jsx("path", { strokeLinecap: "round", strokeLinejoin: "round", strokeWidth: 2, d: "M19 9l-7 7-7-7" }) })] }), isOpen && (_jsxs("div", { className: "absolute left-0 bottom-full mb-2 w-full bg-background rounded-lg shadow-lg border border-border z-50", children: [_jsx("div", { className: "px-4 py-3 border-b border-border", children: _jsxs("div", { className: "flex items-center gap-3", children: [user?.picture_url ? (_jsx("img", { src: user.picture_url, alt: user.name || user.email, className: "w-10 h-10 rounded-full" })) : (_jsx("div", { className: "w-10 h-10 rounded-full bg-accent text-accent-foreground flex items-center justify-center text-sm font-medium", children: initials })), _jsxs("div", { className: "flex-1 min-w-0", children: [user?.name && (_jsx("p", { className: "text-sm font-medium text-foreground truncate", children: user.name })), _jsx("p", { className: "text-xs text-muted-foreground truncate", children: user?.email })] })] }) }), _jsxs("div", { className: "py-1", children: [onOpenSettings && (_jsxs("button", { onClick: () => {
                                    setIsOpen(false);
                                    onOpenSettings();
                                }, className: "w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-muted/60 flex items-center gap-3", children: [_jsx(Settings, { className: "w-4 h-4 text-muted-foreground" }), "Panel Settings"] })), onImportThread && (_jsxs("button", { onClick: () => {
                                    setIsOpen(false);
                                    onImportThread();
                                }, className: "w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-muted/60 flex items-center gap-3", children: [_jsx(Upload, { className: "w-4 h-4 text-muted-foreground" }), "Import Thread"] })), _jsxs("button", { onClick: toggleTheme, className: "w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-muted/60 flex items-center gap-3", children: [theme === "dark" ? (_jsx(Sun, { className: "w-4 h-4 text-muted-foreground" })) : (_jsx(Moon, { className: "w-4 h-4 text-muted-foreground" })), theme === "dark" ? "Light Mode" : "Dark Mode"] })] }), _jsx("div", { className: "border-t border-border py-1", children: _jsxs("button", { onClick: () => {
                                setIsOpen(false);
                                logout();
                            }, className: "w-full px-4 py-2.5 text-left text-sm text-destructive hover:bg-destructive/10 flex items-center gap-3", children: [_jsx(LogOut, { className: "w-4 h-4" }), "Sign out"] }) })] }))] }));
}
