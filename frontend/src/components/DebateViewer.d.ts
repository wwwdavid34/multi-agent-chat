import type { DebateRound, PanelistConfigPayload } from "../types";
interface ScoreData {
    cumulative: number;
    roundDelta?: number;
    events?: Array<{
        category: string;
        points: number;
        reason: string;
    }>;
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
export declare function DebateViewer({ debateHistory, panelists, onCopy, stepReview, debatePaused, onContinue, tagged_panelists, user_as_participant, scores, onVote, }: DebateViewerProps): import("react/jsx-runtime").JSX.Element | null;
export {};
