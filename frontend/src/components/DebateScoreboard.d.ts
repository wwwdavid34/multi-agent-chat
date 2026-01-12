/**
 * DebateScoreboard - Display debate scores for all panelists
 *
 * Shows cumulative scores, round deltas, and ranking.
 * Updates in real-time via SSE events.
 */
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
export declare function DebateScoreboard({ scores, showDetails, }: DebateScoreboardProps): import("react/jsx-runtime").JSX.Element | null;
export default DebateScoreboard;
