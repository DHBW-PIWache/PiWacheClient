import time
from datetime import datetime
import os
import wave
import cv2
import pyaudio
import numpy as np
import sounddevice as sd
import subprocess
from picamera2 import Picamera2
from threading import Event, Thread


# Einstellungen
DURATION = 0.5
THRESHOLD = 0.015
COOLDOWN_TIME = 5
VIDEO_PATH_RAW = "/home/berry/Videos/video.h264"
AUDIO_PATH = "/home/berry/Videos/audio.wav"
CHANNELS, RATE, CHUNK = 1, 44100, 1024
FORMAT = pyaudio.paInt16

def get_volume(indata):
    if indata.ndim > 1:
        indata = indata.flatten()
    return np.sqrt(np.mean(indata**2))

def record_audio(filename, stop_flag):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []

    while not stop_flag.is_set():
        data = stream.read(CHUNK)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def motion_loop(stop_flag):
    

    while not stop_flag.is_set():
        motion_detection(stop_flag)
    

def motion_detection(stop_flag):
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (1920, 1080)})
    picam2.configure(config)
    picam2.start()

    for _ in range(10):
        picam2.capture_array()
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
        motion_detected = any(cv2.contourArea(c) > 600 for c in contours)
        if motion_detected:
            print("Bewegung erkannt!")


        if not motion_detected:
            recording = sd.rec(int(DURATION * RATE), samplerate=RATE, channels=1, dtype='float32')
            sd.wait()
            if get_volume(recording) > THRESHOLD:
                motion_detected = True
                print("Geräusch erkannt")

        if motion_detected:
            last_motion_time = time.time()
            if not is_recording:
                print("Starte Aufnahme...")
                try: os.system('beep -f 1000 -l 100')
                except: pass

                audio_stop_flag = Event()
                audio_thread = Thread(target=record_audio, args=(AUDIO_PATH, audio_stop_flag))
                audio_thread.start()

                picam2.start_and_record_video(VIDEO_PATH_RAW)
                is_recording = True

        if is_recording and last_motion_time and (time.time() - last_motion_time > 5):
            print("Beende Aufnahme...")
            picam2.stop_recording()
            audio_stop_flag.set()
            audio_thread.join()
            is_recording = False
            break

        prev_gray = gray

    picam2.stop()
    picam2.close()
    print("Kamera gestoppt.")


    if last_motion_time:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        final_video = f"/home/berry/Videos/{timestamp}.mp4"

        subprocess.run([
            "ffmpeg", "-y",
            "-i", VIDEO_PATH_RAW,
            "-i", AUDIO_PATH,
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            final_video
        ])

        print(f"Gespeichert: {final_video}")
        os.remove(VIDEO_PATH_RAW)
        os.remove(AUDIO_PATH)

    print("Cooldown...")
    time.sleep(COOLDOWN_TIME)
