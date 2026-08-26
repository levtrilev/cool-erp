my_enterprise_project/
│
├── .env                       # Переменные окружения (БД, секреты)
├── .gitignore
├── README.md
├── requirements.txt           # Зависимости проекта
│
└── app/                       # Главный пакет приложения
    ├── __init__.py
    ├── main.py                # Входная точка: сборка всех роутеров и запуск lifespan
    │
    ├── core/                  # ЯДРО ПРИЛОЖЕНИЯ (Общий разделяемый слой)
    │   ├── __init__.py
    │   ├── config.py          # Pydantic-настройки (наш класс Settings)
    │   ├── database.py        # Настройка движка PostgreSQL, async_session и get_db
    │   ├── security.py        # Хеширование паролей, генерация и проверка JWT tokens
    │   ├── exceptions.py      # Кастомные глобальные ошибки
    │   │
    │   ├── crud/              # Общие базовые классы
    │   │   ├── __init__.py
    │   │   └── base.py        # Тот самый универсальный CRUDBase с total_count и GIN поиском
    │   │
    │   └── auth/              # Управление полномочиями, ролями и правами доступа (RBAC)
    │       ├── __init__.py
    │       ├── dependencies.py # Проверки прав (например, RoleChecker(["admin", "manager"]))
    │       ├── models.py      # Модели UserModel, RoleModel, PermissionModel
    │       ├── schemas.py     # Схемы для авторизации и прав
    │       └── router.py      # Эндпоинты /auth/login, /auth/register
    │
    └── modules/               # БИЗНЕС-МОДУЛИ (Специфические изолированные папки)
        │
        ├── sales/             # Модуль продаж
        │   ├── __init__.py
        │   ├── models.py      # Таблицы SaleOrder, Invoice, Customer
        │   ├── schemas.py     # Схемы Pydantic для валидации заказов продаж
        │   ├── crud.py        # Специфичные методы (например, расчет скидок), наследует CRUDBase
        │   ├── services.py    # Сложная бизнес-логика (проведение оплаты, списание со склада)
        │   └── router.py      # Маршруты /sales/orders, /sales/invoices
        │
        ├── inventory/         # Модуль склада (Устроен аналогично)
        │   ├── __init__.py
        │   ├── models.py      # Таблицы StockItem, Warehouse, StockMovement
        │   ├── schemas.py
        │   ├── crud.py
        │   └── router.py      # Маршруты /inventory/stocks
        │
        ├── assets/            # Модуль управления активами
        │   ├── __init__.py
        │   ├── models.py
        │   └── router.py      # Маршруты /assets/...
        │
        └── service/           # Модуль сервисного обслуживания (Ремонты, заявки)
            ├── __init__.py
            ├── models.py
            └── router.py      # Маршруты /service/tickets
