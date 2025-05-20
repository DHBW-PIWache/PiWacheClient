from datetime import datetime
import cv2
import time
import threading
import wave
import os
import pyaudio
import subprocess
from picamera2 import Picamera2

# Pfade der temporären output-Dateien
VIDEO_PATH_RAW = "/home/berry/Videos/video.h264"
AUDIO_PATH = "/home/berry/Videos/audio.wav"
# Pfad der finalen output-Datei wird unten dynamisch erzeugt 

# Audio-Parameter
CHANNELS = 1 # Anzahl Audiokanäle
RATE = 44100 # Abtastrate in Hz   
CHUNK = 1024 # Größe der Audio-Frames
FORMAT = pyaudio.paInt16 # Audioformat
DURATION_LIMIT = 60  # Sicherheitslimit für Audioaufnahme

# Funktion zur Audioaufnahme in eigenem Thread
def record_audio(filename, stop_flag):
    # PyAudio-Instanz erstellen
    p = pyaudio.PyAudio()

    # Audio-Stream öffnen
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK)
    frames = []  # Liste zur Speicherung der Audio-Frames
    start_time = time.time() 
    print("Audioaufnahme gestartet...")

    # Audioaufnahme-Schleife
    while not stop_flag.is_set() and (time.time() - start_time < DURATION_LIMIT):
        # Audio-Daten lesen und speichern
        data = stream.read(CHUNK)
        frames.append(data)

    # Audio-Stream stoppen und schließen
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Audioaufnahme beendet.")

    # Audio-Frames in eine WAV-Datei schreiben
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)  
        wf.setsampwidth(p.get_sample_size(FORMAT)) 
        wf.setframerate(RATE)  
        wf.writeframes(b''.join(frames))  # Audio-Daten schreiben

# Funktion zur Bewegungserkennung und Videoaufnahme
def motion_detection(picam2):
    # Kamera vorbereiten
    picam2.start()

    # 1. Referenzbild aufnehmen
    prev_frame = picam2.capture_array() 
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) # Aufnahme in Graustufenbild umwandeln, um Datenmenge zu minimieren
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0) # Bildrauschen reduzieren + Bild glätten

    # Aufnahme-Status
    recording = False
    last_motion_time = None
    audio_stop_flag = threading.Event()
    audio_thread = None

    while True:
        # Vergleichsbild aufnehmen
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Differenzbild erstellen
        delta = cv2.absdiff(prev_gray, gray) # Erstellen eines Differenzbildes
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1] # Umwandeln des Differenzbildes in ein Binärbild
        thresh = cv2.dilate(thresh, None, iterations=2) # Vergrößerung der weißen Bereiche im Binärbild

        # Differenzbild analysieren
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) # Erkennen der Umrisse der weißen Bereiche
        motion_detected = any(cv2.contourArea(c) > 400 for c in contours) # Überprüfen, ob ein Umriss den Schwellwert überschreitet

        if motion_detected:
            last_motion_time = time.time()
            if not recording:
                print("Starte Videoaufnahme...")
                picam2.start_and_record_video(VIDEO_PATH_RAW) # Videoaufnahme starten
                audio_stop_flag.clear() # Audio-Stop-Flag zurücksetzen
                audio_thread = threading.Thread(target=record_audio, args=(AUDIO_PATH, audio_stop_flag)) # Audioaufnahme in neuem Thread starten
                audio_thread.start()
                recording = True

        # Wenn Bewegung >5 Sekunden nicht mehr erkannt wird: Aufnahme beenden
        if recording and last_motion_time and (time.time() - last_motion_time > 5):
            print("Beende Aufnahme.")
            recording = False
            picam2.stop_recording() # Videoaufnahme stoppen
            audio_stop_flag.set() # Audioaufnahme beenden
            audio_thread.join() # Auf Audio-Thread warten
            break
        
        prev_gray = gray

    picam2.stop() # Kamera stoppen

    # Finalen Dateinamen erzeugen
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    VIDEO_PATH_FINAL = f"/home/berry/Videos/{timestamp}.mp4"

    # Nachbearbeitung: Video + Audio zusammenführen
    print("Füge Video und Audio zusammen...")

    # ffmpeg-Kommando
    subprocess.run([
        "ffmpeg",
        "-y",  # Überschreiben, falls Datei schon existiert
        "-i", VIDEO_PATH_RAW,
        "-i", AUDIO_PATH,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        VIDEO_PATH_FINAL
    ])

    print(f"Fertig! Datei gespeichert unter: {VIDEO_PATH_FINAL}")

    # Temporäre Dateien löschen 
    os.remove(VIDEO_PATH_RAW)
    os.remove(AUDIO_PATH)
    print("Temporäre Dateien gelöscht.")

# Hauptfunktion
def main():
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (1920, 1080) # Festlegung der Auflösung

    while True:
        motion_detection(picam2)
        print("Bereit für neue Bewegung...")
        time.sleep(2)  # Kurze Pause, damit Kamera sich zurücksetzen kann

# Starte das Programm
if __name__ == "__main__":
    main()