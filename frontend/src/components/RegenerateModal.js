import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
export function RegenerateModal({ open, onClose, onConfirm, defaultDebateMode, defaultMaxRounds = 3, title = "Regenerate Response", subtitle = "Choose settings for this regeneration", confirmLabel = "Regenerate", headerIcon, confirmIcon, }) {
    const [debateMode, setDebateMode] = useState(defaultDebateMode);
    const [maxDebateRounds, setMaxDebateRounds] = useState(defaultMaxRounds);
    // Reset state when modal opens with new defaults
    useEffect(() => {
        if (open) {
            setDebateMode(defaultDebateMode);
            setMaxDebateRounds(defaultMaxRounds);
        }
    }, [open, defaultDebateMode, defaultMaxRounds]);
    const handleConfirm = () => {
        onConfirm(debateMode, maxDebateRounds);
        onClose();
    };
    if (!open)
        return null;
    const defaultRegenerateIcon = (_jsx("svg", { viewBox: "0 0 24 24", className: "w-5 h-5 text-accent", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", children: _jsx("path", { d: "M4 12a8 8 0 0 1 8-8 8 8 0 0 1 6.18 2.82l2.82-2.82M20 4v6h-6M20 12a8 8 0 0 1-8 8 8 8 0 0 1-6.18-2.82l-2.82 2.82M4 20v-6h6" }) }));
    const modeOptions = [
        { value: undefined, label: "Panel (No Debate)", description: "Single round of responses from all panelists" },
        { value: "autonomous", label: "Autonomous Debate", description: "Debate runs until consensus or max rounds" },
        { value: "supervised", label: "Supervised Debate", description: "Pause after each round for review" },
        { value: "participatory", label: "Participatory Debate", description: "Pause for your input each round" },
    ];
    return (_jsx(AnimatePresence, { children: _jsx(motion.div, { className: "fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 backdrop-blur-sm p-4", initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, onClick: onClose, children: _jsxs(motion.div, { className: "bg-background text-foreground rounded-2xl shadow-2xl max-w-md w-full border border-border", initial: { scale: 0.9, opacity: 0 }, animate: { scale: 1, opacity: 1 }, exit: { scale: 0.9, opacity: 0 }, transition: { type: "spring", stiffness: 300, damping: 30 }, onClick: (e) => e.stopPropagation(), children: [_jsxs("div", { className: "flex items-center justify-between p-6 border-b border-border", children: [_jsxs("div", { className: "flex items-center gap-3", children: [_jsx("div", { className: "w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center", children: headerIcon ?? defaultRegenerateIcon }), _jsxs("div", { children: [_jsx("h2", { className: "text-lg font-semibold m-0", children: title }), _jsx("p", { className: "text-xs text-muted-foreground mt-0.5", children: subtitle })] })] }), _jsx("button", { type: "button", onClick: onClose, className: "rounded-lg w-8 h-8 border border-border flex items-center justify-center hover:bg-muted transition-colors text-lg", "aria-label": "Close", children: "\u00D7" })] }), _jsxs("div", { className: "p-6 space-y-5", children: [_jsxs("div", { className: "space-y-2", children: [_jsx("h4", { className: "text-sm font-semibold m-0", children: "Mode" }), _jsx("div", { className: "space-y-2", children: modeOptions.map((option) => (_jsxs("label", { className: `flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${debateMode === option.value
                                                ? "border-accent bg-accent/5"
                                                : "border-border hover:bg-muted/50"}`, children: [_jsx("input", { type: "radio", name: "debateMode", checked: debateMode === option.value, onChange: () => setDebateMode(option.value), className: "mt-0.5 accent-accent" }), _jsxs("div", { children: [_jsx("div", { className: "text-sm font-medium", children: option.label }), _jsx("div", { className: "text-xs text-muted-foreground", children: option.description })] })] }, option.label))) })] }), _jsx(AnimatePresence, { children: debateMode && (_jsx(motion.div, { initial: { opacity: 0, height: 0 }, animate: { opacity: 1, height: "auto" }, exit: { opacity: 0, height: 0 }, transition: { duration: 0.2 }, className: "rounded-lg border border-border p-4 bg-card overflow-hidden", children: _jsxs("label", { className: "block", children: [_jsxs("div", { className: "flex items-center justify-between mb-3", children: [_jsxs("div", { children: [_jsx("h4", { className: "text-sm font-semibold m-0", children: "Maximum Debate Rounds" }), _jsx("p", { className: "text-xs text-muted-foreground mt-1", children: "Limit debate iterations (1-10 rounds)" })] }), _jsx("span", { className: "text-lg font-bold text-accent", children: maxDebateRounds })] }), _jsx("input", { type: "range", min: "1", max: "10", value: maxDebateRounds, onChange: (e) => setMaxDebateRounds(Number(e.target.value)), className: "w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-accent" }), _jsxs("div", { className: "flex justify-between text-xs text-muted-foreground mt-2", children: [_jsx("span", { children: "1 round" }), _jsx("span", { children: "10 rounds" })] })] }) })) }), _jsx("div", { className: "rounded-lg border border-accent/20 bg-accent/5 p-3", children: _jsx("p", { className: "text-xs text-muted-foreground m-0", children: debateMode === undefined
                                        ? "The panel will provide immediate responses without debate."
                                        : debateMode === "autonomous"
                                            ? `The panel will debate for up to ${maxDebateRounds} round${maxDebateRounds > 1 ? 's' : ''} or until consensus is reached.`
                                            : debateMode === "supervised"
                                                ? `Debate will pause after each round for you to review. Up to ${maxDebateRounds} rounds.`
                                                : `You can add input and @mention panelists each round. Up to ${maxDebateRounds} rounds.` }) })] }), _jsxs("div", { className: "flex items-center justify-end gap-3 p-6 border-t border-border", children: [_jsx("button", { type: "button", onClick: onClose, className: "px-4 py-2 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors", children: "Cancel" }), _jsxs("button", { type: "button", onClick: handleConfirm, className: "px-4 py-2 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2", children: [confirmIcon ?? (_jsx("svg", { viewBox: "0 0 24 24", className: "w-4 h-4", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", children: _jsx("path", { d: "M4 12a8 8 0 0 1 8-8 8 8 0 0 1 6.18 2.82l2.82-2.82M20 4v6h-6M20 12a8 8 0 0 1-8 8 8 8 0 0 1-6.18-2.82l-2.82 2.82M4 20v-6h6" }) })), confirmLabel] })] })] }) }) }));
}
