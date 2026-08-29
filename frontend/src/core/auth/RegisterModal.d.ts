interface RegisterModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSwitchToLogin: () => void;
}
export declare const RegisterModal: ({ open, onOpenChange, onSwitchToLogin }: RegisterModalProps) => import("react").JSX.Element;
export {};
