# iridi-script-sql-api

**Категория:** iRidi Script
**Источник:** https://dev.iridi.com/JS_Handbook + https://dev.iridi.com/JS_Guide + empirical testing

---

## SQL Object — пользовательская SQLite БД в iRidi Pro Server

В iRidi Pro Server можно создавать и использовать локальную SQLite базу данных через JS-скрипты.

### Создание и открытие БД

```javascript
var db = new SQL();                     // создать объект БД
db.Open("mybase.db", true);             // открыть файл (true = создать если не существует)
db.Open("mybase.db");                   // открыть существующий файл
```

**Важно:**
- Второй аргумент `true` в `Open()` означает "создать файл БД, если не существует".
- Если файл не существует и `true` не передан — `Open()` может не сработать.
- Путь к файлу — относительный (относительно рабочей директории сервера, обычно папка проекта).
- **Рекомендация:** всегда передавайте `true` во избежание ошибок, если БД должна существовать.
- Для надёжности используйте абсолютный путь, если рабочая директория может меняться.

### Выполнение SQL-запросов

```javascript
// Изменение данных (INSERT, UPDATE, DELETE, CREATE, etc.)
db.Execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, ts TEXT, event TEXT)");
db.Execute("INSERT INTO logs (ts, event) VALUES (datetime('now'), 'test')");
db.Execute("UPDATE logs SET event = 'updated' WHERE id = 1");

// Чтение данных (SELECT)
var rs = db.Request("SELECT id, event FROM logs WHERE event = 'test'");
```

### RecordSet — работа с результатами SELECT

```javascript
var rs = db.Request("SELECT id, event FROM logs");

var rowsCount = rs.GetRowsCount();      // количество строк
var value     = rs.GetRowValue(row, col); // значение (row и col — 0-indexed)

// Пример:
for (var i = 0; i < rowsCount; i++) {
    var id    = rs.GetRowValue(i, 0);
    var event = rs.GetRowValue(i, 1);
    IR.Log("Row " + i + ": id=" + id + ", event=" + event);
}

rs.Free();  // ВАЖНО: освободить RecordSet после использования!
```

**Методы RecordSet:**
- `GetRowsCount()` — количество строк
- `GetRowValue(row, col)` — получить значение по индексам (0-based)
- `Free()` — освободить ресурсы (обязательно вызывать!)

### Транзакции

iRidi SQLite поддерживает транзакции. **Настоятельно рекомендуется** оборачивать операции записи в BEGIN/COMMIT для производительности и атомарности:

```javascript
db.Execute("BEGIN");
db.Execute("INSERT INTO logs (ts, event) VALUES (datetime('now'), 'event1')");
db.Execute("INSERT INTO logs (ts, event) VALUES (datetime('now'), 'event2')");
db.Execute("COMMIT");
// или db.Execute("ROLLBACK"); для отката
```

### Закрытие БД

```javascript
db.Close();
```

### Полный пример

```javascript
IR.AddListener(IR.EVENT_START, 0, function() {
    var db = new SQL();
    db.Open("mybase.db", true);

    db.Execute("BEGIN");
    db.Execute("CREATE TABLE IF NOT EXISTS temperature_log (id INTEGER PRIMARY KEY, ts TEXT, zone TEXT, temp REAL)");
    db.Execute("INSERT INTO temperature_log (ts, zone, temp) VALUES (datetime('now'), 'living_room', 22.5)");
    db.Execute("COMMIT");

    db.Close();
});
```

### Работа с БД на разных событиях

SQL API работает на **любых событиях сервера** — `EVENT_START`, `EVENT_TAG_CHANGE`, `EVENT_SCHEDULE_EVENT_CHANGE`, `EVENT_ACCEPT`, `EVENT_AUTHORIZE` и т.д.

```javascript
IR.AddListener(IR.EVENT_TAG_CHANGE, IR.GetServer(), function(name_, value_) {
    var db = new SQL();
    db.Open("mybase.db", true);

    db.Execute("BEGIN");
    db.Execute("INSERT INTO logs (ts, event) VALUES (datetime('now'), '" + name_ + "=" + value_ + "')");
    db.Execute("COMMIT");

    db.Close();
});
```

**Важно:** на `EVENT_TAG_CHANGE` убедитесь, что:
1. Передаётся второй аргумент `true` в `Open()` — если БД не существует.
2. Путь к файлу БД резолвится корректно (используйте абсолютный путь при сомнениях).
3. `IR.GetServer()` как второй аргумент `AddListener` — корректная подписка на все теги сервера.

### IR.GetDatabase() — системная БД (только чтение)

```javascript
var sysdb = IR.GetDatabase();
var rs = sysdb.Request("SELECT * FROM INTEGER_TAG_HISTORY WHERE VALUE > 0 LIMIT 10");
rs.Free();
```

**Внимание:** системная БД — **read-only**. Попытки записи могут привести к неработоспособности сервера.

### ODBC — внешние БД

Для подключения к MySQL, PostgreSQL, Microsoft SQL Server и др. используется `new ODBC()`:

```javascript
var base = new ODBC("user", "password", "MySQL_DSN");
var rs = base.Query("SELECT * FROM table_name");
```

Подробнее: [dev.iridi.com/ODBC](https://dev.iridi.com/ODBC)

### Ограничения

- Файл БД — SQLite3 (встроенный движок).
- **Версия SQLite: 3.8.7** (см. [doc.iridi.com/SWDL/dev-iridi/DB_API/](https://doc.iridi.com/SWDL/dev-iridi/DB_API/)). Это старая версия — многие современные функции SQLite недоступны.
- SQLite не поддерживает хранимые процедуры.
- RecordSet нужно освобождать через `.Free()` — иначе утечка памяти.
- Объект `SQL` живёт только в пределах функции, если не сохранён в глобальную переменную.
- Для хранения между вызовами событий создавайте новое подключение каждый раз.

### Недоступные функции (из-за SQLite 3.8.7)

| Функция | Появилась в | Статус в iRidi |
|---------|-------------|----------------|
| `timediff(A, B)` | 3.43.0 (2023) | **Недоступна** |
| `unixepoch()` | 3.38.0 (2022) | **Недоступна** |
| `auto` модификатор | 3.38.0 (2022) | **Недоступен** |

**Альтернативы для вычисления разницы времени:**

```sql
-- Разница в секундах (через julianday)
SELECT (julianday(Stop) - julianday(Start)) * 86400 AS seconds FROM events;

-- Разница в секундах (через strftime)
SELECT (strftime('%s', Stop) - strftime('%s', Start)) AS seconds FROM events;

-- Разница в минутах
SELECT (strftime('%s', Stop) - strftime('%s', Start)) / 60 AS minutes FROM events;
```

Или вычисление на стороне JavaScript (см. `tickets/207-904103/research.md` — Вариант 3).

### Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| БД не создаётся | `Open()` без `true` | Добавить второй аргумент: `Open("file.db", true)` |
| Не пишет на `EVENT_TAG_CHANGE` | Относительный путь не совпадает | Использовать абсолютный путь |
| RecordSet не возвращает данные | Не вызван `Free()` на предыдущем запросе | Убедиться, что `Free()` вызывается всегда |
| Сервер падает при SQL-запросе | Некорректный SQL или ODBC проблема | Проверить SQL синтаксис, логи сервера |
| `timediff()` — "no such function" | SQLite 3.8.7 не поддерживает `timediff()` | Использовать `julianday()` или `strftime('%s')` |
