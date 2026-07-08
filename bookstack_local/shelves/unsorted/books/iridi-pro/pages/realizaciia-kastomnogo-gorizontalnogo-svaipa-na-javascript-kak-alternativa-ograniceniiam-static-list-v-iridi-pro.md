# Реализация кастомного горизонтального свайпа на JavaScript как альтернатива ограничениям Static List в iRidi Pro

## Содержание
- [Реализация кастомного горизонтального свайпа на JavaScript как альтернатива ограничениям Static List в iRidi Pro](#реализация-кастомного-горизонтального-свайпа-на-javascript-как-альтернатива-ограничениям-static-list-в-iridi-pro)
  - [1. Описание проблемы и системные ограничения](#1-описание-проблемы-и-системные-ограничения)
  - [2. Диагностическая карта (Symptom → Cause)](#2-диагностическая-карта-symptom-cause)
  - [3. Базовое решение (Официальный обходной путь для Static List)](#3-базовое-решение-официальный-обходной-путь-для-static-list)
  - [4. Альтернативное решение: Кастомный свайп графических контейнеров](#4-альтернативное-решение-кастомный-свайп-графических-контейнеров)
    - [Алгоритм работы](#алгоритм-работы)
    - [Пример программной реализации](#пример-программной-реализации)
  - [5. Ограничения решения и безопасность](#5-ограничения-решения-и-безопасность)
  - [6. Шаблоны ответов технической поддержки](#6-шаблоны-ответов-технической-поддержки)
    - [Шаблон на русском языке (RU)](#шаблон-на-русском-языке-ru)
    - [Шаблон на английском языке (EN)](#шаблон-на-английском-языке-en)
  - [7. Критерии эскалации на L2 / Dev](#7-критерии-эскалации-на-l2-dev)
  - [8. Справочные материалы](#8-справочные-материалы)
  - [9. История изменений](#9-история-изменений)

---


## 1. Описание проблемы и системные ограничения

При проектировании современных интерфейсов автоматизации в iRidi Pro часто требуется динамическое управление элементами (например, отображение/скрытие Popups комнат, виджетов климата или панелей освещения) непосредственно во время физического перетаскивания списка пользователем. 

Однако стандартный компонент `Static List` с типом прокрутки *Center* накладывает жесткие архитектурные ограничения:
* Событие `IR.EVENT_LIST_SCROLL` генерируется только в момент окончательной фиксации элемента по центру списка. Микро-свайпы и незавершенные жесты полностью игнорируются ядром.
* Свойство `EDGE` в режиме прокрутки по центру некорректно возвращает значение `0`, делая невозможным стандартное отслеживание крайних положений списка.
* В текущем GUI API iRidi отсутствует прямой метод получения активной позиции списка (например, `GetPosition()`).

## 2. Диагностическая карта (Symptom → Cause)

| Визуальный симптом / Лог ошибки | Вероятная первопричина | Необходимые данные для диагностики |
| :--- | :--- | :--- |
| Свойство `EDGE` всегда возвращает `0` | Баг в обработчике границ `Static List` при активном типе прокрутки `Center` в ядре клиента. | Файл проекта (*.irpz), лог эмулятора iRidi. |
| Отсутствует реакция интерфейса на незавершенный жест сдвига | Событие `LIST_SCROLL` привязано к окончанию анимации доводки элемента к центру, а не к координатам пальца. | Описание ожидаемой UX/UI-логики. |
| Ошибка `TypeError: list.GetPosition is not a function` | Метод получения текущей активной позиции отсутствует в текущем API компонента. | JS-код скрипта проекта. |

## 3. Базовое решение (Официальный обходной путь для Static List)

Если отказаться от `Static List` невозможно, используйте метод ручного трекинга состояния через глобальную переменную:

1. Объявите переменную для сохранения индекса (например, `var currentListPos = 1;`).
2. Обновляйте её значение строго внутри обработчика события `IR.EVENT_LIST_SCROLL`.
3. Считывайте значение этой переменной при вызове внешних функций.

```javascript
var currentListPos = 1; // Хранение текущей позиции списка

IR.AddListener(IR.EVENT_LIST_SCROLL, IR.GetPage("Page_Name").GetItem("List_Name"), function(position) {
    currentListPos = position;
    IR.Log("Текущая позиция списка сохранена: " + currentListPos);
});
```

*Примечание: Баг со свойством `EDGE` и запрос на добавление метода `GetPosition()` зарегистрированы и переданы команде разработки iRidi Studio в качестве официального баг-репорта.*

## 4. Альтернативное решение: Кастомный свайп графических контейнеров

Для реализации плавного, отзывчивого интерфейса с эффектом динамического изменения прозрачности и параллакса рекомендуется полностью отказаться от `Static List`. Вместо него используется управление координатами контейнеров внутри единого полноэкранного всплывающего окна (Popup).

### Алгоритм работы
1. Создается полноэкранный Popup (например, `SwipePopup`), внутри которого размещаются панели-контейнеры (`Page1`, `Page2` типа Panel или Label).
2. JavaScript перехватывает низкоуровневые события касания (`IR.EVENT_TOUCH_DOWN`, `IR.EVENT_TOUCH_MOVE`, `IR.EVENT_TOUCH_UP`) и мыши.
3. В процессе сдвига (`onTouchMove`) рассчитывается смещение `dx`. Координаты элементов меняются динамически в реальном времени, а прозрачность плавно нарастает или убывает.
4. При отпускании пальца (`onTouchUp`) проверяется порог сдвига (более 30% от ширины экрана). Если порог преодолен, запускается плавная нативная анимация перехода на другую страницу, если нет — происходит возврат в исходное состояние.

### Пример программной реализации

```javascript
var popup = IR.GetPopup("SwipePopup");
var page1 = popup.GetItem("Page1");
var page2 = popup.GetItem("Page2");

var screenWidth = popup.Width;
var currentPage = 1;

// Состояние жеста
var swipe = false;
var startX = 0;
var startY = 0;
var currentOffset = 0;
var minSwipeDistance = 10; // Минимальный сдвиг для начала распознавания (в пикселях)
var isSwiping = false;
var swipeDirection = null;
var horizontalFactor = 2; // Коэффициент фильтрации вертикальных движений

function updatePositions() {
    if (currentPage === 1) {
        page1.X = 0;
        page2.X = screenWidth;
        page2.GetState(0).Opacity = 0;
        page1.ZIndex = 2;
        page2.ZIndex = 1;
    } else {
        page1.X = -screenWidth;
        page2.X = 0;
        page2.GetState(0).Opacity = 255;
        page1.ZIndex = 1;
        page2.ZIndex = 2;
    }
}

// Инициализация стартовых позиций
updatePositions();

function startSwipe(x, y) {
    swipe = true;
    startX = x;
    startY = y;
    isSwiping = false;
    swipeDirection = null;
    currentOffset = 0;
}

function moveSwipe(x, y) {
    if (!swipe) return;
    
    var dx = x - startX;
    var dy = y - startY;
    
    if (!isSwiping) {
        if (Math.abs(dx) >= minSwipeDistance || Math.abs(dy) >= minSwipeDistance) {
            if (Math.abs(dx) > Math.abs(dy) * horizontalFactor) {
                swipeDirection = 'horizontal';
            } else {
                swipeDirection = 'vertical';
            }
            isSwiping = true;
            if (swipeDirection !== 'horizontal') return;
        } else {
            return;
        }
    }
    
    if (swipeDirection !== 'horizontal') return;
    
    if (currentPage === 1) {
        var newOffset = Math.min(0, dx); // Движение только влево
        if (newOffset < -screenWidth) newOffset = -screenWidth;
        currentOffset = newOffset;
        
        page1.X = currentOffset;
        page2.X = page1.X + screenWidth;
        
        var opacity = Math.min(255, Math.max(0, Math.abs(currentOffset) / screenWidth * 255));
        page2.GetState(0).Opacity = opacity;
    } else {
        var newOffset = Math.max(0, dx); // Движение только вправо
        if (newOffset > screenWidth) newOffset = screenWidth;
        currentOffset = newOffset;
        
        page2.X = currentOffset;
        page1.X = page2.X - screenWidth;
        
        var opacity = Math.min(255, Math.max(0, (screenWidth - currentOffset) / screenWidth * 255));
        page2.GetState(0).Opacity = opacity;
    }
}

function endSwipe() {
    swipe = false;
    
    if (!isSwiping || swipeDirection !== 'horizontal') {
        updatePositions();
        isSwiping = false;
        swipeDirection = null;
        return;
    }
    
    var threshold = screenWidth * 0.3;
    var shouldSwitch = false;
    
    if (currentPage === 1) {
        if (currentOffset < -threshold) shouldSwitch = true;
    } else {
        if (currentOffset > threshold) shouldSwitch = true;
    }
    
    if (shouldSwitch) {
        currentPage = (currentPage === 1) ? 2 : 1;
    }
    
    // Плавная анимация завершения перехода
    if (currentPage === 1) {
        IR.AddAnimation({Type: IR.ANIMATION_MOVE_HORIZONTAL, From: page1.X, To: 0, Duration: 250}, page1, 0, false, true);
        IR.AddAnimation({Type: IR.ANIMATION_MOVE_HORIZONTAL, From: page2.X, To: screenWidth, Duration: 250}, page2, 0, false, true);
        IR.AddAnimation({Type: IR.ANIMATION_OPACITY, From: page2.GetState(0).Opacity, To: 0, Duration: 250}, page2, 0, false, false);
    } else {
        IR.AddAnimation({Type: IR.ANIMATION_MOVE_HORIZONTAL, From: page1.X, To: -screenWidth, Duration: 250}, page1, 0, false, true);
        IR.AddAnimation({Type: IR.ANIMATION_MOVE_HORIZONTAL, From: page2.X, To: 0, Duration: 250}, page2, 0, false, true);
        IR.AddAnimation({Type: IR.ANIMATION_OPACITY, From: page2.GetState(0).Opacity, To: 255, Duration: 250}, page2, 0, false, false);
    }
    
    isSwiping = false;
    swipeDirection = null;
}

// Регистрация слушателей событий сенсора и мыши
IR.AddListener(IR.EVENT_TOUCH_DOWN, popup, function(x, y) { startSwipe(x, y); });
IR.AddListener(IR.EVENT_TOUCH_MOVE, popup, function(x, y) { moveSwipe(x, y); });
IR.AddListener(IR.EVENT_TOUCH_UP, popup, function() { endSwipe(); });

IR.AddListener(IR.EVENT_MOUSE_DOWN, popup, function(x, y) { startSwipe(x, y); });
IR.AddListener(IR.EVENT_MOUSE_MOVE, popup, function(x, y) { moveSwipe(x, y); });
IR.AddListener(IR.EVENT_MOUSE_UP, popup, function() { endSwipe(); });
```

## 5. Ограничения решения и безопасность

* **Важно:** Свойство `.Opacity` в методе нативной анимации `IR.AddAnimation` принимает целые числа в диапазоне от `0` (абсолютно прозрачно) до `255` (полностью непрозрачно). Стандартные веб-форматы (0..1) здесь не поддерживаются.
* **Запрещено:** Вызывать нативное открытие, закрытие или перерисовку других ресурсоемких Popups непосредственно внутри циклического события `IR.EVENT_TOUCH_MOVE`. Это приведет к критическому падению FPS и зависанию UI-потока. Все смежные окна должны быть предзагружены (`Preload`).

## 6. Шаблоны ответов технической поддержки

### Шаблон на русском языке (RU)

> Здравствуйте!
>
> Мы детально изучили ваше обращение касательно поведения компонента `Static List`.
>
> Действительно, событие `IR.EVENT_LIST_SCROLL` по своей архитектуре генерируется только после окончательной фиксации элемента по центру списка. При мелких и незавершенных жестах скролла событие не срабатывает, а свойство `EDGE` в данном режиме возвращает `0`. Эта особенность зарегистрирована нами как баг и передана команде разработчиков iRidi Studio.
>
> В качестве надежного обходного пути, позволяющего гибко управлять прозрачностью и координатами элементов в реальном времени в момент свайпа, мы рекомендуем использовать структуру графических контейнеров внутри одного полноэкранного Popup.
>
> Готовый демонстрационный пример проекта вы можете скачать по следующей ссылке: [https://drive.google.com/file/d/1jwXHP_OtZWjojRUnj1uVLyIXC6jktjOd/view](https://drive.google.com/file/d/1jwXHP_OtZWjojRUnj1uVLyIXC6jktjOd/view)
>
> Скрипт перехватывает события касания и мыши, плавно изменяя координаты `X` и прозрачность `Opacity` панелей-контейнеров, что обеспечивает бесшовный кинетический эффект перелистывания экранов. Если у вас возникнут сложности при интеграции решения, мы готовы помочь вам на любом из этапов.

### Шаблон на английском языке (EN)

> Hello!
>
> We have investigated your request regarding the `Static List` component behavior.
>
> Indeed, the `IR.EVENT_LIST_SCROLL` event is designed to trigger only when a list element settles in the center position. Small gestures or scrolls that return to the starting position do not fire the event, and the `EDGE` property returns `0` in this mode. We have registered this limitation as a bug and submitted it to the iRidi Studio development team.
>
> To achieve smooth, real-time control over layout opacity and coordinates during touch moves, we highly recommend using custom graphic containers inside a single fullscreen Popup instead of the `Static List` component.
>
> We have prepared a fully functional sample project implementing this custom swipe navigation. You can download it here: [https://drive.google.com/file/d/1jwXHP_OtZWjojRUnj1uVLyIXC6jktjOd/view](https://drive.google.com/file/d/1jwXHP_OtZWjojRUnj1uVLyIXC6jktjOd/view)
>
> This script handles both touch and mouse events, dynamically adjusting `X` and `Opacity` properties to provide a native-like swipe experience. Please let us know if you need any assistance with integrating this logic.

## 7. Критерии эскалации на L2 / Dev

1. Наблюдается критическое падение частоты кадров (FPS) на мобильных устройствах (iOS/Android) при анимации движения контейнеров, содержащих большое количество сложных векторных или растровых виджетов.
2. Возникают внутренние сбои рендеринга графического движка или переполнение стека вызовов (Stack Overflow) при циклическом вызове метода `IR.AddAnimation()` во время частых высокоскоростных жестов.

## 8. Справочные материалы

* [Официальная документация iRidi - GUI API Events](https://dev.iridi.com/GUI_API/en#Events)
* [Официальное руководство по нативным анимациям (IR.AddAnimation)](https://dev.iridi.com/Native_Animation_API/ru)
* [Описание типов графических элементов и контейнеров](https://dev.iridi.com/Editor_Tools/ru#Types_of_graphic_items)

## 9. История изменений

| Дата | Версия | Описание изменений | Автор |
| :--- | :--- | :--- | :--- |
| 2026-05-25 | 1.0 | Создание статьи на основе тикета #572-567564. Добавлена JS-реализация кастомного свайпа. | KBAE Assistant |