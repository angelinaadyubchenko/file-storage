# File Storage Service

- **Развёрнутый сервис:** https://201.51.7.237.nip.io
- **Swagger:** https://201.51.7.237.nip.io/docs

## Что умеет

- Регистрация / логин по JWT (регистрация создаёт только аккаунт, без хранилищ).
- **Хранилища** двух типов, тип выбирается при создании (`POST /storages`, поле
  `type`): `personal` — может создать любой пользователь; `global` — нужно
  глобальное право `CAN_CREATE_GLOBAL_STORAGE`.
- **Заявки на права**: пользователь запрашивает право на создание глобальных
  хранилищ через сайт; **администратор** (аккаунт с email из настройки
  `ADMIN_EMAIL`) одобряет или отклоняет заявку.
- **Политики хранилища**: лимит размера файла, общий лимит хранилища, белые
  списки MIME-типов и расширений.
- **Загрузка файлов** с потоковой проверкой размера, определением MIME-типа по
  **содержимому** (python-magic, а не по Content-Type/расширению) и контролем
  квоты.
- **Гранты доступа** к хранилищу: `STORAGE_READ`, `STORAGE_WRITE`,
  `STORAGE_DELETE`, `STORAGE_MANAGE_ACCESS`. Владелец хранилища неявно обладает
  всеми правами. **Личное** хранилище можно открыть другим только на
  `STORAGE_READ` (чтение и скачивание); полный набор прав — только у глобальных.
- **Переименование** хранилища (`PATCH /storages/{id}`).
- **Soft delete** файлов: при удалении проставляется `deleted_at`, физический
  файл остаётся на диске для аудита/восстановления. Физическая очистка — отдельной
  командой `cleanup_deleted_files`.
- **Временные ссылки** (`share`-токены): публичный доступ к файлу без авторизации,
  с ограничением по сроку и числу скачиваний; ручной отзыв.

## Хранение данных

Метаданные (пользователи, хранилища, файлы, гранты) — в **PostgreSQL**. Сами байты
файлов — на **локальной файловой системе сервера**, с раздельными каталогами по
типу хранилища:

```
storage/
├── personal/<storage_id>/<file_id><ext>
└── global/<storage_id>/<file_id><ext>
```

В БД у файла хранится путь (`file_path`), по которому он лежит на диске.

## Администратор

Админ — это пользователь, чей email совпадает с настройкой `ADMIN_EMAIL` (по
умолчанию `admin@gmail.com`). Только он одобряет заявки и управляет глобальными
правами. Чтобы назначить админа, достаточно зарегистрировать аккаунт с этим email
(или изменить `ADMIN_EMAIL` в `.env`). Никакой записи в БД вручную не требуется.

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
cp .env.example .env
docker-compose up --build
```

`entrypoint.sh` перед стартом uvicorn выполняет `alembic upgrade head`.
API поднимется на http://localhost:8000, интерактивная документация —
http://localhost:8000/docs.

## Примеры использования (curl)

### 1. Регистрация (создаётся только аккаунт)
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

### 3. Создание личного хранилища
```bash
STORAGE_ID=$(curl -s -X POST http://localhost:8000/storages \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Мои файлы", "type": "personal"}' | jq -r .id)
```

### 4. Загрузка файла
```bash
curl -X POST http://localhost:8000/storages/$STORAGE_ID/files \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./report.pdf"
# вернёт JSON с "id" файла -> FILE_ID
```

### 5. Скачивание файла
```bash
curl -OJ http://localhost:8000/files/$FILE_ID/download \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Выдача доступа другому пользователю (на личное — только чтение)
```bash
curl -X POST http://localhost:8000/storages/$STORAGE_ID/access \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"target_user_id": "<uuid>", "grant_type": "STORAGE_READ"}'
```

### 7. Временная публичная ссылка
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

### 8. Запросить право на создание глобальных хранилищ → одобрение админом
```bash
# пользователь подаёт заявку
curl -X POST http://localhost:8000/access-requests \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'

# админ (email = ADMIN_EMAIL) смотрит заявки и одобряет
ADMIN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@gmail.com", "password": "..."}' | jq -r .access_token)
curl -s http://localhost:8000/admin/access-requests -H "Authorization: Bearer $ADMIN"
curl -X POST http://localhost:8000/admin/access-requests/<request_id>/approve \
  -H "Authorization: Bearer $ADMIN"
```

### 9. Создание глобального хранилища (после получения права)
```bash
curl -X POST http://localhost:8000/storages \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Team storage", "type": "global", "policy": {"max_file_size": 10485760}}'
```

## Основные эндпоинты

| Метод и путь | Назначение | Требуемое право |
|---|---|---|
| `POST /auth/register` | регистрация (только аккаунт) | — |
| `POST /auth/login` | получить JWT | — |
| `GET /auth/me` | данные текущего пользователя | авторизация |
| `GET /auth/me/access` | флаги: админ / может создавать global / есть заявка | авторизация |
| `GET /storages` | доступные хранилища | авторизация |
| `POST /storages` | создать хранилище (личное/глобальное) | personal — любой; global — `CAN_CREATE_GLOBAL_STORAGE` |
| `GET /storages/{id}` | инфо + занятость | `STORAGE_READ` / владелец |
| `PATCH /storages/{id}` | переименовать | `STORAGE_MANAGE_ACCESS` / владелец |
| `PUT /storages/{id}/policy` | обновить политику | `STORAGE_MANAGE_ACCESS` / владелец |
| `GET /storages/{id}/my-grants` | мои права на хранилище | авторизация |
| `POST /storages/{id}/files` | загрузить файл | `STORAGE_WRITE` / владелец |
| `GET /storages/{id}/files` | список файлов | `STORAGE_READ` / владелец |
| `GET /files/{id}/download` | скачать файл | `STORAGE_READ` / владелец |
| `DELETE /files/{id}` | soft delete | `STORAGE_DELETE` / владелец |
| `POST /storages/{id}/access` | выдать грант (личное — только `STORAGE_READ`) | `STORAGE_MANAGE_ACCESS` / владелец |
| `GET /storages/{id}/access` | список грантов | `STORAGE_MANAGE_ACCESS` / владелец |
| `DELETE /storages/{id}/access/{user_id}` | отозвать грант | `STORAGE_MANAGE_ACCESS` / владелец |
| `POST /files/{id}/share` | создать ссылку | `STORAGE_MANAGE_ACCESS` / владелец |
| `GET /shared/{token}` | публичное скачивание | — |
| `DELETE /files/{id}/share/{token}` | отозвать ссылку | `STORAGE_MANAGE_ACCESS` / владелец |
| `POST /access-requests` | запросить право | авторизация |
| `GET /admin/access-requests` | список заявок | админ (`ADMIN_EMAIL`) |
| `POST /admin/access-requests/{id}/approve` | одобрить заявку | админ (`ADMIN_EMAIL`) |
| `POST /admin/access-requests/{id}/reject` | отклонить заявку | админ (`ADMIN_EMAIL`) |
| `POST /admin/grants` | выдать глобальное право напрямую | админ (`ADMIN_EMAIL`) |
| `DELETE /admin/grants` | отозвать глобальное право | админ (`ADMIN_EMAIL`) |

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

Покрытые сценарии: регистрация (только аккаунт), неверный логин, создание личного
и глобального хранилищ (с проверкой права на global), превышение размера файла и
квоты, недопустимый MIME, доступ без/с грантом, ограничение личного хранилища на
read-only, отзыв гранта, защита от эскалации прав, переименование, soft delete,
публичные ссылки (валидная, просроченная, сверх лимита, отозванная), заявки на
права (запрос/одобрение/отклонение, админ только по email).

## Технологический стек

Python 3.12 · FastAPI · SQLAlchemy 2.0 (async + asyncpg) · Alembic · PostgreSQL ·
Pydantic v2 · python-jose (JWT) · passlib[bcrypt] · python-magic · pytest/httpx.
