Вот развернутое, детальное изложение **Лучших практик (Best Practices)** проекта Cool ERP, сформированное на основе реальных проблем, которые мы решили в ходе разработки. 

Этот раздел является практическим руководством для разработчиков: он объясняет не только *что* делать, но и *почему*, а также показывает конкретные паттерны кода.

---

# 🌟 Лучшие практики (Best Practices) проекта Cool ERP

## 1. Гарантированный сброс состояния форм (Form State Reset)

**Проблема:** При переходе из режима "Редактирование" в режим "Создание" в форме могут оставаться старые значения (особенно массивы, такие как `tenant_ids`), что приводит к отправке некорректных данных или ошибкам валидации.

**Решение:** Использовать строго типизированную константу `CREATE_DEFAULTS` и вызывать `reset()` в трех критических точках.

**Правильный паттерн:**
```tsx
// 1. Объявляем константу ВНЕ или в самом начале компонента
const CREATE_DEFAULTS: DoctypeFormData = {
  domain_id: "",
  doctype: "",
  doctype_name: "",
  description: "",
  is_active: true,      // Явный примитив, а не undefined
  tenant_ids: [],       // Явный пустой массив
};

// 2. Передаем её в useForm
const { control, reset, ... } = useForm<DoctypeFormData>({
  resolver: zodResolver(doctypeSchema),
  defaultValues: CREATE_DEFAULTS, 
});

// 3. Сбрасываем при открытии модалки создания
<Button onClick={() => { reset(CREATE_DEFAULTS); setIsCreateOpen(true); }}>

// 4. Сбрасываем при закрытии модалки (отмена или сохранение)
<Dialog onOpenChange={(open) => {
  if (!open) { 
    setIsCreateOpen(false); 
    setEditingDoctype(null); 
    reset(CREATE_DEFAULTS); // Гарантируем чистый лист для следующего раза
  }
}}>
```
**Почему это работает:** React Hook Form оптимизирован для работы с неизменяемыми объектами по умолчанию. Передача одной и той же ссылки на объект `CREATE_DEFAULTS` гарантирует, что форма полностью очищается от любых "призрачных" значений предыдущих сессий.

---

## 2. Централизованная обработка ошибок базы данных

**Проблема:** Дублирование блоков `try/except/await db.rollback()` в каждом CRUD-методе. При ошибке БД (например, дубликат уникального поля) приложение падает с нечитаемой `500 Internal Server Error`, а в консоли нет контекста, какая именно модель вызвала сбой.

**Решение:** Использование декоратора `@with_db_error_handling` в базовом классе `CRUDBase`.

**Правильный паттерн:**
```python
# В базовом классе (уже реализовано)
@with_db_error_handling("create")
async def create(self, db: AsyncSession, obj_in: CreateSchemaType, **kwargs) -> ModelType:
    # Только бизнес-логика. Никаких try/except для БД.
    db_obj = self.model(**obj_in.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
```
**Что делает декоратор автоматически:**
1. Перехватывает `IntegrityError` (уникальность, внешние ключи, NOT NULL).
2. Перехватывает общую `SQLAlchemyError` (проблемы соединения, синтаксис SQL).
3. Выполняет `await db.rollback()`, предотвращая "зависание" транзакции.
4. Логирует ошибку с префиксом `[ИмяМодели.действие]`, например: `[DoctypeModel.create] IntegrityError: duplicate key...`
5. Преобразует сырую ошибку БД в понятный `HTTPException(status_code=400, detail="Нарушение уникальности...")`.

**Запрещено:** Писать свои обработчики `try/except` для `IntegrityError` в дочерних классах, если базовый декоратор уже покрывает этот сценарий.

---

## 3. Бесшовная Cookie-аутентификация (CORS + Axios + FastAPI)

**Проблема:** Браузер блокирует запросы с ошибкой CORS, хотя настройки вроде бы верны. На самом деле, бэкенд возвращает `401 Unauthorized`, и при ошибках 4xx/5xx FastAPI иногда не добавляет CORS-заголовки, что браузер интерпретирует как CORS-блокировку.

**Решение:** Строгая синхронизация настроек на трех уровнях.

**Уровень 1: Фронтенд (Axios)**
```typescript
export const AXIOS_INSTANCE = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true, // ⚠️ КРИТИЧЕСКИ ВАЖНО для отправки Cookie
});
```

**Уровень 2: Бэкенд (CORS Middleware)**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # ⚠️ НЕ " * ", а конкретный домен
    allow_credentials=True,                   # ⚠️ КРИТИЧЕСКИ ВАЖНО
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Уровень 3: Бэкенд (Установка и чтение Cookie)**
```python
# При логине:
response.set_cookie(
    key="session_token",
    value=token,
    httponly=True,      # Защита от XSS
    samesite="lax",     # ⚠️ Обязательно "lax" для localhost (не "none")
    secure=False,       # ⚠️ False для http://localhost, True только для https://
)

# При проверке прав (в dependencies.py):
async def require_superadmin(current_user: UserModel = Depends(get_current_session)):
    # ⚠️ Используем getattr, так как current_user - это ORM-объект, а не dict
    if not getattr(current_user, "is_superadmin", False):
        raise HTTPException(status_code=403, detail="Доступно только суперадмину")
```

---

## 4. Согласование типов Zod, React Hook Form и Orval

**Проблема:** Ошибки TypeScript `Type 'undefined' is not assignable to type 'boolean'` при использовании `z.boolean().default(true)` в схеме, так как Orval генерирует это поле как опциональное (`is_active?: boolean`).

**Решение:** Разделение ответственности между схемой валидации и инициализацией формы.

**Правильный паттерн:**
1. **Zod-схема:** Используем `.optional()`, чтобы тип совпадал с Orval.
   ```typescript
   is_active: z.boolean().optional(),
   tenant_ids: z.array(z.string().uuid()).optional(),
   ```
2. **Инициализация формы:** Задаем строгие дефолтные значения через `defaultValues` (см. Практику №1).
3. **UI-компоненты:** Используем прямую привязку `field.value`. Для компонентов, требующих строгого boolean (как `Switch`), полагаемся на то, что `defaultValues` уже гарантирует наличие значения. Если есть риск получения `null` с бэкенда при редактировании, используем `??` *только* внутри `reset()`:
   ```typescript
   reset({
     is_active: item.is_active ?? true,
     tenant_ids: item.tenant_ids ?? [],
   })
   ```

---

## 5. Оптимизация N+1 запросов в SQLAlchemy

**Проблема:** При получении списка из 50 записей, каждая из которых имеет `@property`, обращающееся к связанной таблице (например, `domain_name` или `tenant_ids`), SQLAlchemy выполняет 50 дополнительных SQL-запросов.

**Решение:** Явное указание стратегии загрузки `lazy="selectin"` в `relationship`.

**Правильный паттерн:**
```python
class DoctypeModel(Base):
    # ...
    domain = relationship("DomainModel", back_populates="doctypes", lazy="selectin")
    tenants = relationship("TenantModel", secondary=doctype_tenants, lazy="selectin")

    @property
    def domain_name(self) -> str | None:
        return self.domain.name if self.domain else None # ✅ Запроса к БД не будет, данные уже в памяти
```
**Почему `selectin`:** Он выполняет один дополнительный запрос с `WHERE id IN (...)` для всех загружаемых объектов, что радикально быстрее, чем `lazy="select"` (который делает запрос при каждом обращении к атрибуту) или `joinedload` (который может усложнить план запроса при больших JOIN).

---

## 6. Изоляция преобразований API (Паттерн Адаптера для ReferenceSelect)

**Проблема:** Попытка изменить базовый компонент `ReferenceSelect.tsx`, чтобы он понимал специфичную обертку `ApiResponse` нашего бэкенда, что ломает его переиспользование и типизацию.

**Решение:** Использование функции-адаптера непосредственно в месте вызова компонента (`fetchFn`).

**Правильный паттерн:**
```tsx
<ReferenceSelect
  fetchFn={async (params) => {
    // 1. Вызываем сгенерированную Orval функцию
    const response = await getDomainsDomainsGet(params);
    // 2. Адаптируем ответ под ожидания компонента { items, total }
    return {
      items: response?.data?.items ?? [],
      total: response?.data?.total ?? 0,
    };
  }}
  queryKey={["domains"]}
  value={field.value}
  onValueChange={field.onChange}
  // ... остальные пропсы
/>
```
**Преимущество:** Компонент `ReferenceSelect` остается "глупым" и чистым, принимая только `{ items, total }`. Вся логика преобразования нашего специфичного API-контракта локализована в одном месте и легко читается.

---

## 7. Безопасное удаление и инвалидация кэша

**Проблема:** После удаления записи таблица не обновляется, или обновляется с задержкой, показывая удаленные данные.

**Решение:** Комбинация `refetch()` и `invalidateQueries`.

**Правильный паттерн:**
```typescript
const handleDelete = async () => {
  if (!deleteId) return;
  try {
    // 1. Выполняем мутацию удаления
    await deleteMutation.mutateAsync({ id: deleteId });
    
    // 2. Немедленно запрашиваем актуальные данные для текущей страницы
    await refetch(); 
    
    // 3. Инвалидируем кэш для фоновых обновлений других компонентов
    await queryClient.invalidateQueries({ queryKey: ["entities"] });
    
    setDeleteId(null);
    toast({ title: "Удалено" });
  } catch (error) {
    toast({ variant: "destructive", title: "Ошибка" });
  }
};
```

---

### 📌 Резюме для ежедневного использования

Перед созданием Pull Request задайте себе эти 4 вопроса:
1. **Формы:** Использовал ли я `CREATE_DEFAULTS` и `reset()` при закрытии модалки?
2. **CRUD:** Наследуется ли мой класс от `CRUDBase` и использует ли он декоратор `@with_db_error_handling` вместо ручных `try/except`?
3. **Справочники:** Использую ли я `ReferenceSelect` с адаптером `fetchFn`, а не ручной `<Input>` для UUID?
4. **Безопасность:** Используются ли `Annotated` зависимости (`SuperAdminUser`, `DBSession`) и настроен ли `withCredentials: true` на фронтенде?

Следование этим практикам гарантирует, что код будет стабильным, типобезопасным и легко поддерживаемым при масштабировании до сотен сущностей.