import depthai as dai
import threading
import time
import cv2

from camera.pipelines.allCam import ALL_CAM_PIPELINE

class DepthAICamera:
    def __init__(self, device_id=None, pipeline_builder = ALL_CAM_PIPELINE):
        
        self.device_id = device_id
        self.device_info = None
        self.device = None
        self.pipeline_builder = None
        self.pipeline = None
        self.queues = {}
        self.latest_frames ={}
        self.latest_data = {}

        self.thread = None
        self.running = False
        self.lock = threading.Lock()

        self.configure(device_id, pipeline_builder)
        

    def get_config(self):
        with self.lock:
            # device_id = self.device.getDeviceId()
            cam_modules = self.device.getConnectedCameras()
            eepromData = self.device.readCalibration2().getEepromData()
            product_name = f"{eepromData.productName}" if eepromData.productName != "" else f"depthai_device"

            out = {"device_id":self.device_id,
                   "device":product_name,
                   "board":eepromData.boardName,
                   "num_cam_modules": len(cam_modules),
                   "cam_modules": [str(cam) for cam in cam_modules],
                   "pipeline":self.pipeline_builder.name,
                   "output_streams": self.pipeline_builder.get_output_meta(self.queues).get("img_streams",[])
                #    "output_streams":list(self.queues.keys())
                   }

            return out
        

    def configure(self,device_id=None, pipeline_builder=None):

        if self.running:
            self.stop()
        self.device_id = device_id
        self.device_info = dai.DeviceInfo(device_id) if device_id else None
        self.pipeline_builder = pipeline_builder or ALL_CAM_PIPELINE
        self.device = dai.Device(self.device_info) if self.device_info else dai.Device()
        self.pipeline = dai.Pipeline(self.device)
        self.queues = self.pipeline_builder.build(self.pipeline, self.device)

        with self.lock:
            self.latest_frames = {}
            self.latest_data = {}

        self.pipeline.start()
        self.running = True
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()

    # def _reader_loop(self):
    #     while self.running:
    #         for name, queue in self.queues.items():
    #             try:
    #                 msg = queue.tryGet()
    #                 if msg is None:
    #                     continue

    #                 # frame = msg.getCvFrame()
    #                 frame = self.pipeline_builder.transform(msg, stream_name=name)

    #                 with self.lock:
    #                     self.latest_frames[name] = frame

    #             except Exception as e:
    #                 print(f"[DepthAI] queue {name} error:",e)
    #         time.sleep(0.001)

    def _reader_loop(self):
        while self.running:

            out = self.pipeline_builder.transform(self.queues)

            if out is not None:
                with self.lock:
                    self.latest_frames.update(out.get("img_out", {}))
                    self.latest_data.update(out.get("data", {}))
            time.sleep(0.001)



    def get_jpg_frame(self, stream=None):
        with self.lock:
            if stream is None:
                frame = next(iter(self.latest_frames.values()), None)
            else:
                frame = self.latest_frames.get(stream)

            if frame is None:
                return None
            
            ok, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            return buffer.tobytes() if ok else None

    def get_raw_frame(self,stream=None):
        with self.lock:
            if stream is None:
                frame = next(iter(self.latest_frames.values()), None)
            else:
                frame = self.latest_frames.get(stream)

            return None if frame is None else frame.copy()

    def stop(self):
        self.running = False

        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None

        if self.pipeline:
            try:
                self.pipeline.stop()
            except Exception as e:
                print(e)

            self.pipeline = None

        if self.device:
            try:
                self.device.close()
            except Exception as e:
                print(e)

            self.device = None

        self.device_id = None
        self.queues = {}
        self.latest_frames = {}



if __name__ == "__main__": 
    oakd = DepthAICamera("19443010313BFB4800")

    out = oakd.get_config()

    print(out)

    # meta_out = DepthAIStream.get_device_config("19443010313BFB4800", default_rgb_pipeline)

    # print(meta_out)

    while True:

        frame = oakd.get_raw_frame("rgb")

        # print(meta_out)


        if frame is not None:
            cv2.imshow("rgb", frame)

        if cv2.waitKey(1) ==ord("q"):
            break