import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Shield, Users, Factory, ShieldCheck } from "lucide-react";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import { Link } from "react-router-dom";

export const AdminPage = () => {
  const { data: userData } = useGetUserAuthUserGet();

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Shield className="h-8 w-8 text-primary" />
          Админ-панель
        </h1>
        <p className="text-muted-foreground mt-2">
          Добро пожаловать, {userData?.data?.name}!
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Карточка 1: Пользователи */}
        <Card className="hover:shadow-md transition-shadow cursor-pointer">
          <Link to="/admin/users" className="block p-6">
            <CardHeader className="p-0 mb-4">
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Пользователи
              </CardTitle>
              <CardDescription>
                Управление пользователями системы
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <p className="text-sm text-muted-foreground">
                Просмотр, поиск и удаление пользователей
              </p>
            </CardContent>
          </Link>
        </Card>

        {/* Карточка 2: Организации */}
        <Card className="hover:shadow-md transition-shadow cursor-pointer">
          <Link to="/admin/tenants" className="block p-6">
            <CardHeader className="p-0 mb-4">
              <CardTitle className="flex items-center gap-2">
                <Factory className="h-5 w-5" />
                Организации
              </CardTitle>
              <CardDescription>Управление тенантами</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <p className="text-sm text-muted-foreground">
                Создание и настройка организаций
              </p>
            </CardContent>
          </Link>
        </Card>

        {/* Карточка 3: Разделы */}
        <Card className="hover:shadow-md transition-shadow cursor-pointer">
          <Link to="/admin/sections" className="block p-6">
            <CardHeader className="p-0 mb-4">
              <CardTitle className="flex items-center gap-2">
                <Factory className="h-5 w-5" />
                Разделы
              </CardTitle>
              <CardDescription>Структура системы</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <p className="text-sm text-muted-foreground">
                Управление разделами внутри организаций
              </p>
            </CardContent>
          </Link>
        </Card>

        {/* Карточка 4: Роли (НОВАЯ) */}
        <Card className="hover:shadow-md transition-shadow cursor-pointer">
          <Link to="/admin/roles" className="block p-6">
            <CardHeader className="p-0 mb-4">
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5" />
                Роли
              </CardTitle>
              <CardDescription>Управление доступом (RBAC)</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <p className="text-sm text-muted-foreground">
                Настройка матрицы прав, разделов и пользователей
              </p>
            </CardContent>
          </Link>
        </Card>
      </div>
    </div>
  );
};