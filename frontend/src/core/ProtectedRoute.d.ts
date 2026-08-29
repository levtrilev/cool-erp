type RoleType = "admin" | "superadmin";
interface ProtectedRouteProps {
    children: React.ReactNode;
    requiredRole?: RoleType;
}
export declare const ProtectedRoute: ({ children, requiredRole }: ProtectedRouteProps) => import("react").JSX.Element;
export {};
