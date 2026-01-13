import React, { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Markdown } from "./Markdown";
import type { DebateRound, PanelistConfigPayload } from "../types";
import { PROVIDER_LABELS } from "../lib/modelProviders";
import { DebateScoreboard } from "./DebateScoreboard";
import { StanceIndicator } from "./StanceIndicator";

interface ScoreData {
  cumulative: number;
  roundDelta?: number;
  events?: Array<{
    category: string;
    points: number;
    reason: string;
  }>;
}

interface StanceData {
  stance: string;
  confidence: number;
  changed_from_previous?: boolean;
  core_claim?: string;
}

interface DebateViewerProps {
  debateHistory: DebateRound[];
  panelists: PanelistConfigPayload[];
  onCopy?: (text: string) => void;
  stepReview?: boolean;
  debatePaused?: boolean;
  onContinue?: () => void;
  tagged_panelists?: string[];
  user_as_participant?: boolean;
  scores?: Record<string, ScoreData>;
  onVote?: (panelistName: string, roundNumber: number, voteType: "compelling" | "weak") => void;
}

export function DebateViewer({
  debateHistory,
  panelists,
  onCopy,
  stepReview = false,
  debatePaused = false,
  onContinue,
  tagged_panelists = [],
  user_as_participant = false,
  scores,
  onVote,
}: DebateViewerProps) {
  const [expandedRounds, setExpandedRounds] = useState<Set<number>>(() => {
    // Auto-expand the first round initially
    if (debateHistory.length > 0) {
      return new Set([debateHistory[0].round_number]);
    }
    return new Set();
  });

  // Extract latest stances from debate history
  const latestStances = useMemo<Record<string, StanceData>>(() => {
    if (debateHistory.length === 0) return {};
    const latestRound = debateHistory[debateHistory.length - 1];
    if (!latestRound.stances) return {};

    const result: Record<string, StanceData> = {};
    for (const [name, stance] of Object.entries(latestRound.stances)) {
      if (stance && typeof stance === "object") {
        result[name] = {
          stance: (stance as any).stance || "NEUTRAL",
          confidence: (stance as any).confidence || 0.5,
          changed_from_previous: (stance as any).changed_from_previous || false,
          core_claim: (stance as any).core_claim,
        };
      }
    }
    return result;
  }, [debateHistory]);

  // Calculate scores from debate history if not provided
  const computedScores = useMemo<Record<string, ScoreData>>(() => {
    if (scores && Object.keys(scores).length > 0) return scores;
    if (debateHistory.length === 0) return {};

    const result: Record<string, ScoreData> = {};
    const latestRound = debateHistory[debateHistory.length - 1];

    if (latestRound.scores) {
      for (const [name, scoreData] of Object.entries(latestRound.scores)) {
        if (scoreData && typeof scoreData === "object") {
          result[name] = {
            cumulative: (scoreData as any).cumulative_total || 0,
            roundDelta: (scoreData as any).round_total || 0,
            events: (scoreData as any).events || [],
          };
        }
      }
    }
    return result;
  }, [debateHistory, scores]);

  // When new rounds arrive, auto-expand the latest one
  useEffect(() => {
    if (debateHistory.length > 0) {
      const latestRound = debateHistory[debateHistory.length - 1];
      setExpandedRounds(new Set([latestRound.round_number]));
    }
  }, [debateHistory.length]);

  const toggleRound = (roundNumber: number) => {
    setExpandedRounds((prev) => {
      const next = new Set(prev);
      if (next.has(roundNumber)) {
        next.delete(roundNumber);
      } else {
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
  // BUT not in stepReview mode - App.tsx has its own user input area at the bottom
  const showContinueButton = debatePaused && onContinue && !stepReview;

  return (
    <div className="mt-6 space-y-3">
      {/* Scoreboard and Stance Indicator */}
      {Object.keys(computedScores).length > 0 && (
        <DebateScoreboard scores={computedScores} showDetails={stepReview} />
      )}
      {Object.keys(latestStances).length > 0 && (
        <StanceIndicator stances={latestStances} showClaims={stepReview} />
      )}

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            <path d="M8 10h.01M12 10h.01M16 10h.01" />
          </svg>
          <span className="font-medium">
            Debate Rounds ({roundsToShow.length}{stepReview ? ` of ${debateHistory.length}` : ''})
          </span>
        </div>
        {stepReview && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent/10 text-accent font-medium">
            Step Review Mode
          </span>
        )}
      </div>

      <div className="space-y-2">
        {roundsToShow.map((round) => {
          const isExpanded = expandedRounds.has(round.round_number);
          const isLatest = round.round_number === debateHistory[debateHistory.length - 1].round_number;

          return (
            <div
              key={round.round_number}
              className={`rounded-lg border transition-all ${
                isLatest
                  ? "border-accent/40 bg-accent/5"
                  : "border-border/40 bg-muted/10"
              }`}
            >
              {/* Round header */}
              <button
                type="button"
                onClick={() => toggleRound(round.round_number)}
                className="w-full flex items-center justify-between p-3 text-left hover:bg-muted/20 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                      isLatest
                        ? "bg-accent/20 text-accent"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {round.round_number + 1}
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-foreground">
                      Round {round.round_number + 1}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {Object.keys(round.panel_responses).length} responses
                      {round.consensus_reached && (
                        <span className="ml-2 inline-flex items-center gap-1 text-accent">
                          <svg viewBox="0 0 24 24" className="w-3 h-3" fill="currentColor">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                          </svg>
                          Consensus
                        </span>
                      )}
                    </span>
                  </div>
                </div>
                <svg
                  viewBox="0 0 24 24"
                  className={`w-5 h-5 text-muted-foreground transition-transform ${
                    isExpanded ? "rotate-180" : ""
                  }`}
                  fill="currentColor"
                >
                  <path d="M7 10l5 5 5-5z" />
                </svg>
              </button>

              {/* Round content */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="border-t border-border/30"
                  >
                    <div className="p-4 space-y-3">
                      {/* User message in user-debate mode */}
                      {user_as_participant && round.user_message && (
                        <div className="rounded-lg border border-accent/30 bg-accent/5 p-3">
                          <div className="flex items-center gap-2 mb-2">
                            <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center text-accent font-semibold text-xs">
                              U
                            </div>
                            <span className="text-xs font-semibold text-foreground">You</span>
                          </div>
                          <div className="text-xs leading-relaxed text-muted-foreground prose prose-sm dark:prose-invert max-w-none">
                            <Markdown content={round.user_message} />
                          </div>
                        </div>
                      )}

                      {Object.entries(round.panel_responses)
                        .filter(([_, response]) => response && typeof response === 'string' && response.trim())
                        .map(([name, response]) => {
                        const panelist = panelists.find((p) => p.name === name);
                        // Case-insensitive check for @mentions
                        const isTagged = tagged_panelists.some(tag => tag.toLowerCase() === name.toLowerCase());
                        // Check if ANY tagged panelist matches a real panelist (otherwise ignore tags)
                        const panelistNames = Object.keys(round.panel_responses);
                        const hasValidTags = tagged_panelists.some(tag =>
                          panelistNames.some(pName => pName.toLowerCase() === tag.toLowerCase())
                        );
                        // Only show "watching" if valid @mentions exist AND this panelist wasn't mentioned
                        const isWatching = user_as_participant && hasValidTags && !isTagged;

                        // Get stance for this panelist in this round
                        const panelistStance = round.stances?.[name];
                        const stanceValue = panelistStance && typeof panelistStance === 'object'
                          ? (panelistStance as any).stance
                          : null;

                        // Stance badge styling
                        const getStanceBadge = (stance: string | null) => {
                          if (!stance) return null;
                          const styles: Record<string, string> = {
                            'FOR': 'bg-green-500/15 text-green-600 dark:text-green-400 border-green-500/30',
                            'AGAINST': 'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30',
                            'NEUTRAL': 'bg-gray-500/15 text-gray-600 dark:text-gray-400 border-gray-500/30',
                          };
                          return styles[stance] || styles['NEUTRAL'];
                        };

                        return (
                          <div
                            key={name}
                            className={`rounded-lg border p-3 transition-colors group/response ${
                              isWatching
                                ? "border-border/20 bg-muted/5"
                                : "border-border/30 bg-background hover:bg-muted/20"
                            }`}
                          >
                            <div className="flex items-center justify-between gap-3 mb-2">
                              <div className="flex items-center gap-2">
                                <div className={`w-6 h-6 rounded-full flex items-center justify-center font-semibold text-xs ${
                                  isWatching
                                    ? "bg-muted text-muted-foreground"
                                    : "bg-accent/10 text-accent"
                                }`}>
                                  {name.charAt(0).toUpperCase()}
                                </div>
                                <div className="flex flex-col">
                                  <div className="flex items-center gap-2">
                                    <span className={`text-xs font-semibold ${
                                      isWatching ? "text-muted-foreground" : "text-foreground"
                                    }`}>
                                      {name}
                                    </span>
                                    {stanceValue && (
                                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${getStanceBadge(stanceValue)}`}>
                                        {stanceValue}
                                      </span>
                                    )}
                                  </div>
                                  {panelist && (
                                    <span className="text-[10px] text-muted-foreground">
                                      {PROVIDER_LABELS[panelist.provider]} · {panelist.model}
                                    </span>
                                  )}
                                </div>
                              </div>
                              {!isWatching && onCopy && (
                                <button
                                  type="button"
                                  onClick={() => onCopy(response)}
                                  className="opacity-0 group-hover/response:opacity-100 p-1.5 rounded hover:bg-muted/40 transition-all"
                                  title="Copy response"
                                >
                                  <svg
                                    viewBox="0 0 24 24"
                                    className="w-3.5 h-3.5 text-muted-foreground"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                  >
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                  </svg>
                                </button>
                              )}
                            </div>
                            {isWatching ? (
                              <div className="text-xs italic text-muted-foreground">
                                Watching this discussion...
                              </div>
                            ) : (
                              <div className="text-xs leading-relaxed text-muted-foreground prose prose-sm dark:prose-invert max-w-none">
                                <Markdown content={response} />
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>

      {/* Continue to Next Round button - triggers backend to run next round */}
      {showContinueButton && (
        <motion.button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('[DebateViewer] Continue debate clicked - triggering next round');
            onContinue();
          }}
          className="w-full mt-4 px-4 py-3 rounded-lg bg-accent text-accent-foreground font-medium text-sm hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <span>Continue to Round {debateHistory.length + 1}</span>
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </motion.button>
      )}
    </div>
  );
}
