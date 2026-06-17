from fastapi import FastAPI
app = FastAPI()

#========================================================================================================
#
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

# --- CONFIGURATION ---
# Replace these with your actual Azure App Service credentials
USERNAME = "$oil-tank-refueling"
PASSWORD = "E8F6BQT62Mt290N5fpK1sHAnQTnxPyvsD2vXAqmmClZnYkyYDQ1Du17aNNiK"
auth=HTTPBasicAuth(USERNAME, PASSWORD)
KUDU_HOST = "oil-tank-refueling-e8a5atdqg9fnh2et.scm.eastasia-01.azurewebsites.net"

os.environ["FLAGS_use_mkldnn"] = "0"

ocr_model = PaddleOCR(
    lang="ch",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False,   # valid flag for CPU acceleration
    )
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

###Module 2: AI proessor function
abnormal_count = 0

# =====================================================================
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

# =====================================================================
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

# =====================================================================
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

# =====================================================================
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
    return abnormal_list_10, msg, *imgs, *txts

# =====================================================================
# Display Functions
def show_img(abnormal_list):
    imgs = []
    for i in range(10):
        if i < len(abnormal_list):
            # List structure: [prefix, ocr_number, file_url]
            file_url = abnormal_list[i][2]
            cv_img = download_from_kudu(file_url)
            if cv_img is None:
                cv_img = np.zeros((100, 100, 3), dtype=np.uint8)
            imgs.append(cv_img)
        else:
            imgs.append(None)
    return imgs

def show_txt(abnormal_list):
    return [
        f"{abnormal_list[i][0]}_{abnormal_list[i][1]}" if i < len(abnormal_list) else ""
        for i in range(10)
    ]

# =====================================================================
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
        if int(ocr_original) != int(text_list[i]):
            num_update += 1
            kudu_rename(file_url, new_name)
    
    if abnormal_count > 10:
        result = analysis_rename(request, root_folder_O=ROOT_FOLDER)
        return result[1], result[0]
    else:
        return "儲存成功", []

# =====================================================================
# Gradio Hosting
with gr.Blocks(head=prefer_back_camera()) as demo:
    gr.Markdown("落油記錄工具")

    with gr.Tabs():
        with gr.Tab("AI處理"):
            abnormal_list = gr.State([])
            state = gr.Textbox(label="狀態", lines=5)
            
            txts, imgs = [], []
            run_btn = gr.Button("運行AI")
            run_btn.click(
                fn=analysis_rename,
                inputs=[],
                outputs=[abnormal_list, state] + imgs + txts
            )


            for i in range(10):
                with gr.Row():
                    img = gr.Image(None, label=i, visible=False, width=150, interactive=False)
                    imgs.append(img)
                    txt = gr.Textbox(value=None, label=i, visible=False)
                    txts.append(txt)

            abnormal_list.change(fn=show_img, inputs=abnormal_list, outputs=imgs)
            abnormal_list.change(fn=show_txt, inputs=abnormal_list, outputs=txts)



            collect_btn = gr.Button("儲存所有修改")
            collect_btn.click(fn=collect_all_texts, inputs=[abnormal_list] + txts, outputs=[state, abnormal_list])

app = gr.mount_gradio_app(app, demo, path="/")
