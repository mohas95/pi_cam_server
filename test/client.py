import requests, cv2, numpy as np

SERVER_URL = "http://campi.local:5000"


lossless_url = "lossless_frame"
raw_url = "raw_frame"
video_url = "video_feed"


def get_lossless_frame():
    url =f"{SERVER_URL}/{lossless_url}"

    resp = requests.get(url)

    if resp.status_code != 200:
        print("ERROR:", resp.json())
        return None
    
    arr = np.frombuffer(resp.content, dtype=np.uint8)

    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    
    return frame


def get_raw_frame():
    url =f"{SERVER_URL}/{raw_url}"

    resp = requests.get(url)

    if resp.status_code != 200:
        print("ERROR:", resp.json())
        return None
    
    height = int(resp.headers["X-Height"])
    width = int(resp.headers["X-Width"])
    channels = int(resp.headers["X-Channels"])
    dtype = np.dtype(resp.headers["X-Dtype"])


    frame = np.frombuffer(resp.content, dtype=dtype).reshape((height, width, channels))
    
    return frame


def stream_video():

    url =f"{SERVER_URL}/{video_url}"
    stream = requests.get(url, stream=True)

    bytes_buf = b""

    for chunk in stream.iter_content(chunk_size=1024):
        bytes_buf +=chunk
        a=bytes_buf.find(b'\xff\xd8')
        b=bytes_buf.find(b'\xff\xd9')
        if a!=-1 and b!= -1:
            jpg = bytes_buf[a:b+2:]
            bytes_buf=bytes_buf[b+2:]
            img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

            cv2.imshow("video feed", img)
            if cv2.waitKey(1) & 0xFF in [27, ord("q")]:  # ESC or q
                break
            
    cv2.destroyAllWindows("video feed")

if __name__ == "__main__":
    
    lossless_frame = get_lossless_frame()
    raw_frame = get_raw_frame()

    if lossless_frame is not None:
        cv2.imshow("Lossless Frame", lossless_frame)
    else:
        print("failed to show lossless frame")

    
    if raw_frame is not None:
        cv2.imshow("raw Frame", raw_frame)
    else:
        print("failed to show lossless frame")

    # while True:
    #     key = cv2.waitKey(1) & 0xFF
    #     if key == 27:  # ESC
    #         break
    #     if key == ord('q'):  # letter q
    #         break

    stream_video()

    cv2.destroyAllWindows()