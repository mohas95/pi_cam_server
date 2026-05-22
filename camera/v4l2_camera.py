import cv2
import threading
import time


class V4l2Camera:
    def __init__(self, device="/dev/video0", codec = None, width= None, height = None, fps = None):
        self.thread = None
        self.cap = None
        self.frame_jpg = None
        self.frame_raw = None
        self.running = False
        self.lock = threading.Lock()
        self.configure(device, codec, width, height, fps)


    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            frame_jpg = buffer.tobytes()

            with self.lock:
                self.frame_jpg = frame_jpg
                self.frame_raw = frame
            time.sleep(0.01)


    def get_config(self):
        with self.lock:

            return {
                "device_id": self.device,
                "codec": self.codec,
                "width": self.width,
                "height": self.height,
                "fps": self.fps
            }



    def get_jpg_frame(self):
        with self.lock:
            return None if self.frame_jpg is None else self.frame_jpg

    def get_raw_frame(self):
        with self.lock:
            return None if self.frame_raw is None else self.frame_raw.copy()


    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        with self.lock:
            if self.cap:
                self.cap.release()
        
        print("Camera stopped and released")

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
        
