#!/bin/sh
set -e

echo "Waiting for postgres..."

DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

echo "Postgres is up"

HAS_VERSION_TABLE=$(psql "$DATABASE_URL_SYNC" -tAc \
  "SELECT to_regclass('public.alembic_version');")

if [ -z "$HAS_VERSION_TABLE" ]; then
  echo "Database is empty"

  echo "Running migrations..."
  alembic upgrade head

  if [ "$LOAD_DB_DUMP" = "true" ] && [ -f /dumps/data.dump ]; then
    echo "Loading data dump via pg_restore..."

    pg_restore \
      --dbname="$DATABASE_URL_SYNC" \
      --data-only \
      --disable-triggers \
      --jobs=4 \
      /dumps/data.dump
  fi
else
  echo "Database already initialized"
fi

echo "Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
