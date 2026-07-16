#***Setup environment for running Gradio interface
from fastapi import FastAPI
app = FastAPI()

#========================================================================================================

#Library imports
import os
import base64
import requests
from requests.auth import HTTPBasicAuth
import gradio as gr
from datetime import datetime
from io import BytesIO
import re
import numpy as np
import cv2
from paddleocr import PaddleOCR
import tempfile
from PIL import Image

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image
from openpyxl.drawing.image import Image as XLImage
from datetime import datetime

#========================================================================================================

# --- CONFIGURATION ---
# Replace these with your actual Azure App Service credentials
USERNAME = "$oil-tank-refueling"
PASSWORD = "E8F6BQT62Mt290N5fpK1sHAnQTnxPyvsD2vXAqmmClZnYkyYDQ1Du17aNNiK"
auth=HTTPBasicAuth(USERNAME, PASSWORD)
KUDU_HOST = "oil-tank-refueling-e8a5atdqg9fnh2et.scm.eastasia-01.azurewebsites.net"

#Information parameters
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

tab_names = ["車牌","油錶前", "油尺前", "封條1", "封條2", "油車前", "油車後", "油錶後", "油尺後", "收據"]
tab_list_S = {
        "{請選擇}": [],
        "CFD創富": ["油錶前", "油尺前", "封條1", "封條2", "油車前", "油車後", "油錶後", "油尺後", "收據"],
        "CWD柴灣": ["車牌", "油錶前",  "封條1", "封條2", "油車前", "油車後", "油錶後", "收據"],
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

###Module 1/O: Uploader camera forced setting
def prefer_back_camera():
    custom_html = """
    <script>
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);

    navigator.mediaDevices.getUserMedia = (constraints) => {
      if (!constraints.video.facingMode) {
        constraints.video.facingMode = { ideal: "environment" };
      }

      constraints.video.width = { exact: 400 };
      constraints.video.height = { exact: 400 };

      return originalGetUserMedia(constraints);
    };

    // Support multiple dropdown IDs
    const TANK_DROPDOWN_IDS = ['tank_dropdown_uploader', 'tank_dropdown_history'];

    function isTankDropdownInput(el) {
      while (el && el !== document) {
        if (TANK_DROPDOWN_IDS.includes(el.id)) {
          return true;
        }
        el = el.parentElement;
      }
      return false;
    }

    function blockTankDropdownTyping(e) {
      if (!isTankDropdownInput(e.target)) {
        return;
      }

      // Allow navigation keys only
      const allowedKeys = [
        'ArrowDown', 'ArrowUp', 'Enter', 'Escape',
        'Tab', 'Shift', 'Control', 'Alt', 'Meta'
      ];

      if (allowedKeys.includes(e.key)) {
        return;
      }

      // Block all other keys
      e.preventDefault();
      e.stopPropagation();
    }

    function blockTankDropdownPaste(e) {
      if (!isTankDropdownInput(e.target)) {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
    }

    function initTankDropdownBlocker() {
      if (window._tankDropdownBlockerInitialized) {
        return;
      }
      window._tankDropdownBlockerInitialized = true;

      document.addEventListener('keydown', blockTankDropdownTyping, true);
      document.addEventListener('input', (e) => {
        if (isTankDropdownInput(e.target) && e.target.tagName === 'INPUT') {
          // Force value back to last known good value (i.e., selected option)
          e.target.value = e.target._lastGoodValue || '';
        }
      }, true);
      document.addEventListener('paste', blockTankDropdownPaste, true);

      // Initialize _lastGoodValue and clear any typed content on load for all dropdowns
      setTimeout(() => {
        TANK_DROPDOWN_IDS.forEach(id => {
          const tankInput = document.querySelector(`#${id} input[type="text"]`);
          if (tankInput) {
            tankInput._lastGoodValue = tankInput.value;
            tankInput.value = tankInput._lastGoodValue; // ensure no stray text
          }
        });
      }, 300);
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initTankDropdownBlocker);
    } else {
      initTankDropdownBlocker();
    }
    </script>
    """
    return custom_html

#============================================================================================================================================================

### Module 4: History functions
# Function to get car ID list
def get_car_ids(date, location):
    # Convert timestamp to YYYY-MM-DD
    date = datetime.fromtimestamp(date).strftime('%Y-%m-%d')
    BASE_URL = f"{ROOT_FOLDER}/{date}/{location}/"
    # Find all subfolders that look like carID folders
    candidates = requests.get(BASE_URL, auth=auth)
    car_id = []
    if candidates.status_code == 200:
        items = candidates.json()
        for item in items:
                if item.get("mime") == "inode/directory":
                    folder_name = item.get("name", "")
                    parts = folder_name.split("_")  # split into two parts only
                    car_id.append(parts[0])  # keep the first part
        return sorted(set(car_id))
    else:
        return []

def safe_update_car_dropdown(date, location):
    try:
        return update_car_dropdown(date, location)
    except Exception:
        # Return safe defaults matching the declared outputs
        return (
            gr.update(choices=["錯誤"], value="錯誤"),
            [], "錯誤",
            [], "錯誤",
            [], "錯誤",
            [], "錯誤",
            "伺服器錯誤：無法載入資料"
        )

def safe_update_all(date, location, car):
    try:
        return update_all(date, location, car)
    except Exception:
        return (
            [], "錯誤",
            [], "錯誤",
            [], "錯誤",
            [], "錯誤",
            "伺服器錯誤：無法載入資料"
        )

def update_car_dropdown(date, location):
    car_ids = get_car_ids(date, location)
    if car_ids:
        car_update = gr.update(choices=["請選擇"] + car_ids, value="請選擇")
    else:
        car_update = gr.update(choices=["沒有記錄"], value="沒有記錄")

    # reset galleries and labels at the same time
    tank_reset = [[], "No Tank", [], "No Tank", [], "No Tank", [], "No Tank", "請先選取有效車號"]

    return (car_update, *tank_reset)

    #if car_ids:
        # ✅ choices updated, value cleared
        #return gr.update(choices=car_ids, value=None)
    #else:
        # ✅ placeholder, no selection
        #return gr.update(choices=["No car available"], value=None)


# Function to get tank names
def get_tank_names(date, location, id):
    date = datetime.fromtimestamp(date).strftime('%Y-%m-%d')
    BASE_URL = f"{ROOT_FOLDER}/{date}/{location}/"
    candidates = requests.get(BASE_URL, auth=auth)
    tank = []
    if candidates.status_code == 200:
        items = candidates.json()
        for item in items:
                if item.get("mime") == "inode/directory":
                    folder_name = item.get("name", "")
                    parts = folder_name.split("_")  # split into two parts only
                    if id == parts[0]:
                        tank.append(parts[1])  # keep the second part
        return tank
    else:
        return []
    

# Function to fetch images for a given tank
def find_jpg_images(date, location, id, tank):
    date = datetime.fromtimestamp(date).strftime('%Y-%m-%d')
    url = f"{ROOT_FOLDER}/{date}/{location}/{id}_{tank}/"
    gallery_items = []

    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=30)
        if response.status_code != 200:
            return [], f"❌ Failed to fetch directory contents: HTTP {response.status_code}"

        files_json = response.json()
        os.makedirs("kudu_cache", exist_ok=True)

        for item in files_json:
            if item.get("mime") == "inode/directory":
                continue

            filename = item.get("name", "")
            file_url = url + filename   # <-- fix: build full file URL

            file_response = requests.get(file_url, auth=auth, timeout=15)
            if file_response.status_code == 200:
                local_cache_path = os.path.join("kudu_cache", filename)
                with open(local_cache_path, "wb") as f:
                    f.write(file_response.content)

                gallery_items.append((local_cache_path, filename))

        if not gallery_items:
            return [], "ℹ️ Connection successful, but no files were found in this tank folder."

        return gallery_items, f"🖼️ Loaded {len(gallery_items)} files successfully from Kudu storage."

    except Exception as e:
        return [], f"💥 Error accessing file structures: {str(e)}"


def assign_tanks(date, location, id):
    if not id or id in ["請選擇", "沒有記錄"]:
        return [], "沒有紀錄", [], "沒有紀錄", [], "沒有紀錄", [], "沒有紀錄", "請先選取有效車號"
    
    tanks = get_tank_names(date, location, id)

    if not tanks:
        return [], "沒有紀錄", [], "沒有紀錄", [], "沒有紀錄", [], "沒有紀錄", "注意：沒有相關紀錄"
        
    if isinstance(tanks, str):  # error message
        return [], "錯誤信號", [], "錯誤信號", [], "錯誤信號", [], "錯誤信號", tanks
    
    galleries_data = []
    labels = []
    
    for i in range(4):
        if i < len(tanks):
            tank_name = tanks[i]
            gallery_items, msg = find_jpg_images(date, location, id, tank_name)
            galleries_data.append(gallery_items)   # only keep the list of images
            labels.append(f"Tank: {tank_name}")
        else:
            galleries_data.append([])              # empty list for missing tanks
            labels.append("No Tank")
    
    msg = f"找到 {len(tanks)} 組紀錄: {', '.join(tanks)}"
    return (
        galleries_data[0], labels[0],
        galleries_data[1], labels[1],
        galleries_data[2], labels[2],
        galleries_data[3], labels[3],
        msg
    )

# Clear tanks when depot/date changes
def clear_tanks():
    return [], "No Tank", [], "No Tank", [], "No Tank", [], "No Tank", "請先選取有效車號"




#============================================================================================================================================================

###Hosting with Gradio
with gr.Blocks(head=prefer_back_camera()) as demo: # DeprecationWarning: The 'head' parameter in the Blocks constructor will be removed in Gradio 6.0. You will need to pass 'head' to Blocks.launch() i[...]
    gr.Markdown("落油記錄工具")

    with gr.Tabs():

        # Module 4
        with gr.Tab("記錄"):
            with gr.Row():
                date_picker = gr.DateTime(
                    label="日期", include_time=False,
                    value=datetime.now().date().isoformat()
                )
                location_dropdown2 = gr.Dropdown(
                    choices=locations, label="地點", value=locations[0]
                )
                car_dropdown2 = gr.Dropdown(
                    choices=[], label="車號", value=None, allow_custom_value=True, filterable=True, interactive=True, elem_id="tank_dropdown_history"
                )

            # Overall status message
            tank_message = gr.Textbox(label="Tank Summary", interactive=False,lines=2)

            # Tank labels + galleries
            tank_label1 = gr.Textbox(label="Tank Info 1", interactive=False)
            gallery1 = gr.Gallery(columns=4)

            tank_label2 = gr.Textbox(label="Tank Info 2", interactive=False)
            gallery2 = gr.Gallery(columns=4)

            tank_label3 = gr.Textbox(label="Tank Info 3", interactive=False)
            gallery3 = gr.Gallery(columns=4)

            tank_label4 = gr.Textbox(label="Tank Info 4", interactive=False)
            gallery4 = gr.Gallery(columns=4)

            # Update galleries + labels + summary when inputs change
            def update_all(date, location, car):
                g1, l1, g2, l2, g3, l3, g4, l4, msg = assign_tanks(date, location, car)
                return g1, l1, g2, l2, g3, l3, g4, l4, msg

            # --- Wiring ---
            date_picker.change(
                fn=safe_update_car_dropdown,
                inputs=[date_picker, location_dropdown2],
                outputs=[car_dropdown2,
                         gallery1, tank_label1,
                         gallery2, tank_label2,
                         gallery3, tank_label3,
                         gallery4, tank_label4,
                         tank_message]
            )
        
            location_dropdown2.change(
                fn=safe_update_car_dropdown,
                inputs=[date_picker, location_dropdown2],
                outputs=[car_dropdown2,
                         gallery1, tank_label1,
                         gallery2, tank_label2,
                         gallery3, tank_label3,
                         gallery4, tank_label4,
                         tank_message]
            )
        
            car_dropdown2.change(
                fn=safe_update_all,
                inputs=[date_picker, location_dropdown2, car_dropdown2],
                outputs=[gallery1, tank_label1,
                         gallery2, tank_label2,
                         gallery3, tank_label3,
                         gallery4, tank_label4,
                         tank_message]
            )


app = gr.mount_gradio_app(app, demo, path="/")
