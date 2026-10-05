# Правило №16: Кнопка удаления с AlertDialog

Кнопка удаления записи на любой списочной CRUD-странице **ОБЯЗАТЕЛЬНО** должна использовать компонент `AlertDialog` из библиотеки shadcn/ui для подтверждения действия. Использование нативного браузерного `window.confirm()` **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

---

### 1. Обоснование (Почему это важно)

1. **Единообразие UI/UX:** Нативный `window.confirm()` выглядит чужеродно в современном веб-приложении, ломает визуальный стиль и не поддерживает темную тему. `AlertDialog` идеально вписывается в дизайн-систему shadcn/ui.
2. **Блокировка главного потока:** `window.confirm()` блокирует основной поток JavaScript (main thread), что может привести к зависанию UI, особенно если в фоне выполняются тяжелые вычисления или рендеринг.
3. **Контроль состояния:** `AlertDialog` позволяет отображать индикатор загрузки (спиннер) на кнопке подтверждения во время выполнения мутации, блокировать повторные клики и кастомизировать текст.

---

### 2. Обязательные требования к реализации

#### 2.1. Управление через состояние (ID)
Удаление не должно выполняться мгновенно по клику на кнопку в таблице. Клик должен лишь **устанавливать ID** удаляемой записии в состояние, что открывает диалог.

#### 2.2. Размещение компонента
Компонент `AlertDialog` должен рендериться **на корневом уровне страницы** (рядом с таблицей), а **НЕ** внутри каждой строки таблицы (`TableRow`). Это предотвращает проблемы с z-index, перекрытием скроллбарами и лишним рендерингом.

#### 2.3. Состояние загрузки
Кнопка подтверждения (`AlertDialogAction`) **ОБЯЗАТЕЛЬНО** должна переходить в состояние `disabled` и показывать индикатор загрузки, пока выполняется мутация удаления.

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Полная реализация с AlertDialog

```tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Trash2, Loader2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/components/ui/use-toast";

export const RolesPage = () => {
  const { toast } = useToast();
  
  // ✅ Состояние для хранения ID удаляемой роли
  const [deleteRoleId, setDeleteRoleId] = useState<string | null>(null);
  
  // Мутация удаления
  const deleteMutation = useDeleteRoleRolesRoleIdDelete();
  const { refetch } = useReadRolesRolesGet({ skip: 0, limit: 10 });

  // Обработчик подтверждения
  const handleConfirmDelete = async () => {
    if (!deleteRoleId) return;

    try {
      // Выполняем удаление
      await deleteMutation.mutateAsync({ role_id: deleteRoleId });
      
      // Обновляем список (Правило №25)
      await refetch(); 
      
      toast({ title: "Роль успешно удалена" });
    } catch (error) {
      toast({ variant: "destructive", title: "Ошибка удаления" });
    } finally {
      // ✅ Всегда закрываем диалог и сбрасываем ID
      setDeleteRoleId(null);
    }
  };

  return (
    <div>
      {/* ... Таблица ... */}
      {/* Кнопка удаления в строке таблицы */}
      <Button 
        variant="ghost" 
        size="icon" 
        onClick={() => setDeleteRoleId(role.id)} // ✅ Только устанавливаем ID
      >
        <Trash2 className="h-4 w-4" />
      </Button>

      {/* ✅ AlertDialog рендерится на корневом уровне страницы */}
      <AlertDialog open={!!deleteRoleId} onOpenChange={(open) => !open && setDeleteRoleId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Вы уверены?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Роль будет безвозвратно удалена из системы, 
              а все пользователи потеряют к ней доступ.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending} // ✅ Блокировка во время загрузки
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Удаление...
                </>
              ) : (
                "Удалить"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
```

#### ❌ НЕПРАВИЛЬНО: Использование нативного confirm

```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №16
const handleDelete = (roleId: string) => {
  //  ЗАПРЕЩЕНО: Нативное окно браузера
  if (window.confirm("Вы действительно хотите удалить эту роль?")) {
    deleteMutation.mutate({ role_id: roleId });
  }
};
```

#### ❌ НЕПРАВИЛЬНО: AlertDialog внутри строки таблицы

```tsx
// ❌ ОШИБКА АРХИТЕКТУРЫ
{roles.map((role) => (
  <TableRow key={role.id}>
    <TableCell>{role.name}</TableCell>
    <TableCell>
      {/* ❌ Рендерить AlertDialog внутри каждой строки — плохая практика. 
          Это создает десятки скрытых диалогов в DOM и может ломать верстку. */}
      <AlertDialog>...</AlertDialog> 
    </TableCell>
  </TableRow>
))}
```

---

### 4. Нюансы и лучшие практики

#### 4.1. Текст предупреждения
Текст в `AlertDialogDescription` должен четко объяснять последствия. Если удаление каскадно (например, удаление Тенанта удаляет всех его Пользователей), об этом **ОБЯЗАТЕЛЬНО** нужно предупредить.

#### 4.2. Обработка `onOpenChange`
Всегда обрабатывайте закрытие диалога по крестику, клику вне окна или нажатию Escape. Проще всего это сделать через проп `onOpenChange`:
```tsx
onOpenChange={(open) => !open && setDeleteRoleId(null)}
```
Это гарантирует, что если пользователь закроет окно без подтверждения, ID сбросится и диалог не "зависнет" в открытом состоянии для несуществующей записии.

#### 4.3. Стилизация кнопки удаления
Кнопка подтверждения в `AlertDialog` должна визуально отличаться как опасное действие. Используйте классы `bg-destructive text-destructive-foreground` (стандартные семантические классы Tailwind/shadcn для деструктивных действий).

---

### 5. Чек-лист для разработчика

При добавлении функционала удаления на любую страницу проверьте:

- [ ] Используется ли компонент `AlertDialog` из `@/components/ui/alert-dialog`?
- [ ] Отсутствует ли в коде вызов `window.confirm()`?
- [] Управляется ли открытие диалога через состояние ID (`deleteXxxId`)?
- [ ] Рендерится ли `AlertDialog` на корневом уровне страницы (вне таблицы)?
- [ ] Заблокирована ли кнопка "Удалить" (`disabled`) во время выполнения мутации (`isPending`)?
- [ ] Отображается ли спиннер (`Loader2`) на кнопке подтверждения при загрузке?
- [ ] Сбрасывается ли `deleteXxxId` в `null` в блоке `finally` или при закрытии диалога?

Следование этому правилу гарантирует, что процесс удаления данных во всем приложении будет безопасным, предсказуемым и визуально целостным.