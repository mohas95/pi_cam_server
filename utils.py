import os, json
import subprocess
import re
import glob

import depthai as dai
from camera.depthai_camera import DepthAICamera
from camera.v4l2_camera import V4l2Camera
from camera.pipelines import AVAILABLE_PIPELINES



def load_config_file(file_path):

    if os.path.exists(file_path):
        with open(file_path,"r") as f:
            config = json.load(f)
    else:
        print(f"{file_path} does not exist")
        config = {}
    
    return config


def save_camera_config(file_path, config):

    with open(file_path,"w") as f:
        json.dump(config, f, indent=4)


def get_pipelineinfo(dev_id):
    pipeline_info={}

    with dai.Device(dai.DeviceInfo(dev_id)) as device:
        pipeline = dai.Pipeline(device)


        for pipeline_name, pipeline_builder in AVAILABLE_PIPELINES.items():

            output_queues = pipeline_builder.build(pipeline, device)
            output_img_streams= pipeline_builder.get_output_meta(output_queues).get("img_streams")
            pipeline_info[pipeline_name] =  output_img_streams

    return pipeline_info
        


def initialize_cameras(data):
    active_depthai_streams = {}
    selected_camera = None
    dev_id = data.get("device_id")
    camera_type = data.get("type")

    if camera_type =="v4l2":
        codec = data.get("codec")
        res = data.get("resolution")
        fps = data.get("fps")

        if res:
            width, height = map(int, res.split("x"))
        else:
            width, height = None, None

        if fps:
            fps = float(fps)
        else:
            fps = None

        selected_camera = V4l2Camera(device= dev_id, codec = codec, width=width, height=height, fps = fps)
    
    elif camera_type == "depthai":

        pipeline_name = data.get("pipeline")
        selected_stream = data.get("output_stream")
        if pipeline_name:
            pipeline_builder = AVAILABLE_PIPELINES[pipeline_name]
        else:
            pipeline_builder=None
        
        
        pipeline_info=get_pipelineinfo(dev_id)

        
        # with dai.Device(dai.DeviceInfo(dev_id)) as temporary_device:
        #     temporary_pipeline = dai.Pipeline(temporary_device)


        #     for temp_pipeline_name, temp_pipeline_builder in AVAILABLE_PIPELINES.items():

        #         output_queues = temp_pipeline_builder.build(temporary_pipeline, temporary_device)
        #         output_data= temp_pipeline_builder.transform(output_queues)
        #         output_streams = output_data.get("img_out")
        #         pipeline_info[temp_pipeline_name] =  list(output_streams.keys())
        
        selected_camera = DepthAICamera(device_id=dev_id, pipeline_builder=pipeline_builder)
    
        active_depthai_streams[dev_id] = {"dev":selected_camera,
                                            "selected_stream": selected_stream,
                                            "pipelines":pipeline_info}

    return selected_camera, active_depthai_streams


def validate_camera_config(config, available_devices):
    if not isinstance(config, dict):
        return False

    if "device_id" not in config or "type" not in config:
        return False

    dev_id = config["device_id"]
    camera_type = config["type"]

    dev_info = available_devices.get(dev_id)
    if not dev_info:
        return False

    if dev_info.get("type") != camera_type:
        return False

    if camera_type == "v4l2":
        codec = config.get("codec")
        resolution = config.get("resolution")
        fps = config.get("fps")

        if not codec or not resolution or fps is None:
            return False

        for fmt in dev_info.get("formats", []):
            if fmt.get("codec") != codec:
                continue

            for res_info in fmt.get("resolutions", []):
                if res_info.get("resolution") != resolution:
                    continue

                available_fps = [float(x) for x in res_info.get("fps", [])]
                return float(fps) in available_fps

        return False

    if camera_type == "depthai":
        pipeline = config.get("pipeline")
        output_stream = config.get("output_stream")

        if not pipeline or not output_stream:
            return False

        pipelines = dev_info.get("pipelines", {})

        return (
            pipeline in pipelines
            and output_stream in pipelines[pipeline]
        )

    return False




def list_available_devices(skip_non_device=True, active_depthai_cameras = None):
    cameras = {}
    if skip_non_device:
        skip_keywords = ["pisp", "bcm2835", "hevc", "codec"]
    else:
        skip_keywords = []

    depthai_devices = dai.Device.getAllAvailableDevices()
    if active_depthai_cameras:
        for dev_id,active_cam_info in active_depthai_cameras.items():

            pipeline_info = active_cam_info.get("pipelines",{})

            cameras[dev_id] = {"device": f"DepthAICam",
                                "pipelines":pipeline_info,
                                "type": "depthai"
                                }


    # print(depthai_devices)
   
    for dev_info in depthai_devices:

        dev_id = dev_info.getDeviceId()

        pipeline_info=get_pipelineinfo(dev_id)

        # with dai.Device(dev_info) as temporary_device:

        #     pipeline_info={}

        #     for pipeline_name, pipeline_builder in AVAILABLE_PIPELINES.items():
        #         temporary_pipeline = dai.Pipeline(temporary_device)


        #         output_queues = pipeline_builder.build(temporary_pipeline, temporary_device)
        #         output_data= pipeline_builder.transform(output_queues)
        #         output_streams = output_data.get("img_out")
        #         pipeline_info[pipeline_name] =  list(output_streams.keys())


        cameras[dev_id] = {"device": f"DepthAICam",
                            "pipelines":pipeline_info,
                            "type": "depthai"
                            }
        

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

            cameras[dev] = {
                "device": name,
                "formats": formats,
                "type": "v4l2"
            }

        except subprocess.CalledProcessError:
            continue
    
    # print(cameras)
    return cameras