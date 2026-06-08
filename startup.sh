pip uninstall -y opencv-python opencv-contrib-python
pip install --upgrade --force-reinstall opencv-python-headless==4.9.0.80
exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
