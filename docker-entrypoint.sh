#!/bin/sh
set -e

if [ -n "${DATABASE_URL:-}" ]; then
  echo "Waiting for PostgreSQL..."
  until python -c "import os, psycopg2; psycopg2.connect(os.environ['DATABASE_URL']).close()"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py seed_initial_data

exec "$@"
