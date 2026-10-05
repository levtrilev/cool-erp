import { useState, useCallback, useRef, useEffect } from "react";

interface ResizableColumn {
  id: string;
  initialWidth: number;
  minWidth?: number;
}

export function useResizableColumns(
  columns: ResizableColumn[],
  storageKey?: string
) {
  // Загружаем сохранённые ширины из localStorage или используем начальные
  const [widths, setWidths] = useState<Record<string, number>>(() => {
    if (storageKey) {
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          return JSON.parse(saved);
        }
      } catch (e) {
        console.error("Failed to load column widths:", e);
      }
    }
    return columns.reduce(
      (acc, col) => ({ ...acc, [col.id]: col.initialWidth }),
      {}
    );
  });

  const isResizing = useRef(false);
  const currentColumn = useRef<string | null>(null);
  const nextColumn = useRef<string | null>(null);
  const startX = useRef(0);
  const startWidth = useRef(0);
  const startNextWidth = useRef(0);

  // Сохраняем ширины в localStorage при изменении
  useEffect(() => {
    if (storageKey) {
      try {
        localStorage.setItem(storageKey, JSON.stringify(widths));
      } catch (e) {
        console.error("Failed to save column widths:", e);
      }
    }
  }, [widths, storageKey]);

  const handleMouseDown = useCallback(
    (columnId: string, e: React.MouseEvent) => {
      e.preventDefault();
      
      // Находим индекс текущей колонки и следующей
      const currentIndex = columns.findIndex((c) => c.id === columnId);
      const nextIndex = currentIndex + 1;
      
      if (nextIndex >= columns.length) return; // Нельзя тянуть последнюю колонку
      
      isResizing.current = true;
      currentColumn.current = columnId;
      nextColumn.current = columns[nextIndex].id;
      startX.current = e.clientX;
      startWidth.current = widths[columnId];
      startNextWidth.current = widths[columns[nextIndex].id];

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [columns, widths]
  );

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing.current || !currentColumn.current || !nextColumn.current) return;

    const deltaX = e.clientX - startX.current;
    
    const currentMinWidth = columns.find((c) => c.id === currentColumn.current)?.minWidth || 50;
    const nextMinWidth = columns.find((c) => c.id === nextColumn.current)?.minWidth || 50;
    
    const newCurrentWidth = startWidth.current + deltaX;
    const newNextWidth = startNextWidth.current - deltaX;
    
    // Проверяем минимальные ширины для обеих колонок
    if (newCurrentWidth >= currentMinWidth && newNextWidth >= nextMinWidth) {
      setWidths((prev) => ({
        ...prev,
        [currentColumn.current!]: newCurrentWidth,
        [nextColumn.current!]: newNextWidth,
      }));
    }
  }, [columns]);

  const handleMouseUp = useCallback(() => {
    if (isResizing.current) {
      isResizing.current = false;
      currentColumn.current = null;
      nextColumn.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
  }, []);

  // Глобальные обработчики
  useEffect(() => {
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const resetWidths = useCallback(() => {
    const defaultWidths = columns.reduce(
      (acc, col) => ({ ...acc, [col.id]: col.initialWidth }),
      {}
    );
    setWidths(defaultWidths);
    if (storageKey) {
      localStorage.removeItem(storageKey);
    }
  }, [columns, storageKey]);

  return { widths, handleMouseDown, resetWidths };
}