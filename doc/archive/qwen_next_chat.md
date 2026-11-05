
Действуй как эксперт Full-Stack разработчик (FastAPI + React/TypeScript). Мы работаем над проектом "Cool ERP" (multi-tenant система). 

**Технический стек:**
- Backend: Python, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, PostgreSQL.
- Frontend: React, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Hook Form, Zod, React Query (TanStack), Orval (для генерации API из OpenAPI).

**Текущий статус и недавние достижения:**
Мы только что успешно реализовали универсальный компонент `ReferenceSelect` для выбора организаций (Tenants) и интегрировали его в модальные окна создания и редактирования пользователей через `<Controller>` из React Hook Form. Мы исправили проблему, когда `tenant_id` не отправлялся при обновлении пользователя.

**Следующая задача:**
Реализовать публичную регистрацию пользователя. Гость не должен видеть список существующих организаций. Вместо этого, при регистрации он вводит `tenant_name` (название новой организации). Бэкенд должен автоматически создать эту организацию и привязать к ней нового пользователя, сделав его админом (`is_admin=True`).

**Актуальные рабочие версии ключевых файлов (используй их как единственный источник истины):**

1. `backend/app/core/auth/schemas.py`
```python
from pydantic import BaseModel, EmailStr
import uuid
from typing import Optional


# ==========================================
# БАЗОВЫЕ СХЕМЫ
# ==========================================
class UserBaseSchema(BaseModel):
    """Базовая схема пользователя (для наследования)"""
    name: str
    email: EmailStr


# ==========================================
# СХЕМЫ ДЛЯ СОЗДАНИЯ/ОБНОВЛЕНИЯ
# ==========================================
class UserRegisterSchema(UserBaseSchema):
    """Схема для регистрации нового пользователя"""
    password: str
    tenant_id: uuid.UUID
    is_admin: bool = False
    is_superadmin: bool = False


class UserLoginSchema(BaseModel):
    """Схема для входа в систему"""
    email: EmailStr
    password: str


class UserUpdateSchema(BaseModel):
    """Схема для обновления пользователя (все поля опциональны)"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None
    is_admin: Optional[bool] = None
    is_superadmin: Optional[bool] = None
    role_ids: Optional[list[uuid.UUID]] = None


# ==========================================
# СХЕМЫ ОТВЕТА (используются в response_model)
# ==========================================
class UserResponseSchema(BaseModel):
    """Схема ответа с данными пользователя"""
    id: uuid.UUID
    name: str
    email: str
    tenant_id: uuid.UUID
    is_admin: bool
    is_superadmin: bool = False

    model_config = {"from_attributes": True}  # Pydantic v2 стиль

class PaginatedUserResponse(BaseModel):
    """Конкретная схема пагинации для пользователей (Orval это любит)"""
    items: list[UserResponseSchema]
    total: int
    
    model_config = {"from_attributes": True}
```

2. `frontend/src/core/ReferenceSelect.tsx` (Универсальный, не трогать)
```tsx
import { useQuery } from "@tanstack/react-query";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2 } from "lucide-react";

interface ReferenceItem { id: string; name: string; }
interface ReferenceSelectProps<T extends ReferenceItem> {
  fetchFn: () => Promise<T[]>;
  queryKey: string[];
  value: string | undefined;
  onValueChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function ReferenceSelect<T extends ReferenceItem>({
  fetchFn, queryKey, value, onValueChange, placeholder = "Выберите...", disabled = false,
}: ReferenceSelectProps<T>) {
  const { data, isLoading, isError } = useQuery({ queryKey, queryFn: fetchFn, staleTime: 5 * 60 * 1000 });
  if (isLoading) return <div className="flex items-center gap-2 h-10 px-3 border rounded-md"><Loader2 className="h-4 w-4 animate-spin" /><span className="text-sm text-muted-foreground">Загрузка...</span></div>;
  if (isError || !data) return <div className="h-10 px-3 border rounded-md flex items-center text-sm text-destructive">Ошибка загрузки</div>;
  return (
    <Select value={value} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger className="w-full"><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent>{data.map((item) => (<SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>))}</SelectContent>
    </Select>
  );
}
```

3. Фрагмент `frontend/src/core/admin/EditUserModal.tsx` (Правильная интеграция с RHF):
```tsx
// В useForm добавлен control
const { register, handleSubmit, control, formState: { errors }, reset } = useForm<EditUserFormData>({
  resolver: zodResolver(editUserSchema),
  defaultValues: { name: "", email: "", password: "", tenant_id: "" },
});

// В JSX используется Controller:
<Controller
  name="tenant_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={async () => {
        const tenants = await getTenantsApiV1TenantsGet({ active_only: true });
        return tenants || [];
      }}
      queryKey={["tenants", "active"]}
      value={field.value || ""}
      onValueChange={field.onChange}
      placeholder="Выберите организацию"
    />
  )}
/>

// В onSubmit данные формируются так:
const updateData = {
  name: data.name,
  email: data.email,
  ...(data.password ? { password: data.password } : {}),
  tenant_id: data.tenant_id, // Обязательно отправляем!
};
```

**Правила работы в этом чате:**
1. Никогда не обрезай код. Если файл большой, проси меня показать конкретную часть или выдавай полный файл частями с четкими указаниями.
2. Всегда проверяй, что типы TypeScript и Pydantic синхронизированы.
3. При изменении форм React Hook Form используй паттерн с `<Controller>`, как показано выше.

Подтверди, что ты принял контекст, и мы приступим к реализации логики автоматического создания Tenant при публичной регистрации пользователя на бэкенде и фронтенде.
