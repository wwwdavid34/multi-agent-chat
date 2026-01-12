import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const stanceColors = {
    FOR: {
        bg: "bg-green-500/10",
        text: "text-green-600 dark:text-green-400",
        border: "border-green-500/30",
    },
    AGAINST: {
        bg: "bg-red-500/10",
        text: "text-red-600 dark:text-red-400",
        border: "border-red-500/30",
    },
    CONDITIONAL: {
        bg: "bg-yellow-500/10",
        text: "text-yellow-600 dark:text-yellow-400",
        border: "border-yellow-500/30",
    },
    NEUTRAL: {
        bg: "bg-gray-500/10",
        text: "text-gray-600 dark:text-gray-400",
        border: "border-gray-500/30",
    },
};
const stanceIcons = {
    FOR: "👍",
    AGAINST: "👎",
    CONDITIONAL: "⚖️",
    NEUTRAL: "🤔",
};
export function StanceIndicator({ stances, showClaims = false, }) {
    if (!stances || Object.keys(stances).length === 0) {
        return null;
    }
    return (_jsxs("div", { className: "mb-4 rounded-xl border border-border/50 bg-muted/30 p-4", children: [_jsxs("div", { className: "flex items-center justify-between mb-3", children: [_jsx("h4", { className: "text-sm font-semibold text-foreground", children: "Current Stances" }), _jsxs("span", { className: "text-xs text-muted-foreground", children: [Object.keys(stances).length, " panelist", Object.keys(stances).length !== 1 ? "s" : ""] })] }), _jsx("div", { className: "flex flex-wrap gap-2", children: Object.entries(stances).map(([name, stance]) => {
                    const colors = stanceColors[stance.stance] || stanceColors.NEUTRAL;
                    const icon = stanceIcons[stance.stance] || "🤔";
                    const confidencePercent = Math.round(stance.confidence * 100);
                    return (_jsxs("div", { className: `flex items-center gap-2 px-3 py-2 rounded-lg border ${colors.bg} ${colors.border}`, title: stance.core_claim || `${name}: ${stance.stance}`, children: [_jsx("span", { className: "text-base", children: icon }), _jsxs("div", { className: "flex flex-col", children: [_jsx("span", { className: `text-sm font-medium ${colors.text}`, children: name }), _jsxs("div", { className: "flex items-center gap-1.5", children: [_jsx("span", { className: "text-xs text-muted-foreground uppercase", children: stance.stance }), _jsxs("span", { className: "text-xs text-muted-foreground/70", children: [confidencePercent, "%"] }), stance.changed_from_previous && (_jsx("span", { className: "text-xs text-amber-500", title: "Changed from previous round", children: "\u21BB" }))] })] })] }, name));
                }) }), showClaims && (_jsx("div", { className: "mt-3 pt-3 border-t border-border/30 space-y-2", children: Object.entries(stances)
                    .filter(([_, s]) => s.core_claim)
                    .map(([name, stance]) => (_jsxs("div", { className: "text-xs text-muted-foreground", children: [_jsxs("span", { className: "font-medium text-foreground", children: [name, ":"] }), " ", stance.core_claim] }, name))) }))] }));
}
export default StanceIndicator;
