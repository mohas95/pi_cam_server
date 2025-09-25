import cv2
from flask import Flask, Response, render_template
from camera import Camera

app = Flask(__name__)
camera = Camera()


def generate_frames():
    while True:
        frame = camera.get_frame()

        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
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




if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)