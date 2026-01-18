#!/bin/sh
set -e

echo "Waiting for postgres..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

echo "Postgres is up"

HAS_VERSION_TABLE=$(psql "$DATABASE_URL" -tAc \
  "SELECT to_regclass('public.alembic_version');")

if [ "$HAS_VERSION_TABLE" = "" ]; then
  echo "Database is empty"

  echo "Running migrations..."
  alembic upgrade head

  if [ "$LOAD_DB_DUMP" = "true" ] && [ -f /dumps/data.dump ]; then
    echo "Loading data dump via pg_restore..."

    LOG_FILE="/tmp/pg_restore.log"
    ERROR_FILE="/tmp/pg_restore_errors.log"

    pg_restore \
      --dbname="$DATABASE_URL" \
      --data-only \
      --disable-triggers \
      --jobs=4 \
      /dumps/data.dump \
      > "$LOG_FILE" 2> "$ERROR_FILE" || true

    echo "pg_restore log saved to $LOG_FILE"
    echo "Errors saved to $ERROR_FILE"

    if [ -s "$ERROR_FILE" ]; then
      echo "===== ERRORS FOUND DURING PG_RESTORE ====="
      cat "$ERROR_FILE"
      echo "========================================="
      exit 1
    fi
  fi
else
  echo "Database already initialized"
fi

echo "Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
