#!/bin/bash
set -e

exec gunicorn main:app \
    --workers 4
    --worker-class uvicorn.workers.UvicornWorker
    --bind 0.0.0.0:${PORT:-8000}
    --timeout 1200
    --keep-alive 75
