import sys
import subprocess
from pathlib import Path


# =========================
# Helpers
# =========================

def run_safely(function):
    try:
        function()
    except Exception as error:
        print("\nError:")
        print(error)


def capture_faces_direct():
    project_dir = Path(__file__).parent
    capture_file = project_dir / "capture_faces.py"

    if not capture_file.exists():
        print("Error: capture_faces.py not found")
        print("Add capture_faces.py in the same folder as main.py")
        return

    subprocess.run([sys.executable, str(capture_file)], cwd=str(project_dir))


def direct_camera_preview():
    import cv2

    possible_indexes = [0, 1, 2, 3, 4, 5]
    cap = None

    for index in possible_indexes:
        temp_cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

        if not temp_cap.isOpened():
            temp_cap.release()
            temp_cap = cv2.VideoCapture(index)

        if temp_cap.isOpened():
            ret, frame = temp_cap.read()

            if ret and frame is not None:
                cap = temp_cap
                print(f"Camera opened successfully. Index: {index}")
                break

        temp_cap.release()

    if cap is None:
        print("Camera not found.")
        print("Close Camera App / Zoom / Teams and try again.")
        return

    print("Camera preview started. Press Q or ESC to exit.")

    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print("Cannot read camera frame.")
            break

        cv2.imshow("Camera Preview", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


# =========================
# Face Recognition Functions
# =========================

def get_face_system():
    from person_recognition import FaceRecognitionSystem
    return FaceRecognitionSystem()


def register_person_by_camera():
    face_system = get_face_system()
    face_system.register_person_by_camera()


def register_person_from_image():
    face_system = get_face_system()
    face_system.register_person_from_image()


def show_registered_persons():
    face_system = get_face_system()
    face_system.list_persons()


def train_face_model():
    face_system = get_face_system()
    face_system.train_model()


def start_live_face_recognition():
    face_system = get_face_system()
    face_system.recognize_live()


def delete_person():
    face_system = get_face_system()
    face_system.delete_person_menu()


# =========================
# Other Project Functions
# =========================

def create_sample_database():
    from database import DatabaseManager

    db = DatabaseManager()
    db.create_sample_data()
    print("Sample database created.")


def test_translator():
    from translator import TranslatorSystem

    translator = TranslatorSystem()

    text = input("Enter English text: ")
    result = translator.translate_text(text, "en", "ar")

    print("Arabic translation:")
    print(result)


def test_tts():
    from speech import SpeechSystem

    speech = SpeechSystem()
    text = input("Enter text to read: ")
    speech.text_to_speech(text)


def meeting_demo():
    from meeting_assistant import MeetingAssistant

    assistant = MeetingAssistant()

    title = input("Meeting title: ")
    participants_text = input("Participants separated by comma: ")
    participants = [p.strip() for p in participants_text.split(",") if p.strip()]

    assistant.start_meeting(title, participants)

    print("Write notes. Type END to finish.")

    while True:
        note = input("Note> ")

        if note.strip().upper() == "END":
            break

        assistant.add_note(note)

    assistant.end_meeting()


def open_smart_assistant():
    from smart_assistant import SmartAssistant

    SmartAssistant().run_terminal()


def open_gui():
    from ui import SmartGlassesUI

    app = SmartGlassesUI()
    app.run()


def run_full_system():
    from full_system import SmartGlassesSystem

    SmartGlassesSystem().run()


def live_voice_translator():
    from live_voice_translator import LiveVoiceTranslator

    LiveVoiceTranslator().run()


def no_microphone_translator():
    from no_mic_translator import NoMicTranslator

    NoMicTranslator().run()


# =========================
# Main Menu
# =========================

def show_menu():
    print("\n======================================")
    print("        Smart AI Glasses System")
    print("======================================")
    print("1. Open camera preview")
    print("2. Register person by camera")
    print("3. Register person from image")
    print("4. Show registered persons")
    print("5. Train face recognition model")
    print("6. Start live face recognition")
    print("7. Delete person")
    print("8. Create sample database")
    print("9. Test translator")
    print("10. Test speech text-to-speech")
    print("11. Meeting assistant demo")
    print("12. Open smart assistant terminal")
    print("13. Open GUI")
    print("14. Run FULL Smart Glasses System")
    print("15. Live voice translator")
    print("16. No microphone translator")
    print("17. Capture Face Direct")
    print("0. Exit")
    print("======================================")


def main():
    try:
        from settings import create_project_folders, print_project_info
        create_project_folders()
        print_project_info()
    except Exception:
        print("Settings file loaded with warning or not found.")

    while True:
        show_menu()

        choice = input("Choose option: ").strip()

        if choice == "1":
            run_safely(direct_camera_preview)

        elif choice == "2":
            run_safely(register_person_by_camera)

        elif choice == "3":
            run_safely(register_person_from_image)

        elif choice == "4":
            run_safely(show_registered_persons)

        elif choice == "5":
            run_safely(train_face_model)

        elif choice == "6":
            run_safely(start_live_face_recognition)

        elif choice == "7":
            run_safely(delete_person)

        elif choice == "8":
            run_safely(create_sample_database)

        elif choice == "9":
            run_safely(test_translator)

        elif choice == "10":
            run_safely(test_tts)

        elif choice == "11":
            run_safely(meeting_demo)

        elif choice == "12":
            run_safely(open_smart_assistant)

        elif choice == "13":
            run_safely(open_gui)

        elif choice == "14":
            run_safely(run_full_system)

        elif choice == "15":
            run_safely(live_voice_translator)

        elif choice == "16":
            run_safely(no_microphone_translator)

        elif choice == "17":
            run_safely(capture_faces_direct)

        elif choice == "0":
            print("Goodbye.")
            break

        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    main()