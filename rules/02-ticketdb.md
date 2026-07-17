# TicketDB — система управления тикетами и знаниями

**НЕ ХРАНИ** статусы тикетов и факты в контексте диалога. Вся информация в SQLite БД `tools/ticketdb/tickets.db`.

## CLI (для AI)

```powershell
# Тикеты
python -m tools.ticketdb.cli tickets list                          # все
python -m tools.ticketdb.cli tickets list --status in_progress     # активные
python -m tools.ticketdb.cli tickets list --status pending         # ожидающие
python -m tools.ticketdb.cli tickets get 370-346871                # детали
python -m tools.ticketdb.cli tickets add NEW-ID --status in_progress --product "..." --summary "..."
python -m tools.ticketdb.cli tickets update 370-346871 --status pending --reply-sent 0
python -m tools.ticketdb.cli tickets delete 999-888888

# База знаний
python -m tools.ticketdb.cli kb list                               # все факты
python -m tools.ticketdb.cli kb list --category android            # по категории
python -m tools.ticketdb.cli kb list --search padding              # поиск
python -m tools.ticketdb.cli kb create iridi_script aes_padding --value "PKCS7 only for non-aligned" --source "ticket 971"
python -m tools.ticketdb.cli kb update 1 --value "new value"
```

## API (для пользователя)

```
http://127.0.0.1:7987/api/tickets           GET/POST
http://127.0.0.1:7987/api/tickets/{id}      GET/PUT/DELETE
http://127.0.0.1:7987/api/kb                GET/POST
http://127.0.0.1:7987/api/kb/{id}           GET/PUT/DELETE
http://127.0.0.1:7987/api/kb/categories     GET
http://127.0.0.1:7987/docs                  Swagger UI
```

## Web UI (для пользователя)

```
http://127.0.0.1:7988/                       Dashboard
http://127.0.0.1:7988/tickets                List + filters
http://127.0.0.1:7988/tickets/{id}           Detail + edit/delete
http://127.0.0.1:7988/tickets/new            Create ticket
http://127.0.0.1:7988/kb                     KB list + filters
http://127.0.0.1:7988/kb/{id}                Detail + edit/delete
http://127.0.0.1:7988/kb/new                 Create KB entry
```

## Правила работы

1. **При старте сессии:** `python -m tools.ticketdb.cli tickets list --status in_progress`
2. **Новый тикет:** сразу создать запись в БД + папку `tickets/{case_number}/`
3. **Новое знание:** сразу записать в KB (category: `iridi_script`, `android`, `api`, `general`, `integration`)
4. Файлы `research.md`, `reply_draft.txt` остаются в `tickets/{id}/`, БД хранит метаданные и пути
5. **Статус `completed`:** только пользователь — см. [08-critical.md](08-critical.md)
