import { ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  type DiscussionModeId,
  getModeConfig,
  getModeIconPath,
} from "../lib/discussionModes";

interface RegenerateModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (modeId: DiscussionModeId) => void;
  /** The locked mode for this conversation */
  modeId?: DiscussionModeId;
  title?: string;
  subtitle?: string;
  confirmLabel?: string;
  headerIcon?: ReactNode;
  confirmIcon?: ReactNode;
}

function ModeIcon({
  icon,
  className = "w-4 h-4",
}: {
  icon: string;
  className?: string;
}) {
  const path = getModeIconPath(icon);
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={path} />
    </svg>
  );
}

export function RegenerateModal({
  open,
  onClose,
  onConfirm,
  modeId = "panel",
  title = "Regenerate Response",
  subtitle = "Re-run this question with the same mode",
  confirmLabel = "Regenerate",
  headerIcon,
  confirmIcon,
}: RegenerateModalProps) {
  const modeConfig = getModeConfig(modeId);

  const handleConfirm = () => {
    onConfirm(modeId);
    onClose();
  };

  if (!open) return null;

  const defaultRegenerateIcon = (
    <svg viewBox="0 0 24 24" className="w-5 h-5 text-accent" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 12a8 8 0 0 1 8-8 8 8 0 0 1 6.18 2.82l2.82-2.82M20 4v6h-6M20 12a8 8 0 0 1-8 8 8 8 0 0 1-6.18-2.82l-2.82 2.82M4 20v-6h6" />
    </svg>
  );

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
          className="bg-background text-foreground rounded-2xl shadow-2xl max-w-sm w-full border border-border"
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
                {headerIcon ?? defaultRegenerateIcon}
              </div>
              <div>
                <h2 className="text-lg font-semibold m-0">{title}</h2>
                <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
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

          {/* Content — show current mode info */}
          <div className="p-6">
            {modeConfig && (
              <div className="flex items-center gap-3 p-3 rounded-lg border border-accent/30 bg-accent/5">
                <div className="w-8 h-8 rounded-lg bg-accent/20 text-accent flex items-center justify-center flex-shrink-0">
                  <ModeIcon icon={modeConfig.icon} className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-medium">{modeConfig.name}</div>
                  <div className="text-xs text-muted-foreground">{modeConfig.description}</div>
                </div>
              </div>
            )}
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
              {confirmIcon ?? (
                <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 12a8 8 0 0 1 8-8 8 8 0 0 1 6.18 2.82l2.82-2.82M20 4v6h-6M20 12a8 8 0 0 1-8 8 8 8 0 0 1-6.18-2.82l-2.82 2.82M4 20v-6h6" />
                </svg>
              )}
              {confirmLabel}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
