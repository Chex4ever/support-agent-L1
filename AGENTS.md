# Правила для AI-агента техподдержки iRidi

> **Единый источник правил:** [rules/](rules/README.md)  
> Прочитай все файлы из `rules/` **полностью** перед началом работы над любым тикетом.

## Быстрый старт

1. Прочитай [rules/README.md](rules/README.md) — оглавление
2. Прочитай файлы `rules/01-workflow.md` … `rules/11-ocr.md` по порядку
3. Проверь активные тикеты: `python -m tools.ticketdb.cli tickets list --status in_progress`

## Критические запреты (всегда в силе)

См. полный текст: [rules/08-critical.md](rules/08-critical.md)

- **НИКОГДА** не отправляй ответы клиенту — только `reply_draft.txt`
- **НИКОГДА** не запускай `git clean` — удалит папку `tickets/`
- **НИКОГДА** не ставь тикету статус `completed` — только пользователь
- **НИКОГДА** не удаляй чужие статьи BookStack

## Точки входа по агентам

| Агент | Дополнительно |
|-------|---------------|
| Cursor | [.cursor/rules/](.cursor/rules/) |
| OpenCode | [.opencode/AGENTS.md](.opencode/AGENTS.md), [opencode.json](opencode.json) |

## Что не дублировать здесь

- Workflow, TicketDB, research, tools, BookStack, iRidi Script → всё в `rules/`
- Доменные знания → `knowledge_base/` и BookStack «Omnigent — знания AI-агента»
- Документация инструментов → `tools/README.md`
