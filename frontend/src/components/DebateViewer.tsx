import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Markdown } from "./Markdown";
import type { DebateRound, PanelistConfigPayload } from "../types";
import { PROVIDER_LABELS } from "../lib/modelProviders";

interface DebateViewerProps {
  debateHistory: DebateRound[];
  panelists: PanelistConfigPayload[];
  onCopy?: (text: string) => void;
  stepReview?: boolean;
  debatePaused?: boolean;
  onContinue?: () => void;
}

export function DebateViewer({ debateHistory, panelists, onCopy, stepReview = false, debatePaused = false, onContinue }: DebateViewerProps) {
  const [expandedRounds, setExpandedRounds] = useState<Set<number>>(() => {
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
  const showContinueButton = debatePaused && onContinue;

  return (
    <div className="mt-6 space-y-3">
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
                      {Object.entries(round.panel_responses)
                        .filter(([_, response]) => response && typeof response === 'string' && response.trim())
                        .map(([name, response]) => {
                        const panelist = panelists.find((p) => p.name === name);
                        return (
                          <div
                            key={name}
                            className="rounded-lg border border-border/30 p-3 bg-background hover:bg-muted/20 transition-colors group/response"
                          >
                            <div className="flex items-center justify-between gap-3 mb-2">
                              <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded-full bg-accent/10 flex items-center justify-center text-accent font-semibold text-xs">
                                  {name.charAt(0).toUpperCase()}
                                </div>
                                <div className="flex flex-col">
                                  <span className="text-xs font-semibold text-foreground">
                                    {name}
                                  </span>
                                  {panelist && (
                                    <span className="text-[10px] text-muted-foreground">
                                      {PROVIDER_LABELS[panelist.provider]} · {panelist.model}
                                    </span>
                                  )}
                                </div>
                              </div>
                              {onCopy && (
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
                            <div className="text-xs leading-relaxed text-muted-foreground prose prose-sm dark:prose-invert max-w-none">
                              <Markdown content={response} />
                            </div>
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
