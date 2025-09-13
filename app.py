import cv2

from flask import Flask, Response, render_template_string

app = Flask(__name__)

pipeline = (
    "v4l2src device=/dev/video0 ! "
    "image/jpeg, width=1280, height=720, framerate=30/1 ! "
    "jpegdec ! videoconvert ! appsink"
)

#camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

#camera = cv2.VideoCapture(0, cv2.CAP_V4L2)

camera = cv2.VideoCapture(0)


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Campi Server</title>
    </head>
    <body>
        <img src="{{ url_for('video_feed') }}" width ="640" height="480">
    </body>
</html>

"""



def generate_frames():
    while True:
        ret, frame = camera.read()

        if not ret:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield(b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template_string(html)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')




if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)