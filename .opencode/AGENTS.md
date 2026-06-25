# Правила для агента

## Скриптинг в iRidi Studio

Перед тем как писать любой JS-скрипт для iRidi Studio (панельного или серверного проекта), **ОБЯЗАТЕЛЬНО** сверяйся с документом `knowledge_base/iridi_script_api.md`.

### Ключевые ограничения (самые частые ошибки):
- **НЕТ** `setTimeout()` — используй `IR.SetTimeout(ms, fn)`
- **НЕТ** `setInterval()` — используй `IR.SetInterval(ms, fn)`
- **НЕТ** стрелочных функций — используй `function() {}`
- **НЕТ** `let`/`const` — используй `var`
- **НЕТ** `JSON.parse`/`JSON.stringify` — передавай данные без JSON
- **НЕТ** `console.log` — используй `IR.Log()`
- **Для Server Tags: чтение через `IR.GetVariable("Server.Tags.*")`, запись ТОЛЬКО через `IR.GetServer().Set()`** (не `IR.SetVariable`)
- **🚨 НИКОГДА не используй `parseFloat(IR.GetVariable(...)) || default`** — когда токен равен `0`, `||` сбросит на default. Используй `isNaN()`. См. `knowledge_base/iridi_script_api.md` раздел про ловушки.
