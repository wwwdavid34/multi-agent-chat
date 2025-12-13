import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";
import { useTheme } from "./theme-provider";
export function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const toggleTheme = () => {
        setTheme(theme === "dark" ? "light" : "dark");
    };
    return (_jsxs(motion.button, { onClick: toggleTheme, className: "rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors relative", "aria-label": "Toggle theme", whileHover: { scale: 1.05 }, whileTap: { scale: 0.95 }, children: [_jsx(motion.div, { initial: false, animate: {
                    rotate: theme === "dark" ? 180 : 0,
                    scale: theme === "dark" ? 1 : 0,
                    opacity: theme === "dark" ? 1 : 0,
                }, transition: { duration: 0.2 }, className: "absolute inset-0 flex items-center justify-center", children: _jsx(Moon, { className: "h-5 w-5" }) }), _jsx(motion.div, { initial: false, animate: {
                    rotate: theme === "dark" ? -180 : 0,
                    scale: theme === "dark" ? 0 : 1,
                    opacity: theme === "dark" ? 0 : 1,
                }, transition: { duration: 0.2 }, className: "flex items-center justify-center", children: _jsx(Sun, { className: "h-5 w-5" }) })] }));
}
