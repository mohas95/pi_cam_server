import cv2
import threading
import time

import subprocess
import re
import glob

def list_available_devices(skip_non_device=True):
    cameras = {}
    if skip_non_device:
        skip_keywords = ["pisp", "bcm2835", "hevc", "codec"]
    else:
        skip_keywords = []

    for dev in glob.glob("/dev/video*"):
        try:
            # udevadm info
            result = subprocess.run(
                ["udevadm", "info", "--query=all", "--name", dev],
                capture_output=True, text=True, check=True
            )
            info = result.stdout.lower()

            # must be capture capable
            if "id_v4l_capabilities=:capture:" not in info:
                continue

            # skip known ISP/decoder/encoder nodes
            if any(skip in info for skip in skip_keywords):
                continue

            # find device model name
            model = None
            for line in result.stdout.splitlines():
                if line.strip().startswith("E: ID_MODEL="):
                    model = line.split("=", 1)[1]
                    break
                if line.strip().startswith("E: ID_V4L_PRODUCT="):
                    model = line.split("=", 1)[1]
                    break

            name = model or dev

            # query supported formats & resolutions
            fmt_result = subprocess.run(
                ["v4l2-ctl", "--device", dev, "--list-formats-ext"],
                capture_output=True, text=True
            )

            formats = []
            current_fmt = None
            current_res = None
            for line in fmt_result.stdout.splitlines():
                line = line.strip()
                # codec line
                m = re.match(r"\[\d+\]: '(\w+)' \((.*)\)", line)
                if m:
                    fourcc, desc = m.groups()
                    current_fmt = {"codec": fourcc, "desc": desc, "resolutions": []}
                    formats.append(current_fmt)
                    continue
                
                # resolution line
                if line.startswith("Size: Discrete"):
                    parts = line.split()
                    res = parts[2]  # e.g. "1920x1080"
                    current_res = {"resolution":res, "fps": []}
                    if current_fmt is not None:
                        current_fmt["resolutions"].append(current_res)
                    continue

                # fps line
                if line.startswith("Interval: Discrete") and current_res is not None:
                    fps_match = re.search(r"\(([\d\.]+)\s*fps\)", line)
                    if fps_match:
                        fps_val= float(fps_match.group(1))
                        current_res["fps"].append(fps_val)

            cameras[name] = {
                "device": dev,
                "formats": formats
            }

        except subprocess.CalledProcessError:
            continue

    return cameras



class Camera:
    def __init__(self, device=0, codec = None, width= None, height = None, fps = None):
        self.thread = None
        self.cap = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self.configure(device, codec, width, height, fps)

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            with self.lock:
                self.frame = frame

    def get_frame(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def configure(self, device=None, codec = None, width = None, height = None, fps = None):

        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
        with self.lock:
            if self.cap:
                self.cap.release()
            
            if device is not None:
                self.device = device
            
            self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)

            if codec:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*codec))
            if width:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            if height:
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            if fps:
                self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        if fourcc:
            self.codec = "".join([chr((fourcc>>8*i) & 0xFF) for i in range(4)])
        else:
            self.codec = "unknown"
        self.width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)


        print(f"Camera Device:{self.device} Active -> codec:{self.codec}, {self.width}x{self.height} @ {self.fps:.1f} fps")
        
        self.running =True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        
