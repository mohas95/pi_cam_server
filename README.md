# campi server

### Author: Mohamed Debbagh (mohas95)

This project creates a simple flask + openCV server for streaming video and accessing camera frames on a rasberry pi (or linux/debian system)

Supports **live MJPEG video streaming**, **lossless PNG snapshots**, and **raw NumPy frame data** for scientific/computer-vision clients.  


---
## Features

- Stream live video feed over HTTP (`/video_feed`)  
- Get **lossless PNG-encoded snapshots** (`/lossless_frame`)  
- Get **raw NumPy frame data** (`/raw_frame`)  
- Query and change camera configuration (`/current_config`, `/configure`)  
- List available devices, codecs, resolutions, and FPS (`/devices`)  
- Graceful shutdown (releases camera device when service stops)  
- Works with **browsers**, **Python clients**, or custom UIs  

---
## Installation

### Requirements
- Python 3.9+  
- OpenCV (`cv2`)  
- NumPy  
- Flask  
- Gunicorn (for production with systemd) 

### Install dependencies
```bash
sudo apt update
sudo apt install python3-opencv python3-numpy python3-flask python3-pip python3-eventlet v4l-utils guinicorn
```
---

## Running the Server

### Development Mode (Flask backend)
```bash
git clone https://github.com/mohas95/pi_cam_server.git
cd pi_cam_server
python3 app.py
```
### Production Mode (gunicorn backend)
#### one time run (not as a service)
```bash
git clone https://github.com/mohas95/pi_cam_server.git
cd pi_cam_server
gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:5000 app:app
```
#### Systemd service Example (run on system boot)

Save as /etc/systemd/system/campi.service:

``` ini
[Unit]
Description=Campi Server using Flask and Gunicorn
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/pi_cam_server
ExecStart=/usr/bin/gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable campi.service
sudo systemctl start campi.service
```
---

## API Endpoints

### 1. Live Video Stream
```bash
GET /video_feed
```
- Returns MJPEG stream (multipart/x-mixed-replace)
- Usable directly in <img> tags or OpenCV clients

### 2. PNG Snapshot (Lossless)
```bash
GET /lossless_frame
```
- Returns a single lossless PNG-encoded frame
- Content-Type: image/png
- Good for one-off snapshots or analysis


### 3. Raw Frame (NumPy buffer)
```bash
GET /raw_frame
```
- Returns raw BGR bytes (application/octet-stream)
- Metadata in response headers:
    - X-Height → image height
    - X-Width → image width
    - X-Channels → number of channels (3 for BGR)
    - X-Dtype → NumPy dtype (e.g., uint8)

Client can reconstruct with:
``` python
frame = np.frombuffer(resp.content, dtype=np.uint8).reshape(height, width, channels)
```

### 4. Current Configuration
```bash
GET /current_config
```
- returns
```json
{
  "device": "/dev/video0",
  "codec": "MJPG",
  "width": 1280,
  "height": 720,
  "fps": 30
}
```

### 5. List Devices
```bash
GET /devices
```
- Returns all available devices, codecs, resolutions, and FPS.
- Example response:

```json
{
  "C922_Pro_Stream_Webcam": {
    "device": "/dev/video0",
    "formats": [
      {
        "codec": "MJPG",
        "desc": "Motion-JPEG",
        "resolutions": [
          {"resolution": "1920x1080", "fps": [30.0]},
          {"resolution": "1280x720", "fps": [30.0]}
        ]
      }
    ]
  }
}
```

### 6. Configure Camera
```bash
POST /configure
```
- Re-initializes the camera with new settings
- Content-Type: application/json
- example of configuration to send:
```json
{
  "device": "/dev/video0",
  "codec": "MJPG",
  "resolution": "1280x720",
  "fps": 30
}
```
- Returns { "status": "ok" } if successful

### 7. info
```bash
GET /info
```
- gets info about the current setup for meta data purposes
```json
{"codec":"YUYV","device":"/dev/video0","device_name":"C922 Pro Stream Webcam","fps":30.0,"height":480.0,"width":640.0}
```


--- 