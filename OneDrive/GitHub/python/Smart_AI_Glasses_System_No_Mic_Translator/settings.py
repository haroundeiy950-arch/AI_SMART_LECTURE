from pathlib import Path

# =========================
# Smart AI Glasses Settings
# =========================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
KNOWN_FACES_DIR = DATA_DIR / "known_faces"

MODELS_DIR = BASE_DIR / "models"
IMAGES_DIR = BASE_DIR / "images"
SOUNDS_DIR = BASE_DIR / "sounds"
LOGS_DIR = BASE_DIR / "logs"

DATABASE_FILE = DATA_DIR / "smart_glasses.db"

PEOPLE_JSON = DATA_DIR / "people.json"
FACE_LABELS_FILE = DATA_DIR / "face_labels.json"

FACE_MODEL_FILE = MODELS_DIR / "face_model.yml"

CAMERA_INDEX = 0
FACE_SIZE = (200, 200)
FACE_CONFIDENCE_THRESHOLD = 75

YOLO_MODEL_NAME = "yolov8n.pt"

DEFAULT_SOURCE_LANGUAGE = "en"
DEFAULT_TARGET_LANGUAGE = "ar"

APP_NAME = "Smart AI Glasses System"
APP_VERSION = "1.0.0"


def create_project_folders():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWN_FACES_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def print_project_info():
    print("=" * 60)
    print(APP_NAME)
    print(f"Version: {APP_VERSION}")
    print("=" * 60)
