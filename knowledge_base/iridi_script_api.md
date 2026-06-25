# iRidi Script API — полный справочник

> Версия JS: **ECMAScript 3** (ES3). Никаких стрелочных функций, `let`/`const`, `class`, `Promise`, `async/await`.
> Обновлено: 25.06.2026

---

## 1. Ограничения (ЧТО НЕ РАБОТАЕТ)

| Конструкция | Статус | Альтернатива |
|------------|--------|--------------|
| `setTimeout(fn, ms)` | **НЕТ** | `IR.SetTimeout(ms, fn)` |
| `setInterval(fn, ms)` | **НЕТ** | `IR.SetInterval(ms, fn)` |
| `clearInterval(id)` | **НЕТ** | `IR.ClearInterval()` |
| Стрелочные функции `() => {}` | **НЕТ** | `function() {}` |
| `let` / `const` | **НЕТ** | `var` |
| `class` / `extends` | **НЕТ** | function-конструкторы |
| `Promise` / `async/await` | **НЕТ** | — |
| `import` / `export` / `require` | **НЕТ** | `module.Import()` (только для модулей) |
| `JSON.parse` / `JSON.stringify` | **НЕТ** | — |
| `fetch` / `XMLHttpRequest` | **НЕТ** | — |
| `localStorage` / `sessionStorage` | **НЕТ** | — |
| `console.log` | **НЕТ** | `IR.Log()` |
| `window` / `document` / DOM | **НЕТ** | — |
| `Math.random` | ДА | но не криптостойкий |
| `Math.sin/cos` | **ДА** | |
| `Date.now` / `new Date().getTime()` | **ДА** | |
| `Array.map/filter/reduce` | **ДА** | |
| `String.charAt/charCodeAt` | **ДА** | |
| `parseInt/parseFloat` | **ДА** | |
| `String/Number/Boolean` | **ДА** | |
| `typeof` / `instanceof` | **ДА** | |

---

## 2. Systems API — таймеры, логи, система

### IR.SetTimeout
```javascript
IR.SetTimeout(delay_ms, callback_function);
```
Выполняет `callback_function` **один раз** через `delay_ms`. Возврата ID нет.

**Пример:**
```javascript
IR.AddListener(IR.EVENT_START, 0, function() {
    IR.SetTimeout(1000, function() {
        IR.Log("Прошла 1 секунда");
    });
});
```

### IR.SetInterval
```javascript
IR.SetInterval(interval_ms, callback_function);
```
Выполняет `callback_function` **повторно** каждые `interval_ms`.

**Пример:**
```javascript
IR.AddListener(IR.EVENT_START, 0, function() {
    IR.SetInterval(1000, function() {
        IR.Log("Tick");
    });
});
```

### IR.ClearInterval
```javascript
IR.ClearInterval();
```
Останавливает **все** интервалы, запущенные через `IR.SetInterval()`.
⚠️ Нет возможности остановить конкретный интервал (нет ID).

### IR.AddListener
```javascript
IR.AddListener(event, object_or_0, callback_function);
```
Подписка на событие.

### IR.RemoveListener
```javascript
IR.RemoveListener(event, object_or_0, callback_function);
```
Отписка от события.

### IR.Log
```javascript
IR.Log(value);
```
Вывод в консоль отладки (Windows — F4 в эмуляторе).

### IR.Exit
```javascript
IR.Exit();
```
Закрытие приложения (Android, Windows). На iOS не работает.

### IR.HWID
```javascript
var hwid = IR.HWID;  // строка
```
HWID (UDID) устройства.

### IR.GetSystemInfo
```javascript
var info = IR.GetSystemInfo();  // объём памяти и пр.
```

### IR.Execute
```javascript
IR.Execute(path_to_program);
```
Запуск внешней программы (только где возможно).

### IR.StartAction
```javascript
IR.StartAction("ActionName");
```
Запуск макроса из проекта.

### IR.ShowSystemMenu
```javascript
IR.ShowSystemMenu();
```
Открыть системное меню (требует пароль инженера).

### IR.ShowKeyboard
```javascript
IR.ShowKeyboard(type);
// type = 1 — алфавит, 2 — цифры, 0 — скрыть (iOS)
```

### IR.CalculateHash
```javascript
var hash = IR.CalculateHash(mode, string);
// mode = IR.HASH_MD5, IR.HASH_SHA1, IR.HASH_SHA256, IR.HASH_SHA512
```

### IR.Tween
```javascript
var value = IR.Tween(formula, current_time, start_value, end_value, duration);
// formula:
//   0 = TWEEN_LINEAR
//   1 = TWEEN_SINE_IN
//   2 = TWEEN_SINE_OUT
//   3 = TWEEN_SINE_IN_OUT
//   4 = TWEEN_QUINT_IN
//   5 = TWEEN_QUINT_OUT
//   6 = TWEEN_QUINT_IN_OUT
```

---

## 3. События (Events)

| Константа | Когда срабатывает |
|-----------|------------------|
| `IR.EVENT_START` | При запуске приложения (один раз) |
| `IR.EVENT_WORK` | Постоянно, пока приложение работает. В callback приходит `time` (ms с прошлого вызова) |
| `IR.EVENT_EXIT` | При закрытии приложения |
| `IR.EVENT_ORIENTATION` | При повороте экрана |
| `IR.EVENT_KEYBOARD_SHOW` | При открытии клавиатуры |
| `IR.EVENT_ITEM_PRESS` | При нажатии на элемент |
| `IR.EVENT_ITEM_RELEASE` | При отпускании элемента |
| `IR.EVENT_ITEM_HOLD` | При удержании элемента |
| `IR.EVENT_ITEM_END_HOLD` | При окончании удержания |
| `IR.EVENT_ITEM_CHANGE` | При изменении значения элемента |
| `IR.EVENT_TAG_CHANGE` | При изменении тега (фидбек) |
| `IR.EVENT_RECEIVE_TEXT` | При получении данных от драйвера |
| `IR.EVENT_ADD_SUBDEVICE` | При создании подустройства (модули) |
| `IR.EVENT_MODULE_START` | При старте модуля |

### EVENT_WORK — альтернатива таймеру
```javascript
var accumulator = 0;
IR.AddListener(IR.EVENT_WORK, 0, function(time) {
    accumulator += time;
    if (accumulator >= 1000) {
        IR.Log("Прошла ~1 секунда");
        accumulator = 0;
    }
});
```
`time` — число ms, прошедших с прошлого вызова (зависит от нагрузки устройства).

---

## 4. Tokens API — чтение/запись переменных

### IR.GetVariable
```javascript
var val = IR.GetVariable("Full.Path.To.Token");
```
Пути:
- `System.*` — системные токены (Update, Online, и т.д.)
- `Global.*` — Project Tokens (КУ/КОС)
- `Drivers.DriverName.*` — токены драйвера
- `UI.PageName.ItemName` — GUI-теги
- `UI.PageName.ItemName.Value` — значение элемента

### IR.SetVariable
```javascript
IR.SetVariable("Full.Path.To.Token", value);
```
Создаёт токен, если его нет.

### Доступ к тегам через path
```javascript
// Upload mode
var update = IR.GetVariable("System.Update");

// Project token
var myVar = IR.GetVariable("Global.MyVar");
IR.SetVariable("Global.MyVar", 42);

// Driver token
var online = IR.GetVariable("Drivers.Modbus RTU.Line_1.Online");

// GUI tag
var text = IR.GetVariable("UI.Page 1.Item 1.Text");
```

---

## 5. GUI API — работа с элементами

### Навигация
```javascript
IR.ShowPage("PageName");         // открыть страницу
IR.HidePage("PageName");         // закрыть страницу
IR.ShowPopup("PopupName");       // открыть попап
IR.HidePopup("PopupName");       // закрыть попап
IR.HideAllPopups();              // закрыть все попапы
```

### Получение объектов
```javascript
var page = IR.GetPage("PageName");
var popup = IR.GetPopup("PopupName");
var item = IR.GetItem("PageName").GetItem("ItemName");
var state = item.GetState(0);
```

### Свойства элементов
```javascript
item.X = 100;                    // позиция X
item.Y = 200;                    // позиция Y
item.Width = 300;                // ширина
item.Height = 150;               // высота
item.Opacity = 255;              // прозрачность (0-255)
state.FillColor = 0xFF0000FF;    // цвет заливки (ARGB)
state.BorderColor = 0x00FF00FF;  // цвет границы
state.Text = "Hello";            // текст
state.TextColor = 0xFFFFFFFF;    // цвет текста
```

### Создание элементов
```javascript
var newItem = IR.CreateItem(IR.ITEM_BUTTON, "Button 1", 30, 40, 800, 150);
// Типы: IR.ITEM_BUTTON, IR.ITEM_LEVEL, IR.ITEM_TRIGGER_BUTTON,
//       IR.ITEM_MUTI_STATE_BUTTON, IR.ITEM_UPDOWN_BUTTON, IR.ITEM_EDIT_BOX,
//       IR.ITEM_LIST, IR.ITEM_JOYSTICK, IR.ITEM_MUTI_STATE_LEVEL
```

---

## 6. Sound API — работа со звуком

```javascript
IR.SoundPlay("sound_name", slot, volume, loop);
IR.SoundStop(slot);
IR.SoundStopAll();
IR.SoundVolume(slot, volume);  // 0.0 — 1.0
```

---

## 7. Server API (init.js) — особенности серверных скриптов

При написании **серверного проекта (init.js)** на iRidi Server:

- Тот же ES3 движок, те же ограничения
- Доступны `IR.GetVariable` и `IR.SetVariable`
- IR.SetInterval / IR.SetTimeout **работают**
- GUI API **НЕ ДОСТУПЕН** — нет страниц, попапов, кнопок
- `IR.Log()` работает в лог сервера
- `require()`, `fs`, `http` из Node.js **НЕ ДОСТУПНЫ**
- Таймер — единственный источник периодичности: `IR.SetInterval` или `EVENT_WORK+аккумулятор`

### Типовой шаблон серверного скрипта
```javascript
IR.AddListener(IR.EVENT_START, 0, function() {
    IR.SetInterval(1000, function() {
        var val = parseFloat(IR.GetVariable("Global.myTag")) || 0;
        IR.SetVariable("Global.myTag", val + 1);
    });
});
```

### Альтернатива через EVENT_WORK (без SetInterval)
Если `IR.SetInterval` по какой-то причине недоступен:
```javascript
var timer = 0;
var INTERVAL = 1000;

IR.AddListener(IR.EVENT_START, 0, function() {
    IR.AddListener(IR.EVENT_WORK, 0, function(time) {
        timer += time;
        if (timer >= INTERVAL) {
            timer = 0;
            // ... твой код
        }
    });
});
```

---

## 8. Лицензия (License API)

```javascript
IR.License;                     // true/false — есть ли лицензия
IR.LicenseVersion;              // версия
IR.LicenseHardwareID;           // HWID лицензии
```

---

## 9. Полезные примеры

### Таймер с самокоррекцией (точный)
```javascript
var start = new Date().getTime();
var elapsed = 0;

function instance() {
    elapsed += 100;
    var diff = (new Date().getTime() - start) - elapsed;
    if (diff < 10) diff = 10;
    IR.SetTimeout(100 - diff, instance);
}
IR.SetTimeout(100, instance);
```

### debounce для частых событий
```javascript
var debounceTimer = 0;
function onTagChange() {
    if (debounceTimer) {
        IR.ClearInterval();
        debounceTimer = 0;
    }
    debounceTimer = 1;
    IR.SetTimeout(300, function() {
        debounceTimer = 0;
        // реальное действие
    });
}
```

---

## 10. Чек-лист «Чего НЕТ в iRidi Script»

Перед тем как писать JS-скрипт, проверь:

- [ ] Нет `setTimeout` — используй `IR.SetTimeout`
- [ ] Нет `setInterval` — используй `IR.SetInterval`
- [ ] Нет стрелочных функций — пиши `function(){}`
- [ ] Нет `let`/`const` — используй `var`
- [ ] Нет `JSON` — думай как передавать данные без него
- [ ] Нет `console.log` — используй `IR.Log`
- [ ] Нет `fetch`/`XMLHttpRequest` — сетевые запросы только через драйверы
- [ ] Нет `class` — используй функции-конструкторы
- [ ] Нет DOM — только GUI API через `IR.GetItem`

---

*Источники: wiki2.iridiummobile.net (Systems API, Characteristics of iRidium Script, IRidium Script API), dev.iridi.com (JS Guide, Handbook), blog.iridi.com.*
