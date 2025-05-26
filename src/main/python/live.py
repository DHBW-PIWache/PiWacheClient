from flask import Flask, Response
from picamera2 import Picamera2
import time

app = Flask(__name__)
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()
time.sleep(2)  # Kamera starten lassen

def generate_frames():
    while True:
        frame = picam2.capture_array()
        from PIL import Image
        import io
        img = Image.fromarray(frame)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.getvalue() + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 MJPEG-Stream läuft auf http://0.0.0.0:5001/video")
    app.run(host='0.0.0.0', port=5001)
