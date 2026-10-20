import cv2
from typing import List, Dict, Any

from settings import YOLO_MODEL_NAME


class ObjectDetectionSystem:
    def __init__(self, model_name: str = YOLO_MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self.available = False
        self.load_model()

    def load_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_name)
            self.available = True
            print("YOLO model loaded successfully.")
        except Exception as error:
            self.available = False
            print("YOLO is not available.")
            print("Install with: pip install ultralytics")
            print(f"Details: {error}")

    def detect(self, frame) -> List[Dict[str, Any]]:
        if not self.available or self.model is None:
            return []

        results = self.model(frame, verbose=False)
        detections = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                name = self.model.names.get(class_id, str(class_id))

                detections.append({
                    "name": name,
                    "confidence": confidence,
                    "box": (int(x1), int(y1), int(x2), int(y2))
                })

        return detections

    def draw_detections(self, frame, detections):
        for item in detections:
            x1, y1, x2, y2 = item["box"]
            name = item["name"]
            confidence = item["confidence"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 180, 0), 2)

            label = f"{name} {confidence:.2f}"

            cv2.putText(
                frame,
                label,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 180, 0),
                2
            )

    def describe_objects(self, detections: List[Dict[str, Any]]) -> str:
        if not detections:
            return "No objects detected."

        names = [item["name"] for item in detections]
        unique_names = sorted(set(names))

        return "Detected objects: " + ", ".join(unique_names)
