import depthai as dai
import threading
import time
import cv2


#TODO: Depthai pipeline integration: Camera and pipeline loading class

def default_rgb_pipeline(pipeline, size=(1280,80), fps=20):
    cam = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.Cam_A)
    output = cam.requestOuput(size, type=dai.ImgFrame.Type.NV12, 
                              resize_mode=dai.IMGResizeMode.CROP, 
                              enableUndistortion=True,
                              fps=fps).createOutputQueue()
    
    return {"rgb":output}


class DepthAIStream:
    def __init__(self, device_id=None, pipeline_builder = None):
        
        self.device_info = dai.DeviceInfo(device_id)
        self.pipeline_builder = pipeline_builder
        self.pipeline = None
        self.queues = {}
        self.latest_frames ={}

        self.thread = None
        self.running = False
        self.lock = threading.Lock()
        
    ##TODO: Change to configure for better api calls
    def start(self):

        with dai.Device(self.device_info) as device:
            self.pipeline = dai.Pipeline(device)
            self.queues = self.pipeline_builder(self.pipeline)

            self.pipeline.start()
            self.running = True
            self.thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.thread.start()

    ##TODO: Test this code and check structure with depthai api
    def _reader_loop(self):
        while self.running:
            for name, queue in self.queues.items():
                try:
                    msg = queue.tryGet()
                    if msg is None:
                        continue

                    frame = msg.getCVFrame()
                    with self.lock:
                        self.latest_frames[name] = frame

                except Exception as e:
                    print(f"[DepthAI] queue {name} error:",e)
            time.sleep(0.001)


    def get_frame(self):
        pass

    def get_raw_frame(self):
        pass
    def stop(self):
        self.running = False

        if self.thread:
            self.thread.join(timeout=2)
        if self.pipeline:
            self.pipeline.stop()

    def get_config(self):
        pass

