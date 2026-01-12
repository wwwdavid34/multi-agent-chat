/**
 * StanceIndicator - Display panelist stances at a glance
 *
 * Shows each panelist's current position (FOR/AGAINST/NEUTRAL/CONDITIONAL)
 * with confidence levels and change indicators.
 */

import React from "react";

interface StanceData {
  stance: string; // 'FOR', 'AGAINST', 'CONDITIONAL', 'NEUTRAL'
  confidence: number; // 0.0-1.0
  changed_from_previous?: boolean;
  core_claim?: string;
}

interface StanceIndicatorProps {
  stances: Record<string, StanceData>;
  showClaims?: boolean;
}

const stanceColors: Record<string, { bg: string; text: string; border: string }> = {
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

const stanceIcons: Record<string, string> = {
  FOR: "👍",
  AGAINST: "👎",
  CONDITIONAL: "⚖️",
  NEUTRAL: "🤔",
};

export function StanceIndicator({
  stances,
  showClaims = false,
}: StanceIndicatorProps) {
  if (!stances || Object.keys(stances).length === 0) {
    return null;
  }

  return (
    <div className="mb-4 rounded-xl border border-border/50 bg-muted/30 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-foreground">
          Current Stances
        </h4>
        <span className="text-xs text-muted-foreground">
          {Object.keys(stances).length} panelist
          {Object.keys(stances).length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.entries(stances).map(([name, stance]) => {
          const colors = stanceColors[stance.stance] || stanceColors.NEUTRAL;
          const icon = stanceIcons[stance.stance] || "🤔";
          const confidencePercent = Math.round(stance.confidence * 100);

          return (
            <div
              key={name}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${colors.bg} ${colors.border}`}
              title={stance.core_claim || `${name}: ${stance.stance}`}
            >
              <span className="text-base">{icon}</span>

              <div className="flex flex-col">
                <span className={`text-sm font-medium ${colors.text}`}>
                  {name}
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground uppercase">
                    {stance.stance}
                  </span>
                  <span className="text-xs text-muted-foreground/70">
                    {confidencePercent}%
                  </span>
                  {stance.changed_from_previous && (
                    <span
                      className="text-xs text-amber-500"
                      title="Changed from previous round"
                    >
                      ↻
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Show core claims if enabled */}
      {showClaims && (
        <div className="mt-3 pt-3 border-t border-border/30 space-y-2">
          {Object.entries(stances)
            .filter(([_, s]) => s.core_claim)
            .map(([name, stance]) => (
              <div key={name} className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{name}:</span>{" "}
                {stance.core_claim}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

export default StanceIndicator;
