import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Markdown } from "./Markdown";
import { PROVIDER_LABELS } from "../lib/modelProviders";
export function DebateViewer({ debateHistory, panelists, onCopy, stepReview = false, debatePaused = false, onContinue, tagged_panelists = [], user_as_participant = false }) {
    const [expandedRounds, setExpandedRounds] = useState(() => {
        // Auto-expand the first round initially
        if (debateHistory.length > 0) {
            return new Set([debateHistory[0].round_number]);
        }
        return new Set();
    });
    // When new rounds arrive, auto-expand the latest one
    useEffect(() => {
        if (debateHistory.length > 0) {
            const latestRound = debateHistory[debateHistory.length - 1];
            setExpandedRounds(new Set([latestRound.round_number]));
        }
    }, [debateHistory.length]);
    const toggleRound = (roundNumber) => {
        setExpandedRounds((prev) => {
            const next = new Set(prev);
            if (next.has(roundNumber)) {
                next.delete(roundNumber);
            }
            else {
                next.add(roundNumber);
            }
            return next;
        });
    };
    if (!debateHistory || debateHistory.length === 0) {
        return null;
    }
    // In step review mode with paused debate, we show all rounds that have completed
    // and wait for user to click Continue to trigger the next round from the backend
    const roundsToShow = debateHistory;
    // Show continue button only when debate is actively paused (waiting for user)
    const showContinueButton = debatePaused && onContinue;
    return (_jsxs("div", { className: "mt-6 space-y-3", children: [_jsxs("div", { className: "flex items-center justify-between gap-2", children: [_jsxs("div", { className: "flex items-center gap-2 text-xs text-muted-foreground", children: [_jsxs("svg", { viewBox: "0 0 24 24", className: "w-4 h-4", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [_jsx("path", { d: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" }), _jsx("path", { d: "M8 10h.01M12 10h.01M16 10h.01" })] }), _jsxs("span", { className: "font-medium", children: ["Debate Rounds (", roundsToShow.length, stepReview ? ` of ${debateHistory.length}` : '', ")"] })] }), stepReview && (_jsx("span", { className: "text-[10px] px-2 py-0.5 rounded-full bg-accent/10 text-accent font-medium", children: "Step Review Mode" }))] }), _jsx("div", { className: "space-y-2", children: roundsToShow.map((round) => {
                    const isExpanded = expandedRounds.has(round.round_number);
                    const isLatest = round.round_number === debateHistory[debateHistory.length - 1].round_number;
                    return (_jsxs("div", { className: `rounded-lg border transition-all ${isLatest
                            ? "border-accent/40 bg-accent/5"
                            : "border-border/40 bg-muted/10"}`, children: [_jsxs("button", { type: "button", onClick: () => toggleRound(round.round_number), className: "w-full flex items-center justify-between p-3 text-left hover:bg-muted/20 transition-colors rounded-lg", children: [_jsxs("div", { className: "flex items-center gap-3", children: [_jsx("div", { className: `flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${isLatest
                                                    ? "bg-accent/20 text-accent"
                                                    : "bg-muted text-muted-foreground"}`, children: round.round_number + 1 }), _jsxs("div", { className: "flex flex-col", children: [_jsxs("span", { className: "text-sm font-medium text-foreground", children: ["Round ", round.round_number + 1] }), _jsxs("span", { className: "text-xs text-muted-foreground", children: [Object.keys(round.panel_responses).length, " responses", round.consensus_reached && (_jsxs("span", { className: "ml-2 inline-flex items-center gap-1 text-accent", children: [_jsx("svg", { viewBox: "0 0 24 24", className: "w-3 h-3", fill: "currentColor", children: _jsx("path", { d: "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" }) }), "Consensus"] }))] })] })] }), _jsx("svg", { viewBox: "0 0 24 24", className: `w-5 h-5 text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`, fill: "currentColor", children: _jsx("path", { d: "M7 10l5 5 5-5z" }) })] }), _jsx(AnimatePresence, { children: isExpanded && (_jsx(motion.div, { initial: { opacity: 0, height: 0 }, animate: { opacity: 1, height: "auto" }, exit: { opacity: 0, height: 0 }, transition: { duration: 0.2 }, className: "border-t border-border/30", children: _jsxs("div", { className: "p-4 space-y-3", children: [user_as_participant && round.user_message && (_jsxs("div", { className: "rounded-lg border border-accent/30 bg-accent/5 p-3", children: [_jsxs("div", { className: "flex items-center gap-2 mb-2", children: [_jsx("div", { className: "w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center text-accent font-semibold text-xs", children: "U" }), _jsx("span", { className: "text-xs font-semibold text-foreground", children: "You" })] }), _jsx("div", { className: "text-xs leading-relaxed text-muted-foreground prose prose-sm dark:prose-invert max-w-none", children: _jsx(Markdown, { content: round.user_message }) })] })), Object.entries(round.panel_responses)
                                                .filter(([_, response]) => response && typeof response === 'string' && response.trim())
                                                .map(([name, response]) => {
                                                const panelist = panelists.find((p) => p.name === name);
                                                const isTagged = tagged_panelists.includes(name);
                                                const isWatching = user_as_participant && !isTagged;
                                                return (_jsxs("div", { className: `rounded-lg border p-3 transition-colors group/response ${isWatching
                                                        ? "border-border/20 bg-muted/5"
                                                        : "border-border/30 bg-background hover:bg-muted/20"}`, children: [_jsxs("div", { className: "flex items-center justify-between gap-3 mb-2", children: [_jsxs("div", { className: "flex items-center gap-2", children: [_jsx("div", { className: `w-6 h-6 rounded-full flex items-center justify-center font-semibold text-xs ${isWatching
                                                                                ? "bg-muted text-muted-foreground"
                                                                                : "bg-accent/10 text-accent"}`, children: name.charAt(0).toUpperCase() }), _jsxs("div", { className: "flex flex-col", children: [_jsx("span", { className: `text-xs font-semibold ${isWatching ? "text-muted-foreground" : "text-foreground"}`, children: name }), panelist && (_jsxs("span", { className: "text-[10px] text-muted-foreground", children: [PROVIDER_LABELS[panelist.provider], " \u00B7 ", panelist.model] }))] })] }), !isWatching && onCopy && (_jsx("button", { type: "button", onClick: () => onCopy(response), className: "opacity-0 group-hover/response:opacity-100 p-1.5 rounded hover:bg-muted/40 transition-all", title: "Copy response", children: _jsxs("svg", { viewBox: "0 0 24 24", className: "w-3.5 h-3.5 text-muted-foreground", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [_jsx("rect", { x: "9", y: "9", width: "13", height: "13", rx: "2", ry: "2" }), _jsx("path", { d: "M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" })] }) }))] }), isWatching ? (_jsx("div", { className: "text-xs italic text-muted-foreground", children: "Watching this discussion..." })) : (_jsx("div", { className: "text-xs leading-relaxed text-muted-foreground prose prose-sm dark:prose-invert max-w-none", children: _jsx(Markdown, { content: response }) }))] }, name));
                                            })] }) })) })] }, round.round_number));
                }) }), showContinueButton && (_jsxs(motion.button, { type: "button", onClick: (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[DebateViewer] Continue debate clicked - triggering next round');
                    onContinue();
                }, className: "w-full mt-4 px-4 py-3 rounded-lg bg-accent text-accent-foreground font-medium text-sm hover:opacity-90 transition-opacity flex items-center justify-center gap-2", initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.3 }, children: [_jsxs("span", { children: ["Continue to Round ", debateHistory.length + 1] }), _jsx("svg", { viewBox: "0 0 24 24", className: "w-4 h-4", fill: "none", stroke: "currentColor", strokeWidth: "2", children: _jsx("path", { d: "M5 12h14M12 5l7 7-7 7" }) })] }))] }));
}
