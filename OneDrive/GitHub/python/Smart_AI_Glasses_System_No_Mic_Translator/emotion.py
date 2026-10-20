import cv2
from typing import Dict, Any


class EmotionSystem:
    def __init__(self):
        self.available = False
        self.deepface = None
        self.load_engine()

    def load_engine(self):
        try:
            from deepface import DeepFace
            self.deepface = DeepFace
            self.available = True
            print("DeepFace emotion engine loaded.")
        except Exception as error:
            self.available = False
            print("DeepFace not available.")
            print("Install with: pip install deepface")
            print(f"Details: {error}")

    def analyze_frame(self, frame) -> Dict[str, Any]:
        if not self.available or self.deepface is None:
            return {
                "emotion": "unknown",
                "confidence": 0,
                "message": "Emotion engine not available"
            }

        try:
            result = self.deepface.analyze(
                frame,
                actions=["emotion"],
                enforce_detection=False
            )

            if isinstance(result, list):
                result = result[0]

            emotion = result.get("dominant_emotion", "unknown")
            emotions = result.get("emotion", {})
            confidence = emotions.get(emotion, 0)

            return {
                "emotion": emotion,
                "confidence": confidence,
                "message": "OK"
            }

        except Exception as error:
            return {
                "emotion": "unknown",
                "confidence": 0,
                "message": f"Emotion error: {error}"
            }

    def draw_emotion(self, frame, emotion_data):
        text = f"Emotion: {emotion_data.get('emotion')}"

        cv2.putText(
            frame,
            text,
            (25, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (180, 255, 180),
            2
        )
