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
            # Upload directly from buffer
            response = requests.put(filepath, data=buffer.getvalue(), auth=auth)
            if response.status_code not in [200, 201]:
                return f"❌{tab_name} save failed."
            saved_paths.append(tab_name)
            detected_tabs_exist.append(tab_name)

        #Completion message
        if saved_paths:
            required_tabs = tab_list_S.get(location, [])
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

def toggle_ui_components(location, car, tank):
    active_tabs = tab_list_S.get(location, [])

    if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
        tab_updates = []
        for i, tab in enumerate(tab_names):
            # Always show the first tab of the active list
            if active_tabs and tab == active_tabs[0]:
                tab_updates.append(gr.update(visible=True))
            else:
                tab_updates.append(gr.update(visible=(tab in active_tabs)))

        save_btn_update = gr.update(visible=True)
        prev_btn_update = gr.update(visible=True)
        next_btn_update = gr.update(visible=True)

        # Select the first active tab index
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
    info_msg = []
    active_tabs = tab_list_S.get(location, [])
    if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
        updates = [gr.update(visible=(tab in active_tabs)) for tab in tab_names]
        info_msg = "Start uploading images"
    else:
        # Hide all tabs if not valid
        updates = [gr.update(visible=False) for _ in tab_names]
        info_msg = "Please select"
    return updates

def toggle_save(location, car, tank):
    # Show save button only if all dropdowns are not placeholders
    if location != "{請選擇}" and car != "{請選擇}" and tank != "{請選擇}":
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)

#def clear_images(selection):
    # Reset all images when depot changes
    #return [gr.update(value=None) for _ in tab_names]

def set_current(idx):
    return idx

def next_tab(current, location):
    active_tabs = tab_list_S.get(location, [])
    if not active_tabs:
        return gr.Tabs(selected=None), current

    # Map active tab names to their indices in tab_names
    active_indices = [tab_names.index(tab) for tab in active_tabs]

    # Find current position in active list
    try:
        pos = active_indices.index(current)
    except ValueError:
        pos = 0  # fallback if current not in active list

    nxt = active_indices[(pos + 1) % len(active_indices)]
    return gr.Tabs(selected=nxt), nxt

def prev_tab(current, location):
    active_tabs = tab_list_S.get(location, [])
    if not active_tabs:
        return gr.Tabs(selected=None), current

    active_indices = [tab_names.index(tab) for tab in active_tabs]

    try:
        pos = active_indices.index(current)
    except ValueError:
        pos = 0

    nxt = active_indices[(pos - 1) % len(active_indices)]
    return gr.Tabs(selected=nxt), nxt


#========================================================================================================

#Module 2/O: OCR Model setup
os.environ["FLAGS_use_mkldnn"] = "0"

ocr_model = PaddleOCR(
    lang="ch",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False,   # valid flag for CPU acceleration
    )

#=========================================================================================================================

###Module 2: AI proessor function
abnormal_count = 0

# Image Enhancement
def auto_adjust_brightness_contrast(img_cv, clip_limit=2.0, tile_grid_size=(8,8)):
    lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l_adjusted = clahe.apply(l)
    lab_adjusted = cv2.merge([l_adjusted, a, b])
    adjusted_cv = cv2.cvtColor(lab_adjusted, cv2.COLOR_LAB2BGR)
    return adjusted_cv

def area(bbox):
    bbox = np.array(bbox, dtype=np.int64)
    x1, y1, x2, y2 = bbox
    return abs((x2-x1)*(y2-y1))


# OCR from Kudu
def ocr_from_kudu(file_url):
    resp = requests.get(file_url, auth=auth)
    resp.raise_for_status()
    file_bytes = np.frombuffer(resp.content, np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    h, w, c = image.shape
    image = cv2.resize(image, (400, int(400 * h / float(w))), interpolation=cv2.INTER_AREA)
    image = auto_adjust_brightness_contrast(image)

    result = ocr_model.predict(image)
    for res in result:
        text = res["rec_texts"]
        conf = res["rec_scores"]
        box = res["rec_boxes"]
        result_list = []
        for i in range(len(text)):
            num = re.sub(r'[.,]', '', text[i])
            if conf[i] > 0.8 and num.isdigit():
                if int(num) < 100000:
                    result_list.append([int(num), round(conf[i], 3), box[i], area(box[i])])
        result_list = sorted(result_list, key=lambda x: x[3], reverse=True)
        if not result_list:
            return 0
        for x, _, _, _ in result_list:
            if 0 < x < 10: continue
            elif x > 30000: continue
            else: return str(x)
        return str(0)


# Kudu Helpers
def kudu_list_files(root_url, pattern="油車前.jpg"):
    resp = requests.get(root_url, auth=auth)
    resp.raise_for_status()
    items = resp.json()   # this is already a list, not a dict
    
    matches = []
    for item in items:
        if item["mime"] == "inode/directory":
            # recurse into subfolder
            sub_url = root_url.rstrip("/") + "/" + item["name"] + "/"
            matches.extend(kudu_list_files(sub_url, pattern))
        else:
            if item["name"].lower() == pattern.lower() or pattern == "*.jpg":
                matches.append(root_url.rstrip("/") + "/" + item["name"])
    return matches

def kudu_rename(file_url, new_name):
    # Download the file
    resp = requests.get(file_url, auth=auth)
    resp.raise_for_status()
    content = resp.content

    # Construct new URL
    folder_url = "/".join(file_url.split("/")[:-1])
    new_url = folder_url + "/" + new_name

    # Upload with overwrite (If-Match: *)
    put_resp = requests.put(
        new_url,
        data=content,
        auth=auth,
        headers={"If-Match": "*"}
    )
    put_resp.raise_for_status()

    # Delete old file
    del_resp = requests.delete(file_url, auth=auth, headers={"If-Match": "*"})
    del_resp.raise_for_status()

    return new_url

def download_from_kudu(file_url):
    resp = requests.get(file_url, auth=auth)
    resp.raise_for_status()
    file_bytes = np.frombuffer(resp.content, np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    return image


# Analysis & Abnormal Extraction
def analysis_rename(request: gr.Request, root_folder_O=ROOT_FOLDER):
    root_folder = f"{root_folder_O}/"
    abnormal_list = []
    num_analysis = 0

    # 油車前
    for file_url in kudu_list_files(root_folder, "油車前.jpg"):
        ocr_number = ocr_from_kudu(file_url)
        new_name = f"X_油車前_{ocr_number}.jpg" if int(ocr_number) != 0 else f"油車前_{ocr_number}.jpg"
        kudu_rename(file_url, new_name)
        num_analysis += 1

    # 油車後
    for file_url in kudu_list_files(root_folder, "油車後.jpg"):
        ocr_number = ocr_from_kudu(file_url)
        new_name = f"X_油車後_{ocr_number}.jpg" if int(ocr_number) < 6000 else f"油車後_{ocr_number}.jpg"
        kudu_rename(file_url, new_name)
        num_analysis += 1

    # Collect abnormal entries
    pattern = re.compile(r'^X_(油車前|油車後)_(.+)\.jpg$', re.IGNORECASE)
    for file_url in kudu_list_files(root_folder, "*.jpg"):
        fname = file_url.split("/")[-1]
        match = pattern.match(fname)
        if match:
            # Store: [prefix, ocr_number, file_url]
            abnormal_list.append([match.group(1), match.group(2), file_url])

    abnormal_list_10 = abnormal_list[:10]
    global abnormal_count
    abnormal_count = len(abnormal_list)

    # Build images (numpy arrays) for gr.Image
    imgs = []
    for i in range(10):
        if i < len(abnormal_list_10):
            file_url = abnormal_list_10[i][2]
            cv_img = download_from_kudu(file_url)
            if cv_img is None:
                # Placeholder for failed images
                cv_img = np.zeros((100, 100, 3), dtype=np.uint8)
            imgs.append(cv_img)
        else:
            imgs.append(None)

    # Build text labels for gr.Textbox
    txts = [
        f"{abnormal_list_10[i][0]}_{abnormal_list_10[i][1]}" if i < len(abnormal_list_10) else ""
        for i in range(10)
    ]

    # Status message
    if len(abnormal_list) <= 10:
        msg = f"{len(abnormal_list)}張照片需要檢查"
    else:
        msg = f"剩餘{len(abnormal_list)}張照片需要檢查，先檢查首 10 張，然後再按一次分析繼續"

    # Return: state, status, 10 images, 10 texts
    return abnormal_list_10, msg


# Display Functions
def show_img(abnormal_list):
    updates = [gr.update(visible=False)] * 10
    for i in range(len(abnormal_list)):
        file_url = abnormal_list[i][2]
        cv_img = download_from_kudu(file_url)
        if cv_img is None:
            cv_img = np.zeros((100, 100, 3), dtype=np.uint8)
        updates[i] = gr.update(visible=True, value=cv_img)
    return updates

def show_txt(abnormal_list):
    updates = [gr.update(visible=False)] * 10
    for i in range(len(abnormal_list)):
        updates[i] = gr.update(
            visible=True,
            value="",
            label=f"{abnormal_list[i][0]}_{abnormal_list[i][1]}"
        )
    return updates


# Correction Function
def collect_all_texts(request: gr.Request, abnormal_list, *texts):
    text_list = []
    n = min(len(abnormal_list), len(texts))
    for idx in range(n):
        txt = texts[idx]
        if txt is None or txt.strip() == "":
            return f"警告：第{idx+1}張照片缺少輸入", abnormal_list
        try:
            num = int(txt.strip())
            text_list.append(num)
        except ValueError:
            return f"警告：第{idx+1}張照片非數字輸入", abnormal_list
    
    if len(text_list) < len(abnormal_list):
        return "警告：缺少輸入", abnormal_list
    
    num_update = 0
    for i in range(len(abnormal_list)):
        # ✅ Fix these lines to use list indices
        file_url = abnormal_list[i][2]      # was ["url"]
        prefix = abnormal_list[i][0]         # was ["prefix"]
        ocr_original = abnormal_list[i][1]   # was ["ocr"]
        
        new_name = f"{prefix}_{text_list[i]}.jpg"
        #if int(ocr_original) != int(text_list[i]): {!!!Considering if the numbers are actually correctly under threshold}
        num_update += 1
        kudu_rename(file_url, new_name)
    
    if abnormal_count > 10:
        result = analysis_rename(request, root_folder_O=ROOT_FOLDER)
        return result[1], result[0]
    else:
        return "儲存成功", []

#=========================================================================================================================

### Module 3: Export functions
def add_data(wb, car, tank, before, after, img_list, rowcount):
    RAW = wb['RAW']
    MAIN = wb['Main']

    for i in range(2, rowcount + 2):
        if RAW.cell(row=i, column=2).value is None:
            RAW.cell(row=i, column=2).value = car
            RAW.cell(row=i, column=3).value = tank
            RAW.cell(row=i, column=4).value = int(before)
            RAW.cell(row=i, column=5).value = int(after)
                
            MAIN.cell(row=10 * (i - 1), column=1).value = i-1
            MAIN.cell(row=10 * (i - 1) + 1, column=1).value = car
            MAIN.cell(row=10 * (i - 1) + 2, column=1).value = tank

            for j, img in enumerate(img_list):
                if img is None:
                    continue
                
                # Download image from Kudu
                response = requests.get(img, auth=auth)
                if response.status_code != 200:
                    raise Exception(f"❌ Failed to download image: HTTP {response.status_code}")
                
                MAIN.cell(row=10 * (i - 1), column=2+3*j).value = img.split("/")[-1].rsplit(".", 1)[0]
                # Load directly from memory
                image_data = BytesIO(response.content)
                image = XLImage(image_data)

                # Resize proportionally
                if image.width > image.height:
                    image.height = image.height / image.width * 180
                    image.width = 180
                else:
                    image.width = image.width / image.height * 180
                    image.height = 180

                # Place into correct cell
                cell_address = get_column_letter(3 * j + 2) + str(10 * i - 9)
                MAIN.add_image(image, cell_address)

    return



def export(request: gr.Request, location, date):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_ip = request.client.host if request else "unknown"
    username = request.username if request and hasattr(request, "username") else "anonymous"
    date = datetime.fromtimestamp(date).strftime('%Y-%m-%d')
    folder_url = f"{ROOT_FOLDER}/{date}/{location}/"
    template_url = f"{ROOT_FOLDER}/template.xlsx"

    if not location or location == "{請選擇}":
            info_msg = "警告：確保已輸入地點"
            info_log = "Error: Please select Location."
            return None, info_msg
    
    #Template from KUDU
    templateR = requests.get(template_url, auth=auth)
    if templateR.status_code != 200:
        raise Exception(f"❌ Error {templateR.status_code}: {templateR.text}")
    # Step 2: Save locally
    local_path = "/tmp/template.xlsx"
    with open(local_path, "wb") as f:
        f.write(templateR.content)
    # Step 3: Load workbook
    wb = load_workbook(local_path)

    folder = requests.get(folder_url, auth=auth, timeout=15)
    if folder.status_code != 200:
        info_msg = "警告：沒有相關記錄"
        info_log = "Warning: No record avaliable"
        return None, info_msg
    RAW = wb['RAW']
    MAIN = wb['Main']
    SUBR = requests.get(folder_url+"/", auth=auth)
    if SUBR.status_code != 200:
        return [], f"❌ Error {SUBR.status_code}: {SUBR.text}"

    items = SUBR.json()
    # Extract only subfolders
    subfolders = [item["name"] for item in items if item.get("mime") == "inode/directory"]

    data_count = len(subfolders)
    for i in range(data_count):
        MAIN.cell(row=10+10*(i), column=1).value = i+1
        for j in range(len(tab_names)):
            MAIN.cell(row=10+10*i, column=2+3*j).value = tab_names[j]
        RAW.cell(row=2+i, column=1).value = i+1
        RAW.cell(row=2+i, column=6).value = f"=E{2+i}-D{2+i}"


    for subfolder_name in subfolders:
        carid, tankid = subfolder_name.split("_")
        subfolder_url = f"{folder_url}{subfolder_name}/"

        before = None
        after = None
        sort_list = []
        images = []
        imagesr = requests.get(subfolder_url, auth=auth)
        if imagesr.status_code == 200:
            items = imagesr.json()
            for item in items:
                if item.get("mime") != "inode/directory":  # only files
                    images.append(item["name"])
        else:
                info_msg = "Can't access image"
                return None, info_msg

        for img in images:
            file_url = f"{subfolder_url}{img}"
            if "油車前" in img:
                try:
                    name, value, _ = img.replace('.', '_').split("_")
                except:
                    info_msg = "警告：缺少圖片，請確保已運行AI並儲存修改"
                    info_log = "Warning: Image undetected. Remember to run AI analysis before exporting."
                    return None, info_msg
                before = [file_url, value]

            elif "油車後" in img:
                try:
                    name, value, _ = img.replace('.', '_').split("_")
                except:
                    info_msg = "警告：缺少圖片，請確保已運行AI並儲存修改"
                    info_log = "Warning: Image undetected. Remember to run AI analysis before exporting."
                    return None, info_msg

                after = [file_url, value]
            else:
                sort_list.append(file_url)

        if before == None or after == None:
            info_msg = "警告：缺少圖片，請確保已拍照並儲存"
            info_log = "Warning: Image missing. Please Upload your image by image recorder."
            return None, info_msg

        sort_list = [before[0], after[0]] + sort_list

        add_data(wb, carid, tankid, before[1], after[1], sort_list, data_count)
    save_url = f"{folder_url}/{location}_{date}.xlsx"
    local_path = f"/tmp/{location}_{date}.xlsx"
    wb.save(local_path)

    with open(local_path, "rb") as f:
        wbp = requests.put(save_url, data=f, auth=auth)
    if wbp.status_code in [200, 201]:
        return local_path, "✅ 導出成功，已上傳"
    else:
        del_resp = requests.delete(save_url, auth=auth, headers={"If-Match": "*"})
        with open(local_path, "rb") as f:
            wbp = requests.put(save_url, data=f, auth=auth)
        if wbp.status_code in [200, 201]:
            return local_path, "✅ 導出成功，已更新存檔"
        else:
            return local_path, f" 導出成功，只能從上下載最新版本: {wbp.status_code} {wbp.text}"

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
            
def update_car_dropdown(date, location):
    car_ids = get_car_ids(date, location)
    if car_ids:
        return gr.update(choices=car_ids, value=car_ids[0])
    else:
        return gr.update(choices=[], value=None)

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
    if not id:
        return [], "沒有紀錄", [], "沒有紀錄", [], "沒有紀錄", [], "沒有紀錄", "請先選取有效日期、地點、車號"
    
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

#============================================================================================================================================================

###Hosting with Gradio
with gr.Blocks(head=prefer_back_camera()) as demo: # DeprecationWarning: The 'head' parameter in the Blocks constructor will be removed in Gradio 6.0. You will need to pass 'head' to Blocks.launch() i[...]
    gr.Markdown("落油記錄工具")

    with gr.Tabs():

        # Module 1
        with gr.Tab("拍照"):
            
            current = gr.State(0)

            with gr.Row():
                location_dropdown = gr.Dropdown(choices=locations, label="地點(gps)", value=locations[0], allow_custom_value=False, filterable=False, interactive=True)
                car_dropdown = gr.Dropdown(choices=car_ids, label="車號", value=car_ids[0], allow_custom_value=False, filterable=False)
                tank_dropdown = gr.Dropdown(choices=["{請選擇}"], label="缸號", value="{請選擇}", allow_custom_value=False, filterable=False)
                confirm_btn = gr.Button("確認選擇")

                raw_gps = gr.Textbox(visible=False)
                demo.load(None, None, raw_gps, js="""() => new Promise(r => navigator.geolocation.getCurrentPosition(
                    p => r(`[${p.coords.latitude}, ${p.coords.longitude}]`),
                    () => r("[Tap Allow Location]"), {enableHighAccuracy:true}))""")
                # GPS sets location
                raw_gps.change(fn=nearest, inputs=raw_gps, outputs=location_dropdown)
                
                # Location change updates tanks
                location_dropdown.change(fn=update_tank_dropdown,
                                         inputs=location_dropdown,
                                         outputs=tank_dropdown)

            gr.Markdown("---")
                
            # --- Tabs with arrow navigation ---
            with gr.Row(equal_height=True):
                prev_btn = gr.Button("⬅️",visible=False, scale=1, min_width=30)
                next_btn = gr.Button("➡️",visible=False, scale=1, min_width=30)      
            
            # Track current tab index
            
            with gr.Row():
                with gr.Tabs(selected=None) as img_tabs:
                    image_inputs = []
                    tab_list = []
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
                            tab_list.append(tab)            
                
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
                outputs=tab_list + [save_btn, prev_btn, next_btn, img_tabs]  # include img_tabs for selected update
            )
           
            # Raw HTML input for back camera
            gr.HTML(prefer_back_camera())
            #Toggle tabs avaliable based on depot selection
            #location_dropdown.change(toggle_tabs, [location_dropdown,car_dropdown,tank_dropdown], tab_list)
            #car_dropdown.change(toggle_tabs, [location_dropdown,car_dropdown,tank_dropdown], tab_list)
            #tank_dropdown.change(toggle_tabs, [location_dropdown,car_dropdown,tank_dropdown], tab_list)

            #Toggle save button
            #location_dropdown.change(toggle_save, [location_dropdown,car_dropdown,tank_dropdown], save_btn)
            #car_dropdown.change(toggle_save, [location_dropdown,car_dropdown,tank_dropdown], save_btn)
            #tank_dropdown.change(toggle_save, [location_dropdown,car_dropdown,tank_dropdown], save_btn)
                
            #Clear uploaded images when changing information values
            #location_dropdown.change(clear_images, location_dropdown, image_inputs)
            #car_dropdown.change(clear_images, location_dropdown, image_inputs)
            #tank_dropdown.change(clear_images, location_dropdown, image_inputs)

        # Module 2
        with gr.Tab("AI 處理"):
            abnormal_list = gr.State([])
            state = gr.Textbox(label="狀態", lines=5)
            txts, imgs = [], []
            img_idx_states, txt_idx_states = [], []  # Store index states
            
            run_btn = gr.Button("運行 AI")
            run_btn.click(
                fn=analysis_rename,
                inputs=[],
                outputs=[abnormal_list, state]
            )
            
            for i in range(10):
                with gr.Row():
                    img = gr.Image(None, label=f"圖{i+1}", visible=False, width=150, interactive=False)
                    imgs.append(img)
                    txt = gr.Textbox(value=None, label=f"待修改/認證{i+1}", visible=False)
                    txts.append(txt)
                    
                    # Create State to hold the index i
                    img_idx_state = gr.State(i)
                    txt_idx_state = gr.State(i)
                    img_idx_states.append(img_idx_state)
                    txt_idx_states.append(txt_idx_state)
            
            # Add individual change handlers for each img/txt
            abnormal_list.change(fn=show_img, inputs=abnormal_list, outputs=imgs)
            abnormal_list.change(fn=show_txt, inputs=abnormal_list, outputs=txts)
            
            collect_btn = gr.Button("儲存所有修改")
            collect_btn.click(fn=collect_all_texts, inputs=[abnormal_list] + txts, outputs=[state, abnormal_list])    

        # Module 3
        with gr.Tab("下載"):
            with gr.Row():
                location_dropdown = gr.Dropdown(choices=locations, label="地點", value=locations[0], allow_custom_value=False, filterable=False)
                date_picker = gr.DateTime(label="日期", include_time=False, value=str(datetime.now().date()))

            output = gr.File(label="下載")
            state = gr.Textbox(label="狀態")

            export_btn = gr.Button("下載")
            export_btn.click(
                fn=export,
                inputs=[location_dropdown, date_picker],
                outputs=[output, state]
            )

        # Module 4
        with gr.Tab("記錄"):
            with gr.Row():
                date_picker = gr.DateTime(
                    label="日期", include_time=False,
                    value=datetime.now().date().isoformat()
                )
                location_dropdown2 = gr.Dropdown(
                    choices=locations, label="地點(gps)", value=locations[0]
                )
                car_dropdown2 = gr.Dropdown(
                    choices=[], label="車號", value=None
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

            # Refresh car dropdown whenever date or location changes
            date_picker.change(update_car_dropdown, [date_picker, location_dropdown2], car_dropdown2)
            location_dropdown2.change(update_car_dropdown, [date_picker, location_dropdown2], car_dropdown2)

            # Update tanks whenever any input changes
            date_picker.change(update_all, [date_picker, location_dropdown2, car_dropdown2],
                                [gallery1, tank_label1, gallery2, tank_label2,
                                gallery3, tank_label3, gallery4, tank_label4, tank_message])
            location_dropdown2.change(update_all, [date_picker, location_dropdown2, car_dropdown2],
                                [gallery1, tank_label1, gallery2, tank_label2,
                                gallery3, tank_label3, gallery4, tank_label4, tank_message])
            car_dropdown2.change(update_all, [date_picker, location_dropdown2, car_dropdown2],
                                [gallery1, tank_label1, gallery2, tank_label2,
                                gallery3, tank_label3, gallery4, tank_label4, tank_message])

            demo.css = """
            #camera_input button {
                transform: scale(1.6);   /* Scaling for making all gr.image buttons larger */
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
        
app = gr.mount_gradio_app(app, demo, path="/")
