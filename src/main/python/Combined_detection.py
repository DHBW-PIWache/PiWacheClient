from datetime import datetime
import cv2
import time
import wave
import os
import pyaudio
import subprocess
from picamera2 import Picamera2
import sounddevice as sd
import numpy as np
import threading
import config_loader
from threading import Event, Thread

# --- Konfiguration ---
DURATION = float(config_loader.get("audio_detection_duration", 0.5))  # Sekunden für Geräuscherkennung
THRESHOLD = float(config_loader.get("audio_threshold", 0.015))        # Schwellwert für Geräuscherkennung
COOLDOWN_TIME = int(config_loader.get("cooldown_time", 5))            # Sekunden Cooldown nach jeder Aufnahme
MOVEMENT_THRESHOLD = int(config_loader.get("movement_threshold", 500)) # Schwellwert für Bewegungserkennung
VIDEO_RESOLUTION = eval(config_loader.get("video_resolution", "(1920,1080)")) # tuple
TIME_TO_STOP = int(config_loader.get("time_to_stop", 15))              # Sekunden bis Aufnahmeende

VIDEO_PATH_RAW = "/home/berry/Videos/video.h264"
AUDIO_PATH = "/home/berry/Videos/audio.wav"

CHANNELS = 1
RATE = 44100
CHUNK = 1024
FORMAT = pyaudio.paInt16

def get_volume(indata):
    """
    Berechnet die Lautstärke (RMS) eines Audiosignals.
    """
    if indata.ndim > 1:
        indata = indata.flatten()
    rms = np.sqrt(np.mean(indata**2))
    return rms

def record_audio(filename, stop_event):
    """
    Nimmt Audio auf, bis stop_event.is_set() True zurückgibt.
    Speichert die Aufnahme als WAV-Datei.
    """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK)
    frames = []
    print("Audioaufnahme gestartet...")

    while not stop_event.is_set():
        data = stream.read(CHUNK)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Audioaufnahme beendet.")

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def motion_detection(stop_flag):
    """
    Erkennt Bewegung und/oder Geräusche und startet bei Erkennung die Aufnahme.
    Kombiniert Audio- und Videoaufnahme und speichert das Ergebnis.
    """
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": VIDEO_RESOLUTION}) # Auflösung aus Config verwenden
    picam2.configure(config)
    picam2.start()
    # Kamera aufwärmen
    for _ in range(10):
        frame = picam2.capture_array()
        time.sleep(0.05)

    prev_gray = cv2.cvtColor(picam2.capture_array(), cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

    is_recording = False
    last_motion_time = None

    while not stop_flag.is_set():
        gray = cv2.cvtColor(picam2.capture_array(), cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        delta = cv2.absdiff(prev_gray, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_detected = any(cv2.contourArea(c) > MOVEMENT_THRESHOLD for c in contours)
        if motion_detected:
            print("Bewegung erkannt!")

        # Geräuscherkennung
        recording = sd.rec(int(DURATION * RATE), samplerate=RATE, channels=1, dtype='float32')
        sd.wait()
        volume = get_volume(recording)
        if volume > THRESHOLD:
            motion_detected = True
            print(f"Geräusch erkannt: {volume:.4f}")

        if motion_detected:
            last_motion_time = time.time()
            if not is_recording:
                print("Starte Video- und Audioaufnahme...")

                # Audioaufnahme vorbereiten
                stop_event = threading.Event()

                # Audioaufnahme im Thread starten
                audio_thread = threading.Thread(target=record_audio, args=(AUDIO_PATH, stop_event))
                audio_thread.start()

                # Videoaufnahme starten
                picam2.start_and_record_video(VIDEO_PATH_RAW)
                is_recording = True

        # Aufnahme beenden, wenn keine Bewegung/Geräusch mehr erkannt wird
        if is_recording and last_motion_time and (time.time() - last_motion_time > TIME_TO_STOP):
            print("Beende Aufnahme.")
            is_recording = False
            picam2.stop_recording()
            stop_event.set()
            audio_thread.join()
            break

        prev_gray = gray

    picam2.stop()
    picam2.close()
    print("Kamera gestoppt.")

    # Video und Audio zusammenführen
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    VIDEO_PATH_FINAL = f"/home/berry/Videos/{timestamp}.mp4"

    print("Füge Video und Audio zusammen...")

    result = subprocess.run([
        "ffmpeg",
        "-y",
        "-i", VIDEO_PATH_RAW,
        "-i", AUDIO_PATH,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-strict", "experimental",
        VIDEO_PATH_FINAL
    ], capture_output=True)
    if result.returncode != 0:
        print("Fehler beim Zusammenführen von Video und Audio:", result.stderr.decode())
    else:
        print(f"Fertig! Datei gespeichert unter: {VIDEO_PATH_FINAL}")

    # Temporäre Dateien löschen
    os.remove(VIDEO_PATH_RAW)
    os.remove(AUDIO_PATH)
    print("Temporäre Dateien gelöscht.")

    print(f"Cooldown läuft ({COOLDOWN_TIME} Sekunden)...")
    time.sleep(COOLDOWN_TIME)

def motion_loop(stop_flag):
    
    """
    Startet die Bewegungserkennung in einer Endlosschleife.
    """
    while not stop_flag.is_set():
        motion_detection(stop_flag)
        print("Bereit für neue Bewegung...")