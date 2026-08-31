interface CreateUserModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onUserCreated: (id: string) => Promise<unknown>;
}
export declare const CreateUserModal: ({ open, onOpenChange, onUserCreated, }: CreateUserModalProps) => import("react").JSX.Element;
export {};
