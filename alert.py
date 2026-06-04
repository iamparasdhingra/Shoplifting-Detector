import time
import smtplib
import urllib.parse
import urllib.request
import requests
import cv2
import os
import threading
from email.mime.text import MIMEText

class AlertSystem:

    def __init__(self):
        # Email configuration (replace with actual)
        self.sender_email = "your_email@example.com"
        self.sender_password = "your_password"
        self.guard_email = "guard@example.com"

        # Telegram bot configuration (hardcoded for manual setup)
        self.telegram_bot_token = "8621068247:AAFesEAioe6dSYZVJ9b0SoetIYwvKdNbR5I"
        self.telegram_chat_id = "6651548880"
        print(f"DEBUG: TELEGRAM_BOT_TOKEN='{self.telegram_bot_token}', TELEGRAM_CHAT_ID='{self.telegram_chat_id}'")  # Debug line

    def trigger(self, event, frame_buffer=None):

        person = event["person"]
        score = event["score"]
        event_type = event.get("type", "suspicious")

        message = f"[ALERT] Person {person} {event_type} (score={score}) at {time.time()}"

        print(message)

        # Send Telegram notification for stealing events
        if event_type == "stealing":
            # Run the video grouping and telegram post in a background thread
            # so the webcam feed does not freeze during file I/O & network upload
            def send_alert_task():
                video_path = None
                if frame_buffer:
                    video_path = self.create_video_clip(frame_buffer)
                self.send_telegram(message, video_path)

            t = threading.Thread(target=send_alert_task)
            t.daemon = True
            t.start()

        # Send email notification (optional)
        # self.send_email(message)

    def create_video_clip(self, frame_buffer):
        if not frame_buffer:
            return None
        temp_path = f"temp_clip_{int(time.time() * 1000)}.mp4"
        height, width, _ = frame_buffer[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, 10.0, (width, height))  # 10 fps
        for frame in frame_buffer:
            out.write(frame)
        out.release()
        return temp_path
        try:
            msg = MIMEText(message)
            msg['Subject'] = 'Security Alert'
            msg['From'] = self.sender_email
            msg['To'] = self.guard_email

            server = smtplib.SMTP('smtp.example.com', 587)  # Replace with actual SMTP
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.guard_email, msg.as_string())
            server.quit()
            print("Email sent to guard.")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def send_telegram(self, message, video_path=None):
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("Telegram bot token/chat_id not configured; skipping Telegram alert.")
            return

        try:
            if video_path and os.path.exists(video_path):
                # Send video
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendVideo"
                with open(video_path, 'rb') as video_file:
                    files = {'video': video_file}
                    data = {'chat_id': self.telegram_chat_id, 'caption': message}
                    response = requests.post(url, files=files, data=data)
                    print(f"Telegram video response: {response.json()}")
                os.remove(video_path)  # Clean up
            else:
                # Send text
                text = urllib.parse.quote_plus(message)
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage?chat_id={self.telegram_chat_id}&text={text}"
                with urllib.request.urlopen(url, timeout=10) as resp:
                    data = resp.read().decode('utf-8')
                    print(f"Telegram text response: {data}")
        except Exception as e:
            print(f"Failed to send Telegram: {e}")