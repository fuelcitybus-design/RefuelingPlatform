import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
import gradio as gr
from fastapi import FastAPI

KUDU_HOST = "oil-tank-refueling-e8a5atdqg9fnh2et.scm.eastasia-01.azurewebsites.net"
KUDU_USER = "$oil-tank-refueling"
KUDU_PASS = "E8F6BQT62Mt290N5fpK1sHAnQTnxPyvsD2vXAqmmClZnYkyYDQ1Du17aNNiK"
AUTH = HTTPBasicAuth(KUDU_USER, KUDU_PASS)

BASE_URL = f"https://{KUDU_HOST}/api/vfs/site/wwwroot/uploads"
app = FastAPI()

def ensure_folder():
    r = requests.put(BASE_URL + "/", auth=AUTH, timeout=20)
    return r.status_code in (200, 201, 409)

def save_one(image, filename):
    if image is None:
        return f"Skipped {filename}: no image"

    if not ensure_folder():
        return f"Folder check failed for {filename}"

    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        filename += ".jpg"

    buf = BytesIO()
    image.save(buf, format="JPEG")
    url = f"{BASE_URL}/{filename}"

    r = requests.put(
        url,
        data=buf.getvalue(),
        auth=AUTH,
        headers={"If-Match": "*"},
        timeout=60
    )

    if r.status_code in (200, 201):
        return f"Uploaded {filename}"
    return f"Failed {filename}: {r.status_code} {r.text}"

def upload_image_to_kudu(image, filename):
    return save_one(image, filename)

with gr.Blocks() as demo:
    gr.Markdown("## Upload image to Azure Kudu")
    img = gr.Image(type="pil", label="Select Image")
    name = gr.Textbox(label="File name", placeholder="example.jpg")
    out = gr.Textbox(label="Status")
    btn = gr.Button("Upload to Kudu")
    btn.click(upload_image_to_kudu, inputs=[img, name], outputs=out)

app = gr.mount_gradio_app(app, demo, path="/")
