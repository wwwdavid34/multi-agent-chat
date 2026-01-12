/**
 * StanceIndicator - Display panelist stances at a glance
 *
 * Shows each panelist's current position (FOR/AGAINST/NEUTRAL/CONDITIONAL)
 * with confidence levels and change indicators.
 */
interface StanceData {
    stance: string;
    confidence: number;
    changed_from_previous?: boolean;
    core_claim?: string;
}
interface StanceIndicatorProps {
    stances: Record<string, StanceData>;
    showClaims?: boolean;
}
export declare function StanceIndicator({ stances, showClaims, }: StanceIndicatorProps): import("react/jsx-runtime").JSX.Element | null;
export default StanceIndicator;
