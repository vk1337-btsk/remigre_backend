Вот подробная инструкция по запуску проекта на FastAPI, с использованием Poetry, venv, и Docker, с учетом, что в проекте используется Redis. Инструкция разбита по способам.

🔧 1. Запуск через Poetry
✅ Установка Poetry (если не установлен):
bash
Копировать
Редактировать
curl -sSL https://install.python-poetry.org | python3 -
Убедись, что poetry доступен в PATH. Если нет, добавь в .bashrc или .zshrc:

bash
Копировать
Редактировать
export PATH="$HOME/.local/bin:$PATH"
📦 Установка зависимостей:
bash
Копировать
Редактировать
poetry install
⚙️ Запуск FastAPI-приложения:
bash
Копировать
Редактировать
poetry run uvicorn src.main:app --reload
Замените src.main:app на путь к вашему приложению.

🐍 2. Запуск через venv
✅ Создание виртуального окружения:
bash
Копировать
Редактировать
python3 -m venv venv
source venv/bin/activate
📦 Установка зависимостей:
Если у вас pyproject.toml, то:

bash
Копировать
Редактировать
pip install poetry
poetry export -f requirements.txt --without-hashes > requirements.txt
pip install -r requirements.txt
Или, если есть requirements.txt напрямую:

bash
Копировать
Редактировать
pip install -r requirements.txt
⚙️ Запуск приложения:
bash
Копировать
Редактировать
uvicorn src.main:app --reload
🐳 3. Запуск через Docker
📁 Пример Dockerfile:
dockerfile
Копировать
Редактировать
FROM python:3.11-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y build-essential

WORKDIR /app

# Poetry
RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-root

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
📁 Пример docker-compose.yml с Redis:
yaml
Копировать
Редактировать
version: "3.9"

services:
  web:
    build: .
    container_name: fastapi_app
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      REDIS_URL: redis://redis:6379/0
    volumes:
      - .:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
▶️ Запуск:
bash
Копировать
Редактировать
docker-compose up --build
📌 Примечания
Убедитесь, что в .env (если используется) переменная REDIS_URL или подобная настроена корректно:
REDIS_URL=redis://localhost:6379/0 (для локального запуска)
REDIS_URL=redis://redis:6379/0 (в Docker)

Если используете Alembic или другие команды, можно запускать так:

bash
Копировать
Редактировать
poetry run alembic upgrade head
Или в Docker:

bash
Копировать
Редактировать
docker-compose exec web poetry run alembic upgrade head
