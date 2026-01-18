# Развёртывание и запуск

## Подготовка к развёртыванию

Для создания дампа памяти из БД на локальном компьютере, нужно создать дамп именно такой командой:

```powershell
pg_dump -U postgres -d trava `
  --format=custom `
  --data-only `
  --no-owner `
  --no-privileges `
  --exclude-table=public.alembic_version `
  --exclude-table-data=public.spatial_ref_sys `
  -f dumps/data.dump

```

Для первого раза

```bash
docker compose down -v
docker compose up --build
```

## Локально - Poetry/Pip

Предусловия (один раз)

- Python 3.11
- PostgreSQL запущен локально и на нём уже есть БД
- Poetry установлен (или через venv)

1. Клонировать проект

```bash
git clone <repo>
cd <repo>
```

2. Установить зависимости

```bash
poetry install
```

3. Активировать окружение

```bash
poetry shell
```

4. Создать .env.local

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=app
DB_USER=postgres
DB_PASSWORD=postgres

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app
```

⚠️ файл не коммитить

5. Накатить миграции

```bash
alembic upgrade head
```

6. Запустить FastAPI

```bash
uvicorn src.main:app --reload
```

🔁 Повседневная работа (локально)
poetry shell
uvicorn src.main:app --reload

🆕 Новая миграция (если менялась схема)
alembic revision --autogenerate -m "описание"
alembic upgrade head


## Локально - Docker


ля первого раза

```bash
docker compose down -v
docker compose up --build
```


# Список задач на будущее

- [ ] Подгрузить города в локализации RU
- [ ] Отрефакторить метод get_all_filtered во всех моделях
