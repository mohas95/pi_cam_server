import cv2
import numpy as np
import time
from flask import Flask, Response, render_template,jsonify, request
from camera import Camera, list_available_devices
import atexit, signal, sys

app = Flask(__name__)

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





if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)