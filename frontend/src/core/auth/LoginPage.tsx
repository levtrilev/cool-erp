import { UserLoginForm } from "@/core/auth/UserLoginForm";

export const LoginPage = () => {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <UserLoginForm />
    </div>
  );
};