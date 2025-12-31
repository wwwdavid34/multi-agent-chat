import type { DebateRound, PanelistConfigPayload } from "../types";
interface DebateViewerProps {
    debateHistory: DebateRound[];
    panelists: PanelistConfigPayload[];
    onCopy?: (text: string) => void;
    stepReview?: boolean;
    debatePaused?: boolean;
    onContinue?: () => void;
}
export declare function DebateViewer({ debateHistory, panelists, onCopy, stepReview, debatePaused, onContinue }: DebateViewerProps): import("react/jsx-runtime").JSX.Element | null;
export {};
