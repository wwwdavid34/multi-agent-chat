/**
 * DebateScoreboard - Display debate scores for all panelists
 *
 * Shows cumulative scores, round deltas, and ranking.
 * Updates in real-time via SSE events.
 */

import React from "react";

interface ScoreData {
  cumulative: number;
  roundDelta?: number;
  events?: Array<{
    category: string;
    points: number;
    reason: string;
  }>;
}

interface DebateScoreboardProps {
  scores: Record<string, ScoreData>;
  showDetails?: boolean;
}

export function DebateScoreboard({
  scores,
  showDetails = false,
}: DebateScoreboardProps) {
  if (!scores || Object.keys(scores).length === 0) {
    return null;
  }

  // Sort by cumulative score descending
  const sorted = Object.entries(scores).sort(
    (a, b) => b[1].cumulative - a[1].cumulative
  );

  const leader = sorted[0];
  const maxScore = leader ? leader[1].cumulative : 0;

  return (
    <div className="mb-4 rounded-xl border border-border/50 bg-muted/30 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-foreground">Debate Scores</h4>
        <span className="text-xs text-muted-foreground">
          {sorted.length} panelist{sorted.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="space-y-2">
        {sorted.map(([name, score], index) => {
          const isLeader = index === 0 && score.cumulative > 0;
          const progressPercent =
            maxScore > 0 ? (score.cumulative / maxScore) * 100 : 0;

          return (
            <div key={name} className="relative">
              <div className="flex items-center gap-3">
                {/* Rank badge */}
                <div className="w-6 text-center">
                  {index === 0 && score.cumulative > 0 ? (
                    <span className="text-lg">🥇</span>
                  ) : index === 1 ? (
                    <span className="text-lg">🥈</span>
                  ) : index === 2 ? (
                    <span className="text-lg">🥉</span>
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      {index + 1}
                    </span>
                  )}
                </div>

                {/* Name and score bar */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-sm font-medium truncate ${
                        isLeader ? "text-accent" : "text-foreground"
                      }`}
                    >
                      {name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-foreground">
                        {score.cumulative} pts
                      </span>
                      {score.roundDelta !== undefined && score.roundDelta !== 0 && (
                        <span
                          className={`text-xs font-medium ${
                            score.roundDelta >= 0
                              ? "text-green-500"
                              : "text-red-500"
                          }`}
                        >
                          {score.roundDelta >= 0 ? "+" : ""}
                          {score.roundDelta}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isLeader ? "bg-accent" : "bg-muted-foreground/40"
                      }`}
                      style={{ width: `${Math.max(progressPercent, 2)}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Score events detail (expandable) */}
              {showDetails && score.events && score.events.length > 0 && (
                <div className="mt-2 ml-9 space-y-1">
                  {score.events.slice(-3).map((event, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs text-muted-foreground"
                    >
                      <span
                        className={`px-1.5 py-0.5 rounded ${
                          event.points >= 0
                            ? "bg-green-500/10 text-green-600 dark:text-green-400"
                            : "bg-red-500/10 text-red-600 dark:text-red-400"
                        }`}
                      >
                        {event.points >= 0 ? "+" : ""}
                        {event.points}
                      </span>
                      <span className="truncate">{event.reason}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Scoring legend */}
      <div className="mt-4 pt-3 border-t border-border/30">
        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
          <span>
            <span className="text-green-500">+10</span> address claim
          </span>
          <span>
            <span className="text-green-500">+8</span> evidence
          </span>
          <span>
            <span className="text-green-500">+24</span> user upvote
          </span>
          <span>
            <span className="text-red-500">-10</span> ignore claim
          </span>
        </div>
      </div>
    </div>
  );
}

export default DebateScoreboard;
