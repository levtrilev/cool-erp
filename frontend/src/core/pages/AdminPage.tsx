import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Shield, Users, Factory } from "lucide-react"; // , Settings, Activity, Building
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
            {" "}
            {/* <-- Делаем всю карточку ссылкой */}
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
        <Card>
          <Link to="/admin/tenants" className="block p-6">
            {" "}
            {/* <-- Делаем всю карточку ссылкой */}
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Factory className="h-5 w-5" />
                Организации
              </CardTitle>
              <CardDescription>Настройки доступа</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Конфигурация приложения
              </p>
            </CardContent>
          </Link>
        </Card>

        {/* Карточка 3: Разделы */}
        <Card>
          <Link to="/admin/sections" className="block p-6">
            {" "}
            {/* <-- Делаем всю карточку ссылкой */}
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Factory className="h-5 w-5" />
                Разделы
              </CardTitle>
              <CardDescription>Настройки доступа</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Конфигурация приложения
              </p>
            </CardContent>
          </Link>
        </Card>
      </div>
    </div>
  );
};
