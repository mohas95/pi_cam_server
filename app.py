import cv2
import numpy as np
import os, json, time,threading
from flask import Flask, Response, render_template,jsonify, request, flash, redirect, url_for
import eventlet
import subprocess
import depthai as dai

from utils import list_available_devices, load_config_file, save_camera_config, initialize_cameras, validate_camera_config

from camera.v4l2_camera import V4l2Camera
from camera.depthai_camera import DepthAICamera
from camera.pipelines import AVAILABLE_PIPELINES
import atexit, signal, sys

CONFIG_DIR = "config"
os.makedirs(CONFIG_DIR, exist_ok=True)
CAMERA_CONFIG_PATH = os.path.join(CONFIG_DIR, "last_camera_config.json")

app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
app.secret_key = "supersecretkey" 

camera_lock = threading.Lock()

last_camera_config = load_config_file(CAMERA_CONFIG_PATH)
available_devices = list_available_devices()

if validate_camera_config(last_camera_config,available_devices):
    selected_camera, ACTIVE_DEPTHAI_STREAMS= initialize_cameras(last_camera_config)
    print("Last configuration validated: loading camera")
else:
    ACTIVE_DEPTHAI_STREAMS = {}
    selected_camera = None
    print("Previous camera configuration not found, please select camera")


@atexit.register
def cleanup():
    with camera_lock:
        if selected_camera:
            selected_camera.stop()

def handle_sigterm(signum, frame):
    with camera_lock:
        if selected_camera:
            selected_camera.stop()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

def generate_frames(stream = None):
    try:
        while True:
            with camera_lock:
                cam = selected_camera
                active_streams = dict(ACTIVE_DEPTHAI_STREAMS)
            if cam is None:
                return
            
            current_stream = stream

            if isinstance(cam,DepthAICamera):
                if current_stream is None:
                    dev_id = cam.device_id
                    current_stream = active_streams.get(dev_id,{}).get("selected_stream")
                
                frame = cam.get_jpg_frame(stream=current_stream)
            elif isinstance(cam,V4l2Camera):
                frame = cam.get_jpg_frame()
            

            if frame is None:
                continue

            yield(b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    except GeneratorExit:
        return
    except Exception as e:
        print(e)
        return


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/video_feed')
def video_feed():

    stream = request.args.get("stream")

    with camera_lock:
        cam = selected_camera
    if cam:
        return Response(generate_frames(stream), 
                        mimetype='multipart/x-mixed-replace; boundary=frame',
                        headers={
                            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                            "Pragma": "no-cache"})
    else:
        return jsonify({"status":"No camera is initialized"})

@app.route("/lossless_frame")
def lossless_frame():

    stream = request.args.get("stream")

    with camera_lock:
        cam = selected_camera
        active_streams = dict(ACTIVE_DEPTHAI_STREAMS)

    if cam is None:
        return jsonify({"status":"No camera is initialized"})

    try:
        if isinstance(cam, DepthAICamera):
            if stream is None:
                dev_id = cam.device_id
                stream = active_streams.get(dev_id,{}).get("selected_stream")

            frame = cam.get_raw_frame(stream=stream)

        elif isinstance(cam, V4l2Camera):
            frame=cam.get_raw_frame()
        
        if frame is None:
            return jsonify({"error": "no raw frame available"}), 500
        
        ret, buf = cv2.imencode(".png", frame)

        if not ret:
            return jsonify({"error": "encoding failed"}), 500

        return Response(buf.tobytes(), mimetype="image/png")
    except Exception as e:
        print(e)
        return jsonify({"error":str(e)}), 500


@app.route("/raw_frame")
def raw_frame():
    stream = request.args.get("stream")


    with camera_lock:
        cam = selected_camera
        active_streams = dict(ACTIVE_DEPTHAI_STREAMS)

    if cam is None:
        return jsonify({"status":"No camera is initialized"})

    try:

        if isinstance(cam, DepthAICamera):
            if stream is None:
                dev_id = cam.device_id
                stream = active_streams.get(dev_id,{}).get("selected_stream")
            frame=cam.get_raw_frame(stream=stream)
        elif isinstance(cam,V4l2Camera):
            frame=cam.get_raw_frame()
        
        if frame is None:
            return jsonify({"error": "no raw frame available"}), 500

        data = frame.tobytes()
        shape = frame.shape
        dtype = str(frame.dtype)

        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Height"] = str(shape[0])
        resp.headers["X-Width"] = str(shape[1])
        resp.headers["X-Channels"] = str(shape[2])
        resp.headers["X-Dtype"] = dtype

        return resp
    except Exception as e:
        print(e)
        return jsonify({"error":str(e)}), 500


@app.route("/devices")
def devices():
    # global selected_camera, ACTIVE_DEPTHAI_STREAMS
    return jsonify(list_available_devices(active_depthai_cameras=ACTIVE_DEPTHAI_STREAMS))


@app.route("/configure", methods=["POST"])
def configure():
    global selected_camera, ACTIVE_DEPTHAI_STREAMS

    data = request.json
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

        with camera_lock:
            if selected_camera:
                selected_camera.stop()
                ACTIVE_DEPTHAI_STREAMS.clear()

            selected_camera = V4l2Camera(device= dev_id, codec = codec, width=width, height=height, fps = fps)
    
    elif camera_type == "depthai":

        pipeline_name = data.get("pipeline")
        selected_stream = data.get("output_stream")
        if pipeline_name:
            pipeline_builder = AVAILABLE_PIPELINES[pipeline_name]
        else:
            pipeline_builder=None

        with camera_lock:
            if selected_camera:
                selected_camera.stop()
                ACTIVE_DEPTHAI_STREAMS.clear()

            pipeline_info={}
            
            with dai.Device(dai.DeviceInfo(dev_id)) as temporary_device:
                temporary_pipeline = dai.Pipeline(temporary_device)


                for temp_pipeline_name, temp_pipeline_builder in AVAILABLE_PIPELINES.items():

                    output_streams = temp_pipeline_builder.build(temporary_pipeline, temporary_device)
                    pipeline_info[temp_pipeline_name] =  list(output_streams.keys())
            
            selected_camera = DepthAICamera(device_id=dev_id, pipeline_builder=pipeline_builder)
        
            ACTIVE_DEPTHAI_STREAMS[dev_id] = {"dev":selected_camera,
                                              "selected_stream": selected_stream,
                                              "pipelines":pipeline_info}

    save_camera_config(CAMERA_CONFIG_PATH,data)

    return jsonify({"status":"ok"})


@app.route("/current_config")
def info():
    with camera_lock:
        cam = selected_camera
        active_streams = dict(ACTIVE_DEPTHAI_STREAMS)
    if cam:
        config = cam.get_config()
        
        if isinstance(cam, DepthAICamera):

            dev_id = config.get("device_id")
            config["type"] = "depthai"
            config["selected_stream"] = active_streams.get(dev_id,{}).get("selected_stream")
        elif isinstance(cam, V4l2Camera):
            config["type"] = "v4l2"

        return config

    else:
        return jsonify({"status":"No camera is initialized"})



########################### wifi configuration
def get_lan_ip():
    try:
        out = subprocess.check_output(["hostname", "-I"]).decode().strip()
        if out:
            return out.split()[0]
        
    except Exception:
        return None

@app.route("/ip")
def ip_route():
    ip = get_lan_ip()

    if not ip:
        return jsonify({"error": "could not determine IP address"}), 500
    return jsonify({"ip":ip})

@app.route("/restart", methods=["POST"])
def restart_pi():
    print("🔄 Restart requested!")
    subprocess.Popen(["sudo", "reboot"])
    return "Restarting...", 200

@app.route("/configure_wifi", methods=["POST"])
def configure_wifi():
    ssid = request.form.get("ssid")
    password = request.form.get("password")

    if not ssid:
        flash("⚠️ SSID is required.", "error")
        return redirect(url_for("index"))

    try:
        # Example using nmcli (you might adapt based on your setup)
        subprocess.run(["sudo", "nmcli", "dev", "wifi", "connect", ssid, "password", password], check=True)
        flash(f"✅ Connected to {ssid}. Restarting system...", "success")
    except subprocess.CalledProcessError as e:
        flash(f"❌ Failed to connect to {ssid}: {e}", "error")
        return redirect(url_for("index"))

    # ✅ Restart the Raspberry Pi
    subprocess.Popen(["sudo", "reboot"])

    return redirect(url_for("index"))


@app.route("/scan_wifi")
def scan_wifi():
    try:
        # Force a fresh scan first
        subprocess.call(["sudo", "nmcli", "dev", "wifi", "rescan"])

        eventlet.sleep(2)  # Optional: slight delay to allow scan completion

        result = subprocess.check_output(["sudo", "nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi"]).decode()

        networks = []
        for line in result.strip().split("\n"):
            if line:
                parts = line.split(":")
                if len(parts) == 2:
                    ssid, signal = parts
                    if ssid:  # Avoid blank SSIDs
                        networks.append({"ssid": ssid, "signal": signal})
        return jsonify({"networks": networks})
    except Exception as e:
        print(f"⚠️ Wi-Fi scan failed: {e}")
        return jsonify({"networks": []})

@app.route("/current_wifi")
def current_wifi():
    try:
        result = subprocess.check_output(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"]).decode()
        for line in result.strip().split("\n"):
            active, ssid = line.split(":")
            if active == "yes":
                return jsonify({"ssid": ssid})
        return jsonify({"ssid": None})
    except Exception as e:
        print(f"⚠️ Failed to get current Wi-Fi: {e}")
        return jsonify({"ssid": None})


if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)