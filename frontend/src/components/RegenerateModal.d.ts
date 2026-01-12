import { ReactNode } from "react";
import type { DebateMode } from "../types";
interface RegenerateModalProps {
    open: boolean;
    onClose: () => void;
    onConfirm: (debateMode: DebateMode | undefined, maxDebateRounds: number) => void;
    defaultDebateMode?: DebateMode;
    defaultMaxRounds?: number;
    title?: string;
    subtitle?: string;
    confirmLabel?: string;
    headerIcon?: ReactNode;
    confirmIcon?: ReactNode;
}
export declare function RegenerateModal({ open, onClose, onConfirm, defaultDebateMode, defaultMaxRounds, title, subtitle, confirmLabel, headerIcon, confirmIcon, }: RegenerateModalProps): import("react/jsx-runtime").JSX.Element | null;
export {};
