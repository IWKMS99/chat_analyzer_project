# Справочник по конфигурации (Русский)

В документе перечислены runtime-переменные для API/движка анализа и runtime-overrides для web-контейнера.

| Переменная | Значение по умолчанию | Где используется | Эффект | Рекомендации по тюнингу |
| --- | --- | --- | --- | --- |
| `TASK_WORKERS` | `1` | Очередь задач API | Количество параллельных воркеров анализа (валидация `1..4`). | Увеличивайте на многоядерных серверах при нескольких задачах. |
| `MAX_UPLOAD_BYTES` | `104857600` (100 MB) | Эндпоинт загрузки API | Максимальный размер файла на уровне FastAPI. | Настраивается вместе с `NGINX_CLIENT_MAX_BODY_SIZE`; фактический лимит равен меньшему значению. |
| `NGINX_CLIENT_MAX_BODY_SIZE` | `100m` | nginx перед API | Максимальный размер запроса, который принимает nginx. | Увеличивайте для больших загрузок и синхронизируйте с `MAX_UPLOAD_BYTES`. |
| `CHAT_ANALYZER_NLP_WORKERS` | `1` | NLP-процессор analyzer-core | Количество воркеров NLP-этапа. | На слабых CPU оставляйте низким; повышайте постепенно. |
| `CHAT_ANALYZER_FALLBACK_JSON_MAX_BYTES` | `52428800` (50 MB) | Загрузчик данных analyzer-core | Лимит размера JSON для fallback-парсинга в памяти. | Повышайте только при необходимости fallback для больших файлов. |
| `TASK_TTL_SECONDS` | `604800` | Очистка задач API | Время хранения артефактов задач. | Уменьшайте для снижения роста хранилища. |
| `CLEANUP_INTERVAL_SECONDS` | `600` | Планировщик очистки API | Частота запуска очистки. | Меньше интервал для агрессивной очистки, больше для снижения нагрузки. |
| `RATE_LIMIT_REQUESTS` | `120` | Rate limiter API | Допустимое число запросов за окно. | Для публичного доступа обычно стоит ужесточить. |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limiter API | Длина окна в секундах. | Настраивается совместно с `RATE_LIMIT_REQUESTS`. |
| `CORS_ORIGINS` | `http://localhost:8080` | CORS middleware API | Список разрешённых origins через запятую. | В проде указывайте только точные боевые домены. |
| `VITE_API_BASE_URL` | `/api` | Runtime-конфиг web (с fallback на build-time) | Базовый URL/префикс API-запросов. | В prebuilt-образах значение подставляется при старте контейнера; за nginx оставляйте `/api`, при раздельном деплое используйте полный URL. |
| `SQLITE_PATH` | `/app/backend_data/analyses.db` (Docker) | API + Alembic | Путь к файлу SQLite. | Храните на персистентном volume в production. |
| `STORAGE_BASE_DIR` | `/app/backend_data` (Docker) | Файловое хранилище API | Каталог для загрузок и `result` JSON. | Используйте быстрый диск и persistent volume. |

## Примечания

- Скопируйте корневой `.env.example` в `.env` и настройте значения под окружение.
- Для локального запуска API `scripts/dev/run_api.sh` выставляет безопасные дефолты:
  - `SQLITE_PATH=backend_data/analyses.db`
  - `STORAGE_BASE_DIR=backend_data`
- После изменения переменных перезапустите сервисы:

```bash
docker compose down
docker compose up -d
```
