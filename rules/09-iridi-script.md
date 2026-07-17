# iRidi Script — ограничения

Перед написанием JS-скрипта **ОБЯЗАТЕЛЬНО** сверься с [knowledge_base/iridi_script_api.md](../knowledge_base/iridi_script_api.md).

## Ключевые ограничения (самые частые ошибки)

| ❌ Нельзя | ✅ Используй |
|----------|-------------|
| `setTimeout()` | `IR.SetTimeout(ms, fn)` |
| `setInterval()` | `IR.SetInterval(ms, fn)` |
| Стрелочные функции | `function() {}` |
| `let` / `const` | `var` |
| `JSON.parse` / `JSON.stringify` | Ручной парсинг или паттерны из KB |
| `console.log` | `IR.Log()` |

## Server Tags

- **Чтение:** `IR.GetVariable("Server.Tags.*")`
- **Запись:** ТОЛЬКО через `IR.GetServer().Set()`

## 🚨 Парсинг числовых токенов

**НИКОГДА** `parseFloat(IR.GetVariable(...)) || default` — при токене `0` сбросит на default.

```javascript
var val = parseFloat(IR.GetVariable("Tokens.MyValue"));
if (isNaN(val)) { val = defaultValue; }
```

## AES

См. [10-aes-encryption.md](10-aes-encryption.md).

## Дополнительные факты

BookStack: `omnigent-znaniia-ai-agenta/pages/iridi-script-*.md`
