#==============================================================================================
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
from PIL import ExifTags
import fnmatch

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from datetime import datetime
import time
import traceback
import sys

#---------------------------------------------------------------------------------
#Setup environment for running Gradio interface
from fastapi import FastAPI
from fastapi.responses import JSONResponse
app = FastAPI()
#---------------------------------------------------------------------------------
#Warm-up -er
def safe_request(url, method="get", retries=3, **kwargs):
    for attempt in range(retries):
        try:
            resp = getattr(requests, method)(url, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # exponential backoff
            else:
                raise

# --- Warm‑up hook ---
@app.on_event("startup")
async def warmup():
    try:
        # Example: ping a lightweight endpoint or Kudu
        safe_request(ROOT_FOLDER + "/healthcheck", auth=auth)
        print("Warm‑up completed")
    except Exception as e:
        print("Warm‑up failed:", e)

# --- Your routes / Gradio mount ---
@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}

#========================================================================================================
# Custom JavaScript to inject into the front-end
# It checks browser online/offline status and attempts to ping the server
# Also attaches listeners to image components to capture source (webcam/upload)
# and timestamps (shutter time for webcam captures, file metadata time for uploads)
monitor_connection_js = """
function checkConnection() {
    const statusBar = document.getElementById("status-bar");
    if (!statusBar) return;

    function setOnline() {
        statusBar.innerHTML = "🟢 Connected to Server";
        statusBar.style.color = "#10B981"; // Green
    }

    function setOffline() {
        statusBar.innerHTML = "🔴 Session Disconnected / Offline";
        statusBar.style.color = "#EF4444"; // Red
    }

    // 1. Check basic browser connectivity
    if (!navigator.onLine) {
        setOffline();
        return;
    }

    // 2. Actively ping the backend to confirm the specific Gradio session is alive
    fetch(window.location.href, { method: 'HEAD', cache: 'no-store' })
        .then(response => {
            if (response.ok) {
                setOnline();
            } else {
                setOffline();
            }
        })
        .catch(() => {
            setOffline();
        });
}

// Start checking every 3 seconds once the application loads
setInterval(checkConnection, 3000);

// Attach listeners to image inputs to capture source & timestamp
function initImageSourceCapture() {
    // Map through all image components by their file input order
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));

    fileInputs.forEach((fileInput, idx) => {
        // On upload via file picker
        fileInput.addEventListener('change', (ev) => {
            try {
                const f = fileInput.files && fileInput.files[0];
                if (!f) return;
                const srcEl = document.getElementById('src_' + idx);
                const tsEl = document.getElementById('ts_' + idx);
                if (srcEl) srcEl.value = 'upload';
                if (tsEl) {
                    // file.lastModified is epoch ms
                    try { tsEl.value = new Date(f.lastModified).toISOString(); } catch(e) { tsEl.value = '' }
                }
            } catch (e) {
                console.warn('image source capture (upload) failed', e);
            }
        });

        // Try to detect a camera "capture/take photo" button associated with this component
        // Buttons vary across Gradio versions and languages; we search for likely candidates nearby
        const container = fileInput.closest('.gradio-component') || fileInput.parentElement;
        if (!container) return;

        // Heuristics: find buttons in the same container that look like capture buttons
        const buttons = Array.from(container.querySelectorAll('button'));
        buttons.forEach(btn => {
            const text = (btn.innerText || '').toLowerCase();
            const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
            if (text.includes('take') || text.includes('拍') || aria.includes('capture') || aria.includes('拍')) {
                btn.addEventListener('click', () => {
                    try {
                        const srcEl = document.getElementById('src_' + idx);
                        const tsEl = document.getElementById('ts_' + idx);
                        if (srcEl) srcEl.value = 'webcam';
                        if (tsEl) tsEl.value = new Date().toISOString();
                    } catch (e) {
                        console.warn('image source capture (webcam) failed', e);
                    }
                });
            }
        });
    });
}

// Run after DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initImageSourceCapture);
} else {
  initImageSourceCapture();
}
"""

#========================================================================================================
# --- CONFIGURATION ---
# Replace these with your actual Azure App Service credentials
USERNAME = "$oil-tank-refueling"
PASSWORD = "E8F6BQT62Mt290N5fpK1sHAnQTnxPyvsD2vXAqmmClZnYkyYDQ1Du17aNNiK"
auth=HTTPBasicAuth(USERNAME, PASSWORD)
KUDU_HOST = "oil-tank-refueling-e8a5atdqg9fnh2et.scm.eastasia-01.azurewebsites.net"

ocr_model = PaddleOCR(
        lang="ch",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,   # valid flag for CPU acceleration
        )

os.environ["FLAGS_use_mkldnn"] = "0"

#Information parameters
locations = ["{請選擇}", "CFD創富", "CWD柴灣", "SHD小蠔灣", "SWD上環", "TCD東涌", "TKD將軍澳", "TMD屯門", "WCD黃竹坑", "WKD西九"]
dePot_gps = []
# (kept original depot_gps variable name for backwards compatibility)
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
        "SHD小蠔灣": ["{請選擇}", "第1缸", "第2缸"],
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
NUM_TABS = len(tab_names)

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

def http_put_status(url, data=None, timeout=HTTP_TIMEOUT, attempts=2, session=None):
    client = session or requests.Session()
    client.auth = auth
    client.headers.update({"User-Agent": "RefuelingUploader/1.0"})

    for attempt in range(attempts):
        try:
            response = client.put(url, data=data, timeout=timeout)
            status = response.status_code
            response.close()

            if status in (200, 201, 204):
                return status

            print(
                f"[http_put_status] HTTP {status} for {url}",
                file=sys.stderr,
                flush=True
            )

        except requests.exceptions.RequestException as e:
            print(
                f"[http_put_status] attempt {attempt + 1} failed: {e}",
                file=sys.stderr,
                flush=True
            )

        if attempt < attempts - 1:
            time.sleep(0.5)

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
      constraints.video.advanced = [{ zoom: 1.0 }];
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
    <script>
    // Append connection & image-source capture script
    (function(){
      const s = document.createElement('script');
      s.type = 'text/javascript';
      s.innerHTML = `"""