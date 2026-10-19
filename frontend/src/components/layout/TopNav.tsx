import { useState, useRef, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { ChevronDown } from "lucide-react";
// import { ChevronDown, Database, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { MENU_CONFIG } from "@/lib/menuConfig";
import type { MenuItem } from "@/lib/menuConfig";

interface TopNavProps {
  className?: string;
}

export const TopNav = ({ className }: TopNavProps) => {
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Закрытие дропдауна при клике вне его
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdown(null);
      }
    };
    
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const renderMenuItem = (item: MenuItem) => {
    const hasChildren = item.children && item.children.length > 0;
    const isOpen = openDropdown === item.id;
    const Icon = item.icon;

    if (hasChildren) {
      return (
        <div key={item.id} className="relative">
          <button
            onClick={() => setOpenDropdown(isOpen ? null : item.id)}
            className={cn(
              "flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-md transition-colors",
              isOpen
                ? "bg-accent text-accent-foreground"
                : "hover:bg-accent hover:text-accent-foreground"
            )}
          >
            {Icon && <Icon className="h-4 w-4" />}
            {item.label}
            <ChevronDown className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
          </button>

          {isOpen && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-popover border border-border rounded-md shadow-lg py-1 z-50">
              {item.children?.map((child) => (
                <NavLink
                  key={child.id}
                  to={child.path || "#"}
                  className={({ isActive }) =>
                    cn(
                      "block px-4 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-accent hover:text-accent-foreground"
                    )
                  }
                  onClick={() => setOpenDropdown(null)}
                >
                  <span className="flex items-center gap-2">
                    {child.icon && <child.icon className="h-4 w-4" />}
                    {child.label}
                  </span>
                </NavLink>
              ))}
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
    <nav className={cn("bg-card border-b border-border px-4 py-2", className)} ref={dropdownRef}>
      <div className="flex items-center gap-2">
        <h1 className="text-lg font-bold text-foreground mr-6">Cool ERP</h1>
        {MENU_CONFIG.map((item) => renderMenuItem(item))}
      </div>
    </nav>
  );
};