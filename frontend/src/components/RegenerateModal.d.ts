interface RegenerateModalProps {
    open: boolean;
    onClose: () => void;
    onConfirm: (debateMode: boolean, maxDebateRounds: number, stepReview: boolean) => void;
    defaultDebateMode?: boolean;
    defaultMaxRounds?: number;
    defaultStepReview?: boolean;
}
export declare function RegenerateModal({ open, onClose, onConfirm, defaultDebateMode, defaultMaxRounds, defaultStepReview, }: RegenerateModalProps): import("react/jsx-runtime").JSX.Element | null;
export {};
