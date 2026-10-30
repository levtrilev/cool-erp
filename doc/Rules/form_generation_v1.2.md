# Спецификация формата `cool-erp-form` и пример-задание для `EditRoleModal`

Документ состоит из двух частей:
1. **Часть 1** — Пример YAML-задание для `EditRoleModal` (версия формата 1.2)
2. **Часть 2** — полная самодостаточная спецификация формата `cool-erp-form v1.2`

---

# ЧАСТЬ 1. Пример задания: `EditRoleModal`

```yaml
# ════════════════════════════════════════════════════════════
# ЗАДАНИЕ НА ФОРМУ: Редактирование роли
# Формат: cool-erp-form v1.2
# Все правила проекта подразумеваются и НЕ описываются здесь.
# ════════════════════════════════════════════════════════════

meta:
  format_version: "1.2"               # Версия формата задания
  module: core/roles                  # Папка модуля во фронтенде и бэкенде
  component: EditRoleModal            # Имя React-компонента модалки
  entity: role                        # Сущность бэкенда (таблица/модель)
  entity_type: RoleResponseSchema     # Тип данных сущности (для initialData)
  entity_kind: reference              # ← ТИП СУЩНОСТИ (обязательное поле)
  # ┌─────────────────────────────────────────────────────────┐
  # │ Значения:                                                │
  # │   document  — контракт документов (§3.3) + жизненный    │
  # │               цикл, блокировки, режим readOnly          │
  # │   reference — справочник без контракта документов       │
  # └─────────────────────────────────────────────────────────┘
  save_mutation: useSaveRoleRolesSavePost   # Orval-хук сохранения

# Заголовки модалки для каждого режима (поддержка интерполяции {поле})
titles:
  create: "Создание новой роли"
  edit: "Редактирование роли: {entity.name}"
  copy: "Копирование роли: {copy_source.name}"

# Геометрия диалога
dialog:
  width: 800
  min_height: 600

# ════════════════════════════════════════════════════════════
# РЕЖИМЫ РАБОТЫ ФОРМЫ
# ════════════════════════════════════════════════════════════
modes:
  create: {}                          # Создание с нуля (entity = null)

  edit: {}                            # Редактирование (передаётся entity)

  copy:                               # Копирование (передаётся copy_source)
    source_prop: copyFromRole         # Имя пропа с исходными данными
    name_transform: "{name} (копия)"  # Трансформация имени при копировании
    strip_ids_in: [permissions]       # Черновики, где убрать id (новые записи)
    close_after_save: true            # Закрыть модалку после сохранения копии

# ════════════════════════════════════════════════════════════
# ИСТОЧНИКИ ДАННЫХ (загружаются при открытии формы)
# ════════════════════════════════════════════════════════════
data_sources:
  current_user:
    endpoint: GET /auth/user
    provides:
      - current_tenant_id             # Организация текущего пользователя
      - current_tenant_name           # Название из профиля
      - is_superadmin                 # Флаг суперадмина

  tenants:
    endpoint: GET /tenants
    params: { limit: 1000, skip: 0 }
    provides: [tenants_list]          # Справочник организаций

  sections:
    endpoint: GET /sections
    params:
      target_tenant_id: "{effective_tenant_id}"   # Зависит от выбранной организации
      limit: 1000
    provides: [sections_list]         # Справочник разделов

  users:
    endpoint: GET /users
    params:
      tenant_id: "{effective_tenant_id}"          # Зависит от выбранной организации
      limit: 1000
    provides: [users_list]            # Список пользователей организации

# ════════════════════════════════════════════════════════════
# КОНТЕКСТ ОРГАНИЗАЦИИ (особая логика мульти-арендности)
# ════════════════════════════════════════════════════════════
tenant_context:
  # Эффективная организация: приоритет источников
  effective_tenant:
    priority:
      - selected_tenant_id            # Явно выбранная суперадмином
      - source_entity.tenant_id       # Из редактируемой/копируемой роли
      - current_tenant_id             # Из профиля текущего пользователя

  # Кто может менять организацию
  change_allowed_for: superadmin

  # Проверка при попытке сменить организацию
  change_validation:
    # Запретить смену, если у роли есть сохранённые связи
    reject_if_any_assigned:
      - sections                      # role.section_ids не пуст
      - permissions                   # role.permissions не пуст
      - users                         # есть пользователи с этой ролью
    rejection_message: |
      Для роли "{entity.name}" уже назначены: {assigned_list}.
      Сначала удалите все назначения.
    on_reject: revert_select          # Откатить выбор справочника

  # Предупреждение при изменённой организации
  change_warning: |
    ⚠ Организация изменена. Сохраните роль для применения изменений.

# ════════════════════════════════════════════════════════════
# ВКЛАДКИ
# ════════════════════════════════════════════════════════════
tabs:

  # ──────────────────────────────────────────────────────────
  # ВКЛАДКА 1: ОСНОВНОЕ
  # ──────────────────────────────────────────────────────────
  - id: main
    label: Основное
    dirty_indicators: [basics, tenant]   # Какие индикаторы подсвечивают вкладку

    fields:
      # Поле "Организация" — особое поведение в зависимости от прав
      - name: organization
        label: Организация
        icon: building
        type: reference_single
        source: tenants
        behavior_by_permission:
          superadmin:
            mode: editable              # ReferenceSelect с поиском
          admin:
            mode: readonly              # Только отображение имени
            hint_edit: "Изменить организацию может только суперадмин."
            hint_create: "Роль будет создана для вашей организации."

      # Название роли
      - name: name
        label: Название роли
        type: text
        placeholder: "Например: Бухгалтер"
        required: true
        validation:
          rule: min_length
          value: 1
          message: "Название обязательно"

      # Описание роли
      - name: description
        label: Описание
        type: textarea
        placeholder: "Описание роли..."
        rows: 3
        required: false

  # ──────────────────────────────────────────────────────────
  # ВКЛАДКА 2: РАЗДЕЛЫ
  # ──────────────────────────────────────────────────────────
  - id: sections
    label: Разделы
    counter: "{sections.count}"          # Счётчик в заголовке вкладки
    dirty_indicators: [sections]

    fields:
      - name: section_ids
        label: Разделы доступа
        type: reference_multi_chips      # Множественный выбор с чипсами
        source: sections
        placeholder: "Добавить разделы..."
        dialog_heading: "Доступные разделы"
        limit: 100
        columns:
          - { field: description, label: Описание }
        # Пометки черновика: зелёный "новый" для добавленных,
        # красный зачёркнутый + кнопка восстановления для удалённых
        draft_marks:
          mark_new: true
          mark_deleted: true

  # ──────────────────────────────────────────────────────────
  # ВКЛАДКА 3: ПОЛНОМОЧИЯ
  # ──────────────────────────────────────────────────────────
  - id: permissions
    label: Полномочия
    counter: "{permissions.active_count}"   # Без помеченных на удаление
    dirty_indicators: [permissions]

    parts:
      - type: draft_table                # Таблица с черновиком
        component: PermissionsTab        # Отдельный компонент вкладки
        draft_entity: permissions
        draft_flags:
          deletion_flag: markedForDeletion  # Флаг пометки на удаление
          new_marker: "id == null"          # Новые записи — без id
        pass_props:
          - { name: permissions, value: "{permissions_draft}" }
          - { name: tenantId, value: "{effective_tenant_id}" }
          - { name: roleName, value: "{entity.name}" }

  # ──────────────────────────────────────────────────────────
  # ВКЛАДКА 4: ПОЛЬЗОВАТЕЛИ
  # ──────────────────────────────────────────────────────────
  - id: users
    label: Пользователи
    counter: "{users.selected_count}"     # Без помеченных на удаление
    dirty_indicators: [users]

    parts:
      - type: draft_table                # Таблица с черновиком
        component: UsersTab              # Отдельный компонент вкладки
        draft_entity: users
        draft_flags:
          deletion_flag: markedForDeletion
          new_marker: "id not in initial_user_ids"
        # Связь: пользователь принадлежит роли, если role.id ∈ user.role_ids
        initial_relation:
          source: users_list
          condition: "user.role_ids contains entity.id"
        pass_props:
          - { name: users, value: "{users_draft}" }
          - { name: allUsers, value: "{users_list}" }
          - { name: initialUserIds, value: "{initial_user_ids}" }
        # Показывать спиннер, пока данные пользователей загружаются
        loading_state: show_spinner

# ════════════════════════════════════════════════════════════
# КНОПКИ-ДЕЙСТВИЯ
# ════════════════════════════════════════════════════════════
actions:
  - id: save
    label: Сохранить
    type: submit
    icon: check
    # Блокируем только при редактировании без изменений.
    # В режиме копирования кнопка активна всегда (создаётся новая запись).
    disabled_when: "not has_any_changes and mode != 'copy'"
    loading_icon: spinner

  - id: cancel
    type: close
    icon: none
    label_rules:
      # Текст кнопки зависит от наличия изменений и режима копирования
      when: "has_any_changes or mode == 'copy'"
      then: "Отмена"
      else: "Закрыть"
    min_width: 96px                    # Фиксированная ширина против "прыжков"

# ════════════════════════════════════════════════════════════
# ИНДИКАТОРЫ ИЗМЕНЕНИЙ
# Каждый индикатор: что отслеживать и с чем сравнивать
# ════════════════════════════════════════════════════════════
change_indicators:
  # Изменения основных полей (название, описание)
  basics:
    watch: [name, description]
    compare_with:
      name: source_entity.name
      description: source_entity.description
    mode: field_by_field

  # Изменение организации
  tenant:
    watch: [effective_tenant_id]
    compare_with: source_entity.tenant_id
    fallback_compare: current_tenant_id
    only_when: tenant_context.change_allowed_for   # Только если смена разрешена

  # Изменение списка разделов
  sections:
    watch: [section_ids]
    compare_with: source_entity.section_ids
    mode: sorted_json                  # Сравнение отсортированных массивов

  # Изменение полномочий
  permissions:
    watch: [permissions_draft]
    compare_with: permissions_snapshot  # JSON-снэпшот при открытии
    mode: json_snapshot

  # Изменение списка пользователей
  users:
    watch: [selected_user_ids]          # Активные (без помеченных на удаление)
    compare_with: initial_user_ids
    mode: sorted_json

# Агрегированный индикатор для кнопки "Сохранить"
has_any_changes:
  formula: "basics or tenant or sections or permissions or users"

# ════════════════════════════════════════════════════════════
# СОБЫТИЯ ЖИЗНЕННОГО ЦИКЛА ФОРМЫ
# ════════════════════════════════════════════════════════════
events:
  # При открытии модалки
  on_open:
    - reset_all_state                  # Сброс черновиков, флагов, источника истины
    - increment_session_key            # Гарантированный перемонт окна
    - init_form_from_source            # Инициализация полей из источника
    - init_permissions_draft           # Черновик полномочий
    - init_users_draft_when_loaded     # Черновик пользователей после загрузки данных
    # Примечание: для режима copy источник = copy_source,
    # для edit источник = entity

  # Перед сохранением (валидации)
  on_save_before:
    - check: effective_tenant_id != null
      on_fail:
        toast_error: "Не выбрана организация для роли"
        abort: true

  # После успешного сохранения
  on_save_success:
    - invalidate_cache: ["roles"]
    - invalidate_cache_detail:         # Только для режима редактирования
        when: mode == 'edit'
        keys:
          - ["role", "{entity.id}"]
          - ["permissions", "{entity.id}"]
    - refetch_queries:                 # Дождаться актуальных данных пользователей
        match: "query_key contains 'user'"
    - update_source_of_truth           # Источник истины = ответ сервера
    - sync_permissions_draft_from_response  # Сброс пометок "новый"/"удалён"
    - resync_users_draft               # Пересинхронизация черновика пользователей
    - call_parent: on_role_saved       # Callback родителя для подсветки в списке
    - if: mode == 'copy'
      then: close_modal                # Закрыть модалку при копировании
    - toast:
        when: "mode == 'copy'"
        text: "Копия роли создана"
        else: "Роль сохранена"

  # При ошибке сохранения
  on_save_error:
    - toast_error: "{error.detail || 'Не удалось сохранить роль'}"

  # При закрытии модалки (любым способом)
  on_close:
    - reset_form_to_defaults
    - clear_source_of_truth
    - clear_all_drafts

# ════════════════════════════════════════════════════════════
# СТРУКТУРА ПОЛЕЗНОЙ НАГРУЗКИ ПРИ СОХРАНЕНИИ
# ════════════════════════════════════════════════════════════
payload:
  name: "{form.name}"
  description: "{form.description || ''}"
  tenant_id: "{effective_tenant_id}"
  section_ids: "{section_ids}"
  section_names: "{sections_list | filter_by(section_ids) | map(name)}"

  permissions:
    source: permissions_draft
    filter: "!markedForDeletion"
    map:
      doctype: "{item.doctype}"
      doctype_name: "{item.doctype_name || item.doctype}"
      role_name: "{item.role_name || form.name}"
      tenant_name: "{tenant_name}"
      tenant_id: "{effective_tenant_id}"
      full_access: "{item.full_access}"
      author: "{item.author}"
      reader: "{item.reader}"
      editor: "{item.editor}"
      can_delete: "{item.can_delete}"
      access_by_tags: "{item.access_by_tags}"
      id: "{item.id if exists else omit}"   # id только для существующих

  user_ids: "{selected_user_ids}"

# Параметры мутации в зависимости от режима
mutation_params:
  edit:
    data: "{payload}"
    params: { role_id: "{entity.id}" }
  create:
    data: "{payload}"
  copy:
    data: "{payload}"                  # Без role_id — создаётся новая роль
```

---

# ЧАСТЬ 2. Спецификация формата `cool-erp-form v1.2`

## 2.1. Общие сведения

### Назначение формата

Формат `cool-erp-form` — декларативный способ описания форм проекта. Он содержит **бизнес-интент** формы: какому модулю принадлежит форма, какую сущность представляет, из каких частей состоит, какие поля содержит, какие действия возможны, какие события происходят при открытии и сохранении.

**Важно:** формат описывает **ЧТО** должна делать форма, а не **КАК** это реализовано. Все технические детали (паттерны синхронизации, обработка ошибок, блокировки) подразумеваются **правилами проекта** и в задании не дублируются.

### Принципы

| Принцип | Формулировка |
|---------|--------------|
| **Декларативность** | Описываем цель, а не алгоритм достижения |
| **Неперегруженность** | Технические паттерны проекта НЕ дублируются в задании |
| **Самодостаточность** | Задание должно быть понятным без чтения исходного кода |
| **Версионирование** | Каждая версия формата имеет номер; при изменении структуры версии увеличивается |
| **Расширяемость** | Новые секции и поля могут добавляться без ломки существующих заданий |

### Область применения

Формат используется для:
- Первичного создания формы (задание → генерация кода)
- Модификации существующей формы (изменение затронутых секций)
- Обратного инжиниринга (код → задание для документирования)

---

## 2.2. Структура файла задания

Файл задания содержит следующие секции верхнего уровня:

| Секция | Обязательность | Назначение |
|--------|:---:|------------|
| `meta` | ✅ Обязательная | Идентификация формы, сущности, типа сущности |
| `titles` | ✅ Обязательная | Заголовки модалки для разных режимов |
| `dialog` | ✅ Обязательная | Геометрия диалогового окна |
| `modes` | ✅ Обязательная | Поддерживаемые режимы работы |
| `data_sources` | ✅ Обязательная | Источники данных, загружаемые при открытии |
| `tenant_context` | ⚪ Опциональная | Особая логика выбора организации |
| `tabs` | ✅ Обязательная | Структура вкладок с полями и частями |
| `actions` | ✅ Обязательная | Кнопки-действия и условия их доступности |
| `change_indicators` | ⚪ Опциональная | Как определять несохранённые изменения |
| `events` | ⚪ Опциональная | События жизненного цикла (могут подразумеваться) |
| `payload` | ⚪ Опциональная | Структура данных при сохранении |

---

## 2.3. Секция `meta` — идентификация формы

### Поля

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `format_version` | `string` | ✅ | Версия формата задания (например, `"1.2"`) |
| `module` | `string` | ✅ | Путь модуля относительно `frontend/src/` и `backend/app/` (например, `core/roles`) |
| `component` | `string` | ✅ | Имя React-компонента модалки (например, `EditRoleModal`) |
| `entity` | `string` | ✅ | Имя сущности бэкенда (таблица/модель) |
| `entity_type` | `string` | ✅ | Имя TypeScript-типа сущности для `initialData` (например, `RoleResponseSchema`) |
| `entity_kind` | `string` | ✅ | Тип сущности: `document` или `reference` |
| `save_mutation` | `string` или `object` | ⚪ | Имя Orval-хука для сохранения (если не выводится из `entity`) |
| `contract_overrides` | `object` | ⚪ | Переопределения контракта для документов (отключение полей) |

### Ключевое поле: `entity_kind`

Это **главный переключатель** формата. От него зависит, какие поля контракта присутствуют, какие паттерны применяются, какие эндпоинты нужны.

| Аспект | `document` | `reference` |
|--------|:---:|:---:|
| Миксины модели | `DocumentAccessMixin` + `DocumentLifecycleMixin` | Нет (только базовые поля) |
| Поле `section_id` в форме | ✅ Обязательное (`ReferenceSelect`) | ❌ Отсутствует |
| Поля `doc_number`, `doc_date` | ✅ В форме | ❌ Отсутствуют |
| Оптимистическая блокировка (`version`) | ✅ | ❌ |
| Пессимистическая блокировка (`/lock`) | ✅ | ❌ |
| Режим `readOnly` при 423 | ✅ | ❌ |
| Паттерн в списке | Название-ссылка + иконка замка | Название-ссылка или кнопка-карандаш |
| Удаление | Мягкое (`deleted_at`) | Жёсткое или мягкое (по решению) |
| Обработка ошибок сохранения | 409, 423, 400 | 400, 404 |
| Применимые правила | №39, Бэкенд №40, ТЗ §3.3 | №35, стандартный паттерн |

### `contract_overrides` (только для `entity_kind: document`)

Если документу не нужны какие-то стандартные поля контракта:

```yaml
meta:
  entity_kind: document
  contract_overrides:
    disable_fields: [doc_number, doc_date]   # Отключить поля жизненного цикла
    disable_tags: true                        # Отключить теги (если тип не использует тег-фильтрацию)
    hide_tags_in_form: true                   # Теги существуют в контракте, но не редактируются в форме
```

По умолчанию все поля контракта присутствуют. Переопределение нужно только для исключений.

### Примеры из проекта

| Сущность | `entity_kind` | Обоснование |
|----------|:---:|-------------|
| `notes` | `document` | Эталонный документ (ТЗ §18.7) |
| `invoices`, `contracts` (будущие) | `document` | Типы документов |
| `goods` (sales) | `document` | Наследует оба миксина по решению проекта |
| `warehouses` (inventory) | `document` | Наследует оба миксина по решению проекта |
| `companies` (business_partners) | `document` | Наследует оба миксина по решению проекта |
| `roles` | `reference` | Административная сущность |
| `tenants` | `reference` | Справочник организаций |
| `users` | `reference` | Учётные записи |
| `doctypes` | `reference` | Реестр типов документов |
| `domains` | `reference` | Группировка типов |
| `sections` | `reference` | Разделы доступа |
| `permissions` | `reference` | Атрибут роли, не самостоятельная сущность |

---

## 2.4. Секция `titles` — заголовки модалки

### Поля

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `create` | `string` | ✅ | Заголовок в режиме создания |
| `edit` | `string` | ✅ | Заголовок в режиме редактирования |
| `copy` | `string` | ⚪ | Заголовок в режиме копирования (если режим поддерживается) |
| `view` | `string` | ⚪ | Заголовок в режиме просмотра (для документов с блокировкой) |

### Интерполяция

В заголовках поддерживается интерполяция переменных через `{...}`:
- `{entity.поле}` — поле текущей сущности (например, `{entity.name}`)
- `{copy_source.поле}` — поле исходной сущности при копировании

### Примеры

```yaml
titles:
  create: "Создание новой роли"
  edit: "Редактирование роли: {entity.name}"
  copy: "Копирование роли: {copy_source.name}"
  view: "Просмотр роли (только чтение)"
```

Для документов:
```yaml
titles:
  create: "Новая заметка"
  edit: "Редактировать заметку"
  copy: "Копирование заметки: {copy_source.title}"
  view: "Просмотр заметки (только чтение)"
```

---

## 2.5. Секция `dialog` — геометрия диалога

### Поля

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `width` | `number` | ⚪ | Ширина в пикселях (по умолчанию — стандартная ширина модалки) |
| `min_height` | `number` | ⚪ | Минимальная высота в пикселях |
| `max_height` | `string` | ⚪ | Максимальная высота с прокруткой (например, `"90vh"`) |

### Примеры

```yaml
dialog:
  width: 800
  min_height: 600
```

Простая форма справочника:
```yaml
dialog:
  # Пусто — используются стандартные размеры
```

---

## 2.6. Секция `modes` — режимы работы формы

### Поддерживаемые режимы

| Режим | Описание | Что передаётся в компонент |
|-------|----------|----------------------------|
| `create` | Создание с нуля | `entity = null` (или `initialData = null`) |
| `edit` | Редактирование существующей записи | `entity = объект` (или `initialData = объект`) |
| `copy` | Копирование существующей записи в новую | `copy_source = объект` |
| `view` | Только просмотр (для документов) | `entity = объект`, `readOnly = true` |

### Поля режима `copy`

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `source_prop` | `string` | ✅ | Имя пропа, через который передаётся исходная сущность |
| `name_transform` | `string` | ⚪ | Шаблон трансформации имени (например, `"{name} (копия)"`) |
| `strip_ids_in` | `list[string]` | ⚪ | Список черновиков, где нужно убрать `id` (новые записи) |
| `preserve_fields` | `list[string]` | ⚪ | Поля, сохраняемые из источника (копируются как есть) |
| `reset_fields` | `list[string]` | ⚪ | Поля, сбрасываемые при копировании (не копируются из источника) |
| `close_after_save` | `boolean` | ⚪ | Закрыть ли модалку после сохранения копии |

### Автоматические поведения для режима копирования

Следующее выполняется автоматически и **не нужно указывать** в задании:

1. **Мутация:** всегда используется мутация СОЗДАНИЯ, не обновления. Копия — это новая запись, не изменение существующей.

2. **Контракт доступа** (для `entity_kind: document`):
   - `tenant_id` → из сессии текущего пользователя
   - `author_id` → заполняет бэкенд из сессии
   - `or_tags`, `and_tags` → копируются из источника (если в `preserve_fields`)

3. **Жизненный цикл** (для `entity_kind: document`):
   - `version` → НЕ передаётся (новая запись всегда версия 1)
   - `editing_by_user_id`, `editing_since` → не копируются
   - `created_at/by`, `updated_at/by`, `deleted_at/by` → не копируются (бэкенд заполняет автоматически при создании)
   - `doc_status` → сбрасывается на `"draft"` (если в `reset_fields`)

4. **Индикаторы изменений:** сравниваются с источником копирования (не с пустыми значениями). Кнопка «Сохранить» активна даже при отсутствии изменений — копирование всегда создаёт новую запись.

### Примеры режимов

```yaml
modes:
  create: {}
  edit: {}
  copy:
    source_prop: copyFromRole
    name_transform: "{name} (копия)"
    strip_ids_in: [permissions]
    close_after_save: true
```

Для документов с дополнительными сбросами:
```yaml
modes:
  create: {}
  edit: {}
  copy:
    source_prop: copyFromData
    name_transform: "{name} (копия)"
    reset_fields: [doc_number]         # Номер документа очищается
    preserve_fields: [section_id, or_tags, and_tags]
    close_after_save: true
  view:
    trigger: "entity.is_editing_locked or http_423"
```

Для простой формы без копирования:
```yaml
modes:
  create: {}
  edit: {}
```

---

## 2.7. Секция `data_sources` — источники данных

### Назначение

Описывает данные, которые загружаются при открытии формы и используются для заполнения полей и справочников.

### Поля источника данных

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `endpoint` | `string` | ✅ | Эндпоинт в формате `METHOD /path` |
| `params` | `object` | ⚪ | Параметры запроса с поддержкой интерполяции |
| `provides` | `list[string]` | ✅ | Список переменных, которые предоставляет этот источник |
| `fallback_if_absent` | `string` | ⚪ | Поведение, если эндпоинт не реализован |

### Интерполяция в параметрах

В параметрах поддерживается интерполяция переменных через `{...}`:
- `{имя_переменной}` — переменная из контекста формы
- `{имя_переменной.поле}` — поле объекта

### Примеры

```yaml
data_sources:
  current_user:
    endpoint: GET /auth/user
    provides:
      - current_tenant_id
      - current_tenant_name
      - is_superadmin

  sections:
    endpoint: GET /sections
    params:
      target_tenant_id: "{effective_tenant_id}"
      limit: 1000
    provides: [sections_list]

  regions:
    endpoint: GET /regions          # ⚠️ Зависимость: модуль регионов должен существовать
    params: { limit: 1000 }
    provides: [regions_list]
    fallback_if_absent: |
      Если модуль регионов ещё не реализован — поле region_id
      временно не рендерить (не заменять текстовым полем).
```

---

## 2.8. Секция `tenant_context` — контекст организации (опционально)

### Назначение

Описывает особую логику выбора организации (тенанта) для сущности, которая может принадлежать разным организациям. Это актуально для сущностей, где суперадмин может выбрать целевую организацию.

Если сущность всегда принадлежит организации текущего пользователя (например, документы), секция **не нужна** или упрощена — `tenant_id` берётся из профиля автоматически.

### Подсекция `effective_tenant`

| Поле | Тип | Описание |
|------|-----|----------|
| `priority` | `list[string]` | Приоритет источников для вычисления эффективного `tenant_id`. Первый непустой источник используется. |

### Подсекция `change_allowed_for`

Определяет, кто может менять организацию:
- `superadmin` — только суперадмин
- `admin` — администратор организации
- `any` — любой пользователь
- `none` — смена запрещена (только отображение)

### Подсекция `change_validation`

Проверка при попытке сменить организацию. Если у сущности есть сохранённые связи в других организациях, смена может быть запрещена.

| Поле | Тип | Описание |
|------|-----|----------|
| `reject_if_any_assigned` | `list[string]` | Список связей, наличие которых запрещает смену |
| `rejection_message` | `string` | Текст сообщения об ошибке |
| `on_reject` | `string` | Действие при отказе: `revert_select` (откатить выбор справочника) |

### Подсекция `change_warning`

Предупреждение, показываемое при изменённой, но не сохранённой организации.

### Подсекция `display_as`

Для случаев, когда организация только отображается (не редактируется):
- `readonly_organization_block` — блок с именем организации и пояснением

### Примеры

**Редактируемая организация (для ролей):**
```yaml
tenant_context:
  effective_tenant:
    priority:
      - selected_tenant_id
      - source_entity.tenant_id
      - current_tenant_id

  change_allowed_for: superadmin

  change_validation:
    reject_if_any_assigned:
      - sections
      - permissions
      - users
    rejection_message: |
      Для роли "{entity.name}" уже назначены: {assigned_list}.
      Сначала удалите все назначения.
    on_reject: revert_select

  change_warning: |
    ⚠ Организация изменена. Сохраните роль для применения изменений.
```

**Только чтение (для документов):**
```yaml
tenant_context:
  effective_tenant:
    priority: [current_tenant_id]
  change_allowed_for: none
  display_as: readonly_organization_block
  hint: "Компания будет создана для вашей организации."
```

---

## 2.9. Секция `tabs` — вкладки

### Назначение

Описывает структуру вкладок формы. Каждая вкладка содержит поля и/или части (таблицы, списки).

### Поля вкладки

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `id` | `string` | ✅ | Уникальный идентификатор вкладки |
| `label` | `string` | ✅ | Название вкладки |
| `counter` | `string` | ⚪ | Шаблон счётчика в заголовке вкладки |
| `dirty_indicators` | `list[string]` | ⚪ | Какие индикаторы изменений подсвечивают вкладку |
| `fields` | `list[Field]` | ⚪ | Список полей на вкладке |
| `parts` | `list[Part]` | ⚪ | Список частей (таблицы, черновики) |

### Шаблон `counter`

Поддерживаются переменные в фигурных скобках:
- `{имя_черновика.свойство}` — например, `{sections.count}`, `{permissions.active_count}`, `{users.selected_count}`

### Примеры

```yaml
tabs:
  - id: main
    label: Основное
    dirty_indicators: [basics, tenant]
    fields:
      # ... список полей ...

  - id: permissions
    label: Полномочия
    counter: "{permissions.active_count}"
    dirty_indicators: [permissions]
    parts:
      # ... список частей ...
```

---

## 2.10. Поля вкладки (тип `Field`)

### Общие поля

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `name` | `string` | ✅ | Имя поля (ключ в данных формы) |
| `label` | `string` | ✅ | Метка поля для отображения |
| `type` | `string` | ✅ | Тип поля (см. ниже) |
| `required` | `boolean` | ⚪ | Обязательность поля |
| `placeholder` | `string` | ⚪ | Текст-заполнитель |
| `validation` | `object` | ⚪ | Правила валидации |
| `icon` | `string` | ⚪ | Имя иконки рядом с меткой |
| `default` | `any` | ⚪ | Значение по умолчанию |
| `rows` | `number` | ⚪ | Количество строк для `textarea` |

### Типы полей

| Тип | Компонент | Описание |
|-----|-----------|----------|
| `text` | `Input` | Однострочный текст |
| `textarea` | `Textarea` | Многострочный текст |
| `number` | `Input type="number"` | Число |
| `date` | `Input type="date"` | Календарь |
| `switch` | `Switch` | Булев переключатель |
| `reference_single` | `ReferenceSelect` | Одиночный выбор из справочника |
| `reference_multi_chips` | `ReferenceMultiSelectChips` | Множественный выбор с чипсами |
| `readonly_display` | `div` с рамкой | Только отображение значения |

### Тип `reference_single` и `reference_multi_chips`

Дополнительные поля:

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `source` | `string` | ✅ | Имя источника данных из `data_sources` |
| `dialog_heading` | `string` | ⚪ | Заголовок диалога выбора |
| `limit` | `number` | ⚪ | Максимум элементов для загрузки |
| `columns` | `list[object]` | ⚪ | Дополнительные колонки в диалоге выбора |
| `draft_marks` | `object` | ⚪ | Пометки черновика (для мультивыбора) |

Поле `draft_marks`:

| Подполе | Тип | Описание |
|---------|-----|----------|
| `mark_new` | `boolean` | Помечать добавленные элементы как «новые» (зелёный бейдж) |
| `mark_deleted` | `boolean` | Помечать удалённые элементы как «помеченные на удаление» (красный зачёркнутый + кнопка восстановления) |

### Поведение по правам (`behavior_by_permission`)

Для полей, которые ведут себя по-разному в зависимости от прав пользователя:

| Ключ | Описание |
|------|----------|
| `superadmin` | Поведение для суперадмина |
| `admin` | Поведение для администратора организации |
| `user` | Поведение для обычного пользователя |

Каждое поведение содержит:
- `mode`: `editable` (редактируемое) или `readonly` (только чтение)
- `hint_edit`: текст пояснения при редактировании
- `hint_create`: текст пояснения при создании

### Валидация (`validation`)

| Поле | Тип | Описание |
|------|-----|----------|
| `rule` | `string` | Правило валидации: `min_length`, `max_length`, `range`, `pattern`, `email` |
| `value` | `any` | Значение для правила (например, минимальная длина) |
| `min` | `number` | Минимум для `range` |
| `max` | `number` | Максимум для `range` |
| `message` | `string` | Текст сообщения об ошибке |

### Примеры полей

**Простое текстовое поле:**
```yaml
- name: name
  label: Название роли
  type: text
  placeholder: "Например: Бухгалтер"
  required: true
  validation:
    rule: min_length
    value: 1
    message: "Название обязательно"
```

**Многострочный текст:**
```yaml
- name: description
  label: Описание
  type: textarea
  placeholder: "Описание роли..."
  rows: 3
  required: false
```

**Справочник с поведением по правам:**
```yaml
- name: organization
  label: Организация
  icon: building
  type: reference_single
  source: tenants
  behavior_by_permission:
    superadmin:
      mode: editable
    admin:
      mode: readonly
      hint_edit: "Изменить организацию может только суперадмин."
      hint_create: "Роль будет создана для вашей организации."
```

**Множественный выбор с чипсами:**
```yaml
- name: section_ids
  label: Разделы доступа
  type: reference_multi_chips
  source: sections
  placeholder: "Добавить разделы..."
  dialog_heading: "Доступные разделы"
  limit: 100
  columns:
    - { field: description, label: Описание }
  draft_marks:
    mark_new: true
    mark_deleted: true
```

**Поле документа (раздел):**
```yaml
- name: section_id
  label: Раздел доступа
  type: reference_single
  source: sections
  required: true
  placeholder: "Выберите раздел..."
```

**Дата документа:**
```yaml
- name: doc_date
  label: Дата документа
  type: date
  required: false
```

**Переключатель:**
```yaml
- name: is_customer
  label: Клиент
  type: switch
  default: false
```

**Только чтение (организация):**
```yaml
- name: organization
  label: Организация
  type: readonly_display
  value: "{current_tenant_name}"
```

**Поле с валидацией по маске:**
```yaml
- name: inn
  label: ИНН
  type: text
  placeholder: "10 цифр для юрлица"
  required: false
  validation:
    rule: pattern
    value: "^\d{10}$"
    message: "ИНН юридического лица — 10 цифр"
```

---

## 2.11. Части вкладки (тип `Part`)

### Назначение

Части — это сложные элементы вкладки, которые не являются простыми полями формы: таблицы, черновики, списки.

### Поля части

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `type` | `string` | ✅ | Тип части (см. ниже) |
| `component` | `string` | ⚪ | Имя отдельного компонента для рендеринга |
| `draft_entity` | `string` | ⚪ | Имя черновика для табличных частей |
| `draft_flags` | `object` | ⚪ | Флаги черновика |
| `initial_relation` | `object` | ⚪ | Начальная связь для заполнения черновика |
| `pass_props` | `list[object]` | ⚪ | Пропсы, передаваемые в компонент |
| `loading_state` | `string` | ⚪ | Поведение при загрузке данных |

### Типы частей

| Тип | Описание |
|-----|----------|
| `draft_table` | Таблица с черновиком (новые/удалённые элементы) |
| `readonly_list` | Список только для чтения |
| `inline_form` | Встроенная форма (например, добавление записей) |

### Черновики с флагами (`draft_flags`)

Для табличных частей с черновиком:

| Подполе | Тип | Описание |
|---------|-----|----------|
| `deletion_flag` | `string` | Имя флага пометки на удаление (например, `markedForDeletion`) |
| `new_marker` | `string` | Условие для определения новых записей (например, `"id == null"`) |

### Начальная связь (`initial_relation`)

Определяет, как заполняется черновик при открытии:

| Подполе | Тип | Описание |
|---------|-----|----------|
| `source` | `string` | Источник данных из `data_sources` |
| `condition` | `string` | Условие включения записи (например, `"user.role_ids contains entity.id"`) |

### Пропсы компонента (`pass_props`)

Список пропсов, передаваемых в компонент:

| Подполе | Тип | Описание |
|---------|-----|----------|
| `name` | `string` | Имя пропа |
| `value` | `string` | Значение с интерполяцией |

### Примеры частей

**Таблица-черновик полномочий:**
```yaml
- type: draft_table
  component: PermissionsTab
  draft_entity: permissions
  draft_flags:
    deletion_flag: markedForDeletion
    new_marker: "id == null"
  pass_props:
    - { name: permissions, value: "{permissions_draft}" }
    - { name: tenantId, value: "{effective_tenant_id}" }
    - { name: roleName, value: "{entity.name}" }
```

**Таблица-черновик пользователей с начальной связью:**
```yaml
- type: draft_table
  component: UsersTab
  draft_entity: users
  draft_flags:
    deletion_flag: markedForDeletion
    new_marker: "id not in initial_user_ids"
  initial_relation:
    source: users_list
    condition: "user.role_ids contains entity.id"
  pass_props:
    - { name: users, value: "{users_draft}" }
    - { name: allUsers, value: "{users_list}" }
    - { name: initialUserIds, value: "{initial_user_ids}" }
  loading_state: show_spinner
```

---

## 2.12. Секция `actions` — кнопки-действия

### Поля действия

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `id` | `string` | ✅ | Уникальный идентификатор действия |
| `label` | `string` | ⚪ | Текст кнопки (может быть переопределён `label_rules`) |
| `type` | `string` | ✅ | Тип действия: `submit`, `close`, `custom` |
| `icon` | `string` | ⚪ | Имя иконки |
| `disabled_when` | `string` | ⚪ | Условие недоступности кнопки |
| `hidden_when` | `string` | ⚪ | Условие скрытия кнопки |
| `loading_icon` | `string` | ⚪ | Иконка загрузки |
| `label_rules` | `object` | ⚪ | Правила динамического изменения текста |
| `min_width` | `string` | ⚪ | Минимальная ширина кнопки (против «прыжков» текста) |

### Правила текста кнопки (`label_rules`)

| Подполе | Тип | Описание |
|---------|-----|----------|
| `when` | `string` | Условие для отображения текста `then` |
| `then` | `string` | Текст при выполнении условия |
| `else` | `string` | Текст при невыполнении условия |

### Примеры

**Для справочника с копированием:**
```yaml
actions:
  - id: save
    label: Сохранить
    type: submit
    icon: check
    # Блокируем только при редактировании без изменений.
    # В режиме копирования кнопка активна всегда.
    disabled_when: "not has_any_changes and mode != 'copy'"
    loading_icon: spinner

  - id: cancel
    type: close
    icon: none
    label_rules:
      when: "has_any_changes or mode == 'copy'"
      then: "Отмена"
      else: "Закрыть"
    min_width: 96px
```

**Для документов с режимом `readOnly`:**
```yaml
actions:
  - id: save
    label: Сохранить
    type: submit
    hidden_when: "read_only"         # Не рендерится в режиме просмотра
    disabled_when: "mode == 'edit' and not has_any_changes"

  - id: cancel
    type: close
    label_rules:
      when: "read_only"
      then: "Закрыть"
      else: "Отмена"
    min_width: 96px
```

---

## 2.13. Секция `change_indicators` — индикаторы изменений

### Назначение

Определяет, как вычисляется наличие несохранённых изменений для каждой группы полей. Эти индикаторы используются для:
- Подсветки вкладок символом `*`
- Доступности кнопки «Сохранить»
- Выбора текста кнопки «Отмена»/«Закрыть»

### Поля индикатора

| Поле | Тип | Обязательность | Описание |
|------|-----|:---:|----------|
| `watch` | `list[string]` | ✅ | Какие поля/черновики отслеживать |
| `compare_with` | `object` или `string` | ✅ | С чем сравнивать |
| `mode` | `string` | ✅ | Режим сравнения |
| `only_when` | `string` | ⚪ | Условие применения индикатора |

### Режимы сравнения (`mode`)

| Режим | Описание |
|-------|----------|
| `field_by_field` | Поэлементное сравнение каждого поля |
| `sorted_json` | Сравнение отсортированных массивов через `JSON.stringify` |
| `json_snapshot` | Сравнение с сохранённым снимком через `JSON.stringify` |

### Агрегированный индикатор

```yaml
has_any_changes:
  formula: "basics or tenant or sections or permissions or users"
```

### Примеры

```yaml
change_indicators:
  basics:
    watch: [name, description]
    compare_with:
      name: source_entity.name
      description: source_entity.description
    mode: field_by_field

  sections:
    watch: [section_ids]
    compare_with: source_entity.section_ids
    mode: sorted_json

  permissions:
    watch: [permissions_draft]
    compare_with: permissions_snapshot
    mode: json_snapshot
```

---

## 2.14. Секция `events` — события жизненного цикла

### Назначение

Описывает события, происходящие при открытии, сохранении и закрытии формы.

**Важно:** большинство событий **подразумеваются правилами проекта** и не требуют явного описания. Явное описание нужно только для нестандартных событий.

### Поддерживаемые события

| Событие | Описание |
|---------|----------|
| `on_open` | При открытии модалки |
| `on_save_before` | Перед сохранением (валидации) |
| `on_save_success` | После успешного сохранения |
| `on_save_error` | При ошибке сохранения |
| `on_close` | При закрытии модалки |

### Действия в событиях

| Действие | Описание |
|----------|----------|
| `reset_all_state` | Сброс всех черновиков и флагов |
| `increment_session_key` | Увеличение ключа сессии для перемонта |
| `init_form_from_source` | Инициализация формы из источника |
| `init_*_draft` | Инициализация черновика |
| `invalidate_cache` | Инвалидация кэшей |
| `invalidate_cache_detail` | Инвалидация детальных кэшей (с условием) |
| `refetch_queries` | Повторная загрузка запросов (с фильтром) |
| `update_source_of_truth` | Обновление источника истины |
| `sync_*_draft_from_response` | Синхронизация черновика с ответом |
| `call_parent` | Вызов родительского колбэка |
| `close_modal` | Закрытие модалки |
| `toast` | Показ уведомления (с условием) |
| `toast_error` | Показ уведомления об ошибке |
| `check` | Проверка условия |
| `acquire_editing_lock` | Захват блокировки (для документов) |
| `release_editing_lock` | Освобождение блокировки (для документов) |

### Автоматические события

В зависимости от `entity_kind` некоторые события **добавляются автоматически**:

| Событие | `document` | `reference` |
|---------|:---:|:---:|
| `reset_all_state` при открытии | ✅ | ✅ |
| `init_form_from_source` | ✅ | ✅ |
| `acquire_editing_lock` при открытии | ✅ | ❌ |
| `release_editing_lock` при закрытии | ✅ | ❌ |
| Обработка 409/423 при сохранении | ✅ | ❌ |

### Примеры

**Для справочника с копированием:**
```yaml
events:
  on_open:
    - reset_all_state
    - increment_session_key
    - init_form_from_source
    - init_permissions_draft
    - init_users_draft_when_loaded

  on_save_before:
    - check: effective_tenant_id != null
      on_fail:
        toast_error: "Не выбрана организация для роли"
        abort: true

  on_save_success:
    - invalidate_cache: ["roles"]
    - invalidate_cache_detail:
        when: mode == 'edit'
        keys:
          - ["role", "{entity.id}"]
          - ["permissions", "{entity.id}"]
    - refetch_queries:
        match: "query_key contains 'user'"
    - update_source_of_truth
    - sync_permissions_draft_from_response
    - resync_users_draft
    - call_parent: on_role_saved
    - if: mode == 'copy'
      then: close_modal
    - toast:
        when: "mode == 'copy'"
        text: "Копия роли создана"
        else: "Роль сохранена"

  on_save_error:
    - toast_error: "{error.detail || 'Не удалось сохранить роль'}"

  on_close:
    - reset_form_to_defaults
    - clear_source_of_truth
    - clear_all_drafts
```

**Для документа:**
```yaml
events:
  on_open:
    - reset_all_state
    - init_form_from_source
    # Захват блокировки — автоматически для entity_kind: document

  on_save_before:
    - check: "section_id != ''"
      on_fail:
        toast_error: "Выберите раздел доступа"
        abort: true

  on_save_success:
    - invalidate_cache: ["business-partners-companies"]
    - call_parent: onSaved
    - if: "mode == 'copy'"
      then: close_modal
    - toast:
        when: "mode == 'copy'"
        text: "Копия компании создана"
        else: "Компания сохранена"

  on_save_error:
    - when: "status == 409"
      toast_error: "Карточка изменена другим пользователем. Обновите данные."
    - when: "status == 423"
      toast_error: "Карточка редактируется другим пользователем."
    - otherwise:
        toast_error: "{error.detail || 'Не удалось сохранить компанию'}"

  on_close:
    - reset_form_to_defaults
    # Освобождение блокировки — автоматически (только если захвачена)
```

---

## 2.15. Секция `payload` — структура данных при сохранении

### Назначение

Описывает структуру данных, отправляемых на сервер при сохранении. Это нужно для понимания, какие поля собираются из формы и как они преобразуются.

### Интерполяция и преобразования

Поддерживаются:
- `{form.поле}` — значение поля формы
- `{имя_переменной}` — переменная из контекста
- `{список | filter_by(условие) | map(поле)}` — преобразование списка
- `{поле if условие else значение}` — условное выражение

### Подсекция `mutation_params`

Определяет параметры мутации в зависимости от режима:

| Режим | Описание |
|-------|----------|
| `create` | Только `data` |
| `edit` | `data` + `params` (с идентификатором сущности) |
| `copy` | Только `data` (без идентификатора, так как создаётся новая) |

### Примеры

**Для справочника с черновиками:**
```yaml
payload:
  name: "{form.name}"
  description: "{form.description || ''}"
  tenant_id: "{effective_tenant_id}"
  section_ids: "{section_ids}"
  section_names: "{sections_list | filter_by(section_ids) | map(name)}"

  permissions:
    source: permissions_draft
    filter: "!markedForDeletion"
    map:
      doctype: "{item.doctype}"
      doctype_name: "{item.doctype_name || item.doctype}"
      role_name: "{item.role_name || form.name}"
      tenant_name: "{tenant_name}"
      tenant_id: "{effective_tenant_id}"
      full_access: "{item.full_access}"
      author: "{item.author}"
      reader: "{item.reader}"
      editor: "{item.editor}"
      can_delete: "{item.can_delete}"
      access_by_tags: "{item.access_by_tags}"
      id: "{item.id if exists else omit}"

  user_ids: "{selected_user_ids}"

mutation_params:
  edit:
    data: "{payload}"
    params: { role_id: "{entity.id}" }
  create:
    data: "{payload}"
  copy:
    data: "{payload}"
```

**Для простого документа:**
```yaml
payload:
  name: "{form.name}"
  description: "{form.description || null}"
  section_id: "{form.section_id}"
  doc_number: "{form.doc_number || null}"
  doc_date: "{form.doc_date || null}"
  tenant_id: "{current_tenant_id}"     # Только create; из сессии
  version: "{entity.version}"          # Только update (оптимистическая блокировка)

mutation_params:
  create:
    data: "{payload}"                  # Без version
  edit:
    data: "{payload}"                  # С version
    params: { company_id: "{entity.id}" }
  copy:
    data: "{payload}"                  # Без version (новая запись)
```

---

## 2.16. Автоматические поведения по `entity_kind`

### Для `entity_kind: document`

Автоматически добавляются следующие элементы, которые **не нужно** описывать в задании:

**Поля формы:**
- `section_id` — обязательный `ReferenceSelect` для выбора раздела
- `doc_number` — `Input` для номера документа
- `doc_date` — `Input type="date"` для даты документа

**Поля при создании (на бэкенде):**
- `tenant_id` — из сессии текущего пользователя
- `author_id` — из сессии текущего пользователя

**В модалку:**
- Проп `readOnly?: boolean`
- `<Alert>` при блокировке
- Обработка 409/423 при сохранении

**В страницу списка:**
- Иконка замка при `is_editing_locked`
- Захват/освобождение блокировки при открытии/закрытии

**В `payload` при обновлении:**
- `version` — для оптимистической блокировки

### Для `entity_kind: reference`

Автоматически **не добавляются**:
- Поля `section_id`, `doc_number`, `doc_date`, `version`
- Обработчики блокировок
- Режим `readOnly`
- Обработка 409, 423

Форма работает по стандартному паттерну для справочников.

---

## 2.17. Инструкция по модификации существующей формы

### Общий подход

При доработке существующей формы изменяйте **только затронутые секции**. Не переписывайте весь файл.

### Сценарий 1: Добавить новое поле

**Шаг 1.** Добавьте поле в нужную вкладку в секции `tabs`:

```yaml
- name: priority
  label: Приоритет
  type: number
  placeholder: "Например: 1"
  required: false
  validation:
    rule: range
    min: 1
    max: 100
    message: "Приоритет должен быть от 1 до 100"
```

**Шаг 2.** Добавьте индикатор изменений (если нужно отслеживать):

```yaml
change_indicators:
  basics:
    watch: [name, description, priority]   # ← добавили поле
    compare_with:
      name: source_entity.name
      description: source_entity.description
      priority: source_entity.priority     # ← добавили сравнение
```

**Шаг 3.** Добавьте в `payload`:

```yaml
payload:
  # ... существующие поля ...
  priority: "{form.priority || null}"
```

Остальные секции (`events`, `actions`, `modes`) **не требуют изменений**.

### Сценарий 2: Добавить новую вкладку

Добавьте новую секцию в `tabs`:

```yaml
- id: history
  label: История
  dirty_indicators: []                 # Вкладка не участвует в индикаторах
  parts:
    - type: readonly_list
      component: HistoryTab
      source_endpoint: GET /roles/{id}/history
      columns:
        - { field: changed_at, label: Дата }
        - { field: changed_by, label: Пользователь }
        - { field: action, label: Действие }
```

### Сценарий 3: Изменить режим копирования

Измените секцию `modes.copy`:

```yaml
modes:
  copy:
    source_prop: copyFromRole
    name_transform: "{name} (клон)"      # ← изменили суффикс
    strip_ids_in: [permissions, users]   # ← добавили пользователей
    close_after_save: true
```

### Сценарий 4: Изменить тип сущности

Измените `entity_kind` в `meta`:

```yaml
meta:
  entity_kind: document   # Было: reference
```

Это потребует:
- Добавить поля контракта документов (автоматически)
- Обновить страницу списка для поддержки блокировок
- Обновить бэкенд для поддержки оптимистической и пессимистической блокировок

### Сценарий 5: Добавить режим копирования к существующей форме

**Шаг 1.** Добавьте режим `copy` в `modes`:

```yaml
modes:
  create: {}
  edit: {}
  copy:
    source_prop: copyFromData
    name_transform: "{name} (копия)"
    close_after_save: true
```

**Шаг 2.** Добавьте заголовок в `titles`:

```yaml
titles:
  # ... существующие ...
  copy: "Копирование сущности: {copy_source.name}"
```

**Шаг 3.** Обновите условие кнопки «Сохранить»:

```yaml
actions:
  - id: save
    disabled_when: "not has_any_changes and mode != 'copy'"
```

**Шаг 4.** Добавьте закрытие при копировании в `events.on_save_success`:

```yaml
events:
  on_save_success:
    # ... существующие действия ...
    - if: "mode == 'copy'"
      then: close_modal
```

---

## 2.18. Версионирование формата

| Версия | Изменения |
|--------|-----------|
| `1.0` | Начальная версия: `meta`, `modes`, `data_sources`, `tabs`, `actions`, `change_indicators`, `events`, `payload` |
| `1.1` | Добавлено обязательное поле `entity_kind` в `meta`; добавлена секция `contract_overrides`; уточнены автоматические поведения |
| `1.2` | Добавлен режим `copy` в секцию `modes` с полями `source_prop`, `name_transform`, `strip_ids_in`, `preserve_fields`, `reset_fields`, `close_after_save`; добавлен заголовок `titles.copy`; обновлены условия `actions.save.disabled_when` и `events.on_save_success` для режима копирования |

При изменении формата задания увеличивайте `meta.format_version`. Это позволяет отслеживать, по какой версии формата было создано задание.

---

## 2.19. Что НЕ нужно писать в задании

Следующее покрывается **правилами проекта** и не должно дублироваться:

| Аспект | Какое правило покрывает |
|--------|-------------------------|
| Сброс формы при закрытии (`reset(CREATE_DEFAULTS)`) | Frontend №20 |
| Синхронизация формы при открытии (`useEffect`) | Frontend №37 |
| Порядок при сохранении (`invalidate → close → reset → onSaved`) | Frontend №24 |
| Обработка ошибок через `unknown` | Frontend №36 |
| `ReferenceSelect` с `selectedLabel` | Frontend №27 |
| Денормализация имён (`tenant_name`, `section_name`) | Backend №42 |
| Безопасная обработка ошибок на бэкенде | Backend №36 |
| Мульти-арендная изоляция (`tenant_id` фильтрация) | Backend №26 |
| Именование схем (`CreateSchema`, `UpdateSchema`, `ResponseSchema`) | Backend №21 |
| Пессимистическая блокировка при открытии (для документов) | Frontend №39, Backend №40 |
| Оптимистическая блокировка (`version`) | Backend №40 |

---

## 2.20. Чек-лист перед передачей задания

Перед передачей задания на генерацию формы проверьте:

**Обязательные секции:**
- [ ] `meta` содержит `format_version`, `module`, `component`, `entity`, `entity_type`, `entity_kind`
- [ ] `titles` содержит заголовки для всех поддерживаемых режимов
- [ ] `modes` содержит все поддерживаемые режимы
- [ ] `tabs` содержит хотя бы одну вкладку
- [ ] `actions` содержит кнопки сохранения и отмены

**Консистентность:**
- [ ] Все `endpoint` в `data_sources` существуют в API
- [ ] Все `source` в полях ссылаются на загружаемые данные из `data_sources`
- [ ] Все `watch` поля в `change_indicators` определены в `fields` или `parts`
- [ ] Все переменные в `payload` определены в `data_sources` или форме

**Соответствие типу сущности:**
- [ ] Для `entity_kind: document` — не описаны блокировки вручную (они автоматические)
- [ ] Для `entity_kind: reference` — нет полей `section_id`, `doc_number`, `doc_date` (если они не нужны по бизнес-логике)

**Режим копирования (если присутствует):**
- [ ] `modes.copy` содержит `source_prop`
- [ ] `titles.copy` определён
- [ ] `actions.save.disabled_when` учитывает режим копирования
- [ ] `events.on_save_success` содержит закрытие модалки при копировании (если `close_after_save: true`)

**Отсутствие дублирования:**
- [ ] В задании нет описания технических паттернов проекта
- [ ] В задании нет правил валидации, покрываемых правилами проекта

---

Формат `cool-erp-form v1.2` готов к использованию. Передавайте задания в таком виде, и я буду генерировать формы с первого раза в соответствии с требованиями задания и всеми правилами проекта.