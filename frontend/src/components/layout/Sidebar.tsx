import { useState } from "react";
import { NavLink } from "react-router-dom";
import { ChevronDown, ChevronRight } from "lucide-react";
// import { ChevronDown, ChevronRight, FileText, Database, Settings, Users, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { MENU_CONFIG } from "@/lib/menuConfig";
import type { MenuItem } from "@/lib/menuConfig";

interface SidebarProps {
  className?: string;
}

export const Sidebar = ({ className }: SidebarProps) => {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set(["nsi"]));

  const toggleItem = (itemId: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }
    setExpandedItems(newExpanded);
  };

  const renderMenuItem = (item: MenuItem, depth: number = 0) => {
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.has(item.id);
    const Icon = item.icon;

    if (hasChildren) {
      return (
        <div key={item.id}>
          <button
            onClick={() => toggleItem(item.id)}
            className={cn(
              "flex items-center w-full px-3 py-2 text-sm font-medium rounded-md transition-colors",
              "hover:bg-accent hover:text-accent-foreground",
              depth > 0 && "ml-4"
            )}
          >
            <span className="flex items-center gap-2 flex-1">
              {Icon && <Icon className="h-4 w-4" />}
              {item.label}
            </span>
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 transition-transform" />
            ) : (
              <ChevronRight className="h-4 w-4 transition-transform" />
            )}
          </button>
          
          {isExpanded && item.children && (
            <div className="mt-1 space-y-1">
              {item.children.map((child) => renderMenuItem(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    return (
      <NavLink
        key={item.id}
        to={item.path || "#"}
        className={({ isActive }) =>
          cn(
            "flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
            depth > 0 && "ml-4",
            isActive
              ? "bg-primary text-primary-foreground"
              : "hover:bg-accent hover:text-accent-foreground"
          )
        }
      >
        <span className="flex items-center gap-2">
          {item.icon && <item.icon className="h-4 w-4" />}
          {item.label}
        </span>
      </NavLink>
    );
  };

  return (
    <aside className={cn("w-64 bg-card border-r border-border flex flex-col", className)}>
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-bold text-foreground">Cool ERP</h1>
      </div>
      
      <nav className="flex-1 overflow-y-auto p-2">
        {MENU_CONFIG.map((item) => renderMenuItem(item))}
      </nav>
    </aside>
  );
};