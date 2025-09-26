import cv2
import threading
import time

class Camera:
    def __init__(self, device=0, codec = None, width= None, height = None, fps = None):

        self.device = device
        # self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        # t = threading.Thread(target=self.update, daemon=True)
        # t.start()
        self.configure(codec, width, height, fps)


    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            with self.lock:
                self.frame = frame
            # time.sleep(0.01)


    def get_frame(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def configure(self, codec = None, width = None, height = None, fps = None):
        with self.lock:
            self.running = False
            self.cap.release()

            self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)

            if codec:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*codec))
                self.codec = codec
            if width:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.width = width
            if height:
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                self.height = height
            if fps:
                self.cap.set(cv2.CAP_PROP_FPS, fps)
                self.fps = fps
        
        fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join([chr((fourcc>>8*i) & 0xFF) for i in range(4)])
        print(f"Width:{self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}, Height:{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}, FPS:{self.cap.get(cv2.CAP_PROP_FPS)}, codec:{codec}")

        self.running =True
        t = threading.Thread(target=self.update, daemon=True)
        t.start()




    def change_device(self, device, width= 1280, height = 720, fps = 30):
        with self.lock:
            self.cap.release()
            self.cap = cv2.VideoCapture(device)
            self.device = device

        
