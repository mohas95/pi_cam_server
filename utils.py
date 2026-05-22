import os, json
import subprocess
import re
import glob

import depthai as dai
# from camera.depthai_camera import DepthAICamera
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




def list_available_devices(skip_non_device=True, active_depthai_cameras = None):
    cameras = {}
    if skip_non_device:
        skip_keywords = ["pisp", "bcm2835", "hevc", "codec"]
    else:
        skip_keywords = []

    depthai_devices = dai.Device.getAllAvailableDevices()
    if active_depthai_cameras:
        for _,active_cam in active_depthai_cameras.items():
            depthai_devices.append(active_cam["dev"].device_info)

    # print(depthai_devices)
   
    for dev_info in depthai_devices:
        cameras[dev_info.getDeviceId()] = {"device": f"DepthAICam",
                                           "pipelines": {pipeline_name: pipeline.output_streams for pipeline_name, pipeline in AVAILABLE_PIPELINES.items()},
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