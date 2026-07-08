При разработке интерфейсов для систем автоматизации часто возникает задача адаптации одного проекта под разные типы устройств (смартфоны, планшеты, панели). Для того чтобы пользователю не приходилось выбирать проект вручную, в iRidi Pro предусмотрен механизм автоматического переключения между дизайнами — **DesignSwitch**.

### Основной метод: Использование DesignSwitch

Метод `IR.DesignSwitch` позволяет приложению анализировать параметры устройства при запуске и автоматически загружать соответствующую версию интерфейса. Это позволяет использовать один QR-код для всех типов устройств в рамках одного объекта в iRidium Cloud.

#### Системные триггеры
Для определения типа устройства используются системные токены (Tokens API). Наиболее популярные параметры:
* **System.Display.Width / Height**: ширина и высота дисплея в пикселях.
* **System.ControlPanelType**: тип панели (iPhone, iPad, Android и т.д.).
* **System.ControlPanelName**: уникальное имя панели (если оно задано в настройках).

#### Пример скрипта для автоматизации
Ниже приведен пример реализации универсального переключателя проектов на базе ширины экрана. 

> **Важно:** Массив проектов должен быть отсортирован по убыванию порога ширины (от самого большого к самому маленькому).

```javascript
(function (){
    function ProjectSelector (projects) {
        this.trigger = "System.Display.Width";
        this.projects = projects;
        
        // Подписка на изменение системных параметров
        IR.SetGlobalListener(IR.EVENT_GLOBAL_TAG_CHANGE, this.select, this);
        IR.SubscribeTagChange(this.trigger);
        
        // Первоначальный анализ при старте
        IR.AddListener(IR.EVENT_START, 0, this.analize, this);
    }

    ProjectSelector.prototype.select = function () {
        var selectID = 0;
        var selectName = "";
        var currentWidth = IR.GetVariable(this.trigger);
        var defaultItem;

        for(var j = 0; j < this.projects.length; j++) {
            var item = this.projects[j];
            if(item.width == undefined) defaultItem = item;
            if(item.width != undefined && currentWidth >= item.width && item.CloudID) {
                selectID = item.CloudID;
                selectName = item.projectName;
                break;
            }
        }

        if(selectID == 0 && defaultItem != undefined) {
            selectID = defaultItem.CloudID;
            selectName = defaultItem.projectName;
        }

        var currentProject = IR.GetCurrentDesign();
        if(currentProject && selectID != currentProject.CloudID) {
            IR.Log("ProjectSelector: Переключение на " + selectName);
            IR.DesignSwitch(selectName, selectID);
        }
    }

    ProjectSelector.prototype.analize = function () {
        var count = IR.GetDesignsCount();
        for(var i = 0; i < count; i++) {
            var project = IR.GetDesignByIndex(i);
            for(var j = 0; j < this.projects.length; j++) {
                var item = this.projects[j];
                if(item.projectName == project.OriginalName) item.CloudID = project.CloudID;
            }
        }
        this.select();
    }

    // Инициализация: укажите названия проектов из iRidium Cloud и пороги срабатывания
    new ProjectSelector ([
        { width: 800, projectName: "Tablet_Project" },
        { width: 400, projectName: "Phone_Project" },
        { projectName: "Default_Project" } // Резервный вариант
    ]);
})();
```

### Альтернативный метод: Динамическое изменение размеров

Если вы не хотите поддерживать несколько разных файлов дизайна, возможен альтернативный подход:
1. Создается один проект с максимальным поддерживаемым разрешением (например, 4048x4048).
2. В настройках проекта отключается масштабирование (Scaling).
3. С помощью скриптов отслеживается текущее разрешение экрана, и размеры графических элементов (например, всплывающих окон/Popups) динамически подстраиваются под текущую область просмотра.

Этот метод сложнее в реализации графической части, но упрощает администрирование логики проекта, так как весь JS-код находится в одном месте.

### Полезные ссылки
* [Документация по Tokens API](https://dev.iridi.com/Tokens_API/en)
* [Руководство по использованию DesignSwitch](https://dev.iridi.com/DesignSwitch/en)