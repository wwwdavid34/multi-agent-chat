import type { DebateRound, PanelistConfigPayload } from "../types";
interface DebateViewerProps {
    debateHistory: DebateRound[];
    panelists: PanelistConfigPayload[];
    onCopy?: (text: string) => void;
    stepReview?: boolean;
    debatePaused?: boolean;
    onContinue?: () => void;
    tagged_panelists?: string[];
    user_as_participant?: boolean;
}
export declare function DebateViewer({ debateHistory, panelists, onCopy, stepReview, debatePaused, onContinue, tagged_panelists, user_as_participant }: DebateViewerProps): import("react/jsx-runtime").JSX.Element | null;
export {};
