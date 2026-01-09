import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * UserMenu - User profile dropdown with logout and settings
 */
import { useState, useRef, useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import { LogOut, User, Settings, Key } from "lucide-react";
export function UserMenu() {
    const { user, logout } = useAuth();
    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef(null);
    // Close menu when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }
        if (isOpen) {
            document.addEventListener("mousedown", handleClickOutside);
            return () => document.removeEventListener("mousedown", handleClickOutside);
        }
    }, [isOpen]);
    if (!user)
        return null;
    const initials = user.name
        ? user.name
            .split(" ")
            .map((n) => n[0])
            .join("")
            .toUpperCase()
            .slice(0, 2)
        : user.email[0].toUpperCase();
    return (_jsxs("div", { className: "relative", ref: menuRef, children: [_jsxs("button", { onClick: () => setIsOpen(!isOpen), className: "flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors", title: user.email, children: [user.picture_url ? (_jsx("img", { src: user.picture_url, alt: user.name || user.email, className: "w-8 h-8 rounded-full" })) : (_jsx("div", { className: "w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-sm font-medium", children: initials })), _jsx("span", { className: "hidden sm:block text-sm font-medium text-gray-700 dark:text-gray-300", children: user.name || user.email.split("@")[0] }), _jsx("svg", { className: `w-4 h-4 text-gray-500 transition-transform ${isOpen ? "rotate-180" : ""}`, fill: "none", stroke: "currentColor", viewBox: "0 0 24 24", children: _jsx("path", { strokeLinecap: "round", strokeLinejoin: "round", strokeWidth: 2, d: "M19 9l-7 7-7-7" }) })] }), isOpen && (_jsxs("div", { className: "absolute left-0 bottom-full mb-2 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50", children: [_jsx("div", { className: "px-4 py-3 border-b border-gray-200 dark:border-gray-700", children: _jsxs("div", { className: "flex items-center gap-3", children: [user.picture_url ? (_jsx("img", { src: user.picture_url, alt: user.name || user.email, className: "w-10 h-10 rounded-full" })) : (_jsx("div", { className: "w-10 h-10 rounded-full bg-blue-500 text-white flex items-center justify-center text-sm font-medium", children: initials })), _jsxs("div", { className: "flex-1 min-w-0", children: [user.name && (_jsx("p", { className: "text-sm font-medium text-gray-900 dark:text-gray-100 truncate", children: user.name })), _jsx("p", { className: "text-xs text-gray-500 dark:text-gray-400 truncate", children: user.email })] })] }) }), _jsxs("div", { className: "py-1", children: [_jsxs("button", { onClick: () => {
                                    setIsOpen(false);
                                    // TODO: Navigate to profile page
                                    console.log("Profile clicked");
                                }, className: "w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2", children: [_jsx(User, { className: "w-4 h-4" }), "Profile"] }), _jsxs("button", { onClick: () => {
                                    setIsOpen(false);
                                    // TODO: Navigate to settings page
                                    console.log("Settings clicked");
                                }, className: "w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2", children: [_jsx(Settings, { className: "w-4 h-4" }), "Settings"] }), _jsxs("button", { onClick: () => {
                                    setIsOpen(false);
                                    // TODO: Navigate to API keys page
                                    console.log("API Keys clicked");
                                }, className: "w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2", children: [_jsx(Key, { className: "w-4 h-4" }), "API Keys"] })] }), _jsx("div", { className: "border-t border-gray-200 dark:border-gray-700 py-1", children: _jsxs("button", { onClick: () => {
                                setIsOpen(false);
                                logout();
                            }, className: "w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2", children: [_jsx(LogOut, { className: "w-4 h-4" }), "Log out"] }) })] }))] }));
}
