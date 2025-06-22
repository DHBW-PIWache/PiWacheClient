from flask import Flask, request, jsonify, Response  # Flask-Framework und Hilfsfunktionen importieren
from threading import Thread, Event                 # Für parallele Ausführung und Steuerung
from Combined_detection import motion_loop           # Importiere die Bewegungserkennungsschleife
import time                                         # Für Zeitfunktionen
from picamera2 import Picamera2                     # Kamera-Modul für Raspberry Pi
from PIL import Image                               # Bildverarbeitung
import io                                           # Für Byte-Streams
import subprocess                                   # Für Systembefehle

app = Flask(__name__)                               # Flask-App initialisieren

# Statusvariablen und Thread-Objekte
motion_thread = None        # Thread für Bewegungserkennung
stream_thread = None        # (Nicht genutzt, aber vorbereitet)
stop_event = Event()        # Event zum Stoppen der Threads
detection_active = False    # Status der Bewegungserkennung
streaming_active = False    # Status des Videostreams

@app.route('/start', methods=['POST'])
def start_motion():
    """
    Startet die Bewegungserkennung, falls kein Stream läuft und sie noch nicht aktiv ist.
    """
    global motion_thread, stop_event, detection_active

    if streaming_active:
        # Wenn Streaming läuft, kann die Erkennung nicht gestartet werden
        return jsonify({"status": "streaming active – cannot start detection"}), 409

    if motion_thread is None or not motion_thread.is_alive():
        # Starte neuen Thread für Bewegungserkennung
        stop_event.clear()
        detection_active = True
        motion_thread = Thread(target=motion_loop_wrapper)
        motion_thread.start()
        return jsonify({"status": "detection started"}), 200

    # Erkennung läuft bereits
    return jsonify({"status": "detection already running"}), 200

def motion_loop_wrapper():
    """
    Wrapper für die Bewegungserkennung, setzt Status zurück wenn Thread endet.
    """
    global detection_active
    try:
        motion_loop(stop_event)  # Starte die eigentliche Bewegungserkennung
    finally:
        detection_active = False  # Status zurücksetzen, wenn Thread fertig

@app.route('/stop', methods=['POST'])
def stop_motion():
    """
    Stoppt die Bewegungserkennung, falls sie läuft.
    """
    global stop_event, motion_thread, detection_active

    if motion_thread and motion_thread.is_alive():
        stop_event.set()         # Signal zum Stoppen senden
        motion_thread.join()     # Auf Thread-Ende warten
        detection_active = False
        time.sleep(1)            # Kurze Pause
        return jsonify({"status": "detection stopped"}), 200

    # Erkennung läuft nicht
    return jsonify({"status": "detection not running"}), 200

@app.route('/status', methods=['GET'])
def check_status():
    """
    Gibt den aktuellen Status von Bewegungserkennung und Streaming zurück.
    """
    return jsonify({
        "detection": "running" if detection_active else "stopped",
        "streaming": "running" if streaming_active else "stopped"
    }), 200

@app.route('/video')
def video_feed():
    """
    Startet einen MJPEG-Stream von der Kamera.
    Stoppt ggf. vorher die Bewegungserkennung.
    """
    global detection_active, streaming_active

    if detection_active:
        stop_motion()    # Stoppe Erkennung, falls aktiv
        time.sleep(1)    # Kurze Pause

    def generate_frames():
        """
        Generatorfunktion für MJPEG-Frames.
        """
        global streaming_active
        streaming_active = True
        picam2 = Picamera2()
        picam2.configure(picam2.create_video_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        ))
        picam2.start()
        time.sleep(1)  # Kamera initialisieren

        try:
            while True:
                frame = picam2.capture_array()      # Bild aufnehmen
                img = Image.fromarray(frame)        # In PIL-Image umwandeln
                buffer = io.BytesIO()               # BytesIO-Buffer für JPEG
                img.save(buffer, format='JPEG')     # Bild als JPEG speichern
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.getvalue() + b'\r\n')
        except GeneratorExit:
            pass
        finally:
            picam2.stop()      # Kamera stoppen
            picam2.close()     # Kamera freigeben
            streaming_active = False

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/restart', methods=['POST'])
def restart_agent():
    """
    Startet den Agenten-Dienst auf Systemebene neu.
    """
    subprocess.Popen(["sudo","systemctl", "restart", "agent.service"])
    return {"status": "restarting"}, 200

if __name__ == '__main__':
    # Starte Flask-App auf allen Interfaces, Port 5000, mit Threading
    app.run(host='0.0.0.0', port=5000, threaded=True)