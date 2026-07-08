# Кастомный AV&CS драйвер для RAPIX

## Возможен ли кастомный драйвер?

Да. В iRidi Studio есть тип устройств "AV & Custom Systems" (HTTP/TCP/WebSocket), который позволяет написать кастомный драйвер на JavaScript (ECMAScript 3).

## Прототип драйвера

Был написан прототип `rapix_avcs_driver.js`, работающий через AV&CS TCP:
- Управление зонами: On/Off/Level
- Сцены: Set/Off
- Статус фидбек через event subscription
- Полностью совместим с ES3 (нет стрелочных функций, `let`/`const`)

Структура драйвера (ES3-совместимый код):
```javascript
IR.AddListener(IR.EVENT_ON_TICK, function() {
    // heartbeat / reconnect logic
});
```

## BACnet vs Custom Driver — сравнение

| Возможность | BACnet (EDE импорт) | Custom DGCM драйвер |
|-------------|---------------------|---------------------|
| Zone On/Off/Level | AnalogValue | zone on/off/fade_to_level |
| Сцены | BinaryValue | xiene set (+ nudge/offset) |
| Фидбек (уровень, сцена) | COV subscription | Push events (event subscription) |
| **Кастомное время fade** | только зона по умолчанию | per-command fade time |
| **Цвет (RGB/XY/CT)** | сложно | fade_to_color одной командой |
| **Диагностика ошибок** | недоступно | extended_status (lamp failure, device missing) |
| **DALI диагностика** | недоступно | emergency tests, output unit status |
| **Lux/Occupancy** | недоступно | extended_status2 |
| **Operating Properties** | частично | полный xi_op_prop |
| **Управление расписанием** | недоступно | schedule set_events |

### Рекомендация

Для базового управления (on/off/level/scenes) **BACnet + EDE импорт — правильный выбор**:
- zero-config, все точки импортируются автоматически
- Контроллер RAPIX уже говорит по BACnet

Кастомный драйвер оправдан, если нужны:
- Цветное управление (RGB/CT)
- Диагностика ламп и DALI
- Emergency тесты
- Управление расписаниями
- Per-command fade time

## Dynamic import КУ/КОС (Universal Import from JS)

Если нужны Project Tokens (КУ/КОС) динамически, Studio поддерживает **"Universal import from JS (\*.js, \*.json)"**:
- Функция: `dev.iridi.com/Universal_import_from_JS`
- Позволяет создать любое устройство с каналами из JSON/JS файла
- `IR.SetVariable("Global.name", value)` авто-создаёт Project Tokens

Это не так страшно, как кажется — достаточно JSON файла, описывающего команды и фидбеки.

## Источник

Тикет 591-266500, эксперименты с прототипом драйвера, документация dev.iridi.com.
