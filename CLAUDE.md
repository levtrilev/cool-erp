# Правила разработки Cool ERP для ИИ

## 🚨 КРИТИЧЕСКИЕ ТРЕБОВАНИЯ (НЕ НАРУШАТЬ)

1. **Строгая типизация (Pylance strict)**: Любой сгенерированный Python-код ДОЛЖЕН проходить проверку в режиме `python.analysis.typeCheckingMode: "strict"`. НЕ ДОПУСКАЕТСЯ использование `Any`, `type: ignore` (кроме случаев, когда это действительно необходимо), нетипизированных функций и неявных `None`.
2. **Асинхронность**: Весь код бэкенда пишется только на `async/await`. Никаких синхронных вызовов БД или блокирующих операций.
3. **Multi-tenancy (Изоляция)**: Любой SQL-запрос (кроме супер-админа) ОБЯЗАТЕЛЬНО должен содержать фильтр `tenant_id == current_user.tenant_id`. Это Правило №26.
4. **Pydantic v2 + Orval**: Все новые эндпоинты должны иметь `response_model` (Pydantic) и после их создания нужно обновить API-клиент для фронтенда через `npm run api:gen` (Orval).
5. **Проверка перед коммитом**: Перед коммитом ОБЯЗАТЕЛЬНО запускай `npm run build` (для фронтенда) и проверяй, что нет красных подчеркиваний Pylance в бэкенде.

## 📚 Архитектурные правила
- Фреймворки: FastAPI, SQLAlchemy 2.0 (async), Pydantic v2.
- Фронтенд: React, TypeScript, Vite, TanStack Query, shadcn/ui.
- Перед написанием нового кода **ВСЕГДА** проверяй папку `E:\ClaudeCode\projects\cool-erp\doc\Rules` на наличие ТЗ по этому модулю.
- Не оставляй "сгенерированный" код как есть. Доводи его до идеала: добавляй аннотации типов, убирай дубли, обрабатывай ошибки.

## 💡 Примеры "правильного" кода
**Плохо (не пройдет strict):**
```python
def get_user(db, user_id):
    return db.query(User).get(user_id)

## 🗺️ Использование графа знаний (Graphify)

В проекте уже построен граф знаний, который лежит в `E:\ClaudeCode\projects\cool-erp\graphify-out\GRAPH_REPORT.md`.

**ПРАВИЛА РАБОТЫ С ГРАФОМ:**
1. **НИКОГДА** не пытайся запускать `graphify query` или `graphify .` через Bash. Эти команды могут не работать в текущей среде (нет доступа к PATH или venv).
2. **ВСЕГДА** при вопросах об архитектуре, связях между модулями или "бог-узлах" (god nodes) сначала читай файл `E:\ClaudeCode\projects\cool-erp\graphify-out\GRAPH_REPORT.md` (через инструмент `Read`).
3. В `GRAPH_REPORT.md` есть разделы:
   - **God Nodes**: самые связанные узлы (например, `UserProtocol` с 130 связями).
   - **Communities**: логические кластеры (например, "Audit API Generated Types").
   - **Surprising Connections**: неочевидные связи (например, `CRUDCompany` использует `AccessService`).
4. Если тебе нужно посмотреть граф визуально, открой файл `E:\ClaudeCode\projects\cool-erp\graphify-out\graphify-out\graph.html` в браузере.

**Пример правильного ответа:**
> Пользователь: "Как аудит связан с пользователями?"
> Ассистент: *"Согласно `GRAPH_REPORT.md`, модуль аудита (Community 29 - "Access Audit Router") связан с пользователями через `UserProtocol` (god node с 130 связями) и `AuditAccessLog`..."*