from fastapi import FastAPI
app = FastAPI()

#========================================================================================================

import os
import base64
import requests
from requests.auth import HTTPBasicAuth
import gradio as gr
from PIL import Image
import io
from pathlib import Path
import glob
import numpy as np
import cv2
from paddleocr import PaddleOCR
import re

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image
from datetime import datetime

os.environ["FLAGS_use_mkldnn"] = "0"

ocr_model = PaddleOCR(lang="ch",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False, enable_mkldnn=False)
# --- CONFIGURATION ---
# Replace these with your actual Azure App Service credentials
USERNAME = "$oil-tank-refueling"
PASSWORD = "E8F6BQT62Mt290N5fpK1sHAnQTnxPyvsD2vXAqmmClZnYkyYDQ1Du17aNNiK"
KUDU_HOST = "oil-tank-refueling-e8a5atdqg9fnh2et.scm.eastasia-01.azurewebsites.net"

#========================================================================================================

locations = ["{請選擇}", "CFD創富", "CWD柴灣", "SHD小蠔灣", "SWD上環", "TCD東涌", "TKD將軍澳", "TMD屯門", "WCD黃竹坑", "WKD西九"]
depot_gps = [("CFD創富", 22.272764832109846, 114.24250389449965),
        ("CWD柴灣", 22.270758379558714, 114.24155512333564),
        ("SHD小蠔灣", 22.315893212234425, 113.99856865402481),
        ("SWD上環", 22.288271040384796, 114.15105773910038),
        ("TCD東涌", 22.28009953657451, 113.9394554386798),
        ("TKD將軍澳", 22.316949281155114, 114.25819879997607),
        ("TMD屯門", 22.383505220952447, 113.96928212236955),
        ("WCD黃竹坑", 22.248418440612717, 114.16227259618798),
        ("WKD西九", 22.329873814418242, 114.14657647254528)]

car_ids = ["{請選擇}", "第1車", "第2車", "第3車", "第4車", "第5車"]

tank_ids = ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸", "第7缸", "第8缸"]
tank_list = {"CFD創富": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸", "第7缸", "第8缸"],
        "CWD柴灣": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸"],
        "SHD小蠔灣": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "SWD上環": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "TCD東涌": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "TKD將軍澳": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "TMD屯門": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "WCD黃竹坑": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "WKD西九": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"]}

tab_names = ["油錶前", "油尺前", "封條1", "封條2", "油車前", "油車後", "油錶後", "油尺後", "收據"]
tab_list_S = {
        "{請選擇}": [],
        "CFD創富": ["油錶前", "油尺前", "封條1", "封條2", "油車前", "油車後", "油錶後", "油尺後", "收據"],
        "CWD柴灣": ["油錶前",  "封條1", "封條2", "油車前", "油車後", "油錶後", "收據"],
        "SHD小蠔灣": ["油尺前", "封條1", "封條2", "油車前", "油車後", "油尺後", "收據"],
        "SWD上環": ["油錶前",  "封條1", "封條2", "油車前", "油車後", "油錶後", "收據"],
        "TCD東涌": ["油尺前", "封條1", "封條2", "油車前", "油車後", "油尺後", "收據"],
        "TKD將軍澳": ["油尺前", "封條1", "封條2", "油車前", "油車後", "油尺後", "收據"],
        "TMD屯門": ["油尺前", "封條1", "封條2", "油車前", "油車後", "油尺後", "收據"],
        "WCD黃竹坑": ["油尺前", "封條1", "封條2", "油車前", "油車後", "油尺後", "收據"],
        "WKD西九": ["油錶前",  "封條1", "封條2", "油車前", "油車後", "油錶後", "收據"]}

required_tabs = ["油車前", "油車後"]
forced_check = False #Forced required image batch uploading button)
ROOT_FOLDER = f"https://{KUDU_HOST}/api/vfs/data"

#=========================================================================================================================
def save_images(location, car_id, tank_id, request: gr.Request, *images):
        return none
    
def prefer_back_camera():
    custom_html = """
    <script>
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);

    navigator.mediaDevices.getUserMedia = (constraints) => {
      if (!constraints.video.facingMode) {
        constraints.video.facingMode = {ideal: "environment"};
      }

      constraints.video.width = {exact: 400};
      constraints.video.height = {exact: 400};

      return originalGetUserMedia(constraints);
    };
    </script>
    """
    return custom_html

def nearest(gps):
    if "Allow" in gps:
        return "{請選擇}"
    lat, lon = map(float, gps.strip("[]").split(","))
    d = lambda c: (lat-c[1])**2 + (lon-c[2])**2
    return min(depot_gps, key=d)[0]

def update_tank_dropdown(tank_id):
    tank_dropdown = tank_list.get(tank_id, ["{請選擇}"])
    return gr.Dropdown(choices=tank_dropdown, label="缸號", value=tank_dropdown[0], allow_custom_value=False, filterable=False, interactive=True)

def toggle_tabs(location, car, tank):

    # For each tab, set visible=True if it belongs to the selected depot
    updates = []
    active_tabs = tab_list_S.get(location, [])
    if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
        for tab in tab_names:
            if tab in active_tabs:
                updates.append(gr.update(visible=True))
            else:
                updates.append(gr.update(visible=False))
    # Also return the active dictionary slice for display
    return updates + [str({location: active_tabs})]

def toggle_save(location, car, tank):
    # Show save button only if all dropdowns are not placeholders
    if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)

def clear_images(selection):
    # Reset all images when depot changes
    return [gr.update(value=None) for _ in tab_names]


#============================================================================================================================================================

with gr.Blocks(head=prefer_back_camera()) as demo: # DeprecationWarning: The 'head' parameter in the Blocks constructor will be removed in Gradio 6.0. You will need to pass 'head' to Blocks.launch() instead.
    gr.Markdown("落油記錄工具")

    with gr.Tabs():
        # Module 2
        with gr.Tab("拍照"):
            with gr.Row():
                location_dropdown = gr.Dropdown(choices=locations, label="地點(gps)", value=locations[0], allow_custom_value=False, filterable=False, interactive=True)
                car_dropdown = gr.Dropdown(choices=car_ids, label="車號", value=car_ids[0], allow_custom_value=False, filterable=False)
                tank_dropdown = gr.Dropdown(choices=["{請選擇}"], label="缸號", value="{請選擇}", allow_custom_value=False, filterable=False)

                raw_gps = gr.Textbox(visible=False)
                demo.load(None, None, raw_gps, js="""() => new Promise(r => navigator.geolocation.getCurrentPosition(
                    p => r(`[${p.coords.latitude}, ${p.coords.longitude}]`),
                    () => r("[Tap Allow Location]"), {enableHighAccuracy:true}))""")
                raw_gps.change(nearest, raw_gps, location_dropdown)

                location_dropdown.change(fn=update_tank_dropdown, inputs=location_dropdown, outputs=tank_dropdown)

            with gr.Tabs() as img_tabs:
                image_inputs = []
                tab_list = []
                for tab_name in tab_names:
                    with gr.Tab(tab_name,visible=False) as tab:
                        img_input = gr.Image(type="pil", label=f"Upload {tab_name} photo", height=400, sources=['webcam'], mirror_webcam=False, elem_id="camera_input")
                        image_inputs.append(img_input)
                        tab_list.append(tab)

            save_btn = gr.Button("儲存所有照片", variant="primary", size="lg",visible=False)

            output_text = gr.Textbox(label="狀態", lines=6)

            save_btn.click(
                fn=save_images,
                inputs=[location_dropdown, car_dropdown, tank_dropdown] + image_inputs,
                outputs=output_text
            )

            #Toggle tabs avaliable based on depot selection
            location_dropdown.change(toggle_tabs, [location_dropdown,car_dropdown,tank_dropdown], tab_list)
            car_dropdown.change(toggle_tabs, [location_dropdown,car_dropdown,tank_dropdown], tab_list)
            tank_dropdown.change(toggle_tabs, [location_dropdown,car_dropdown,tank_dropdown], tab_list)

            #Toggle save button
            location_dropdown.change(toggle_save, [location_dropdown,car_dropdown,tank_dropdown], save_btn)
            car_dropdown.change(toggle_save, [location_dropdown,car_dropdown,tank_dropdown], save_btn)
            tank_dropdown.change(toggle_save, [location_dropdown,car_dropdown,tank_dropdown], save_btn)

            #Clear uploaded images when changing information values
            location_dropdown.change(clear_images, location_dropdown, image_inputs)
            car_dropdown.change(clear_images, location_dropdown, image_inputs)
            tank_dropdown.change(clear_images, location_dropdown, image_inputs)

    demo.css = """
    #camera_input button {
        transform: scale(2);   /* Scaling for making all gr.image buttons larger */
    }
    """

app = gr.mount_gradio_app(app, demo, path="/")
