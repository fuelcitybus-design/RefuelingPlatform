#!/bin/bash
# Runtime startup script for Azure App Service

# Ensure headless OpenCV is installed (safe in sandbox)
pip uninstall -y opencv-python
pip install opencv-python-headless
python -m gunicorn main:app -k uvicorn.workers.UvicornWorker
