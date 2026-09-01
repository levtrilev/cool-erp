import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ShieldCheck, Database, Server } from "lucide-react";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";

export const SuperAdminPage = () => {
  const { data: userData } = useGetUserAuthUserGet();

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <ShieldCheck className="h-8 w-8 text-primary" />
          Панель супер-администратора
        </h1>
        <p className="text-muted-foreground mt-2">
          Добро пожаловать, {userData?.data?.name}!
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Карточка 1: Тенанты */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Тенанты
            </CardTitle>
            <CardDescription>
              Управление тенантами
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Создание и управление тенантами системы
            </p>
          </CardContent>
        </Card>

        {/* Карточка 2: Системные настройки */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Системные настройки
            </CardTitle>
            <CardDescription>
              Глобальные настройки
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Конфигурация всей системы
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};