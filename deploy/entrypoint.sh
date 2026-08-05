#!/bin/sh
set -eu

cd /app/backend

# Seed helix.config.yaml from example when missing (volume may be empty on first run).
if [ ! -f /app/helix.config.yaml ] && [ -f /app/helix.config.example.yaml ]; then
  cp /app/helix.config.example.yaml /app/helix.config.yaml
fi

exec gunicorn helix.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
