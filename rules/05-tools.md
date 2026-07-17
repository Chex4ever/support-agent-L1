# Инструменты (tools/)

Перед тем как писать любой код — проверь, нет ли готового инструмента в `tools/`.

| Категория | Инструмент | Назначение |
|-----------|-----------|------------|
| **Omnidesk API** | `tools/omnidesk/fetch_messages.py` | Получить все сообщения тикета по internal case ID |
| | `tools/omnidesk/download_attachments.py` | Скачать вложения + inline-изображения. `--ocr` для распознавания |
| **Анализ проектов** | `tools/project/analyze_irpz.py` | Распарсить .irpz: страницы, попапы, токены, скрипты |
| **PDF** | `tools/pdf/extract.py` | Извлечение текста из PDF (PyMuPDF + OCR-фолбэк) |
| **OCR** | `tools/image/ocr.py` | Текст из скриншотов / фото мониторов (3 engine) |
| **JS-паттерны** | `tools/script-patterns/*.js` | Dynamic List, Token Bus, Sine Gen |
| **BookStack** | `tools/bookstack/sync.py` | Синхронизация BookStack ↔ `bookstack_local/` |
| | `tools/bookstack/migrate_kb.py` | Миграция старых KB записей в BookStack |
| **Эмуляция** | `tools/emulation/up.py` | KNX + Modbus + HTTP mock для клиентских проектов |

Подробности, параметры и примеры: [tools/README.md](../tools/README.md).

## Быстрые команды

```powershell
python tools/omnidesk/fetch_messages.py <case_id>
python tools/omnidesk/download_attachments.py <case_id> --ocr
python tools/project/analyze_irpz.py <file.irpz>
python tools/image/ocr.py <image> -p monitor
python tools/pdf/extract.py <file.pdf>
python -m tools.bookstack.sync pull
python -m tools.bookstack.sync push
```
