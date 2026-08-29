import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LayoutDashboard, TrendingUp, Clock } from "lucide-react";

export const DashboardPage = () => {
  const { data: userData } = useGetUserAuthUserGet();

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <LayoutDashboard className="h-8 w-8 text-primary" />
          Панель управления
        </h1>
        <p className="text-muted-foreground mt-2">
          Добро пожаловать, {userData?.data?.name}!
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Статистика
            </CardTitle>
            <CardDescription>Обзор вашей активности</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">0</p>
            <p className="text-sm text-muted-foreground">Активных проектов</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Последние действия
            </CardTitle>
            <CardDescription>Ваша недавняя активность</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Пока нет действий</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};