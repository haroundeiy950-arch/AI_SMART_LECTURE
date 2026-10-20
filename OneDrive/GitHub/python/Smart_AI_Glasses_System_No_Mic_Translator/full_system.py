import cv2
import  cv2
from datetime import datetime

from camera import CameraSystem
from person_recognition import PersonRecognitionSystem
from object_detection import ObjectDetectionSystem
from emotion import EmotionSystem
from ocr import OCRSystem
from speech import SpeechSystem
from translator import TranslatorSystem
from meeting_assistant import MeetingAssistant
from security import SecuritySystem
from database import DatabaseManager
from live_voice_translator import LiveVoiceTranslator
from settings import CAMERA_INDEX
from playsound3 import playsound
playsound('sound.mp3')

class SmartGlassesSystem:
    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index

        print("Loading Smart Glasses modules...")

        self.camera = CameraSystem(camera_index)
        self.db = DatabaseManager()
        self.security = SecuritySystem()

        self.person_recognition = PersonRecognitionSystem()
        self.object_detection = ObjectDetectionSystem()
        self.emotion_system = EmotionSystem()
        self.ocr_system = OCRSystem()
        self.speech_system = SpeechSystem()
        self.translator = TranslatorSystem()
        self.meeting_assistant = MeetingAssistant()
        self.live_voice_translator = LiveVoiceTranslator()

        self.person_model_loaded = False
        self.meeting_running = False
        self.last_detected_text = ""
        self.last_translation = ""

        self.try_load_person_model()

    def try_load_person_model(self):
        try:
            self.person_recognition.load_model()
            self.person_model_loaded = True
            print("Person recognition model loaded.")
        except Exception as error:
            self.person_model_loaded = False
            print("Person recognition model not loaded.")
            print("Train faces first from main.py option 4.")
            print(f"Details: {error}")

    def draw_status_bar(self, frame):
        h, w = frame.shape[:2]

        cv2.rectangle(frame, (0, h - 45), (w, h), (0, 0, 0), -1)

        status = (
            "Q Exit | O Objects | P People | E Emotion | T OCR | R Translate OCR | "
            "S Speak | V Voice Translate | M Meeting Note"
        )

        cv2.putText(
            frame,
            status,
            (10, h - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

    def draw_header(self, frame):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cv2.rectangle(frame, (0, 0), (frame.shape[1], 55), (0, 0, 0), -1)

        cv2.putText(
            frame,
            "Smart AI Glasses System - Full Mode",
            (15, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            now,
            (15, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

    def draw_text_box(self, frame, title, text, y_start=65):
        if not text:
            return

        x = 15
        y = y_start
        width = min(760, frame.shape[1] - 30)
        height = 95

        cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 0, 0), -1)

        cv2.putText(
            frame,
            title,
            (x + 10, y + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            1,
            cv2.LINE_AA
        )

        lines = self.wrap_text(text, 80)
        text_y = y + 45

        for line in lines[:3]:
            cv2.putText(
                frame,
                line,
                (x + 10, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )
            text_y += 18

    def wrap_text(self, text, max_chars):
        words = str(text).split()
        lines = []
        current = ""

        for word in words:
            if len(current + " " + word) <= max_chars:
                current = (current + " " + word).strip()
            else:
                lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def run_people_recognition_on_frame(self, frame, gray):
        if not self.person_model_loaded:
            cv2.putText(
                frame,
                "Person model not trained",
                (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 255),
                2
            )
            return

        faces = self.person_recognition.detect_faces(gray)

        for box in faces:
            x, y, w, h = box
            gray_face = gray[y:y + h, x:x + w]

            person_info, confidence = self.person_recognition.recognize_face(gray_face)
            self.person_recognition.draw_person_info(frame, box, person_info, confidence)

    def run_object_detection_on_frame(self, frame):
        detections = self.object_detection.detect(frame)
        self.object_detection.draw_detections(frame, detections)

        description = self.object_detection.describe_objects(detections)

        cv2.putText(
            frame,
            description[:80],
            (20, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 180, 0),
            2
        )

    def run_emotion_on_frame(self, frame):
        emotion_data = self.emotion_system.analyze_frame(frame)
        self.emotion_system.draw_emotion(frame, emotion_data)

    def read_ocr_from_frame(self, frame):
        text = self.ocr_system.image_to_text(frame)
        self.last_detected_text = text
        print("OCR Text:")
        print(text)

    def translate_last_text(self):
        if not self.last_detected_text:
            self.last_translation = "No OCR text to translate."
            return

        self.last_translation = self.translator.translate_text(
            self.last_detected_text,
            "en",
            "ar"
        )

        print("Translation:")
        print(self.last_translation)

    def speak_last_info(self):
        text = ""

        if self.last_translation:
            text = self.last_translation
        elif self.last_detected_text:
            text = self.last_detected_text
        else:
            text = "Smart glasses system is running."

        self.speech_system.text_to_speech(text)

    def meeting_note_from_ocr(self):
        if not self.meeting_running:
            self.meeting_assistant.start_meeting(
                "Smart Glasses Auto Meeting",
                ["User"]
            )
            self.meeting_running = True

        note = self.last_detected_text or "Visual note captured from smart glasses."
        self.meeting_assistant.add_note(note)
        print("Meeting note added.")

    def run(self):
        print(self.security.privacy_warning())

        if not self.camera.open_camera():
            return

        mode_people = True
        mode_objects = False
        mode_emotion = False

        print("Full Smart Glasses System started.")
        print("Controls:")
        print("P = Toggle person recognition")
        print("O = Toggle object detection")
        print("E = Toggle emotion analysis")
        print("T = OCR read text from camera")
        print("R = Translate last OCR text")
        print("S = Speak last OCR/translation")
        print("M = Add OCR text as meeting note")
        print("V = Open live voice translator in terminal")
        print("Q = Exit")

        while True:
            ret, frame = self.camera.read_frame()

            if not ret or frame is None:
                print("Cannot read camera frame.")
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            self.draw_header(frame)

            if mode_people:
                self.run_people_recognition_on_frame(frame, gray)

            if mode_objects:
                self.run_object_detection_on_frame(frame)

            if mode_emotion:
                self.run_emotion_on_frame(frame)

            if self.last_detected_text:
                self.draw_text_box(frame, "OCR Text", self.last_detected_text, y_start=65)

            if self.last_translation:
                self.draw_text_box(frame, "Translation", self.last_translation, y_start=165)

            self.draw_status_bar(frame)

            cv2.imshow("Smart AI Glasses System - Full Mode", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                break

            elif key == ord("p"):
                mode_people = not mode_people
                print(f"Person recognition: {mode_people}")

            elif key == ord("o"):
                mode_objects = not mode_objects
                print(f"Object detection: {mode_objects}")

            elif key == ord("e"):
                mode_emotion = not mode_emotion
                print(f"Emotion analysis: {mode_emotion}")

            elif key == ord("t"):
                self.read_ocr_from_frame(frame)

            elif key == ord("r"):
                self.translate_last_text()

            elif key == ord("s"):
                self.speak_last_info()

            elif key == ord("m"):
                self.meeting_note_from_ocr()

            elif key == ord("v"):
                print("Opening live voice translator. Use terminal instructions.")
                self.live_voice_translator.run()

        if self.meeting_running:
            self.meeting_assistant.end_meeting()

        self.camera.release()
        print("Smart Glasses System closed.")


if __name__ == "__main__":
    system = SmartGlassesSystem()
    system.run()
