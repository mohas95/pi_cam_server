import cv2
import numpy as np
import time
from flask import Flask, Response, render_template,jsonify, request, flash, redirect, url_for
import eventlet
import subprocess

from camera import Camera, list_available_devices
import atexit, signal, sys

app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
app.secret_key = "supersecretkey" 


camera = Camera()

@atexit.register
def cleanup():
    camera.stop()

def handle_sigterm(signum, frame):
    camera.stop()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

def generate_frames():
    while True:
        frame = camera.get_jpg_frame()

        if frame is None:
            continue

        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/current_config")
def current_config():
    return jsonify(camera.get_config())

@app.route('/video_feed')
def video_feed():
    # return Response(generate_frames(), 
    #                 mimetype='multipart/x-mixed-replace; boundary=frame')
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                        "Pragma": "no-cache"})

@app.route("/lossless_frame")
def lossless_frame():
    frame=camera.get_raw_frame()
    if frame is None:
        return jsonify({"error": "no raw frame available"}), 500
    
    ret, buf = cv2.imencode(".png", frame)

    if not ret:
        return jsonify({"error": "encoding failed"}), 500

    return Response(buf.tobytes(), mimetype="image/png")


@app.route("/raw_frame")
def raw_frame():
    frame=camera.get_raw_frame()
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

@app.route("/devices")
def devices():
    return jsonify(list_available_devices())


@app.route("/configure", methods=["POST"])
def configure():
    data = request.json
    dev = data.get("device")
    codec = data.get("codec")
    res = data.get("resolution")
    fps = data.get("fps")

    if res:
        width, height = map(int, res.split("x"))
    else:
        width, height = None, None

    if fps:
        fps = int(fps)
    else:
        fps = None

    camera.configure(device= dev, codec = codec, width=width, height=height, fps = fps)
    
    return jsonify({"status":"ok"})


@app.route("/info")
def info():
    config = camera.get_config()

    devices = list_available_devices()
    device_name = None
    for name, info in devices.items():
        if info["device"] == config.get("device"):
            device_name = name
            break

    return jsonify({
        "device_name": device_name or "unknown",
        "device": config.get("device"),
        "codec": config.get("codec"),
        "width": config.get("width"),
        "height": config.get("height"),
        "fps": config.get("fps")
    })


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