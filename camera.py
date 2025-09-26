import cv2
import threading
import time

import subprocess
import re
import glob

def list_available_devices():
    cameras = {}

    # find all /dev/video* nodes
    for dev in glob.glob("/dev/video*"):
        try:
            # query udevadm for device info
            result = subprocess.run(
                ["udevadm", "info", "--query=all", "--name", dev],
                capture_output=True, text=True, check=True
            )
            info = result.stdout

            # filter: must have capture capability
            if "ID_V4L_CAPABILITIES=:capture:" not in info:
                continue

            # get model name if available
            model = None
            for line in info.splitlines():
                if line.strip().startswith("E: ID_MODEL="):
                    model = line.split("=", 1)[1]
                    break

            # fallback if no model found
            if not model:
                model = dev

            cameras[model] = dev

        except subprocess.CalledProcessError:
            continue

    return cameras






# def list_available_devices(skip_non_device = True):
#     results = subprocess.run(
#         ["v4l2-ctl", "--list-devices"],
#         capture_output=True, text=True
#     )

#     lines = results.stdout.strip().splitlines()

#     cameras = {}
#     device_name = None

#     if skip_non_device:
#         skip_keywords = ["pisp","rpi-hevc", "platform"]
#     else:
#         skip_keywords=[]

#     for line in lines:
#         if not line.startswith("\t") and line.strip():
#             device_name = line.strip().strip(":")
#             if any(key in device_name.lower() for key in skip_keywords):
#                 device_name=None
#             else:
#                 cameras[device_name] = []
#         elif device_name and line.startswith("\t"):
#             dev_path = line.strip()
#             if device_name:
#                 cameras[device_name].append(dev_path)
#     return cameras



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
        
