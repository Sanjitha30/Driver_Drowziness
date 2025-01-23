from flask import Flask, render_template, Response, jsonify, request
import csv
from datetime import datetime
import os
import time
import dlib
import cv2
import numpy as np
import imutils
from imutils.video import VideoStream
from imutils import face_utils
import pygame
import subprocess
import sys
from scipy.spatial import distance as dist
import pyttsx3

app = Flask(__name__)

drowsiness_alert = False
yawn_alert = False
system_enabled = True
voice_assistant_process = None

def eye_aspect_ratio(eye):
    """Calculate the eye aspect ratio to detect blink."""
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

def final_ear(shape):
    """Compute the average eye aspect ratio for both eyes."""
    (lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
    (rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
    leftEye = shape[lStart:lEnd]
    rightEye = shape[rStart:rEnd]
    leftEAR = eye_aspect_ratio(leftEye)
    rightEAR = eye_aspect_ratio(rightEye)
    ear = (leftEAR + rightEAR) / 2.0
    return (ear, leftEye, rightEye)

def lip_distance(shape):
    """Calculate the distance between the upper and lower lip to detect yawning."""
    top_lip = shape[50:53]
    top_lip = np.concatenate((top_lip, shape[61:64]))
    low_lip = shape[56:59]
    low_lip = np.concatenate((low_lip, shape[65:68]))
    top_mean = np.mean(top_lip, axis=0)
    low_mean = np.mean(low_lip, axis=0)
    distance = abs(top_mean[1] - low_mean[1])
    return distance

def play_alert_sound(file_path, message):
    """Play an alert sound and a voice message."""
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[1].id)  # Set to a more engaging voice
        engine.say(message)
        engine.runAndWait()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except pygame.error as e:
        print(f"Error playing sound: {e}")
    finally:
        pygame.mixer.quit()

def log_event(event_type, ear=None, yawn_distance=None):
    """Log events with details to a CSV file."""
    with open('event_log.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), event_type, ear, yawn_distance])

def generate_frames():
    global drowsiness_alert, yawn_alert

    vs = VideoStream(src=0).start()
    time.sleep(1.0)
    
    EYE_AR_THRESH = 0.25
    EYE_AR_CONSEC_FRAMES = 20
    YAWN_THRESH = 12
    YAWN_FRAMES_THRESH = 12
    COUNTER = 0
    yawn_counter = 0

    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
    
    while True:
        frame = vs.read()
        frame = imutils.resize(frame, width=450)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = detector(gray, 0)

        if system_enabled:
            for rect in rects:
                shape = predictor(gray, rect)
                shape = face_utils.shape_to_np(shape)
                ear, leftEye, rightEye = final_ear(shape)
                distance = lip_distance(shape)

                leftEyeHull = cv2.convexHull(leftEye)
                rightEyeHull = cv2.convexHull(rightEye)
                cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
                cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
                lip = shape[48:60]
                cv2.drawContours(frame, [lip], -1, (0, 255, 0), 1)

                if ear < EYE_AR_THRESH:
                    COUNTER += 1
                    if COUNTER >= EYE_AR_CONSEC_FRAMES:
                        cv2.putText(frame, "DROWSINESS ALERT!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        play_alert_sound("static/beep.mp3", "Attention! You seem drowsy. Please take a break and refresh yourself.")
                        log_event("Drowsiness detected", ear, distance)
                        drowsiness_alert = True
                else:
                    COUNTER = 0
                    drowsiness_alert = False

                if distance > YAWN_THRESH:
                    yawn_counter += 1
                    if yawn_counter >= YAWN_FRAMES_THRESH:
                        cv2.putText(frame, "Yawn Alert", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        play_alert_sound("static/beep.mp3", "Attention! You seem tired. Please take a break and refresh yourself.")
                        log_event("Yawn detected", ear, distance)
                        yawn_alert = True
                else:
                    yawn_counter = 0
                    yawn_alert = False

                cv2.putText(frame, "EAR: {:.2f}".format(ear), (300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, "YAWN: {:.2f}".format(distance), (300, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    vs.stop()

def start_voice_assistant():
    """Start the voice assistant."""
    global voice_assistant_process
    voice_assistant_process = subprocess.Popen([sys.executable, 'voice_assistant.py'])

def stop_voice_assistant():
    """Stop the voice assistant."""
    global voice_assistant_process
    if voice_assistant_process is not None:
        voice_assistant_process.terminate()
        voice_assistant_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/alert_status')
def alert_status():
    return jsonify(drowsiness=drowsiness_alert, yawn=yawn_alert)

@app.route('/toggle_system', methods=['POST'])
def toggle_system():
    global system_enabled
    system_enabled = request.json['enabled']
    if system_enabled:
        stop_voice_assistant()
    else:
        start_voice_assistant()
    return jsonify(success=True, system_enabled=system_enabled)

if __name__ == '__main__':
    app.run(debug=True)
