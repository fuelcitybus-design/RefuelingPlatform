#!/bin/bash

python -m gunicorn main:app -k uvicorn.workers.UvicornWorker
