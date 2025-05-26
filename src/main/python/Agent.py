from flask import Flask, request, jsonify, Response
from threading import Thread, Event
from Combined_detection import motion_loop
import time
from picamera2 import Picamera2
from PIL import Image
import io

app = Flask(__name__)

# Status und Threads
motion_thread = None
stream_thread = None
stop_event = Event()
detection_active = False
streaming_active = False

@app.route('/start', methods=['POST'])
def start_motion():
    global motion_thread, stop_event, detection_active

    if streaming_active:
        return jsonify({"status": "streaming active – cannot start detection"}), 409

    if motion_thread is None or not motion_thread.is_alive():
        stop_event.clear()
        detection_active = True
        motion_thread = Thread(target=motion_loop_wrapper)
        motion_thread.start()
        return jsonify({"status": "detection started"}), 200

    return jsonify({"status": "detection already running"}), 200

def motion_loop_wrapper():
    global detection_active
    try:
        motion_loop(stop_event)
    finally:
        detection_active = False  # Rücksetzen wenn Thread fertig

@app.route('/stop', methods=['POST'])
def stop_motion():
    global stop_event, motion_thread, detection_active

    if motion_thread and motion_thread.is_alive():
        stop_event.set()
        motion_thread.join()
        detection_active = False
        time.sleep(1)  
        return jsonify({"status": "detection stopped"}), 200

    return jsonify({"status": "detection not running"}), 200

@app.route('/status', methods=['GET'])
def check_status():
    return jsonify({
        "detection": "running" if detection_active else "stopped",
        "streaming": "running" if streaming_active else "stopped"
    }), 200

@app.route('/video')
def video_feed():
    global detection_active, streaming_active

    if detection_active:
        return "Detection läuft – Stream nicht möglich", 409

    def generate_frames():
        global streaming_active
        streaming_active = True
        picam2 = Picamera2()
        picam2.configure(picam2.create_video_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        ))
        picam2.start()
        time.sleep(1)

        try:
            while True:
                frame = picam2.capture_array()
                img = Image.fromarray(frame)
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG')
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.getvalue() + b'\r\n')
        except GeneratorExit:
            pass
        finally:
            picam2.stop()
            picam2.close()
            streaming_active = False

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
