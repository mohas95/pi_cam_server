import cv2
import numpy as np
import requests

URL = "http://campi.local:5000/video_feed"  # or http://<host>:5000/video_feed

def stream_mjpeg(url):
    # Open a streaming HTTP connection
    with requests.get(url, stream=True) as r:
        if r.status_code != 200:
            raise RuntimeError(f"Bad status code: {r.status_code}")

        bytes_buf = b""

        for chunk in r.iter_content(chunk_size=1024):
            if not chunk:
                continue

            bytes_buf += chunk

            # Look for JPEG start and end markers
            start = bytes_buf.find(b"\xff\xd8")  # SOI
            end   = bytes_buf.find(b"\xff\xd9")  # EOI

            if start != -1 and end != -1 and end > start:
                jpg = bytes_buf[start:end+2]
                bytes_buf = bytes_buf[end+2:]

                # Decode JPEG to an image
                img_array = np.frombuffer(jpg, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                if frame is None:
                    continue

                yield frame

if __name__ == "__main__":
    try:
        for frame in stream_mjpeg(URL):
            cv2.imshow("Flask Video Feed", frame)

            # Press q to quit
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()
