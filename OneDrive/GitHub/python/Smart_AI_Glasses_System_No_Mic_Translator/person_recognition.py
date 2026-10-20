import cv2
import json
import uuid
import time
import shutil
import numpy as np
from pathlib import Path
from datetime import datetime


class FaceRecognitionSystem:
    def __init__(self):
        self.camera_index = 0
        self.sample_count = 30
        self.face_size = (200, 200)
        self.confidence_threshold = 75

        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data"
        self.faces_dir = self.base_dir / "known_faces"
        self.models_dir = self.base_dir / "models"

        self.persons_file = self.data_dir / "persons.json"
        self.model_file = self.models_dir / "face_model.yml"
        self.labels_file = self.models_dir / "labels.json"

        self.create_folders()

    def create_folders(self):
        self.data_dir.mkdir(exist_ok=True)
        self.faces_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)

    def load_persons(self):
        if not self.persons_file.exists():
            return []

        try:
            with open(self.persons_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return []

    def save_persons(self, persons):
        with open(self.persons_file, "w", encoding="utf-8") as file:
            json.dump(persons, file, ensure_ascii=False, indent=4)

    def clean_name(self, name):
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        name = name.strip().replace(" ", "_")
        result = "".join(ch for ch in name if ch in allowed)

        if not result:
            result = "person"

        return result

    def check_cv2_face(self):
        if not hasattr(cv2, "face"):
            print("Error: cv2.face not found.")
            print("Run this command:")
            print("python -m pip uninstall -y opencv-python opencv-contrib-python")
            print("python -m pip install opencv-contrib-python numpy")
            return False

        return True

    def get_face_cascade(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)

        if cascade.empty():
            raise RuntimeError("Error: face cascade model not loaded.")

        return cascade

    def open_camera(self):
        possible_indexes = [self.camera_index, 0, 1, 2, 3, 4, 5]
        tried = set()

        for index in possible_indexes:
            if index in tried:
                continue

            tried.add(index)

            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(index)

            if not cap.isOpened():
                cap.release()
                continue

            ret, frame = cap.read()

            if ret and frame is not None:
                print(f"Camera opened successfully. Index: {index}")
                return cap

            cap.release()

        print("Error: Camera not found.")
        print("Close Camera App / Zoom / Teams and try again.")
        return None

    def biggest_face(self, faces):
        if len(faces) == 0:
            return None

        return max(faces, key=lambda f: f[2] * f[3])

    def register_person_by_camera(self):
        print("\n===== Register Person By Camera =====")

        name = input("Enter person name: ").strip()
        if not name:
            print("Name is required.")
            return

        role = input("Enter role/student/job: ").strip()
        note = input("Enter note/info: ").strip()

        person_id = str(uuid.uuid4())[:8]
        folder_name = f"{person_id}_{self.clean_name(name)}"
        person_folder = self.faces_dir / folder_name
        person_folder.mkdir(exist_ok=True)

        person_data = {
            "id": person_id,
            "name": name,
            "role": role,
            "note": note,
            "folder": folder_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        persons = self.load_persons()
        persons.append(person_data)
        self.save_persons(persons)

        print("\nNow camera will open.")
        print("Stand in front of camera.")
        print("Press Q or ESC to cancel.")
        print(f"The system will capture {self.sample_count} face images.")

        cap = self.open_camera()

        if cap is None:
            self.delete_person_by_id(person_id, silent=True)
            return

        face_cascade = self.get_face_cascade()
        count = 0
        last_capture_time = 0

        while count < self.sample_count:
            ret, frame = cap.read()

            if not ret or frame is None:
                print("Cannot read frame from camera.")
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(80, 80)
            )

            face = self.biggest_face(faces)

            if face is not None:
                x, y, w, h = face

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                now = time.time()

                if now - last_capture_time >= 0.25:
                    face_img = gray[y:y + h, x:x + w]
                    face_img = cv2.resize(face_img, self.face_size)

                    image_path = person_folder / f"{count + 1}.jpg"
                    cv2.imwrite(str(image_path), face_img)

                    count += 1
                    last_capture_time = now

                    print(f"Captured image {count}/{self.sample_count}")

            cv2.putText(
                frame,
                f"Registering: {name} | Captured: {count}/{self.sample_count}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "Look at camera. Press Q or ESC to cancel.",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.imshow("Register Person By Camera", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                print("Registration cancelled.")
                break

        cap.release()
        cv2.destroyAllWindows()

        if count >= 5:
            print(f"\nPerson saved successfully: {name}")
            print(f"Images saved in: {person_folder}")
            print("Now train the system.")
        else:
            print("\nNot enough images captured. Deleting registration.")
            self.delete_person_by_id(person_id, silent=True)

    def register_person_from_image(self):
        print("\n===== Register Person From Image =====")
        print("Example:")
        print(r"C:\Users\user\Pictures\haroun.jpg")

        image_path = input("\nEnter image path: ").strip().strip('"')
        name = input("Enter person name: ").strip()

        if not image_path:
            print("Image path is required.")
            return

        if not name:
            print("Name is required.")
            return

        role = input("Enter role/student/job: ").strip()
        note = input("Enter note/info: ").strip()

        img = cv2.imread(image_path)

        if img is None:
            print("Error: image not found or cannot read image.")
            return

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = self.get_face_cascade()

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        face = self.biggest_face(faces)

        if face is None:
            print("No face detected in this image.")
            return

        x, y, w, h = face
        face_img = gray[y:y + h, x:x + w]
        face_img = cv2.resize(face_img, self.face_size)

        person_id = str(uuid.uuid4())[:8]
        folder_name = f"{person_id}_{self.clean_name(name)}"
        person_folder = self.faces_dir / folder_name
        person_folder.mkdir(exist_ok=True)

        samples = []

        samples.append(face_img)
        samples.append(cv2.equalizeHist(face_img))
        samples.append(cv2.convertScaleAbs(face_img, alpha=1.1, beta=10))
        samples.append(cv2.convertScaleAbs(face_img, alpha=0.9, beta=-10))

        rows, cols = face_img.shape

        for angle in [-8, -5, 5, 8]:
            matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), angle, 1)
            rotated = cv2.warpAffine(face_img, matrix, (cols, rows))
            samples.append(rotated)

        samples.append(cv2.GaussianBlur(face_img, (3, 3), 0))

        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ])

        samples.append(cv2.filter2D(face_img, -1, kernel))

        for i in range(self.sample_count):
            sample = samples[i % len(samples)]
            cv2.imwrite(str(person_folder / f"{i + 1}.jpg"), sample)

        person_data = {
            "id": person_id,
            "name": name,
            "role": role,
            "note": note,
            "folder": folder_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        persons = self.load_persons()
        persons.append(person_data)
        self.save_persons(persons)

        print(f"\nPerson saved successfully: {name}")
        print(f"Images saved in: {person_folder}")
        print("Now train the system.")

    def list_persons(self):
        persons = self.load_persons()

        print("\n===== Registered Persons =====")

        if not persons:
            print("No persons registered yet.")
            return

        for index, person in enumerate(persons, start=1):
            print(f"\n{index}. {person.get('name', 'Unknown')}")
            print(f"   ID: {person.get('id')}")
            print(f"   Role: {person.get('role')}")
            print(f"   Note: {person.get('note')}")
            print(f"   Folder: {person.get('folder')}")
            print(f"   Created: {person.get('created_at')}")

    def delete_person_by_id(self, person_id, silent=False):
        persons = self.load_persons()
        new_persons = []
        deleted = False

        for person in persons:
            if person.get("id") == person_id:
                folder = self.faces_dir / person.get("folder", "")

                if folder.exists():
                    shutil.rmtree(folder)

                deleted = True
            else:
                new_persons.append(person)

        self.save_persons(new_persons)

        if not silent:
            if deleted:
                print("Person deleted successfully.")
                print("Train the system again after delete.")
            else:
                print("Person ID not found.")

    def delete_person_menu(self):
        self.list_persons()

        person_id = input("\nEnter person ID to delete: ").strip()

        if not person_id:
            print("ID is required.")
            return

        self.delete_person_by_id(person_id)

    def train_model(self):
        if not self.check_cv2_face():
            return

        persons = self.load_persons()

        if not persons:
            print("No persons found. Register persons first.")
            return

        faces = []
        labels = []
        labels_map = {}

        label_id = 0

        for person in persons:
            folder_name = person.get("folder")
            person_folder = self.faces_dir / folder_name

            if not person_folder.exists():
                continue

            image_files = list(person_folder.glob("*.jpg")) + list(person_folder.glob("*.png"))

            if len(image_files) == 0:
                continue

            labels_map[str(label_id)] = {
                "id": person.get("id"),
                "name": person.get("name"),
                "role": person.get("role"),
                "note": person.get("note")
            }

            for image_path in image_files:
                img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)

                if img is None:
                    continue

                img = cv2.resize(img, self.face_size)

                faces.append(img)
                labels.append(label_id)

            label_id += 1

        if len(faces) == 0:
            print("No valid face images found.")
            return

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(labels))

        recognizer.save(str(self.model_file))

        with open(self.labels_file, "w", encoding="utf-8") as file:
            json.dump(labels_map, file, ensure_ascii=False, indent=4)

        print("\nTraining completed successfully.")
        print(f"Model saved: {self.model_file}")
        print(f"Labels saved: {self.labels_file}")

    def recognize_live(self):
        if not self.model_file.exists() or not self.labels_file.exists():
            print("Model not found. Train system first.")
            return

        if not self.check_cv2_face():
            return

        with open(self.labels_file, "r", encoding="utf-8") as file:
            labels_map = json.load(file)

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(str(self.model_file))

        face_cascade = self.get_face_cascade()

        cap = self.open_camera()

        if cap is None:
            return

        print("\nRecognition started.")
        print("Press Q or ESC to exit.")

        last_print_time = 0

        while True:
            ret, frame = cap.read()

            if not ret or frame is None:
                print("Cannot read camera frame.")
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(80, 80)
            )

            for (x, y, w, h) in faces:
                face_img = gray[y:y + h, x:x + w]
                face_img = cv2.resize(face_img, self.face_size)

                label, confidence = recognizer.predict(face_img)
                label_info = labels_map.get(str(label), {})

                if confidence < self.confidence_threshold:
                    name = label_info.get("name", "Unknown")
                    role = label_info.get("role", "")
                    note = label_info.get("note", "")

                    display_text = name

                    if role:
                        display_text += f" - {role}"

                    color = (0, 255, 0)
                    print_text = f"Known person: {name} | Confidence: {confidence:.1f}"

                else:
                    display_text = "Unknown Person"
                    note = ""
                    color = (0, 0, 255)
                    print_text = f"Unknown person | Confidence: {confidence:.1f}"

                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                cv2.putText(
                    frame,
                    display_text,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    color,
                    2
                )

                if note:
                    cv2.putText(
                        frame,
                        note[:40],
                        (x, y + h + 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 0),
                        2
                    )

                now = time.time()

                if now - last_print_time >= 1:
                    print(print_text)
                    last_print_time = now

            cv2.putText(
                frame,
                "Face Recognition System | Press Q or ESC to exit",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 0),
                2
            )

            cv2.imshow("Live Face Recognition", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                break

        cap.release()
        cv2.destroyAllWindows()