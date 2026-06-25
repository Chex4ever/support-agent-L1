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
