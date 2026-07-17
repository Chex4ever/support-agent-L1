# Правила AI-агента Omnigent

Единый источник правил для Cursor, OpenCode и других агентов.

## Порядок чтения

Перед работой над тикетом прочитай файлы **по порядку**:

| # | Файл | Содержание |
|---|------|------------|
| 1 | [01-workflow.md](01-workflow.md) | Старт сессии, чеклист первых 5 минут |
| 2 | [02-ticketdb.md](02-ticketdb.md) | TicketDB: CLI, API, Web UI |
| 3 | [03-research-format.md](03-research-format.md) | Формат `research.md` |
| 4 | [04-factchecking.md](04-factchecking.md) | Фактчекинг перед записью |
| 5 | [05-tools.md](05-tools.md) | Готовые инструменты в `tools/` |
| 6 | [06-ticket-structure.md](06-ticket-structure.md) | Структура папки тикета |
| 7 | [07-bookstack.md](07-bookstack.md) | BookStack KB |
| 8 | [08-critical.md](08-critical.md) | Критические запреты |
| 9 | [09-iridi-script.md](09-iridi-script.md) | iRidi Script ограничения |
| 10 | [10-aes-encryption.md](10-aes-encryption.md) | AES через IR.CreateEncryption |
| 11 | [11-ocr.md](11-ocr.md) | OCR скриншотов |

## Точки входа для агентов

| Агент | Файл | Как подключается |
|-------|------|------------------|
| **Cursor** | [AGENTS.md](../AGENTS.md) | Workspace rules (корень) |
| **Cursor** | [.cursor/rules/](../.cursor/rules/) | `.mdc` с `alwaysApply: true` |
| **OpenCode** | [AGENTS.md](../AGENTS.md) | Корневой AGENTS.md |
| **OpenCode** | [.opencode/AGENTS.md](../.opencode/AGENTS.md) | Дополнительные указания |
| **OpenCode** | [opencode.json](../opencode.json) | `instructions: ["rules/*.md"]` |

## Что НЕ входит в rules/

- **Доменные знания** (факты по продуктам, API) — [bookstack_local/.../omnigent-znaniia-ai-agenta/](../bookstack_local/shelves/baza-znanii-tp/books/omnigent-znaniia-ai-agenta/) и [knowledge_base/](../knowledge_base/)
- **Архитектурный план** — [PLAN.md](../PLAN.md)
- **Документация инструментов** — [tools/README.md](../tools/README.md)

## Обновление правил

1. Редактируй файлы в `rules/` — это единственный источник истины.
2. Не дублируй содержимое в `AGENTS.md` — там только указатель и критические запреты.
3. `.cursor/rules/` и `.opencode/AGENTS.md` — тонкие обёртки, не копии.
