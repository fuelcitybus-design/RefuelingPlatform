#!/bin/bash
apt-get update
apt-get install -y libgl1-mesa-glx libglib2.0-0 libgomp1
gunicorn --bind=0.0.0.0 --timeout 600 main:app
