from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FACES_DIR = DATA_DIR / "faces"
UNKNOWN_DIR = DATA_DIR / "unknown"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"

DATABASE_PATH = DATA_DIR / "security_system.db"
MODEL_PATH = MODELS_DIR / "lbph_face_model.yml"

CAMERA_INDEX = 0
FACE_WIDTH = 200
FACE_HEIGHT = 200
CAPTURE_SAMPLES = 30

# LBPH returns a distance: lower is better.
# Values below this threshold are treated as recognized.
RECOGNITION_DISTANCE_THRESHOLD = 65.0
ATTENDANCE_COOLDOWN_SECONDS = 60
UNKNOWN_CAPTURE_COOLDOWN_SECONDS = 20
EMAIL_ALERT_COOLDOWN_SECONDS = 120

APP_TITLE = "Face Recognition Security System"
WINDOW_SIZE = "1180x720"
