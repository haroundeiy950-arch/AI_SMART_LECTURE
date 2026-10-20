from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

from alerts import EmailAlertService
from config import (
    ATTENDANCE_COOLDOWN_SECONDS,
    CAMERA_INDEX,
    CAPTURE_SAMPLES,
    EMAIL_ALERT_COOLDOWN_SECONDS,
    FACE_HEIGHT,
    FACE_WIDTH,
    FACES_DIR,
    MODEL_PATH,
    RECOGNITION_DISTANCE_THRESHOLD,
    UNKNOWN_CAPTURE_COOLDOWN_SECONDS,
    UNKNOWN_DIR,
)
from database import Database


class FaceEngineError(RuntimeError):
    pass


class FaceEngine:
    def __init__(self, db: Database):
        self.db = db
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self.face_cascade.empty():
            raise FaceEngineError("OpenCV face detector could not be loaded.")

        if not hasattr(cv2, "face"):
            raise FaceEngineError(
                "cv2.face is unavailable. Install opencv-contrib-python and "
                "remove opencv-python if both are installed."
            )

        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.alert_service = EmailAlertService()

    @staticmethod
    def open_camera(camera_index: int = CAMERA_INDEX):
        indexes = []
        for idx in [camera_index, 0, 1, 2, 3]:
            if idx not in indexes:
                indexes.append(idx)

        for idx in indexes:
            if hasattr(cv2, "CAP_DSHOW"):
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ok, _ = cap.read()
                if ok:
                    return cap, idx
            cap.release()
        raise FaceEngineError(
            "Camera not found. Close other camera applications and check privacy permissions."
        )

    def detect_faces(self, gray_frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        return list(
            self.face_cascade.detectMultiScale(
                gray_frame,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(80, 80),
            )
        )

    @staticmethod
    def normalize_face(gray_face: np.ndarray) -> np.ndarray:
        face = cv2.resize(gray_face, (FACE_WIDTH, FACE_HEIGHT))
        return cv2.equalizeHist(face)

    def capture_samples(
        self,
        person_id: int,
        person_name: str,
        sample_count: int = CAPTURE_SAMPLES,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        person_dir = FACES_DIR / str(person_id)
        person_dir.mkdir(parents=True, exist_ok=True)

        cap, camera_index = self.open_camera()
        captured = 0
        last_capture = 0.0

        try:
            while captured < sample_count:
                ok, frame = cap.read()
                if not ok:
                    raise FaceEngineError("Could not read a frame from the camera.")

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.detect_faces(gray)

                for x, y, w, h in faces[:1]:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 0), 2)
                    now = time.time()
                    if now - last_capture >= 0.20:
                        face = self.normalize_face(gray[y : y + h, x : x + w])
                        captured += 1
                        filename = person_dir / f"sample_{captured:03d}.jpg"
                        if not cv2.imwrite(str(filename), face):
                            raise FaceEngineError(f"Could not save {filename.name}")
                        self.db.add_face_sample(person_id, str(filename))
                        last_capture = now
                        if progress_callback:
                            progress_callback(captured, sample_count)

                cv2.putText(
                    frame,
                    f"{person_name} | Samples: {captured}/{sample_count}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                )
                cv2.putText(
                    frame,
                    "Look at the camera and move your head slightly. Press Q to cancel.",
                    (20, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    1,
                )
                cv2.imshow("Register Face", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        return captured

    def train_model(self) -> int:
        samples = self.db.list_face_samples()
        images: List[np.ndarray] = []
        labels: List[int] = []

        for sample in samples:
            path = Path(sample["image_path"])
            if not path.exists():
                continue
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue
            images.append(self.normalize_face(image))
            labels.append(int(sample["person_id"]))

        if not images:
            raise FaceEngineError("No valid face samples are available for training.")

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.train(images, np.array(labels, dtype=np.int32))
        self.recognizer.write(str(MODEL_PATH))
        return len(images)

    def load_model(self) -> None:
        if not MODEL_PATH.exists():
            raise FaceEngineError(
                "Recognition model not found. Register a person and train the model first."
            )
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(str(MODEL_PATH))

    @staticmethod
    def confidence_percent(distance: float) -> float:
        # User-friendly approximation. LBPH itself returns a distance, not a probability.
        return max(0.0, min(100.0, 100.0 * (1.0 - distance / 120.0)))

    def run_recognition(
        self,
        mode: str = "IN",
        camera_name: str = "Camera 1",
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, int]:
        self.load_model()
        mode = mode.upper()
        if mode not in {"IN", "OUT"}:
            raise ValueError("mode must be IN or OUT")

        cap, camera_index = self.open_camera()
        recent_attendance: Dict[int, float] = {}
        last_unknown_capture = 0.0
        last_email_alert = 0.0
        summary = {"recognized": 0, "unknown": 0, "attendance": 0}

        if status_callback:
            status_callback(f"Camera {camera_index} opened in {mode} mode.")

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    raise FaceEngineError("Could not read a frame from the camera.")

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.detect_faces(gray)
                now = time.time()

                for x, y, w, h in faces:
                    face = self.normalize_face(gray[y : y + h, x : x + w])
                    label, distance = self.recognizer.predict(face)
                    confidence = self.confidence_percent(float(distance))

                    person = (
                        self.db.get_person(int(label))
                        if float(distance) <= RECOGNITION_DISTANCE_THRESHOLD
                        else None
                    )
                    if person and person["active"]:
                        summary["recognized"] += 1
                        color = (0, 210, 0)
                        display_name = person["full_name"]
                        text = f"{display_name} | {confidence:.1f}%"

                        last_log = recent_attendance.get(person["id"], 0.0)
                        if now - last_log >= ATTENDANCE_COOLDOWN_SECONDS:
                            self.db.add_attendance(
                                person["id"], mode, confidence, ""
                            )
                            recent_attendance[person["id"]] = now
                            summary["attendance"] += 1
                            if status_callback:
                                status_callback(
                                    f"{mode}: {display_name} ({confidence:.1f}%)"
                                )
                    else:
                        summary["unknown"] += 1
                        color = (0, 0, 255)
                        text = "UNKNOWN"

                        if now - last_unknown_capture >= UNKNOWN_CAPTURE_COOLDOWN_SECONDS:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            image_path = UNKNOWN_DIR / f"unknown_{timestamp}.jpg"
                            UNKNOWN_DIR.mkdir(parents=True, exist_ok=True)
                            cv2.imwrite(str(image_path), frame)
                            self.db.add_unknown_event(str(image_path), camera_name)
                            last_unknown_capture = now

                            if status_callback:
                                status_callback(f"Unknown person captured: {image_path.name}")

                            if now - last_email_alert >= EMAIL_ALERT_COOLDOWN_SECONDS:
                                try:
                                    if self.alert_service.send_unknown_alert(
                                        str(image_path), self.db.now()
                                    ):
                                        last_email_alert = now
                                except Exception as exc:
                                    if status_callback:
                                        status_callback(f"Email alert failed: {exc}")

                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(
                        frame,
                        text,
                        (x, max(25, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        color,
                        2,
                    )

                cv2.putText(
                    frame,
                    f"ACCESS MODE: {mode} | Press Q to stop",
                    (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2,
                )
                cv2.imshow("Live Face Recognition", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        return summary
