import cv2
import time
from flask import Flask, Response, render_template
from camera import Camera, list_available_devices




app = Flask(__name__)

cams = list_available_devices()
for name, info in cams.items():
    print(f"{name} -> {info['device']}")
    for fmt in info["formats"]:
        print(f"  Codec: {fmt['codec']} ({fmt['desc']})")
        for res in fmt["resolutions"]:
            print(f"    {res}")



camera = Camera(device =0, codec="MJPG", width=1920, height=1080, fps=30)

def generate_frames():
    while True:
        frame = camera.get_frame()

        if frame is None:
            continue
        
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        frame = buffer.tobytes()
        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')


    # return Response(generate_frames(), 
    #                 mimetype='multipart/x-mixed-replace; boundary=frame',
    #                 headers={
    #                     "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    #                     "Pragma": "no-cache"})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)