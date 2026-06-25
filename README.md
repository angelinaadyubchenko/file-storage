# File Storage Service

- **Развёрнутый сервис:** https://201.51.7.237.nip.io
- **Swagger (документация API):** https://201.51.7.237.nip.io/docs

## Что умеет

- Регистрация / логин по JWT. При регистрации пользователю автоматически
  создаётся **личное хранилище** с дефолтной политикой (100 MB на файл, 1 GB
  всего, любые MIME-типы).
- **Хранилища** двух типов: `personal` (по одному на пользователя) и `global`
  (создаётся обладателями глобального гранта `CAN_CREATE_GLOBAL_STORAGE`).
- **Политики хранилища**: лимит размера файла, общий лимит хранилища, белые
  списки MIME-типов и расширений.
- **Загрузка файлов** с потоковой проверкой размера, определением MIME-типа по
  **содержимому** (python-magic, а не по Content-Type/расширению) и контролем
  квоты.
- **Гранты доступа** к хранилищу: `STORAGE_READ`, `STORAGE_WRITE`,
  `STORAGE_DELETE`, `STORAGE_MANAGE_ACCESS`. Владелец хранилища неявно обладает
  всеми правами.
- **Soft delete** файлов: при удалении проставляется `deleted_at`, физический
  файл остаётся на диске для аудита/восстановления. Физическая очистка — отдельной
  командой `cleanup_deleted_files`.
- **Временные ссылки** (`share`-токены): публичный доступ к файлу без авторизации,
  с ограничением по сроку и числу скачиваний; ручной отзыв.

## Архитектура

Роуты (`app/api/*`) тонкие — только разбор зависимостей и вызов сервиса. Вся
бизнес-логика в `app/services/*`. Enum-значения определены один раз в
`app/models/enums.py` и переиспользуются в моделях и схемах. Конфигурация — через
Pydantic Settings из переменных окружения (`app/core/config.py`).

```
app/
├── api/         # тонкие роуты + зависимости (deps.py)
├── services/    # бизнес-логика
├── models/      # SQLAlchemy ORM + enums
├── schemas/     # Pydantic v2
├── core/        # config, security (JWT/bcrypt), logging
├── db/          # async engine/session, declarative Base
├── exceptions.py
└── main.py
alembic/         # миграции
scripts/         # cleanup_deleted_files (management-команда)
tests/           # pytest + httpx
```

## Запуск локально (Docker)

```bash
cp .env.example .env          # при желании поправьте SECRET_KEY и т.д.
docker-compose up --build
```

`entrypoint.sh` перед стартом uvicorn выполняет `alembic upgrade head`.
API поднимется на http://localhost:8000, интерактивная документация —
http://localhost:8000/docs.

## Примеры использования (curl)

### 1. Регистрация (создаётся личное хранилище)
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "password123"}'
```

### 2. Логин → JWT
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "password123"}' | jq -r .access_token)
```

### 3. Список хранилищ (найти id личного хранилища)
```bash
curl -s http://localhost:8000/storages -H "Authorization: Bearer $TOKEN"
STORAGE_ID=...   # id хранилища с "type": "personal"
```

### 4. Создание глобального хранилища (нужен грант CAN_CREATE_GLOBAL_STORAGE)
```bash
curl -X POST http://localhost:8000/storages \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Team storage", "policy": {"max_file_size": 10485760, "max_storage_size": 104857600}}'
```

### 5. Загрузка файла
```bash
curl -X POST http://localhost:8000/storages/$STORAGE_ID/files \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./report.pdf"
# вернёт JSON с "id" файла -> FILE_ID
```

### 6. Скачивание файла
```bash
curl -OJ http://localhost:8000/files/$FILE_ID/download \
  -H "Authorization: Bearer $TOKEN"
```

### 7. Выдача доступа другому пользователю
```bash
curl -X POST http://localhost:8000/storages/$STORAGE_ID/access \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"target_user_id": "<uuid>", "grant_type": "STORAGE_READ"}'
```

### 8. Временная публичная ссылка
```bash
# создать ссылку (24 часа, максимум 5 скачиваний)
curl -X POST http://localhost:8000/files/$FILE_ID/share \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"expires_in_hours": 24, "max_downloads": 5}'
# вернёт {"token": "..."} -> SHARE_TOKEN

# скачать без авторизации
curl -OJ http://localhost:8000/shared/$SHARE_TOKEN

# отозвать вручную
curl -X DELETE http://localhost:8000/files/$FILE_ID/share/$SHARE_TOKEN \
  -H "Authorization: Bearer $TOKEN"
```

## Основные эндпоинты

| Метод и путь | Назначение | Требуемое право |
|---|---|---|
| `POST /auth/register` | регистрация + личное хранилище | — |
| `POST /auth/login` | получить JWT | — |
| `GET /storages` | доступные хранилища | авторизация |
| `POST /storages` | создать global-хранилище | `CAN_CREATE_GLOBAL_STORAGE` |
| `GET /storages/{id}` | инфо + занятость | `STORAGE_READ` / владелец |
| `PUT /storages/{id}/policy` | обновить политику | `STORAGE_MANAGE_ACCESS` / владелец |
| `POST /storages/{id}/files` | загрузить файл | `STORAGE_WRITE` / владелец |
| `GET /files/{id}/download` | скачать файл | `STORAGE_READ` / владелец |
| `DELETE /files/{id}` | soft delete | `STORAGE_DELETE` / владелец |
| `POST /storages/{id}/access` | выдать грант | `STORAGE_MANAGE_ACCESS` / владелец |
| `GET /storages/{id}/access` | список грантов | `STORAGE_MANAGE_ACCESS` / владелец |
| `DELETE /storages/{id}/access/{user_id}` | отозвать грант | `STORAGE_MANAGE_ACCESS` / владелец |
| `POST /files/{id}/share` | создать ссылку | `STORAGE_MANAGE_ACCESS` / владелец |
| `GET /shared/{token}` | публичное скачивание | — |
| `DELETE /files/{id}/share/{token}` | отозвать ссылку | `STORAGE_MANAGE_ACCESS` / владелец |

## Очистка soft-deleted файлов

Удаление файла — мягкое: запись помечается `deleted_at`, байты остаются на диске
(аудит/восстановление). Физически файлы старше `CLEANUP_RETENTION_DAYS` (по
умолчанию 30 дней) удаляются отдельной командой:

```bash
python -m scripts.cleanup_deleted_files
# или внутри контейнера:
docker-compose exec app python -m scripts.cleanup_deleted_files
```

## Тесты

Тестам нужен PostgreSQL. Поднимите БД для тестов и укажите `TEST_DATABASE_URL`:

```bash
# например, поднять только контейнер БД и создать тестовую базу
docker-compose up -d db
docker-compose exec db createdb -U postgres filestorage_test

export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/filestorage_test"
pip install -r requirements.txt   # нужен системный libmagic (brew install libmagic / apt install libmagic1)
pytest -v
```

Схема БД пересоздаётся вокруг каждого теста для полной изоляции; файлы пишутся во
временный каталог (`TEST_STORAGE_DIR`, по умолчанию `/tmp/filestorage_test_storage`).

Покрытые сценарии: регистрация с авто-хранилищем, неверный логин, превышение
размера файла и квоты, недопустимый MIME, доступ без/с грантом, отзыв гранта,
soft delete, публичные ссылки (валидная, просроченная, сверх лимита, отозванная).

## Технологический стек

Python 3.12 · FastAPI · SQLAlchemy 2.0 (async + asyncpg) · Alembic · PostgreSQL ·
Pydantic v2 · python-jose (JWT) · passlib[bcrypt] · python-magic · pytest/httpx.
