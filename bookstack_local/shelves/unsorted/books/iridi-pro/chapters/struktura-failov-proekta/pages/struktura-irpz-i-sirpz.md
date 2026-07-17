# Структура файлов .irpz и .sirpz

## Общая информация

Файлы `.irpz` и `.sirpz` — это **архивы ZIP** с внутренней структурой из **текстовых XML-файлов** и ресурсов. Бинарных данных в формате нет.

| Расширение | Тип проекта | Назначение |
|---|---|---|
| `.irpz` | Панельный (Panel) | Проект интерфейса для iPad/Android/ПК |
| `.sirpz` | Серверный (Server) | Проект iRidi Server (橋接/логика) |

**Разница в именовании** — исключительно для удобства: чтобы сразу отличить панельный проект от серверного. Внутренняя структура файлов **идентична**.

## Распаковка

`.irpz` / `.sirpz` — обычный ZIP. Чтобы посмотреть содержимое:

```powershell
# Windows
Copy-Item "project.irpz" "project.zip"
Expand-Archive "project.zip" -DestinationPath "extracted"

# Или через Python
python -c "import zipfile; zipfile.ZipFile('project.irpz').extractall('extracted')"
```

> **Важно:** расширение `.irpz` не распознаётся `Expand-Archive` как ZIP — нужно либо переименовать, либо использовать `zipfile` из Python.

## Структура файлов после распаковки

```
project.irpz (ZIP)
├── Editor.xml              — основной XML: настройки проекта, дерево устройств,
│                             RelationTags, Scripts, Images, Resolutions
├── Project.irp             — XML (!): страницы, попапы, элементы интерфейса,
│                             виртуальные теги, папки. Формально .irp, но это XML.
├── Config.xml              — XML: настройки подключения (Host, Port, SSL),
│                             логирование, пароли
├── scripts/                — JavaScript-скрипты (.js)
│   ├── weatherClient.js
│   └── Screensaver.js
├── images/                 — изображения (PNG, JPG)
├── fonts/                  — шрифты
└── style/                  — стили
```

## Ключевые файлы

### Editor.xml

Основной файл конфигурации проекта. Содержит:

- **`<DeviceFolders>`** — дерево устройств (HDL, KNX, Modbus и др.)
  - `<Branch Name="..." Type="9">` — физическое устройство с `ParamChild="Subnet ID=X;Device ID=Y;Device Type=Z;"`
  - `<Branch Name="..." Type="13">` — команды (Commands) устройства
  - `<Branch Name="..." Type="14">` — обратная связь (Feedbacks) устройства
  - Каждая ветка имеет уникальный `ID`, `GUID` и `Data` (hex-представление протокола)
- **`<RelationsTags>`** — привязки обратной связи: `LHS` (драйвер) → `RHS` (UI-элемент)
- **`<Scripts>`** — список скриптов
- **`<Images>`** — спрайты и изображения
- **`<Resolutions>`** — доступные разрешения

### Project.irp

Несмотря на расширение `.irp` — это **чистый XML**. Содержит:

- **`<Pages>`** — страницы интерфейса
  - `<Page Name="..." Orientation="0">` — каждая страница
  - `<Item>` — элементы интерфейса (кнопки, слайдеры, текст)
    - `Type` — тип элемента (0=статичный, 1=слайдер, 12=toggle)
    - `SIT` — состояние интерактивности (2=только текст, 14=send tag)
    - `Hit` — обработка нажатий (1=да, 2=нет)
    - `Feedback` — привязка к обратной связи (1=по RelationTag)
    - `<ActionCases>` — действия при событиях (press/release)
      - `<Action Type="send_tag" DeviceID="2" ChannelID="XXX">` — отправка тега на сервер
- **`<Popups>`** — попапы (аналогично страницам)
  - `Group` — группа для группировки попапов
  - `Modal`, `Timeout`, `ShowEffect`, `HideEffect` — параметры отображения
- **`<VirtualTags>`** — виртуальные теги проекта
- **`<Folders>`** — структура папок UI

### Config.xml

Настройки подключения и запуска:

```xml
<Config ServerPort="30464" ServerHost="..." ...>
  <Connections>
    <Connection Host="255.255.255.255" Port="6000" Type="C2"
                Name="HDL Buspro Network (UDP)"/>
    <Connection Host="192.168.8.2" Port="30464" Type="271"
                Name="iRidium Server"/>
  </Connections>
</Config>
```

## Маппинг ID в дереве устройств

Каждый канал устройства в Editor.xml имеет численный `ID` — это и есть `ChannelID` в `send_tag`. Например:

| ID | Имя в дереве | send_tag ChannelID |
|---|---|---|
| 911 | `HDL Buspro Network.2-9 Relay 8ch 16a:Channel 2` | 911 |
| 913 | `HDL Buspro Network.2-9 Relay 8ch 16a:Channel 4` | 913 |
| 974 | `HDL Buspro Network.2-243 Relay 8ch 16a:Channel 09` | 974 |

> **Ловушка:** один и тот же `ID` может встречаться дважды — как команда (Type=13) и как обратная связь (Type=14) для разных устройств. При анализе всегда проверяйте GUID для уникальной идентификации.

## RelationTags: как работает привязка обратной связи

```xml
<RelationTags
  LHS="Drivers.iRidium Server.Tags.HDL Buspro Network.2-243 Relay 8ch 16a:Channel 09"
  RHS="UI.Home_Rooms.Home_Rooms45.Value"/>
```

- **LHS** — путь к тегу драйвера (обратная связь с устройства)
- **RHS** — путь к UI-элементу (`UI.<Попап>.<Элемент>.Value`)

Когда HDL-устройство сообщает изменение состояния канала, сервер обновляет `Value` соответствующего UI-элемента. Если на элементе настроен `Feedback="1"`, он переключает визуальное состояние (State 0/1).

## Отладка проектов

### Просмотр XML

1. Распаковать `.irpz` как ZIP
2. Открыть `Project.irp` и `Editor.xml` в любом XML-редакторе (VS Code, Notepad++)

### Поиск элементов

```powershell
# Поиск всех RelationTags для конкретного попапа
Select-String -Path "Editor.xml" -Pattern "UI.Home_Rooms"

# Поиск ChannelID в дереве устройств
Select-String -Path "Editor.xml" -Pattern 'ID="974"'
```

### Анализ через инструменты

```powershell
python tools/project/analyze_irpz.py "path/to/project.irpz"
```

Выводит: устройства, скрипты, токены, RelationTags, страницы и попапы.
