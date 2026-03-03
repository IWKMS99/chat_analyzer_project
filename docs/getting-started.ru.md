# Быстрый старт (Русский)

## Вариант A: запуск на готовых образах (рекомендуется)

```bash
docker compose -f docker-compose.prod.yml up -d
```

Открыть:

- Web UI: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`

## Вариант B: локальная сборка в контейнерах (без hot reload)

```bash
docker compose up --build
```

Этот режим собирает образы локально из исходников, но не даёт hot reload.

## Вариант C: нативный режим разработки (с hot reload)

```bash
uv sync
corepack pnpm install
scripts/dev/run_api.sh
```

Во втором терминале запустите фронтенд:

```bash
scripts/dev/run_web.sh
```

## Первый анализ за 3 шага

1. Экспортируйте чат Telegram в JSON (см. [user-guide.ru.md](user-guide.ru.md)).
2. Загрузите файл в Web UI.
3. Дождитесь статуса `done` и откройте дашборд.

## Что читать дальше

- Полный пользовательский сценарий: [user-guide.ru.md](user-guide.ru.md)
- Тюнинг окружения: [configuration.ru.md](configuration.ru.md)
- Операционные детали: [operations.en.md](operations.en.md)
