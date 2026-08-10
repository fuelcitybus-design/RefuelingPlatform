#Setup environment for running Gradio interface
from fastapi import FastAPI
app = FastAPI()

#========================================================================================================

#Library imports
import os
import base64
import requests
from requests.auth import HTTPBasicAuth
import requests.exceptions
import gradio as gr
from datetime import datetime
from io import BytesIO
import re
import numpy as np
import cv2
from paddleocr import PaddleOCR
import tempfile
from PIL import Image as PILImage

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from datetime import datetime
import time
import traceback
import sys

#========================================================================================================

# --- CONFIGURATION ---
# Replace these with your actual Azure App Service credentials (consider reading from env vars)
USERNAME = "$oil-tank-refueling"
PASSWORD = "E8F6BQT62Mt290N5fpK1sHAnQTnxPyvsD2vXAqmmClZnYkyYDQ1Du17aNNiK"
auth = HTTPBasicAuth(USERNAME, PASSWORD)
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
        ("WKD西九", 22.329873814418242, 114.14657657248228)]

car_ids = ["{請選擇}", "第1車", "第2車", "第3車", "第4車", "第5車"]

tank_ids = ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸", "第7缸", "第8缸"]
tank_list = {"CFD創富": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸", "第7缸", "第8缸"],
        "CWD柴灣": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸"],
        "SHD小蠔灣": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "SWD上環": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "TCD東涌": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "TKD將軍澳": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "TMD屯門": ["{請選擇}", "第1缸", "第2缸", "第3缸", "第4缸", "第5缸", "第6缸"],
        "WCD黃竹坑": ["{請選擇}", "第1缸(廠外)", "第2缸(廠外)", "第3缸(廠內)"],
        "WKD西九": ["{請選擇}", "第1缸", "第2缸", "第3缸"]}

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
forced_check = False
ROOT_FOLDER = f"https://{KUDU_HOST}/api/vfs/data"

# =========================================================================================================================

HTTP_TIMEOUT = 12  # seconds

def http_get_json(url, timeout=HTTP_TIMEOUT, attempts=2):
    for attempt in range(attempts):
        try:
            with requests.Session() as s:
                s.auth = auth
                s.headers.update({"User-Agent": "RefuelingUploader/1.0"})
                r = s.get(url, timeout=timeout)
                status = r.status_code
                data = None
                try:
                    data = r.json()
                except Exception:
                    data = None
                try:
                    r.close()
                except Exception:
                    pass
                return status, data
        except requests.exceptions.RequestException as e:
            print(f"[http_get_json] attempt {attempt+1} error fetching {url}: {e}", file=sys.stderr)
            time.sleep(0.25 * (attempt + 1))
    return None, None

def http_put_status(url, data=None, timeout=HTTP_TIMEOUT, attempts=2):
    for attempt in range(attempts):
        try:
            with requests.Session() as s:
                s.auth = auth
                s.headers.update({"User-Agent": "RefuelingUploader/1.0"})
                r = s.put(url, data=data, timeout=timeout)
                status = r.status_code
                try:
                    r.close()
                except Exception:
                    pass
                return status
        except requests.exceptions.RequestException as e:
            print(f"[http_put_status] attempt {attempt+1} error putting {url}: {e}", file=sys.stderr)
            time.sleep(0.25 * (attempt + 1))
    return None

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
      const allowedKeys = [
        'ArrowDown', 'ArrowUp', 'Enter', 'Escape',
        'Tab', 'Shift', 'Control', 'Alt', 'Meta'
      ];
      if (allowedKeys.includes(e.key)) {
        return;
      }
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
          e.target.value = e.target._lastGoodValue || '';
        }
      }, true);
      document.addEventListener('paste', blockTankDropdownPaste, true);

      setTimeout(() => {
        TANK_DROPDOWN_IDS.forEach(id => {
          const tankInput = document.querySelector(`#${id} input[type="text"]`);
          if (tankInput) {
            tankInput._lastGoodValue = tankInput.value;
            tankInput.value = tankInput._lastGoodValue;
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

#=========================================================================================================================
global active_tabs
active_tabs = []
global tank_choices
tank_choices = []

# Single synchronous save handler (no global messages)
def save_images(location, car_id, tank_id, *images, request=None):
    start_ts = datetime.now().isoformat()
    try:
        client_repr = "unknown"
        try:
            if request and getattr(request, "client", None):
                client_repr = f"{request.client.host}:{request.client.port}"
        except Exception:
            client_repr = "unknown"

        print(f"[{start_ts}] save_images START location={location} car={car_id} tank={tank_id} client={client_repr}", file=sys.stderr, flush=True)

        uploaded_tabs = [tab_names[i] for i, img in enumerate(images) if img is not None]
        if not uploaded_tabs:
            return "警告：沒有選擇任何照片"

        if (
            not location or location == "{請選擇}"
            or not car_id or car_id == "{請選擇}"
            or not tank_id or tank_id == "{請選擇}"
        ):
            return "警告：確保已輸入地點，車號，缸號"

        tank_choices_local = tank_list.get(location, [])
        if not tank_choices_local or tank_id not in tank_choices_local:
            return f"警告：無效的缸號 \"{tank_id}\""

        prefix = f"{location}/{car_id}_{tank_id}"
        today = datetime.now().strftime("%Y-%m-%d")
        base_url = f"{ROOT_FOLDER}/{today}/{prefix}/"

        status, items = http_get_json(base_url)
        if status is None:
            return "網絡錯誤：無法連接到儲存伺服器（目錄檢查失敗）"
        detected_tabs_exist = []
        if status in (200, 201):
            items = items or []
            existing_files = [item.get("name") for item in items if item.get("name") and item.get("mime") != "inode/directory"]
            for f in existing_files:
                name, ext = os.path.splitext(f)
                if name and name not in detected_tabs_exist:
                    detected_tabs_exist.append(name)
                if "油車前" in name and "油車前" not in detected_tabs_exist:
                    detected_tabs_exist.append("油車前")
                if "油車後" in name and "油車後" not in detected_tabs_exist:
                    detected_tabs_exist.append("油車後")
        elif status == 404:
            created = False
            for attempt in range(3):
                put_status = http_put_status(base_url, data=b"")
                if put_status is None:
                    return "網絡錯誤：無法建立資料夾（伺服器未響應）"
                if put_status in (200, 201, 204):
                    created = True
                    break
                time.sleep(0.4 * (attempt + 1))
            if not created:
                return "❌Folder creation failed."
        else:
            put_status = http_put_status(base_url, data=b"")
            if put_status is None or put_status not in (200, 201, 204):
                return "❌Folder creation failed."

        saved = []
        messages_local = []
        for i, img in enumerate(images):
            if img is None:
                continue
            tab_name = tab_names[i]

            if tab_name in detected_tabs_exist:
                messages_local.append(f"跳過已上傳照片 {tab_name}")
                continue

            # Coerce to PILImage if necessary
            try:
                if hasattr(img, "size"):
                    original_width, original_height = img.size
                else:
                    img = PILImage.fromarray(np.array(img))
                    original_width, original_height = img.size
            except Exception:
                messages_local.append(f"錯誤：處理影像 {tab_name} 時發生錯誤")
                continue

            try:
                new_width = int(original_width * (400 / float(original_height))) if original_height else 400
            except Exception:
                new_width = 400
            img_resized = img.resize((max(1, new_width), 400))
            buffer = BytesIO()
            try:
                img_resized.save(buffer, format="JPEG", quality=85)
            except Exception:
                try:
                    img_resized = img_resized.convert("RGB")
                    buffer = BytesIO()
                    img_resized.save(buffer, format="JPEG", quality=85)
                except Exception:
                    messages_local.append(f"錯誤：儲存影像 {tab_name} 時發生錯誤")
                    continue
            buffer.seek(0)
            filepath = f"{base_url}{tab_name}.jpg"

            uploaded = False
            last_status = None
            for attempt in range(3):
                last_status = http_put_status(filepath, data=buffer.getvalue())
                if last_status is None:
                    messages_local.append(f"網絡錯誤：上傳 {tab_name} 失敗（未能連線）")
                    break
                if last_status in (200, 201, 204):
                    uploaded = True
                    break
                time.sleep(0.3 * (attempt + 1))
            if uploaded:
                saved.append(tab_name)
                detected_tabs_exist.append(tab_name)
                messages_local.append(f"已上傳: {tab_name}")
            else:
                messages_local.append(f"❌{tab_name} save failed. HTTP {last_status if last_status is not None else 'N/A'}")

        if saved:
            location_required_tabs = tab_list_S.get(location, [])
            missing = [tab for tab in location_required_tabs if tab not in detected_tabs_exist]
            if missing:
                messages_local.append(f"已上傳 {len(saved)} 張新照片\n請上傳{', '.join(missing)}.")
            else:
                messages_local.append(f"已上傳 {len(saved)} 張新照片")
        else:
            if not messages_local:
                messages_local.append("警告：沒有新照片")

        result_text = "\n".join(messages_local)
        print(f"[{datetime.now().isoformat()}] RETURNING: {repr(result_text)}", file=sys.stderr, flush=True)
        end_ts = datetime.now().isoformat()
        print(f"[{end_ts}] save_images END location={location} saved={len(saved)} client={client_repr}", file=sys.stderr, flush=True)
        return result_text
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[save_images] Exception: {e}\n{tb}", file=sys.stderr, flush=True)
        return f"未知錯誤: {str(e)}"

def nearest(gps):
    if "Allow" in gps:
        return "{請選擇}"
    lat, lon = map(float, gps.strip("[]").split(","))
    d = lambda c: (lat-c[1])**2 + (lon-c[2])**2
    return min(depot_gps, key=d)[0]

def update_tank_dropdown(location):
    global tank_choices
    tank_choices = tank_list.get(location, ["{請選擇}"])
    return gr.update(
        choices=tank_choices,
        value=tank_choices[0],
        label="缸號",
        interactive=True
    )

def toggle_ui_components(location, car, tank):
    global active_tabs
    active_tabs = tab_list_S.get(location, [])

    if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
        tab_updates = []
        for i, tab in enumerate(tab_names):
            if active_tabs and tab == active_tabs[0]:
                tab_updates.append(gr.update(visible=True))
            else:
                tab_updates.append(gr.update(visible=(tab in active_tabs)))

        save_btn_update = gr.update(visible=True)
        prev_btn_update = gr.update(visible=True)
        next_btn_update = gr.update(visible=True)

        first_idx = tab_names.index(active_tabs[0]) if active_tabs else None
        tabs_update = gr.update(selected=first_idx)
    else:
        tab_updates = [gr.update(visible=False) for _ in tab_names]
        save_btn_update = gr.update(visible=False)
        prev_btn_update = gr.update(visible=False)
        next_btn_update = gr.update(visible=False)
        tabs_update = gr.update(selected=None)

    return tab_updates + [save_btn_update, prev_btn_update, next_btn_update, tabs_update]

def toggle_tabs(location, car, tank):
    active_tabs_local = tab_list_S.get(location, [])
    if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
        updates = [gr.update(visible=(tab in active_tabs_local)) for tab in tab_names]
        info_msg = "Start uploading images"
    else:
        updates = [gr.update(visible=False) for _ in tab_names]
        info_msg = "Please select"
    return updates

def toggle_save(location, car, tank):
    if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)

def set_current(idx):
    return idx

def next_tab(current, location):
    active_tabs_local = tab_list_S.get(location, [])
    if not active_tabs_local:
        return gr.Tabs(selected=None), current
    active_indices = [tab_names.index(tab) for tab in active_tabs_local]
    try:
        pos = active_indices.index(current)
    except ValueError:
        pos = 0
    nxt = active_indices[(pos + 1) % len(active_indices)]
    return gr.Tabs(selected=nxt), nxt

def prev_tab(current, location):
    active_tabs_local = tab_list_S.get(location, [])
    if not active_tabs_local:
        return gr.Tabs(selected=None), current
    active_indices = [tab_names.index(tab) for tab in active_tabs_local]
    try:
        pos = active_indices.index(current)
    except ValueError:
        pos = 0
    nxt = active_indices[(pos - 1) % len(active_indices)]
    return gr.Tabs(selected=nxt), nxt

#============================================================================================================================================================

with gr.Blocks(head=prefer_back_camera()) as demo:
    gr.Markdown("落油記錄工具")

    with gr.Tabs():

        with gr.Tab("拍照"):
            
            current = gr.State(0)

            with gr.Row():
                location_dropdown = gr.Dropdown(choices=locations, label="地點(gps)", value=locations[0], allow_custom_value=False, filterable=False, interactive=True)
                car_dropdown = gr.Dropdown(choices=car_ids, label="車號", value=car_ids[0], allow_custom_value=False, filterable=False)
                tank_dropdown = gr.Dropdown(choices=["{請選擇}"], label="缸號", value="{請選擇}", allow_custom_value=True, filterable=True, interactive=True, elem_id="tank_dropdown_uploader")
                confirm_btn = gr.Button("確認選擇")

                raw_gps = gr.Textbox(visible=False)
                demo.load(None, None, raw_gps, js="""() => new Promise(r => navigator.geolocation.getCurrentPosition(
                    p => r(`[${p.coords.latitude}, ${p.coords.longitude}]`),
                    () => r("[Tap Allow Location]"), {enableHighAccuracy:true}))""")
                raw_gps.change(fn=nearest, inputs=raw_gps, outputs=location_dropdown)
                location_dropdown.change(fn=update_tank_dropdown,
                                         inputs=location_dropdown,
                                         outputs=tank_dropdown)

            gr.Markdown("---")
                
            with gr.Row(equal_height=True):
                prev_btn = gr.Button("⬅️",visible=False, scale=1, min_width=30)
                next_btn = gr.Button("➡️",visible=False, scale=1, min_width=30)      
            
            def sync_tab_index(evt: gr.SelectData):
                return evt.index
                
            with gr.Row():
                with gr.Tabs(selected=None) as img_tabs:
                    image_inputs = []
                    tab_list_local = []
                    for i, tab_name in enumerate(tab_names):
                        with gr.Tab(tab_name, id =i, visible=False) as tab:
                            img_input = gr.Image(
                                type="pil",
                                label=f"上傳「{tab_name}」相片",
                                height=400,
                                elem_id="camera_input",
                                mirror_webcam=False,
                                sources=['webcam','upload']
                            )
                            image_inputs.append(img_input)
                            tab_list_local.append(tab)

            img_tabs.select(sync_tab_index, None, current)

            save_btn = gr.Button("儲存所有相片", variant="primary", size="lg", visible=False)

            output_text = gr.Textbox(label="狀態", lines=6)

            next_btn.click(
                    fn=next_tab,
                    inputs=[current, location_dropdown],
                    outputs=[img_tabs, current]
                )
                
            prev_btn.click(
                    fn=prev_tab,
                    inputs=[current, location_dropdown],
                    outputs=[img_tabs, current]
                )

            save_btn.click(
                fn=save_images,
                inputs=[location_dropdown, car_dropdown, tank_dropdown] + image_inputs,
                outputs=output_text
            )

            confirm_btn.click(
                fn=toggle_ui_components,
                inputs=[location_dropdown, car_dropdown, tank_dropdown],
                outputs=tab_list_local + [save_btn, prev_btn, next_btn, img_tabs]
            )
           
            gr.HTML(prefer_back_camera())

            demo.css = """
            #camera_input button {
                transform: scale(1.6);
            }
            .gradio-container,
            body,
            div,
            span,
            p,
            label,
            button,
            h1, h2, h3, h4, h5, h6,
            textarea,
            input,
            select {
                font-size: 16px !important;
            }
            #camera_input label {
                font-size: 20px !important;
            }
            #camera_input .dropdown-arrow {
                display: none !important;
            }
            #camera_input .select-wrap {
                display: none !important;
            }
            #camera_input button-wrap.button.icon {
                display: none !important;
            }            
            """
# Enable Gradio queue (compatibility fallback)
try:
    demo.queue(concurrency_count=4, max_size=32)
except TypeError:
    demo.queue()

app = gr.mount_gradio_app(app, demo, path="/")
