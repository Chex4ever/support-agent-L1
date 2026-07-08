# Импорт EDE из RAPIX в iRidi Studio

## Проблема

RAPIX экспортирует CSV с освещением, но iRidi Studio не импортирует его, показывая "Unknown csv file type".

## Причины (3 штуки)

1. **Разделитель**: Rapix использует запятые (`,`), а iRidi Studio ожидает точку с запятой (`;`). Стандарт BACnet EDE (v2.1 и v2.3) определяет `;` как стандартный разделитель.
2. **Magic header**: Studio ищет строку `#Engineering-Data-Exchange` в первой строке файла для идентификации BACnet EDE. В Rapix экспорте этой строки нет.
3. **Лишняя колонка**: Rapix экспортирует 17 колонок (включая `notification-class`), а Studio ожидает 16 колонок.

**VERSION_OF_LAYOUT 2.3 не является проблемой** — файл импортируется с версией 2.3 после исправления трёх проблем выше.

## Решение: конвертер

Скрипт на Python `convert_ede_rapix_to_iridi.py`:
- Меняет разделитель `,` → `;`
- Добавляет `#Engineering-Data-Exchange - Rapix Export Converter` в первую строку
- Удаляет колонку `notification-class` (столбец 17)
- Оставляет `VERSION_OF_LAYOUT 2.3` как есть

```python
# convert_ede_rapix_to_iridi.py
import csv, sys

def convert_rapix_ede(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    out_lines = []
    out_lines.append('#Engineering-Data-Exchange - Rapix Export Converter\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        cols = line.split(',')
        if len(cols) >= 17:
            cols = cols[:16]  # remove notification-class
        out_lines.append(';'.join(cols) + '\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

if __name__ == '__main__':
    convert_rapix_ede(sys.argv[1], sys.argv[2])
```

## Источник

Тикет 591-266500, тесты с Device2603_EDE (1).csv (YABE экспорт, 854 строки).
