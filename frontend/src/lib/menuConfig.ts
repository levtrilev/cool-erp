import { FileText, Database, Settings, Users, Building2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface MenuItem {
  id: string;
  label: string;
  path?: string;
  icon?: LucideIcon;
  children?: MenuItem[];
  requiresAdmin?: boolean;
}

export const MENU_CONFIG: MenuItem[] = [
  {
    id: "nsi",
    label: "НСИ",
    icon: Database,
    children: [
      {
        id: "notes",
        label: "Заметки",
        path: "/notes",
        icon: FileText,
      },
      // Здесь будут добавлены другие пункты НСИ:
      // { id: "organizations", label: "Организации", path: "/organizations", icon: Building2 },
      // { id: "sections", label: "Разделы", path: "/sections", icon: Folder },
    ],
  },
  {
    id: "admin",
    label: "Администрирование",
    icon: Settings,
    requiresAdmin: true,
    children: [
      {
        id: "users",
        label: "Пользователи",
        path: "/users",
        icon: Users,
      },
      {
        id: "tenants",
        label: "Организации",
        path: "/tenants",
        icon: Building2,
      },
    ],
  },
];

// Функция для получения плоского списка всех путей (для активной навигации)
export const getAllPaths = (items: MenuItem[] = MENU_CONFIG): string[] => {
  const paths: string[] = [];
  
  const traverse = (item: MenuItem) => {
    if (item.path) {
      paths.push(item.path);
    }
    if (item.children) {
      item.children.forEach(traverse);
    }
  };
  
  items.forEach(traverse);
  return paths;
};