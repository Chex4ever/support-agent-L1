# OCR распознавание скриншотов

Если в тикете есть вложения-изображения (jpg/png):

1. Запусти `tools/image/ocr.py` на каждом изображении
2. `-p monitor` для фото мониторов, `-p screenshot` для скриншотов
3. Сохрани результат в `files/ocr_{image_name}.txt`
4. Если не распозналось — попробуй другой engine:
   - `--engine tesseract`
   - `--engine easyocr`
   - `--engine web`
5. Если OCR не дал результата — опиши содержимое изображения средствами модели

## Пример

```powershell
python tools/image/ocr.py tickets/123/files/screenshot.png -p monitor -l rus+eng
```

Или через скачивание вложений с OCR:

```powershell
python tools/omnidesk/download_attachments.py <case_id> --ocr
```

Подробности: [tools/README.md](../tools/README.md#image-processing)
