import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface RegenerateModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (debateMode: boolean, maxDebateRounds: number, stepReview: boolean) => void;
  defaultDebateMode?: boolean;
  defaultMaxRounds?: number;
  defaultStepReview?: boolean;
}

export function RegenerateModal({
  open,
  onClose,
  onConfirm,
  defaultDebateMode = false,
  defaultMaxRounds = 3,
  defaultStepReview = false,
}: RegenerateModalProps) {
  const [debateMode, setDebateMode] = useState(defaultDebateMode);
  const [maxDebateRounds, setMaxDebateRounds] = useState(defaultMaxRounds);
  const [stepReview, setStepReview] = useState(defaultStepReview);

  const handleConfirm = () => {
    onConfirm(debateMode, maxDebateRounds, stepReview);
    onClose();
  };

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 backdrop-blur-sm p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="bg-background text-foreground rounded-2xl shadow-2xl max-w-md w-full border border-border"
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-5 h-5 text-accent" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6m6 0a9 9 0 0 1-15-6.7L3 16" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-semibold m-0">Regenerate Response</h2>
                <p className="text-xs text-muted-foreground mt-0.5">Choose settings for this regeneration</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg w-8 h-8 border border-border flex items-center justify-center hover:bg-muted transition-colors text-lg"
              aria-label="Close"
            >
              ×
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-5">
            {/* Debate Mode Toggle */}
            <div className="rounded-lg border border-border p-4 bg-card">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold m-0">Enable Debate Mode</h4>
                  <p className="text-xs text-muted-foreground mt-1">
                    Agents will debate until consensus or max rounds
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={debateMode}
                    onChange={(e) => setDebateMode(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-accent/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent"></div>
                </label>
              </div>
            </div>

            {/* Max Debate Rounds (only shown when debate mode is enabled) */}
            <AnimatePresence>
              {debateMode && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="rounded-lg border border-border p-4 bg-card overflow-hidden"
                >
                  <label className="block">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="text-sm font-semibold m-0">Maximum Debate Rounds</h4>
                        <p className="text-xs text-muted-foreground mt-1">
                          Limit debate iterations (1-10 rounds)
                        </p>
                      </div>
                      <span className="text-lg font-bold text-accent">{maxDebateRounds}</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={maxDebateRounds}
                      onChange={(e) => setMaxDebateRounds(Number(e.target.value))}
                      className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-accent"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-2">
                      <span>1 round</span>
                      <span>10 rounds</span>
                    </div>
                  </label>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Step Review Mode (only shown when debate mode is enabled) */}
            <AnimatePresence>
              {debateMode && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="rounded-lg border border-border p-4 bg-card overflow-hidden"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold m-0">Enable Step Review Mode</h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        Reveal debate rounds one at a time
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={stepReview}
                        onChange={(e) => setStepReview(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-accent/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent"></div>
                    </label>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Info box */}
            <div className="rounded-lg border border-accent/20 bg-accent/5 p-3">
              <p className="text-xs text-muted-foreground m-0">
                {debateMode
                  ? `The panel will debate for up to ${maxDebateRounds} round${maxDebateRounds > 1 ? 's' : ''} or until consensus is reached.${stepReview ? ' Rounds will be revealed step-by-step.' : ''}`
                  : "The panel will provide immediate responses without debate."}
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-6 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              className="px-4 py-2 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6m6 0a9 9 0 0 1-15-6.7L3 16" />
              </svg>
              Regenerate
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
