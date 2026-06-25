# Omnidesk API Reference

**Base URL:** `https://[domain].omnidesk.ru/api/`  
**Формат:** JSON (`.json` suffix)  
**Аутентификация:** HTTP Basic Auth (`email:api_key`)  
**Лимиты:** 500 запросов/час на сотрудника (мин. 1000), отслеживается через header `api_calls_left`  
**Режим работы агента: ТОЛЬКО ЧТЕНИЕ. Никаких POST/PUT/DELETE — только GET.**

## Аутентификация

```
curl -u staff_email:api_key -H "Content-Type: application/json" -X GET https://domain.omnidesk.ru/api/cases.json
```

API-ключ создаётся в Настройки → API → «добавить API-ключ».

## Обращения (Cases)

### GET /api/cases.json — Получение списка обращений

**Параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| page | number | Номер страницы (1-500) |
| limit | number | Лимит на странице (1-100) |
| user_id | array/number | ID пользователя |
| user_email | array/string | Поиск по email (>=4 символов) |
| user_phone | array/string | Поиск по телефону (>=4 символов) |
| subject | string | Поиск по теме (>=4 символов) |
| staff_id | array/number | ID ответственного сотрудника (0 = без ответственного) |
| group_id | array/number | ID группы |
| channel | array/string | Канал: email, web, call, chat, facebook, telegram, viber, wa_chat и др. |
| priority | array/string | Приоритет: low, normal, high, critical |
| filter | string | ID фильтра |
| status | array/string | Статус: open, waiting, closed |
| labels | array | ID меток для фильтрации |
| sort | string | Сортировка: updated_at_desc/asc, created_at_desc/asc, response_asc/desc, priority_desc/asc, status_asc/desc |
| from_time | string/int | Начало периода по дате создания |
| to_time | string/int | Конец периода по дате создания |
| from_updated_time | string/int | Начало периода по дате обновления |
| to_updated_time | string/int | Конец периода по дате обновления |

**Ответ:** Массив объектов `case` + `total_count`.

**Поля case:**
- `case_id` (int) — ID обращения
- `case_number` (string) — Номер вида "664-245651"
- `subject` (string) — Тема
- `user_id` (int) — ID пользователя
- `staff_id` (int) — ID ответственного сотрудника
- `group_id` (int) — ID группы
- `status` (string) — open / waiting / closed
- `priority` (string) — low / normal / high / critical
- `channel` (string) — Канал обращения
- `recipient` (string) — Email получателя или название канала
- `cc_emails` (string) — Копии
- `bcc_emails` (string) — Скрытые копии
- `deleted` (bool) — В корзине
- `spam` (bool) — Спам
- `created_at` (string) — Дата создания
- `updated_at` (string) — Дата обновления
- `closed_at` (string) — Дата закрытия ("-" если не закрыто)
- `last_response_at` (string) — Время последнего ответа
- `closing_speed` (int/string) — Время закрытия в минутах, "-" если не закрыто
- `language_id` (int) — ID языка
- `custom_fields` (object) — Кастомные поля (ключи вида `cf_25`)
- `labels` (array[int]) — ID меток
- `locked_labels` (array[int]) — Заблокированные метки (от правил/SLA)
- `rating` (string) — Оценка: low/middle/high
- `rating_comment` (string) — Комментарий к оценке
- `rated_staff_id` (int) — ID оценённого сотрудника

### GET /api/cases/[id].json — Просмотр обращения

Детальная информация по одному обращению. Те же поля, что и в списке.

### GET /api/cases/[id]/messages.json — Просмотр сообщений

**Параметры:**
- `page` — номер страницы
- `limit` — лимит (1-100)
- `order` — asc/desc (по умолч. asc)

**Поля message:**
- `message_id` (int)
- `user_id` (int) — ID пользователя (0 если от сотрудника)
- `staff_id` (int) — ID сотрудника (0 если от пользователя)
- `content` (string) — Текст (может быть пустым, если есть content_html)
- `content_html` (string) — HTML-версия
- `attachments` (array) — [{file_id, file_name, file_size, mime_type, url}]
- `note` (bool) — true если это заметка (внутренняя)
- `sent_via_rule` (bool) — отправлено через правило
- `created_at` (string) — время создания
- `sent_at` (string) — время отправки (отличается если отложенная)

### GET /api/cases/[id]/changelog.json — История действий

**Параметры:** page, limit + фильтры: staff, status, subject, group, priority, labels, rules.

## Пользователи (Users)

### GET /api/users.json — Список пользователей

Параметры: page, limit, user_email, user_phone, user_full_name, company_id, created_at_from/to.

**Поля user:**
- `user_id`, `user_full_name`, `user_email`, `user_phone`
- `companies`, `user_custom_id`
- `blocked`, `disabled`, `created_at`, `updated_at`

### GET /api/users/[id].json — Просмотр пользователя

## Компании (Companies)

### GET /api/companies.json — Список компаний
### GET /api/companies/[id].json — Просмотр компании

## Группы (Groups)

### GET /api/groups.json — Список групп
### GET /api/groups/[id].json — Просмотр группы

**Поля group:**
- `group_id`, `group_name`, `group_active`, `sort_order`

## Сотрудники (Staff)

### GET /api/staff.json — Список сотрудников

Параметры: page, limit, staff_email, staff_group_id, staff_active.

**Поля staff:**
- `staff_id`, `staff_email`, `staff_full_name`, `staff_group_id`
- `staff_mobile`, `staff_active`, `staff_role`
- `created_at`, `updated_at`

### GET /api/staff/[id].json — Просмотр сотрудника

## Метки (Labels)

### GET /api/labels.json — Список меток

**Поля label:**
- `label_id`, `label_title`, `label_color`, `label_active`

### GET /api/labels/[id].json — Просмотр метки

## База знаний (KB)

### GET /api/kb/categories.json — Категории
### GET /api/kb/categories/[id].json — Категория
### GET /api/kb/sections.json — Разделы
### GET /api/kb/sections/[id].json — Раздел
### GET /api/kb/articles.json — Статьи
### GET /api/kb/articles/[id].json — Статья

## Email-адреса

### GET /api/emails.json — Список email-адресов

## Кастомные поля

### GET /api/custom_fields.json — Список кастомных полей

## Кастомные каналы

### GET /api/custom_channels.json — Список кастомных каналов

## Языки

### GET /api/languages.json — Список языков

## Фильтры

### GET /api/filters.json — Фильтры сотрудника

## Шаблоны (Macros)

### GET /api/macros.json — Список шаблонов

## Статистика

### GET /api/stats/leaderboard.json — Лучшие в команде
### GET /api/stats/ratings.json — Оценки качества
### GET /api/stats/staff_statuses.json — Статусы сотрудников

## МЕТОДЫ, ЗАПРЕЩЁННЫЕ ДЛЯ АГЕНТА (write operations)

Следующие методы **НЕ ИСПОЛЬЗОВАТЬ** — агент работает только в режиме чтения:

- POST /api/cases.json — создание обращения
- POST /api/cases/[id]/messages.json — добавление ответа
- POST /api/cases/[id]/note.json — добавление заметки
- PUT /api/cases/[id].json — изменение обращения
- PUT /api/cases/[id]/messages/[mid].json — редактирование ответа
- DELETE /api/cases/[id]/messages/[mid].json — удаление ответа
- PUT /api/cases/[id]/trash.json — удаление в корзину
- PUT /api/cases/[id]/spam.json — пометить спамом
- PUT /api/cases/[id]/restore.json — восстановление
- DELETE /api/cases/[id].json — полное удаление
- и любые другие POST/PUT/DELETE методы для пользователей, компаний, групп, сотрудников, меток, БЗ и т.д.
