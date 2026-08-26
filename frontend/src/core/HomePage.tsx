import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const HomePage = () => {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">Добро пожаловать!</CardTitle>
          <CardDescription>
            Это главная страница вашего приложения
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground">
            Здесь может быть список пользователей, дашборд или любое другое содержимое.
          </p>
          <Link to="/auth/register">
            <Button className="w-full">
              Перейти к регистрации
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
};