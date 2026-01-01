import { ReactNode } from "react";
interface RegenerateModalProps {
    open: boolean;
    onClose: () => void;
    onConfirm: (debateMode: boolean, maxDebateRounds: number, stepReview: boolean) => void;
    defaultDebateMode?: boolean;
    defaultMaxRounds?: number;
    defaultStepReview?: boolean;
    title?: string;
    subtitle?: string;
    confirmLabel?: string;
    headerIcon?: ReactNode;
    confirmIcon?: ReactNode;
}
export declare function RegenerateModal({ open, onClose, onConfirm, defaultDebateMode, defaultMaxRounds, defaultStepReview, title, subtitle, confirmLabel, headerIcon, confirmIcon, }: RegenerateModalProps): import("react/jsx-runtime").JSX.Element | null;
export {};
