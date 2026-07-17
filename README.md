# iRidi Omnigent — AI-агент техподдержки

Система для анализа, классификации и обработки тикетов техподдержки iRidi.
Парсит тикеты из Omnidesk, ищет ответы в базе знаний, формирует рекомендации инженеру.

> **Правила для AI-агентов:** [rules/](rules/README.md) — единый источник для Cursor, OpenCode и других агентов.  
> Точки входа: [AGENTS.md](AGENTS.md) · [.cursor/rules/](.cursor/rules/) · [.opencode/AGENTS.md](.opencode/AGENTS.md) · [opencode.json](opencode.json)

---

## Быстрый старт

```powershell
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Настроить .env (скопировать .env.example,填入 ключи Omnidesk/Redmine)
copy .env.example .env

# 3. Запустить все сервисы
.\start.ps1
```

После запуска:

| Сервис | URL | Описание |
|--------|-----|----------|
| TicketDB API | `http://localhost:7987` | REST API для тикетов и базы знаний (Swagger: `/docs`) |
| TicketDB WebUI | `http://localhost:7988` | Веб-интерфейс управления тикетами и базой знаний |
| L1 Agent WebUI | `http://localhost:7989` | Интерфейс L1-агента: просмотр тикетов Omnidesk + AI-рекомендации |

---

## Архитектура

```
Omnidesk ──▶ L1 Agent (web/) ──▶ TicketDB (tools/ticketdb/)
              │                      ├── SQLite (tickets.db)
              │  классификация       ├── REST API (порт 7987)
              │  + поиск по KB       └── WebUI (порт 7988)
              │
              └── knowledge_base/     — локальная база знаний (MD)
```

### Компоненты

**`web/` — L1 Agent**
- Парсинг тикетов из Omnidesk (API + HTML-скрапинг)
- Классификация: продукт, категория, срочность (regex)
- Поиск по локальной базе знаний
- Формирование рекомендации инженеру
- Веб-интерфейс (порт 7989)

**`tools/ticketdb/` — TicketDB**
- SQLite БД для хранения тикетов и фактов базы знаний
- REST API (порт 7987): CRUD тикетов + KB записей
- WebUI (порт 7988): Bootstrap-дашборд
- CLI: `python -m tools.ticketdb.cli`
- Автозапуск через планировщик Windows

**`tools/` — Вспомогательные инструменты**
- `omnidesk/fetch_messages.py` — получить сообщения тикета
- `omnidesk/download_attachments.py` — скачать вложения (+ OCR)
- `project/analyze_irpz.py` — анализ .irpz проектов
- `image/ocr.py` — распознавание текста со скриншотов (3 движка)
- `script-patterns/` — готовые JS-решения для iRidi Script

**`agent/` — Ядро AI-агента**
- `main.py` — CLI: `python -m agent.main --text "..."` или `--interactive`
- `classifier.py` — классификация по regex-правилам
- `knowledge_base.py` — поиск по MD и CSV
- `recommender.py` — пайплайн анализа

**`knowledge_base/` — База знаний**
- `iridi_script_api.md` — полный API-справочник iRidi Script
- `common_issues.md` — частые проблемы по категориям
- `products/` — документация по продуктам
- `data/products.csv` — каталог продуктов

---

## Работа с тикетами

Подробные правила для AI-агентов: [rules/02-ticketdb.md](rules/02-ticketdb.md), [rules/06-ticket-structure.md](rules/06-ticket-structure.md).

```powershell
python -m tools.ticketdb.cli tickets list --status in_progress
python -m tools.ticketdb.cli tickets get <id>
```

---

## Инструменты (tools/)

См. [rules/05-tools.md](rules/05-tools.md) и [tools/README.md](tools/README.md).

---

## API Endpoints

### TicketDB API (порт 7987)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/tickets` | Список тикетов (фильтр: `?status=in_progress`) |
| POST | `/api/tickets` | Создать тикет |
| GET | `/api/tickets/{id}` | Детали тикета |
| PUT | `/api/tickets/{id}` | Обновить тикет |
| DELETE | `/api/tickets/{id}` | Удалить тикет |
| GET | `/api/kb` | Список записей БЗ |
| POST | `/api/kb` | Создать запись |
| GET | `/api/kb/categories` | Список категорий |
| GET/PUT/DELETE | `/api/kb/{id}` | CRUD записи БЗ |
| GET | `/docs` | Swagger UI |

### L1 Agent API (порт 7989)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/tickets` | Список тикетов из Omnidesk |
| GET | `/tickets/{id}` | Детали + AI-рекомендация |
| GET | `/api/tickets` | JSON-список |
| GET | `/api/tickets/{id}` | JSON-детали + рекомендация |

---

## Тестирование

```powershell
pytest
```

---

## Переменные окружения (.env)

| Переменная | Описание |
|-----------|----------|
| `OMNIDESK_API_KEY` | API-ключ Omnidesk |
| `OMNIDESK_STAFF_EMAIL` | Email для HTTP Basic Auth |
| `OMNIDESK_EMAIL` | Email для HTML-скрапинга |
| `OMNIDESK_PASSWORD` | Пароль для HTML-скрапинга |
| `OMNIDESK_API_BASE` | Базовый URL Omnidesk |
| `REDMINE_API_KEY` | API-ключ Redmine |
| `REDMINE_API_BASE` | Базовый URL Redmine |
| `HOST` | Хост L1 Agent (по умолч. 0.0.0.0) |
| `PORT` | Порт L1 Agent (по умолч. 7989) |
