from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import BASE_DIR, settings

try:
    import cv2
    import numpy as np
    CV_IMPORT_ERROR: Exception | None = None
except Exception as error:  # pragma: no cover - optional dependency
    cv2 = None
    np = None
    CV_IMPORT_ERROR = error

MODEL_DIR = BASE_DIR / "models" / "face_recognition"
MODEL_PATH = MODEL_DIR / "lbph_model.yml"
LABELS_PATH = MODEL_DIR / "labels.json"
FACE_SIZE = (200, 200)
UNKNOWN_THRESHOLD = 75.0


def vision_status() -> dict[str, Any]:
    if cv2 is None or np is None:
        return {"available": False, "reason": f"OpenCV unavailable: {CV_IMPORT_ERROR}"}
    if not hasattr(cv2, "face"):
        return {
            "available": False,
            "reason": "cv2.face is unavailable. Install opencv-contrib-python.",
        }
    return {"available": True, "reason": "ready"}


def _require_vision() -> None:
    status = vision_status()
    if not status["available"]:
        raise RuntimeError(status["reason"])


def _cascade():
    _require_vision()
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        raise RuntimeError(f"Could not load face cascade: {cascade_path}")
    return detector


def _decode_image(content: bytes):
    _require_vision()
    array = np.frombuffer(content, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image")
    return image


def _largest_face(gray, detector):
    faces = detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(70, 70))
    if len(faces) == 0:
        return None
    return max(faces, key=lambda box: int(box[2]) * int(box[3]))


def save_face_sample(person_code: str, content: bytes) -> str:
    image = _decode_image(content)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face = _largest_face(gray, _cascade())
    if face is None:
        raise ValueError("No clear face was detected. Look directly at the camera.")
    x, y, width, height = [int(value) for value in face]
    crop = cv2.resize(gray[y : y + height, x : x + width], FACE_SIZE)
    directory = settings.known_faces_dir / person_code
    directory.mkdir(parents=True, exist_ok=True)
    existing = sorted(directory.glob("sample_*.jpg"))
    output = directory / f"sample_{len(existing) + 1:03d}.jpg"
    if not cv2.imwrite(str(output), crop):
        raise RuntimeError("Could not save face sample")
    return str(output.relative_to(BASE_DIR))


def train_face_model() -> dict[str, Any]:
    _require_vision()
    samples: list[Any] = []
    numeric_labels: list[int] = []
    label_map: dict[int, str] = {}
    next_label = 0

    for person_dir in sorted(settings.known_faces_dir.iterdir()):
        if not person_dir.is_dir():
            continue
        images = sorted(person_dir.glob("sample_*.jpg"))
        if not images:
            continue
        label_map[next_label] = person_dir.name
        for image_path in images:
            image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue
            samples.append(cv2.resize(image, FACE_SIZE))
            numeric_labels.append(next_label)
        next_label += 1

    if not samples:
        raise RuntimeError("No face samples found. Capture samples before training.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(samples, np.array(numeric_labels, dtype=np.int32))
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    recognizer.write(str(MODEL_PATH))
    LABELS_PATH.write_text(json.dumps(label_map, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"people": len(label_map), "samples": len(samples), "model": str(MODEL_PATH)}


def recognize_faces(content: bytes) -> dict[str, Any]:
    _require_vision()
    if not MODEL_PATH.exists() or not LABELS_PATH.exists():
        return {"available": True, "trained": False, "faces": []}
    label_map = {int(key): value for key, value in json.loads(LABELS_PATH.read_text(encoding="utf-8")).items()}
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(MODEL_PATH))
    detector = _cascade()
    image = _decode_image(content)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detected = detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(70, 70))
    results: list[dict[str, Any]] = []
    for x, y, width, height in detected:
        crop = cv2.resize(gray[y : y + height, x : x + width], FACE_SIZE)
        label, confidence = recognizer.predict(crop)
        known = float(confidence) <= UNKNOWN_THRESHOLD and label in label_map
        match_percent = max(0.0, min(100.0, 100.0 - float(confidence)))
        results.append(
            {
                "code": label_map.get(label) if known else None,
                "name": label_map.get(label, "Unknown") if known else "Unknown",
                "known": known,
                "confidence_distance": round(float(confidence), 2),
                "match_percent": round(match_percent, 1),
                "box": [int(x), int(y), int(width), int(height)],
            }
        )
    return {"available": True, "trained": True, "faces": results}
