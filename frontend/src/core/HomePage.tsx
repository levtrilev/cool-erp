import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const HomePage = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Добро пожаловать!</h1>
        <p className="text-muted-foreground mt-2">
          Это главная страница вашего приложения
        </p>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Начало работы</CardTitle>
          <CardDescription>
            Здесь может быть дашборд, список задач или любое другое содержимое
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Используйте меню в верхней части страницы для навигации.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};