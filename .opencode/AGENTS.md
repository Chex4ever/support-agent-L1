# OpenCode — дополнительные указания

Основные правила проекта: [rules/README.md](../rules/README.md)

OpenCode автоматически подгружает все файлы из `rules/` через [opencode.json](../opencode.json).

## При старте сессии

1. Убедись, что загружены правила из `rules/` (через `opencode.json` → `instructions`)
2. Прочитай [rules/01-workflow.md](../rules/01-workflow.md)
3. Проверь активные тикеты:
   ```powershell
   python -m tools.ticketdb.cli tickets list --status in_progress
   ```

## OpenCode-специфика

- Корневой [AGENTS.md](../AGENTS.md) также загружается OpenCode — не дублируй его содержимое здесь
- Редактируй правила только в `rules/` — этот файл только для OpenCode-специфичных дополнений
- Если нужно добавить правило для всех агентов — создай файл в `rules/`, не пиши сюда

## Связанные файлы

| Файл | Назначение |
|------|------------|
| [rules/](../rules/) | Единый источник правил |
| [AGENTS.md](../AGENTS.md) | Указатель для всех агентов |
| [opencode.json](../opencode.json) | Автозагрузка `rules/*.md` |
| [.cursor/rules/](../.cursor/rules/) | Обёртки для Cursor |
