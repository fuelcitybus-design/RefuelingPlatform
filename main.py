from fastapi import FastAPI
app = FastAPI()

#========================================================================================================

import os
import base64
import requests
from requests.auth import HTTPBasicAuth
import gradio as gr
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image
from openpyxl.drawing.image import Image as XLImage
from datetime import datetime

# --- CONFIGURATION ---
# Replace these with your actual Azure App Service credentials
USERNAME = "$oil-tank-refueling"
PASSWORD = "E8F6BQT62Mt290N5fpK1sHAnQTnxPyvsD2vXAqmmClZnYkyYDQ1Du17aNNiK"
auth=HTTPBasicAuth(USERNAME, PASSWORD)
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

###Module 1/O: Uploader camera forced setting
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

#=========================================================================================================================

### Module 1: Uploader function
def save_images(location, car_id, tank_id, request: gr.Request, *images):
    try:
        # logging
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        client_ip = request.client.host if request else "unknown"
        username = request.username if request and hasattr(request, "username") else "anonymous"
        uploaded_tabs = [tab_names[i] for i, img in enumerate(images) if img is not None]
        num_images = len(uploaded_tabs)

        #Warning for not selecting depot, tank car and tank info
        if (
            not location or location == "{請選擇}"
            or not car_id or car_id == "{請選擇}"
            or not tank_id or tank_id == "{請選擇}"
           ):
            info_msg = "警告：確保已輸入地點，車號，缸號"
            info_log = "Error: Please select Location, Car ID, and Tank ID."
            return info_msg

        #File path and name format for the images
        prefix = f"{location}/{car_id}_{tank_id}"
        #Auto-select today's date
        today = datetime.now().strftime("%Y-%m-%d")


        # --- Warning checkpoint 1: Check required tabs if any necessary images to be uploaded are missing (Forced batch uploading)---
        if required_tabs and forced_check:
            tab_dict = dict(zip(tab_names, images))
            missing = [tab for tab in required_tabs if not tab_dict.get(tab)]
            if missing:
                info_msg = f"警告：確保已輸入以下照片 {', '.join(missing)}"
                info_log = f"Error: Missing images for required tabs: {', '.join(missing)}"
                return info_msg

        #Setup connection to base directory
        base_url = f"{ROOT_FOLDER}/{today}/{prefix}/"

        # --- Warning checkpoint 2: Check if previous recording was made based on the individual image uploaded ---
        detected_tabs_exist = []
        baser = requests.get(base_url, auth=auth)
        if baser.status_code in [200,201]:
            # Check if any file of any image type to be uploaded exists in the folder
            items = baser.json()
            existing_files = [item["name"] for item in items if item.get("mime") != "inode/directory"]
            for f in existing_files:
                # Always add the raw filename (without extension)
                name, ext = os.path.splitext(f)
                detected_tabs_exist.append(name)

                # Special handling: detect 'before' or 'after' anywhere in the filename
                if "油車前" in name.lower() and "油車前" not in detected_tabs_exist:
                    detected_tabs_exist.append("油車前")
                if "油車後" in name.lower() and "油車後" not in detected_tabs_exist:
                    detected_tabs_exist.append("油車後")

        else:
            #Create image folder
            response = requests.put(base_url, auth=auth)
            if not(response.status_code in [200, 201]):
                info_msg = "❌Folder creation failed." 
                return info_msg

        #Saving the images
        return_msg = []
        saved_paths = []
        for i, img in enumerate(images):
            if img is None:
                continue
            if tab_names[i] in detected_tabs_exist:
                info_msg = f"跳過已上傳照片 {tab_names[i]}"
                info_log = f"Skipped uploaded image {tab_names[i]}"
                return_msg.append(info_msg)
                continue

            original_width, original_height = img.size
            new_width = int(original_width * (400 / original_height))
            img = img.resize((new_width, 400))
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)
            tab_name = tab_names[i]
            filename = f"{tab_name}.jpg"
            filepath = f"{base_url}{filename}"
            with open(img, "rb") as f:
                response = requests.put(filepath, data=buffer.getvalue(), auth=auth)
            if not(response.status_code in [200, 201]):
                info_msg = f"❌{tab_name} save failed." 
                return info_msg
            saved_paths.append(tab_name)
            detected_tabs_exist.append(tab_name)

        #Completion message
        if saved_paths:
            missing = [tab for tab in required_tabs if tab not in detected_tabs_exist]

            #Reminder message for if any required images are missing
            if missing:
              info_msg = f"已上傳 {len(saved_paths)} 張新照片\n請上傳{', '.join(missing)}."
              info_log = f"Uploaded {len(saved_paths)} new images \nPlease upload{', '.join(missing)}."
              return_msg.append(info_msg)
              return '\n'.join(return_msg)
            else:
              info_msg = f"已上傳 {len(saved_paths)} 張新照片"
              info_log = f"Uploaded {len(saved_paths)} new images"
              return_msg.append(info_msg)
              return '\n'.join(return_msg)
        else:
            info_msg = "警告：沒有新照片"
            info_log = "Warning: No new image"
            return_msg.append(info_msg)
            return '\n'.join(return_msg)

    except Exception as e:
        return f"未知錯誤: {str(e)}"

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
        if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
            return gr.update(visible=True)
        else:
            return gr.update(visible=False)

def clear_images(selection):
    # Reset all images when depot changes
    return [gr.update(value=None) for _ in tab_names]

#============================================================================================================================================================

with gr.Blocks(head=prefer_back_camera()) as demo: # DeprecationWarning: The 'head' parameter in the Blocks constructor will be removed in Gradio 6.0. You will need to pass 'head' to Blocks.launch() i[...]
    gr.Markdown("落油記錄工具")

    with gr.Tabs():

        # Module 1
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
                        img_input = gr.Image(
                                                type="pil",
                                                label=f"Upload {tab_name} photo",
                                                height=400,
                                                elem_id="camera_input"
                                            )
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

app = gr.mount_gradio_app(app, demo, path="/")
