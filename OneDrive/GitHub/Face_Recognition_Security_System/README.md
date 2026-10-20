# Face Recognition Security System

A professional educational desktop system built with Python, OpenCV Contrib,
SQLite and Tkinter.

## Included features

- Administrator login with PBKDF2 password hashing
- Register authorized people
- Capture multiple face samples using a camera
- Train an OpenCV LBPH recognition model
- Live recognition in check-in or check-out mode
- Approximate match display
- Attendance and access-event records
- Unknown-person image capture
- Optional unknown-person email alerts
- Search, update, activate/deactivate and delete people
- Daily/monthly date filtering
- CSV attendance and unknown-event reports
- Database backups
- Administrator audit logs in SQLite
- Camera-index fallback: 0, 1, 2 and 3

## Important security and privacy notice

This is an educational/local deployment project. Obtain consent before collecting
biometric data and comply with applicable privacy laws. Face recognition should
not be the only control protecting a high-security location.

For production use, add:

- Presentation-attack/liveness detection
- Badge, PIN or OTP as a second factor
- Encryption at rest and key management
- Role-based access control
- Physical door-controller integration
- TLS and secure server deployment
- Retention/deletion policies
- Human review and incident-response procedures
- Accuracy and fairness testing under your real lighting/camera conditions

LBPH returns a distance, not a biometric probability. The percentage displayed by
this project is a user-friendly approximation.

## Requirements

Recommended:

- Windows 10/11
- Python 3.11, 3.12 or 3.13
- Webcam
- Good lighting

The project uses `opencv-contrib-python`, because `cv2.face` is part of the
contrib package.

## Fast installation on Windows

1. Extract the ZIP.
2. Open the project folder.
3. Double-click `run_windows.bat`.
4. Wait for the virtual environment and packages to install.
5. The application opens automatically.

You can also use PowerShell:

```powershell
cd Face_Recognition_Security_System
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python-headless
python -m pip install -r requirements.txt
python main.py
```

## First login

```text
Username: admin
Password: 
```

Change this password immediately from the **Settings** tab.

## How to use

### 1. Register a person

1. Open `Register Person`.
2. Enter a unique code, name and optional details.
3. Select `Save Person and Capture Face`.
4. Look directly at the camera.
5. Move your head slightly left and right.
6. The application captures 30 images.
7. The model is trained automatically.

### 2. Run live recognition

1. Open `Live Recognition`.
2. Select `IN` for check-in or `OUT` for check-out.
3. Select `Start Camera`.
4. Press `Q` inside the OpenCV camera window to stop.

### 3. Reports

- Use the Attendance tab.
- Enter dates in `YYYY-MM-DD` format.
- Filter and export CSV.
- Unknown-person events can also be exported.

## Optional email alerts

Configure the following Windows environment variables before opening the app:

```powershell
$env:FRS_SMTP_HOST="smtp.example.com"
$env:FRS_SMTP_PORT="587"
$env:FRS_SMTP_USER="security@example.com"
$env:FRS_SMTP_PASSWORD="your-app-password"
$env:FRS_ALERT_TO="manager@example.com"
$env:FRS_SMTP_USE_TLS="1"
python main.py
```

Use an application-specific SMTP password where supported. Do not place passwords
inside source code.

## Project structure

```text
Face_Recognition_Security_System/
├── main.py
├── ui.py
├── database.py
├── face_engine.py
├── security.py
├── alerts.py
├── reports.py
├── backup.py
├── config.py
├── reset_admin_password.py
├── requirements.txt
├── run_windows.bat
├── data/
│   ├── faces/
│   └── unknown/
├── models/
├── reports/
├── logs/
└── backups/
```

## Common errors

### `module 'cv2' has no attribute 'face'`

Remove conflicting OpenCV packages and install the contrib package:

```powershell
python -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python-headless opencv-contrib-python
python -m pip install opencv-contrib-python
```

### Camera not found

- Close Camera, Zoom, Teams and browser tabs using the camera.
- Open Windows Settings > Privacy & security > Camera.
- Allow desktop applications to access the camera.
- Try another USB port.
- Change `CAMERA_INDEX` in `config.py`.

### PowerShell blocks virtual-environment activation

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Forgot administrator password

Run:

```powershell
python reset_admin_password.py
```

Then log in with `` and change it immediately.

## Data locations

- SQLite database: `data/security_system.db`
- Registered face images: `data/faces/<person_id>/`
- Unknown-person captures: `data/unknown/`
- Trained model: `models/lbph_face_model.yml`
- Reports: `reports/`
- Database backups: `backups/`
