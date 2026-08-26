// import { useNavigate } from "react-router-dom";
import { UserRegisterForm } from "@/core/auth/UserRegisterForm";

export const RegisterPage = () => {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <UserRegisterForm />
    </div>
  );
};