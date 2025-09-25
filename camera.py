import cv2
import threading

class Camera:
    def __init__(self, device=0, width= 1280, height = 720, fps = 30):

        self.device = device
        self.cap = cv2.VideoCapture(self.device)
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        t = threading.Thread(target=self.update, daemon=True)
        t.start()
        # self.configure(width, height, fps)


    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            with self.lock:
                self.frame = frame


    def get_frame(self):
        with self.lock:
            return self.frame

    def configure(self, width= None, height = None, fps = None):

        with self.lock:
            if width:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.width = width
            if height:
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                self.height = height
            if fps:
                self.cap.set(cv2.CAP_PROP_FPS, fps)
                self.fps = fps

    def change_device(self, device, width= 1280, height = 720, fps = 30):
        with self.lock:
            self.cap.release()
            self.cap = cv2.VideoCapture(device)
            self.device = device

        
