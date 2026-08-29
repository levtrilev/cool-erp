# Cool ERP

[![GitHub license](https://img.shields.io/github/license/levtrilev/cool-erp)](LICENSE)
<!-- [![GitHub stars](https://img.shields.io/github/stars/levtrilev/cool-erp)](https://github.com/levtrilev/cool-erp/stargazers) -->

**Cool ERP** (https://coolerp.ru) — это модульная, легко расширяемая ERP-система с открытым кодом, специально адаптированная для надежной ИИ-генерации новых функций. Монорепозиторий FastAPI/Orval + Vite/React/TailwindCSS/TanStackQuery.

🌐 **Официальный сайт проекта:** [coolerp.ru](https://coolerp.ru) (under construction)

---

## 🚀 Основные возможности (under construction)

* **Управление складом:** учет остатков, перемещения, инвентаризация.
* **CRM-модуль:** ведение базы клиентов, история взаимодействия, воронка продаж.
* **Финансы:** контроль доходов и расходов, аналитические отчеты.
* **Интеграции:** поддержка сторонних сервисов по API.

---

## 🛠️ Стек технологий

* **Backend:** FastAPI/Orval
* **Frontend:** Vite/React/TailwindCSS/TanStackQuery
* **База данных:** PostgreSQL

---

## 📦 Быстрый старт (under construction)

### Требования (under construction)
Перед началом убедитесь, что у вас установлены:
* Node.js (версии 18 и выше)
* Docker (опционально)

### Установка (under construction)

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/levtrilev/cool-erp.git
   cd coolerp
   ```

2. Установите зависимости:
   ```bash
   npm install
   ```

3. Настройте конфигурацию:
   Создайте файл `.env` на основе примера `.env.example` и укажите ваши настройки БД.(under construction)

4. Запустите проект в режиме разработки:
   ```bash
   npm run dev
   ```

---

## 🗺️ Дорожная карта (Roadmap) (under construction)

- [x] Разработка базового модуля CRM
- [x] Интеграция с базой данных
- [ ] Запуск складского модуля (в процессе)
- [ ] Мобильное приложение

---

## 🤝 Участие в разработке (Contributing)

Мы рады любому вкладу в развитие проекта! Чтобы внести изменения:
1. Сделайте форк репозитория.
2. Создайте ветку для вашей фичи (`git checkout -b feature/AmazingFeature`).
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`).
4. Отправьте ветку в origin (`git push origin feature/AmazingFeature`).
5. Откройте Pull Request.

---

## 📄 Лицензия

Этот проект распространяется под лицензией **MIT**. Подробности в файле [LICENSE](LICENSE).

---

## 📞 Контакты

* **Email:** levtrishankov@yandex.ru
* **Telegram:** [@coolerp_community](https://t.me/coolerp) (under construction)

## Кратко резюмируем, что у нас работает (27.08.2026):
✅ FastAPI отдает OpenAPI-схему и корректно обрабатывает CORS.
✅ Orval автоматически генерирует строгие TypeScript-типы, Zod-схемы валидации и React Query хуки.
✅ React Hook Form + Zod перехватывают и валидируют ввод на клиенте до отправки.
✅ TanStack Query управляет состоянием запроса (loading, error, success).
✅ React Router управляет навигацией и редиректом после успеха.
✅ shadcn/ui + Tailwind обеспечивают красивый и доступный интерфейс