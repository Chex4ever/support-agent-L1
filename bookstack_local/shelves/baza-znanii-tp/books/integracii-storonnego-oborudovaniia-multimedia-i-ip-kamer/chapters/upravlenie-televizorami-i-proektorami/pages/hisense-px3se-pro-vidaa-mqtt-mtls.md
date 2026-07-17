# Hisense PX3SE-PRO / VIDAA — управление через MQTT mTLS

## Обзор

Телевизоры и проекторы Hisense на платформе VIDAA имеют встроенный MQTT-брокер, доступный по протоколу MQTT 3.1.1 over TLS (mTLS) на порту **36669**. Управление осуществляется локально, без облака и внешних брокеров.

## Параметры подключения

| Параметр | Значение |
|----------|----------|
| Порт | 36669 |
| Протокол | MQTT 3.1.1 over TLS 1.2 |
| Аутентификация | mutual TLS (mTLS) |
| Клиентский сертификат | vidaa_client.pem |
| Приватный ключ | vidaa_client.key |

## Генерация учётных данных

Устройство требует динамически рассчитываемые Client ID, Username и Password. Алгоритм обратно-разработан из библиотеки `libmqttcrypt.so`:

```
Константы:
  PATTERN       = "38D65DC30F45109A369A86FCE866A85B"
  XOR_CONSTANT  = 0x5698_1477_2b03_a968
  SUFFIX_MODERN = "h!i@s#$v%i^d&a*a"

Алгоритм:
  1. race = MD5(PATTERN$MAC)[:6]
  2. client_id = MAC$his$race_vidaacommon_001
  3. xor_time = timestamp XOR XOR_CONSTANT
  4. username = his$xor_time
  5. remainder = sum_of_digits(timestamp) % 10
  6. value = his + remainder + SUFFIX_MODERN
  7. password = MD5(timestamp$MD5(value)[:6])
```

## Процесс сопряжения (PIN pairing)

1. Клиент подключается с динамическими учётными данными
2. Публикует `vidaa_app_connect` — на ТВ появляется 4-значный PIN
3. Клиент отправляет `authenticationcode` с `{"authNum": <pin>}`
4. ТВ отвечает `{"result": 1}`
5. Клиент запрашивает токен (`gettoken`)
6. ТВ выдаёт `accesstoken` (7 дней) + `refreshtoken` (30 дней)
7. При переподключении: пароль MQTT = accesstoken

## Основные топики

### Команды (клиент → ТВ)

| Действие | Топик |
|----------|-------|
| Кнопка пульта | `/remoteapp/tv/remote_service/{client_id}/actions/sendkey` |
| Начать сопряжение | `/remoteapp/tv/ui_service/{client_id}/actions/vidaa_app_connect` |
| Отправить PIN | `/remoteapp/tv/ui_service/{client_id}/actions/authenticationcode` |
| Запросить токен | `/remoteapp/tv/platform_service/{client_id}/data/gettoken` |
| Громкость | `/remoteapp/tv/platform_service/{client_id}/actions/changevolume` |
| Выбор источника | `/remoteapp/tv/ui_service/{client_id}/actions/changesource` |
| Запуск приложения | `/remoteapp/tv/ui_service/{client_id}/actions/launchapp` |

### Ответы (ТВ → клиент)

| Действие | Топик |
|----------|-------|
| Состояние ТВ | `/remoteapp/mobile/broadcast/ui_service/state` |
| Результат аутентификации | `/remoteapp/mobile/{client_id}/ui_service/data/authentication` |
| Токен | `/remoteapp/mobile/{client_id}/platform_service/data/tokenissuance` |
| Информация об устройстве | `/remoteapp/mobile/{client_id}/platform_service/data/getdeviceinfo` |

## Коды кнопок

`KEY_POWER`, `KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT`, `KEY_OK`, `KEY_BACK`, `KEY_MENU`, `KEY_HOME`, `KEY_EXIT`, `KEY_VOLUME_UP`, `KEY_VOLUME_DOWN`, `KEY_MUTE`, `KEY_CHANNEL_UP`, `KEY_CHANNEL_DOWN`, `KEY_0`–`KEY_9`, `KEY_RED`, `KEY_GREEN`, `KEY_YELLOW`, `KEY_BLUE`, `KEY_PLAY`, `KEY_PAUSE`, `KEY_STOP`, `KEY_REWIND`, `KEY_FAST_FORWARD`, `KEY_INFO`, `KEY_SUBTITLE`

## Интеграция с iRidi

**Важно:** Встроенный MQTT-драйвер iRidi **не поддерживает** TLS/mTLS. Прямая реализация в JS-скриптах невозможна (нет крипто-примитивов для TLS 1.2 handshake).

### Рекомендуемый способ: Python bridge

На iRidi Server с полноценной ОС (Raspberry Pi, Mini PC, x86):

1. Установить библиотеку: `pip install vidaa-control`
2. Python-скрипт подключается к ТВ через mTLS
3. Команды читаются из `Server.Tags.TV_Command`
4. Состояние пишется в `Server.Tags.TV_State`

Готовый скрипт-мост: `tickets/352-100895/files/vidaa_iridi_bridge.py`

### Эмулятор для тестирования

Для отладки без реального ТВ написан эмулятор VIDAA MQTT-брокера:
`tickets/352-100895/files/emulator/vidaa_tv_emulator.py`

```bash
# Запуск без TLS
python vidaa_tv_emulator.py --no-tls

# Запуск с TLS
python generate_certs.py
python vidaa_tv_emulator.py --server-cert certs/server_cert.pem --server-key certs/server_key.pem
```

## Ссылки

- Библиотека vidaa-control: https://github.com/tombabolewski/vidaa-control (PyPI: `vidaa-control`)
- Home Assistant интеграция: https://github.com/habby1337/ha-hisense-remote
- Тикет Omnidesk: #352-100895
- Эмулятор: `tickets/352-100895/files/emulator/`
