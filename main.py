import os
import logging
import warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore')
logging.getLogger('tensorflow').setLevel(logging.ERROR)

import cv2
import numpy as np
from detector import ObjectDetector
from behavior import BehaviorAnalyzer
from alert import AlertSystem
from theft_model import TheftModelAnalyzer
import tkinter as tk
from tkinter import filedialog
import time

detector = ObjectDetector()
behavior = BehaviorAnalyzer()
alert = AlertSystem()
theft_analyzer = TheftModelAnalyzer()

# Target FPS for video playback (change this value to adjust framerate)
TARGET_FPS = 30
frame_time = 1.0 / TARGET_FPS

# Processing resolution (change these values to adjust resolution for faster/slower processing)
PROCESS_WIDTH = 1280  # 720p width
PROCESS_HEIGHT = 720  # 720p height

# Ask user for input source
root = tk.Tk()
root.withdraw()  # Hide the main window

choice = input("Enter 'w' for webcam or 'v' for video file: ").strip().lower()

if choice == 'v':
    file_path = filedialog.askopenfilename(title="Select video file", filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
    if file_path:
        cap = cv2.VideoCapture(file_path)
        is_video_file = True
    else:
        print("No file selected, using webcam")
        cap = cv2.VideoCapture(0)
        is_video_file = False
else:
    cap = cv2.VideoCapture(0)
    is_video_file = False

frame_buffer = []
last_theft_msg = ""

while True:
    start_time = time.time()

    ret, frame = cap.read()

    if not ret:
        if is_video_file:
            # Video ended, loop back to start
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        else:
            print("Failed to grab frame from webcam")
            continue

    # Resize for faster processing
    original_h, original_w = frame.shape[:2]
    scale_w = original_w / PROCESS_WIDTH
    scale_h = original_h / PROCESS_HEIGHT
    frame_small = cv2.resize(frame, (PROCESS_WIDTH, PROCESS_HEIGHT))

    # Buffer last 30 frames (about 1 second at 30fps)
    frame_buffer.append(frame.copy())
    if len(frame_buffer) > 30:
        frame_buffer.pop(0)

    persons, items, carts = detector.detect(frame_small)

    # Scale boxes back to original size
    persons = [{'bbox': [p['bbox'][0] * scale_w, p['bbox'][1] * scale_h, p['bbox'][2] * scale_w, p['bbox'][3] * scale_h], 'id': p['id']} for p in persons]
    items = [[x * scale_w, y * scale_h, x2 * scale_w, y2 * scale_h] for x, y, x2, y2 in items]
    carts = [[x * scale_w, y * scale_h, x2 * scale_w, y2 * scale_h] for x, y, x2, y2 in carts]

    tracked_people = {p['id']: {'bbox': p['bbox'], 'center': [(p['bbox'][0]+p['bbox'][2])/2, (p['bbox'][1]+p['bbox'][3])/2], 'score': behavior.person_scores.get(p['id'], 0)} for p in persons if p['id'] is not None}

    events = behavior.analyze(tracked_people, items, carts)

    for event in events:
        alert.trigger(event, frame_buffer)

    msg, is_theft, prob = theft_analyzer.predict_frame(frame_small)

    if msg == "Very high probability of theft" and msg != last_theft_msg:
        alert.trigger({
            "person": "Global_Model",
            "score": prob,
            "type": "stealing"
        }, frame_buffer)
    last_theft_msg = msg

    # Draw visualizations
    # Draw persons with IDs
    for p in persons:
        if p['id'] is not None:
            pid = p['id']
            score = behavior.person_scores.get(pid, 0)
            color = (0, 0, 255) if score > 50 else (0, 255, 0)  # Red if suspicious
            box = p['bbox']
            cv2.rectangle(frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color, 2)
            cv2.putText(frame, f"ID:{pid} Score:{score}", (int(box[0]), int(box[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Draw items in green
    for item in items:
        cv2.rectangle(frame, (int(item[0]), int(item[1])), (int(item[2]), int(item[3])), (0, 255, 0), 2)
        cv2.putText(frame, "Item", (int(item[0]), int(item[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Draw carts in blue
    for cart in carts:
        cv2.rectangle(frame, (int(cart[0]), int(cart[1])), (int(cart[2]), int(cart[3])), (255, 0, 0), 2)
        cv2.putText(frame, "Cart", (int(cart[0]), int(cart[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    kaggle_color = (0, 0, 255) if is_theft and msg != "Analyzing video..." else (0, 255, 0)
    display_msg = f"Model: {msg} ({prob}%)" if msg != "Analyzing video..." else "Model: Analyzing video..."
    cv2.rectangle(frame, (0, 0), (800, 40), (255, 255, 255), -1)
    cv2.putText(frame, display_msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, kaggle_color, 2)

    cv2.imshow("AI Theft Detection", frame)

    # Removed framerate control for maximum speed
    # elapsed = time.time() - start_time
    # sleep_time = max(0, frame_time - elapsed)
    # time.sleep(sleep_time)

    if cv2.waitKey(1) == 27:
        break