import { z } from "zod";
import { readUsersAuthGetResponse } from "@/api/generated/zod/authentication/authentication.schema";
type UserResponseSchema = z.infer<typeof readUsersAuthGetResponse>["items"][number];
interface EditUserModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    user: UserResponseSchema | null;
    onUserUpdated: () => void;
}
export declare const EditUserModal: ({ open, onOpenChange, user, onUserUpdated }: EditUserModalProps) => import("react").JSX.Element;
export {};
