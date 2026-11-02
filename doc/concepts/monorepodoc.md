### Часть 1. Имеет ли смысл "один раз задать базовый класс и управлять классами для front & backend"?

**Короткий ответ:** В том виде, как вы это сформулировали (создать некий "нейтральный" абстрактный класс и генерировать из него и Python, и TypeScript) — **нет, это не имеет смысла и приведет к боли.** Это называется "проклятие генераторов кода". Вы потеряете нативные фичи языков (Python decorators, Pydantic validators, Zod refinements), а отладка сгенерированного кода превратится в ад.

**Правильный подход (Industry Standard): Backend-First (Contract-First).**
Единственный источник истины (Single Source of Truth, SSOT) — это **Pydantic модели в вашем FastAPI бэкенде**. 
1. Вы пишете бизнес-логику и модели на Python (Pydantic).
2. FastAPI автоматически генерирует `openapi.json` (строгий контракт).
3. Frontend (через Orval) читает `openapi.json` и генерирует TypeScript типы, Zod схемы и React Query хуки.

Это работает идеально, потому что Pydantic — это не просто "схема", это реальный runtime код с валидацией. А OpenAPI — это стандартизированный мост.

---

### Часть 2. Структура проекта (Monorepo)

Мы объединим фронтенд и бэкенд в один репозиторий. Это даст единую историю Git, общие скрипты и удобную работу в одном окне VS Code.

```text
my-awesome-app/                  # Корень monorepo
├── .vscode/                     # Настройки VS Code (критично для единой сессии)
│   ├── settings.json
│   ├── tasks.json
│   └── launch.json
├── backend/                     # FastAPI приложение
│   ├── venv/                    # Виртуальное окружение Python (в .gitignore)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Точка входа FastAPI
│   │   ├── models/              # SSOT: Pydantic модели (Базовые классы сущностей)
│   │   │   ├── __init__.py
│   │   │   └── user.py
│   │   └── routers/             # Роутеры FastAPI
│   │       └── users.py
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/                    # Vite + React приложение
│   ├── src/
│   │   ├── api/
│   │   │   ├── generated/       # Сюда Orval сгенерирует типы, Zod, хуки
│   │   │   └── custom-instance.ts
│   │   ├── features/            # Ваши формы (generated/ и custom/)
│   │   └── ...
│   ├── orval.config.ts
│   ├── package.json
│   └── tsconfig.json
├── scripts/                     # Скрипты для оркестрации (опционально)
├── .gitignore
├── package.json                 # Корневой package.json для запуска всего сразу
└── README.md
```

---

### Часть 3. Настройка VS Code для единой сессии

Чтобы VS Code "понимал" и Python (с его venv), и Node.js, и мог запускать оба сервера одной кнопкой, нужно настроить `.vscode`.

#### 1. `.vscode/settings.json`
Указываем VS Code, где лежит виртуальное окружение Python, и настраиваем форматирование.

```json
{
  // Указываем путь к Python интерпретатору
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python", // На Windows: "...\\Scripts\\python.exe"
  
  // Настройки Python
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true,
  
  // Игнорируем сгенерированные папки для поиска
  "search.exclude": {
    "**/node_modules": true,
    "**/backend/venv": true,
    "**/frontend/src/api/generated": true
  },
  
  // Форматирование
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff" // Рекомендуется использовать Ruff
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

#### 2. `.vscode/tasks.json`
Создаем задачи для запуска бэкенда, фронтенда и генерации API.

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start Backend (FastAPI)",
      "type": "shell",
      "command": "./venv/bin/uvicorn app.main:app --reload --port 8000", // Для Windows: venv\\Scripts\\uvicorn...
      "options": { "cwd": "${workspaceFolder}/backend" },
      "isBackground": true,
      "problemMatcher": [],
      "group": "build"
    },
    {
      "label": "Start Frontend (Vite)",
      "type": "npm",
      "script": "dev",
      "path": "frontend/",
      "isBackground": true,
      "problemMatcher": [],
      "group": "build"
    },
    {
      "label": "Generate API (Orval)",
      "type": "npm",
      "script": "api:generate",
      "path": "frontend/",
      "problemMatcher": []
    }
  ]
}
```

#### 3. `.vscode/launch.json`
Магия единой сессии. Нажимаем **F5**, и у вас одновременно стартуют и бэкенд, и фронтенд.

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "env": { "PYTHONPATH": "${workspaceFolder}/backend" }
    },
    {
      "name": "Frontend: Vite",
      "type": "node",
      "request": "launch",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "cwd": "${workspaceFolder}/frontend"
    }
  ],
  "compounds": [
    {
      "name": "🚀 Run Full Stack (Backend + Frontend)",
      "configurations": ["Python: FastAPI", "Frontend: Vite"],
      "stopAll": true
    }
  ]
}
```
*Теперь в меню отладки VS Code (Ctrl+Shift+D) вы можете выбрать **"🚀 Run Full Stack"** и нажать F5.*

---

### Часть 4. Корневой `package.json` и автоматизация

В корне проекта создайте `package.json`, чтобы не переключаться между папками для общих команд.

```json
{
  "name": "my-awesome-app",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\"",
    "dev:backend": "cd backend && ./venv/bin/uvicorn app.main:app --reload",
    "dev:frontend": "cd frontend && npm run dev",
    
    "api:download": "curl http://localhost:8000/openapi.json -o ./frontend/openapi.json",
    "api:generate": "cd frontend && npm run api:generate",
    
    "build": "cd frontend && npm run build",
    "lint": "cd frontend && npm run lint"
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  }
}
```
*(Примечание: для Windows в скриптах `cd backend && ...` нужно использовать `&&` или писать отдельные `.cmd` файлы, либо использовать `npm-run-all`)*.

---

### Часть 5. Рабочий процесс (Workflow)

Как это выглядит на практике для разработчика:

#### Шаг 1: Создаем сущность на Бэкенде (SSOT)
В `backend/app/models/user.py`:
```python
from pydantic import BaseModel, EmailStr, Field

# Это наш "базовый класс". Из него всё сгенерируется.
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=50)
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: int
    
    class Config:
        from_attributes = True # Важно для FastAPI
```

#### Шаг 2: Создаем роутер
В `backend/app/routers/users.py`:
```python
from fastapi import APIRouter
from app.models.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate):
    # Логика сохранения в БД
    return {"id": 1, **user.model_dump()}
```

#### Шаг 3: Генерация для Фронтенда
1. Убедитесь, что бэкенд запущен (F5 в VS Code).
2. В терминале VS Code выполните:
   ```bash
   npm run api:generate
   ```
   *Эта команда скачает `openapi.json` с `localhost:8000` и запустит Orval.*

#### Шаг 4. Использование на Фронтенде
Orval создал в `frontend/src/api/generated/`:
*   `UserCreate` (TypeScript interface)
*   `userCreateSchema` (Zod schema)
*   `useCreateUser` (React Query hook)

Теперь вы можете написать форму (как в прошлом ответе), используя `userCreateSchema` и `useCreateUser`. Вы **не пишете** типы и валидацию вручную.

---

### Часть 6. Что делать со сложными документами? (Ручная кастомизация)

Допустим, у вас есть сложный документ `Contract`, который требует кастомной UI логики (например, динамические шаги).

1. На бэкенде вы всё равно описываете базовую Pydantic модель `ContractBase`.
2. Orval генерирует `contractBaseSchema` (Zod).
3. На фронтенде в `frontend/src/features/contracts/custom/ComplexContractForm.tsx` вы **расширяете** сгенерированную схему:

```typescript
import { contractBaseSchema } from '@/api/generated/zod';
import { z } from 'zod';

// Добавляем UI-специфичные поля и сложную валидацию
const complexContractSchema = contractBaseSchema.extend({
  currentStep: z.number(),
  clauses: z.array(z.object({ text: z.string() })).min(1, "Добавьте хотя бы один пункт"),
});
```
При отправке на бэкенд вы просто отсекаете UI-поля (`currentStep`), отправляя только то, что ожидает Pydantic модель на бэкенде.

### Резюме

1. **Не пытайтесь изобрести свой язык схем.** Используйте Pydantic (Python) как единственный источник истины.
2. **Используйте Monorepo.** Держите фронт и бэк в одной папке, но разделяйте их окружения (`venv` и `node_modules`).
3. **Настройте VS Code.** Используйте `launch.json` с `compounds`, чтобы запускать весь стек одной кнопкой F5.
4. **Автоматизируйте мост.** Скрипт `npm run api:generate` — это ваш главный инструмент синхронизации. Запускайте его каждый раз, когда меняете Pydantic модели или роутеры на бэкенде.