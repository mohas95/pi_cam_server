import cv2

from flask import Flask, Response, render_template_string

app = Flask(__name__)

camera = cv2.VideoCapture(2)


html = """"
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

            yield(b'--frame/r/n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template_string(html)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')




if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)