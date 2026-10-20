
import tkinter as tk
from tkinter import messagebox

from database import DatabaseManager
from camera import CameraSystem
from person_recognition import PersonRecognitionSystem
from smart_assistant import SmartAssistant


class SmartGlassesUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Smart AI Glasses System")
        self.root.geometry("600x500")

        self.db = DatabaseManager()

        self.build_ui()

    def build_ui(self):
        title = tk.Label(
            self.root,
            text="Smart AI Glasses System",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=20)

        subtitle = tk.Label(
            self.root,
            text="AI Vision • Translation • Speech • Meetings • Security",
            font=("Arial", 11)
        )
        subtitle.pack(pady=5)

        buttons = [
            ("Open Camera Preview", self.open_camera),
            ("Run Person Recognition", self.run_person_recognition),
            ("Train Face Model", self.train_faces),
            ("Show Registered People", self.show_people),
            ("Open Smart Assistant", self.open_assistant),
            ("Exit", self.root.destroy)
        ]

        for text, command in buttons:
            button = tk.Button(
                self.root,
                text=text,
                width=35,
                height=2,
                command=command
            )
            button.pack(pady=7)

    def open_camera(self):
        camera = CameraSystem()
        camera.preview()

    def run_person_recognition(self):
        try:
            system = PersonRecognitionSystem()
            system.run_camera_recognition()
        except Exception as error:
            messagebox.showerror("Error", str(error))

    def train_faces(self):
        try:
            system = PersonRecognitionSystem()
            system.train()
            messagebox.showinfo("Success", "Face model trained successfully.")
        except Exception as error:
            messagebox.showerror("Error", str(error))

    def show_people(self):
        people = self.db.list_people()

        if not people:
            messagebox.showinfo("People", "No people registered.")
            return

        text = ""

        for person in people:
            text += f"ID: {person['person_id']}\n"
            text += f"Name: {person['name']}\n"
            text += f"Type: {person['type']}\n"
            text += f"Job: {person['job']}\n"
            text += "-" * 30 + "\n"

        messagebox.showinfo("Registered People", text)

    def open_assistant(self):
        messagebox.showinfo(
            "Assistant",
            "Smart assistant works in terminal. Run: python smart_assistant.py"
        )

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SmartGlassesUI()
    app.run()
