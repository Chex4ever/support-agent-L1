# BookStack — база знаний (KB)

**URL:** http://bookstack.mytunnel.org  
**Локальная копия:** `bookstack_local/` (синхронизируй перед работой)

## Правила

1. **🚫 НИКОГДА не удаляй чужие статьи.**
2. **Всегда работай через локальную копию.** Не пиши напрямую в BookStack.
3. **Новое знание → сразу в BookStack.** Не храни в контексте диалога.
4. **Push только своих изменений.** Pull перед началом работы.

## Синхронизация

```powershell
python -m tools.bookstack.sync pull      # скачать всё из BookStack
python -m tools.bookstack.sync push      # загрузить локальные изменения
python -m tools.bookstack.sync status    # показать расхождения
```

## Структура локальной копии

```
bookstack_local/
└── shelves/<shelf_slug>/
    └── books/<book_slug>/
        ├── book.json
        └── chapters/<chapter_slug>/
            ├── chapter.json
            └── pages/<page_slug>.md
```

AI-агент читает `.md` файлы, редактирует их, потом делает `push`.

## Куда писать знания агента

Книга **Omnigent — знания AI-агента**:  
`bookstack_local/shelves/baza-znanii-tp/books/omnigent-znaniia-ai-agenta/`

## API (если нужно напрямую)

```powershell
python -m tools.bookstack.client
python -m tools.bookstack.migrate_kb
python -m tools.bookstack.migrate_kb --apply
```
