import os
import logging
import warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore')
logging.getLogger('tensorflow').setLevel(logging.ERROR)

import tensorflow as tf
import tf_keras
import numpy as np
import cv2
import math
import kagglehub

class TheftModelAnalyzer:
    def __init__(self, sequence_length=160, frame_width=90, frame_height=90):
        self.sequence_length = sequence_length
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        print("Loading global theft detection model...")
        path = kagglehub.model_download("kaledhoshme/early-detection-of-theft-attempts/tensorFlow2/early-detection-of-theft-attempts")
        model_path = path + '/lrcn_160S_90_90Q.h5'
        
        self.model = tf_keras.models.load_model(model_path)
        self.frames_queue = []
        self.previous_frame = None
        self.last_message = "Analyzing video..."
        self.last_is_theft = False
        self.last_probability = 0
        
    def generate_message(self, probability, label):
        if label == 0:
            if probability <= 75:
                return "Little chance of theft", probability
            elif probability <= 85:
                return "High probability of theft", probability
            else:
                return "Very high probability of theft", probability
        elif label == 1:
            if probability <= 75:
                return "Movement is confusing, watch", probability
            elif probability <= 85:
                return "Normal, but better to watch", probability
            else:
                return "Movement is normal", probability
        return "", 0

    def pre_process_frame(self, current_frame, previous_frame):
        diff = cv2.absdiff(current_frame, previous_frame)
        diff = cv2.GaussianBlur(diff, (3, 3), 0)
        resized_frame = cv2.resize(diff, (self.frame_height, self.frame_width))
        gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
        normalized_frame = gray_frame / 255.0
        return normalized_frame

    def predict_frame(self, frame):
        if self.previous_frame is None:
            self.previous_frame = frame.copy()
            return self.last_message, self.last_is_theft, self.last_probability
            
        normalized_frame = self.pre_process_frame(frame, self.previous_frame)
        self.previous_frame = frame.copy()
        
        self.frames_queue.append(normalized_frame)
        
        if len(self.frames_queue) == self.sequence_length:
            try:
                # Prediction
                probabilities = self.model.predict(np.expand_dims(self.frames_queue, axis=0), verbose=0)[0]
                predicted_label = np.argmax(probabilities)
                probability = math.floor(max(probabilities[0], probabilities[1]) * 100)
                
                msg, prob = self.generate_message(probability, predicted_label)
                self.last_message = msg
                self.last_is_theft = (predicted_label == 0)
                self.last_probability = prob
                
                # Slide the window so we check every 30 frames (approx 1 second)
                self.frames_queue = self.frames_queue[30:]
            except Exception as e:
                print(f"Prediction error: {e}")
                self.frames_queue.pop(0) # pop one to keep moving
            
        return self.last_message, self.last_is_theft, self.last_probability
