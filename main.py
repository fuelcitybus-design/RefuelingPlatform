import os
from io import BytesIO
import base64
import requests
from requests.auth import HTTPBasicAuth
import gradio as gr
from fastapi import FastAPI

# ====== Azure Kudu settings ======
KUDU_HOST = "oil-tank-refueling-e8a5atdqg9fnh2et.scm.eastasia-01.azurewebsites.net"
KUDU_USER = "$oil-tank-refueling"
KUDU_PASS = "E8F6BQT62Mt290N5fpK1sHAnQTnxPyvsD2vXAqmmClZnYkyYDQ1Du17aNNiK"

AUTH = HTTPBasicAuth(KUDU_USER, KUDU_PASS)
BASE_URL = f"https://{KUDU_HOST}/api/vfs/site/wwwroot/uploads"

app = FastAPI()

def ensure_folder():
    r = requests.put(BASE_URL + "/", auth=AUTH)
    return r.status_code in (200, 201, 409)

def upload_image_to_kudu(image, filename):
    if image is None:
        return "No image selected."

    ensure_folder()

    if not filename:
        filename = "upload.jpg"

    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        filename += ".jpg"

    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    url = f"{BASE_URL}/{filename}"
    headers = {"If-Match": "*"}
    r = requests.put(url, data=buffer.getvalue(), auth=AUTH, headers=headers)

    if r.status_code in (200, 201):
        return f"Uploaded successfully to Kudu: {filename}"
    return f"Upload failed: {r.status_code} {r.text}"

with gr.Blocks() as demo:
    gr.Markdown("## Upload image to Azure Kudu")
    img = gr.Image(type="pil", label="Select Image")
    name = gr.Textbox(label="File name", placeholder="example.jpg")
    out = gr.Textbox(label="Status")
    btn = gr.Button("Upload to Kudu")
    btn.click(upload_image_to_kudu, inputs=[img, name], outputs=out)

app = gr.mount_gradio_app(app, demo, path="/")
