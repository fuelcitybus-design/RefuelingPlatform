from fastapi import FastAPI
app = FastAPI()

#========================================================================================================

import os
import base64
import requests
from requests.auth import HTTPBasicAuth
import gradio as gr
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image
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

def add_data(wb, car, tank, before, after, img_list, rowcount):
    RAW = wb['RAW']
    MAIN = wb['Main']
    for i in range(2,rowcount+2):
        if RAW.cell(row=i, column=2).value is None:
            # data
            RAW.cell(row=i, column=2).value = car
            RAW.cell(row=i, column=3).value = tank
            RAW.cell(row=i, column=4).value = int(before)
            RAW.cell(row=i, column=5).value = int(after)
            MAIN.cell(row=10*(i-1)+1, column=1).value = car
            MAIN.cell(row=10*(i-1)+2, column=1).value = tank

            for j, img in enumerate(img_list):
                if img == None:
                    continue
                image = Image(img)
                if image.width > image.height:
                    image.height = image.height/image.width*180
                    image.width = 180
                else:
                    image.width = image.width/image.height*180
                    image.height = 180
                MAIN.add_image(image, get_column_letter(3*j+2)+str(10*i-9))
            return
    return

def export(request: gr.Request, location, date):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_ip = request.client.host if request else "unknown"
    username = request.username if request and hasattr(request, "username") else "anonymous"
    date = datetime.fromtimestamp(date).strftime('%Y-%m-%d')
    folder_url = f"{ROOT_FOLDER}/{date}/{location}"
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
        subfolder_url = f"{folder_url}/{subfolder_name}/"

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
        return local_path, f"❌ 導出成功，但上傳失敗: {wbp.status_code} {wbp.text}"


#============================================================================================================================================================

with gr.Blocks(head=prefer_back_camera()) as demo: # DeprecationWarning: The 'head' parameter in the Blocks constructor will be removed in Gradio 6.0. You will need to pass 'head' to Blocks.launch() i[...]
    gr.Markdown("落油記錄工具")
        
    # Module 4
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



app = gr.mount_gradio_app(app, demo, path="/")
