# Многостадийная сборка с Python 3.12
FROM python:3.12-slim AS builder

WORKDIR /app

# Установка UV (быстрый менеджер пакетов)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем только файлы зависимостей (для кеширования)
COPY pyproject.toml uv.lock* ./

# Устанавливаем зависимости в виртуальное окружение (без dev-пакетов)
RUN uv sync --frozen --no-dev --no-install-project

# Финальный образ — минимальный
FROM python:3.12-slim

WORKDIR /app

# Копируем виртуальное окружение из первого слоя
COPY --from=builder /app/.venv /app/.venv

# Копируем весь исходный код
COPY . .

# Добавляем .venv/bin в PATH для доступа к uvicorn
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]