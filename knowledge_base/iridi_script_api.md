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
| `JSON.parse` / `JSON.stringify` (camelCase) | **НЕТ** | Используй `JSON.Parse()` / `JSON.Stringify()` (PascalCase) |
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
- `Global.*` — Project Tokens (Токены проекта)
- `Server.Tags.*` — **виртуальные тэги сервера** (в серверном проекте)
- `Drivers.DriverName.*` — токены драйвера
- `UI.PageName.ItemName` — GUI-теги
- `UI.PageName.ItemName.Value` — значение элемента

### IR.SetVariable
```javascript
IR.SetVariable("Full.Path.To.Token", value);
```
Создаёт токен, если его нет. **Работает только для `Global.*` (Project Tokens).**
⚠️ Для записи виртуальных тэгов сервера (`Server.Tags.*`) НЕ ИСПОЛЬЗУЕТСЯ.

### 🚨 Ловушка: `|| default` с числовыми токенами
```javascript
var ph = parseFloat(IR.GetVariable("Server.Tags.phase")) || 60;  // БАГ!
```
Когда фаза дойдёт до 360 и сбросится в 0, `parseFloat("0")` вернёт `0`, `0 || 60` даст `60` — сброс значения.
**Всегда используй `isNaN()` для проверки:**
```javascript
var ph = parseFloat(IR.GetVariable("Server.Tags.phase"));
if (isNaN(ph)) ph = 60;  // только если реально нет значения
```

### IR.GetServer().Set — запись виртуальных тэгов сервера
```javascript
IR.GetServer().Set("TagName", value);
var val = IR.GetServer().Get("TagName");
```
**Только в серверном проекте (init.js).** Запись и чтение виртуальных тэгов сервера (Server Tags).
Виртуальные тэги сервера доступны на чтение также через `IR.GetVariable("Server.Tags.TagName")`,
НО запись — только через `IR.GetServer().Set()`.

### Доступ к тегам через path
```javascript
// System Tokens
var update = IR.GetVariable("System.Update");

// Project Tokens (Токены проекта)
var myVar = IR.GetVariable("Global.MyVar");
IR.SetVariable("Global.MyVar", 42);

// Server virtual tags (только серверный проект)
var t1 = IR.GetVariable("Server.Tags.sin1");  // чтение
var t2 = IR.GetServer().Get("sin1");           // чтение (альтернатива)
IR.GetServer().Set("sin1", 3.14);              // запись — ТОЛЬКО ТАК

// Driver token
var online = IR.GetVariable("Drivers.Modbus RTU.Line_1.Online");

// GUI tag (только панельный проект)
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

## 7. Encryption API — шифрование

### IR.CreateEncryption
```javascript
var aes = IR.CreateEncryption(IR.ENCRYPTION_AES, {
    "Vector": "hex_iv_bytes_separated_by_commas",
    "Key": "hex_key_bytes_separated_by_commas",
    "Type": 0  // 0=CBC, 1=ECB
});
```

### .Encode / .Decode
```javascript
var encrypted = aes.Encode(data, resultType, inputType);
var decrypted = aes.Decode(data, resultType, inputType);
```

- `data` — Array (байты) или String (comma-separated decimal)
- `resultType` — `IR.RESULT_TYPE_ARRAY`, `IR.RESULT_TYPE_STRING`, `IR.BASE64_STRING`

### Важные особенности (экспериментально, build 1.3.87.42647)

**Padding:** iRidi дополняет данные до 16 байт (PKCS7), но ТОЛЬКО если
длина не кратна 16. Для aligned данных (кратно 16) — padding не добавляется.

  | Вход | Выход | Поведение |
  |------|-------|-----------|
  | 1 байт `[0x01]` | 16 | PKCS7 добавлен `0x0F`×15 |
  | 15 байт | 16 | PKCS7 добавлен `0x01`×1 |
  | 16 байт | 16 | padding не добавлен |
  | 12 + ручной PKCS7 | 16 | совместимо со стандартным PKCS7 |

Это НЕ стандартный PKCS7 (RFC 2315 §10.3 требует ВСЕГДА добавлять
padding, включая полный блок 0x10 для aligned данных). iRidi пропускает
финализацию для уже выровненных данных.

**Важно:** `.Decode()` уже автоматически стриппит PKCS7 padding.
При расшифровке внутри iRidi не нужно дополнительно удалять padding.

**Рекомендация:** Всегда делайте ручной PKCS7 padding перед `.Encode()`:
```javascript
var padLen = 16 - (data.length % 16);
for (var i = 0; i < padLen; i++) data.push(padLen);
```
После этого ciphertext совместим с любым AES-128-CBC-PKCS7 дешифратором.
Для расшифровки внутри iRidi используйте `.Decode()` с `inputType`:
```javascript
var dec = aes.Decode(cipherBytes, IR.RESULT_TYPE_ARRAY, IR.RESULT_TYPE_ARRAY);
// dec уже содержит чистые данные без padding
```

**Формат Key/Vector:** hex-байты через запятую.
  `"60,25,57,cd"` = байты `[0x60, 0x25, 0x57, 0xcd]`.
  НЕ десятичные числа! Строка `"1,2,3"` = байты `[0x01, 0x02, 0x03]`.

**Под капотом:** используется OpenSSL (`libcrypto-1_1-x64.dll` в
составе Studio64). iRidium64.exe импортирует `EVP_CIPHER_CTX_set_padding`
из неё.

### IR.CalculateHash
```javascript
var hash = IR.CalculateHash(mode, string);
// mode = IR.HASH_MD5, IR.HASH_SHA1, IR.HASH_SHA256, IR.HASH_SHA512
```

## 8. Push API — push-уведомления

### IR.SendPush
```javascript
IR.SendPush(title, js_data, group_id, status_callback, this_ptr, sound_type);
```
Отправляет push-уведомление (FCM/APNs) на панели i3 Pro из серверного скрипта (init.js).
**Только для iRidium Server!**

**Параметры (6 штук):**

| # | Параметр | Тип | Описание |
|---|----------|-----|----------|
| 1 | `title` | String | Текст уведомления |
| 2 | `js_data` | String | Данные для JS-скрипта на принимающей панели (строка или JSON) |
| 3 | `group_id` | Number | ID группы панелей из iRidi Cloud (Users & Panels). `0` = всем группам |
| 4 | `status_callback` | Function | **Колбек логирования результата!** Получает `object.Error` (0=успех) и `object.ErrorDescription` |
| 5 | `this_ptr` | this | Указатель на окружение, доступен в status_callback как `this` |
| 6 | `sound_type` | Number | `0` = короткий звук (по умолч.), `1` = длинный звук |

**Ограничения:**
- iOS: до 2 КБ на уведомление
- Android: до 4 КБ на уведомление
- Символы `&` и `#` **НЕ ПОДДЕРЖИВАЮТСЯ** в title и js_data

### Push Groups

**Группы панелей настраиваются В ЛИЧНОМ КАБИНЕТЕ iRidi Cloud** (НЕ в приложении):
- Объект → Users & Panels → создать/редактировать группу
- Группа привязывается к «пользователь + проект» (автоматически для всех панелей)
- Можно привязать к HWID конкретной панели

### Примеры

```javascript
// Простой push (только текст)
IR.SendPush("Дверь открыта", "", 1, null, this, 0);

// Push с status_callback — логирование результата отправки
IR.SendPush("Дверь открыта", "", 1, function(obj) {
    IR.Log("Push result: code=" + obj.Error + " desc=" + obj.ErrorDescription);
    // obj.Error = 0  → успех (push ушёл в FCM/APNs)
    // obj.Error > 0  → ошибка (obj.ErrorDescription — текст)
}, this, 0);

// Аварийный push — всем группам + длинный звук + данные для панели
IR.SendPush("ПОЖАР!", "fire_alarm", 0, function(obj) {
    IR.Log("Fire push: " + obj.Error + " - " + obj.ErrorDescription);
}, this, 1);
```

### Приём push на панели (IR.EVENT_RECEIVE_PUSH_NOTIFY)

```javascript
// Только для i3 Pro (НЕ сервер!)
IR.AddListener(IR.EVENT_RECEIVE_PUSH_NOTIFY, 0, function(text, data, group) {
    IR.Log("Push received: " + text + " data=" + data + " group=" + group);
    if (data === "fire_alarm") { IR.ShowPage("Alarm"); }
});
```

**Источники:** [dev.iridiummobile.net/Push_API/en](https://dev.iridiummobile.net/Push_API/en), ticket #763-321866

---

## 9. JSON API — работа с JSON

В iRidi Script JSON API использует PascalCase (не camelCase, как в стандартном JS):

| Метод | Описание |
|-------|----------|
| `JSON.Parse(str)` | Преобразует строку в JSON-объект |
| `JSON.Stringify(obj)` | Преобразует JSON-объект в строку |

### Пример
```javascript
var text = '{"firstName": "Peter","lastName": "Smirnoff"}';
var obj = JSON.Parse(text);
IR.Log(obj.lastName); // "Smirnoff"
var str = JSON.Stringify(obj);
```

**Источник:** `wiki2.iridiummobile.net/JSON_objects`

---

## 10. Server API (init.js) — особенности серверных скриптов

При написании **серверного проекта (init.js)** на iRidi Server:

- Тот же ES3 движок, те же ограничения
- Доступны `IR.GetVariable` и `IR.SetVariable` (только для `Global.*`)
- IR.SetInterval / IR.SetTimeout **работают**
- GUI API **НЕ ДОСТУПЕН** — нет страниц, попапов, кнопок
- `IR.Log()` работает в лог сервера
- `require()`, `fs`, `http` из Node.js **НЕ ДОСТУПНЫ**
- Таймер — единственный источник периодичности: `IR.SetInterval` или `EVENT_WORK+аккумулятор`

### Виртуальные тэги сервера (Server.Tags)

В серверном проекте виртуальные тэги создаются в разделе **Server Tags**,
а не в Project Tokens. Для работы с ними используется другой API:

| Операция | Код |
|----------|-----|
| Чтение | `IR.GetVariable("Server.Tags.TagName")` |
| Запись | `IR.GetServer().Set("TagName", value)` |
| Чтение (альт.) | `IR.GetServer().Get("TagName")` |

**`IR.SetVariable("Server.Tags.TagName", value)` НЕ РАБОТАЕТ!**
Для записи Server Tags только `IR.GetServer().Set()`.

### Типовой шаблон серверного скрипта (с Server Tags)
```javascript
IR.AddListener(IR.EVENT_START, 0, function() {
    IR.SetInterval(1000, function() {
        var val = parseFloat(IR.GetVariable("Server.Tags.myTag")) || 0;
        IR.GetServer().Set("myTag", val + 1);  // НЕ IR.SetVariable!
    });
});
```

### Типовой шаблон серверного скрипта (с Global Tokens)
```javascript
IR.AddListener(IR.EVENT_START, 0, function() {
    IR.SetInterval(1000, function() {
        var val = parseFloat(IR.GetVariable("Global.myTag")) || 0;
        IR.SetVariable("Global.myTag", val + 1);  // так можно
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

## 11. Лицензия (License API)

```javascript
IR.License;                     // true/false — есть ли лицензия
IR.LicenseVersion;              // версия
IR.LicenseHardwareID;           // HWID лицензии
```

---

## 12. Полезные примеры

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

## 13. Чек-лист «Чего НЕТ в iRidi Script»

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
