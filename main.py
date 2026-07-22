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

TAB_NAMES = [
    "車牌", "油錶前", "油尺前", "封條1", "封條2",
    "油車前", "油車後", "油錶後", "油尺後", "收據"
]

def ensure_folder():
    r = requests.put(BASE_URL + "/", auth=AUTH, timeout=20)
    return r.status_code in (200, 201, 409)

def save_one(image, filename):
    if image is None:
        return f"Skipped {filename}: no image"

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

def upload_all_images(*images):
    if not ensure_folder():
        return "Folder check failed"

    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    for tab_name, img in zip(TAB_NAMES, images):
        filename = f"{today}_{tab_name}.jpg"
        results.append(save_one(img, filename))

    return "\n".join(results)

with gr.Blocks() as demo:
    gr.Markdown("## Upload images from multiple tabs to Azure Kudu")

    inputs = []
    with gr.Tabs():
        for tab_name in TAB_NAMES:
            with gr.Tab(tab_name):
                img = gr.Image(type="pil", label=f"Image for {tab_name}")
                inputs.append(img)

    out = gr.Textbox(label="Upload result", lines=12)
    btn = gr.Button("Upload all images")
    btn.click(upload_all_images, inputs=inputs, outputs=out)

app = gr.mount_gradio_app(app, demo, path="/")
