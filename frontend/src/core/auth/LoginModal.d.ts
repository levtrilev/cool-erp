interface LoginModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSwitchToRegister: () => void;
}
export declare const LoginModal: ({ open, onOpenChange, onSwitchToRegister, }: LoginModalProps) => import("react").JSX.Element;
export {};
