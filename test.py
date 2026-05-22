from camera.depthai_camera import DepthAICamera
import cv2



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