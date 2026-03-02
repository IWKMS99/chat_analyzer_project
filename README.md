# Chat Analyzer Project

Stream-first анализатор Telegram JSON экспортов.

## Что изменено
- Потоковая загрузка через `iter_chat_messages` / `iter_chat_chunks`.
- Инкрементальные агрегаторы для модулей анализа.
- Визуализация на Plotly (`HTML` + опциональный `PNG` через `kaleido`).
- NLP на `spaCy` (RU/EN) с sentiment baseline.
- Шаблонные отчеты `Jinja2`, основной формат `HTML`.
- Доп. аналитика: reactions, social graph, edited/deleted.

## Установка
```bash
pip install -r requirements.txt
python -m spacy download ru_core_news_sm
python -m spacy download en_core_web_sm
```

## Быстрый старт
```bash
python main.py data/result.json
```

## CLI
```bash
python main.py INPUT_JSON \
  --output-dir output \
  --report-format html \
  --profile full \
  --chunk-size 50000
```

### Основные параметры
- `--timezone`: по умолчанию системная таймзона (`tzlocal`).
- `--report-format`: `html|json|md|all` (default `html`).
- `--modules`: выбор модулей (`summary activity temporal user message dialog nlp anomaly social`).
- `--chunk-size`: размер чанка для stream-пайплайна.
- `--max-workers`: процессы для NLP `spaCy.pipe`.
- `--disable-interactive`: не сохранять HTML-графики.
- `--skip-plots`: не строить графики.

## Публичные API
- `iter_chat_messages(file_path, normalize=True)`
- `iter_chat_chunks(file_path, chunk_size=50000)`
- `load_and_process_chat_data(...)` — deprecated wrapper.

## Выходные артефакты
- `output/report.html` (или `report.md/report.json`).
- `output/charts/*.html` и `output/charts/*.png`.
- `output/social_graph.html` (если есть данные для графа).
