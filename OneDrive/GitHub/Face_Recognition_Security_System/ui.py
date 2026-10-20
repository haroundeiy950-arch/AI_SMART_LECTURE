from __future__ import annotations

import sqlite3
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Dict, Optional

from backup import create_database_backup
from config import APP_TITLE, CAPTURE_SAMPLES, WINDOW_SIZE
from database import Database
from face_engine import FaceEngine, FaceEngineError
from reports import ReportService


class LoginWindow:
    def __init__(self, root: tk.Tk, db: Database):
        self.root = root
        self.db = db
        self.result: Optional[Dict[str, Any]] = None

        root.title(f"{APP_TITLE} - Login")
        root.geometry("440x330")
        root.resizable(False, False)

        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        frame = ttk.Frame(root, padding=32)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Security Administration",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(10, 8))
        ttk.Label(
            frame,
            text="Sign in to manage registered persons and access records.",
        ).pack(pady=(0, 24))

        form = ttk.Frame(frame)
        form.pack(fill="x")

        ttk.Label(form, text="Username").grid(row=0, column=0, sticky="w", pady=7)
        self.username = ttk.Entry(form, width=32)
        self.username.grid(row=0, column=1, pady=7, padx=(12, 0))
        self.username.insert(0, "admin")

        ttk.Label(form, text="Password").grid(row=1, column=0, sticky="w", pady=7)
        self.password = ttk.Entry(form, width=32, show="*")
        self.password.grid(row=1, column=1, pady=7, padx=(12, 0))

        ttk.Button(frame, text="Sign In", command=self.login).pack(
            fill="x", pady=(24, 8), ipady=5
        )
        ttk.Label(
            frame,
            text="First login: admin / Admin@123",
            foreground="#7a1d1d",
        ).pack()

        self.password.bind("<Return>", lambda _event: self.login())
        self.password.focus_set()

    def login(self):
        admin = self.db.authenticate_admin(
            self.username.get().strip(), self.password.get()
        )
        if not admin:
            messagebox.showerror("Login failed", "Invalid username or password.")
            self.db.add_audit(
                self.username.get().strip() or "unknown",
                "LOGIN_FAILED",
                "Invalid administrator login.",
            )
            return

        self.db.add_audit(admin["username"], "LOGIN_SUCCESS", "Administrator signed in.")
        self.result = admin
        self.root.destroy()


class SecurityApp:
    def __init__(self, root: tk.Tk, db: Database, admin: Dict[str, Any]):
        self.root = root
        self.db = db
        self.admin = admin
        self.report_service = ReportService(db)
        self.face_engine: Optional[FaceEngine] = None

        root.title(APP_TITLE)
        root.geometry(WINDOW_SIZE)
        root.minsize(1050, 650)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._configure_style()
        self._build_layout()
        self.refresh_all()

        if admin.get("must_change_password"):
            root.after(
                600,
                lambda: messagebox.showwarning(
                    "Security notice",
                    "You are using the default administrator password. "
                    "Open Settings and change it now.",
                ),
            )

    def _configure_style(self):
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Heading.TLabel", font=("Segoe UI", 13, "bold"))
        style.configure("CardValue.TLabel", font=("Segoe UI", 25, "bold"))
        style.configure("CardTitle.TLabel", font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_layout(self):
        top = ttk.Frame(self.root, padding=(18, 12))
        top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, style="Title.TLabel").pack(side="left")
        ttk.Label(
            top,
            text=f'Administrator: {self.admin["full_name"]}',
        ).pack(side="right")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.dashboard_tab = ttk.Frame(self.notebook, padding=16)
        self.register_tab = ttk.Frame(self.notebook, padding=16)
        self.people_tab = ttk.Frame(self.notebook, padding=16)
        self.recognition_tab = ttk.Frame(self.notebook, padding=16)
        self.attendance_tab = ttk.Frame(self.notebook, padding=16)
        self.unknown_tab = ttk.Frame(self.notebook, padding=16)
        self.settings_tab = ttk.Frame(self.notebook, padding=16)

        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.register_tab, text="Register Person")
        self.notebook.add(self.people_tab, text="People")
        self.notebook.add(self.recognition_tab, text="Live Recognition")
        self.notebook.add(self.attendance_tab, text="Attendance")
        self.notebook.add(self.unknown_tab, text="Unknown Events")
        self.notebook.add(self.settings_tab, text="Settings")

        self._build_dashboard()
        self._build_registration()
        self._build_people()
        self._build_recognition()
        self._build_attendance()
        self._build_unknown()
        self._build_settings()

        status_frame = ttk.Frame(self.root, padding=(16, 4, 16, 8))
        status_frame.pack(fill="x")
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left")
        ttk.Button(status_frame, text="Refresh All", command=self.refresh_all).pack(
            side="right"
        )

    def _build_dashboard(self):
        ttk.Label(
            self.dashboard_tab,
            text="System Overview",
            style="Heading.TLabel",
        ).pack(anchor="w", pady=(0, 14))

        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill="x")
        self.card_vars = {
            "active_people": tk.StringVar(value="0"),
            "today_events": tk.StringVar(value="0"),
            "unreviewed_unknown": tk.StringVar(value="0"),
            "face_samples": tk.StringVar(value="0"),
        }
        card_info = [
            ("Active People", "active_people"),
            ("Today's Access Events", "today_events"),
            ("Unreviewed Unknown", "unreviewed_unknown"),
            ("Face Samples", "face_samples"),
        ]
        for i, (title, key) in enumerate(card_info):
            card = ttk.LabelFrame(cards, text="", padding=20)
            card.grid(row=0, column=i, sticky="nsew", padx=6)
            cards.columnconfigure(i, weight=1)
            ttk.Label(card, text=title, style="CardTitle.TLabel").pack()
            ttk.Label(
                card,
                textvariable=self.card_vars[key],
                style="CardValue.TLabel",
            ).pack(pady=(10, 0))

        actions = ttk.LabelFrame(
            self.dashboard_tab,
            text="Quick Actions",
            padding=18,
        )
        actions.pack(fill="x", pady=22)

        ttk.Button(
            actions,
            text="Open Registration",
            command=lambda: self.notebook.select(self.register_tab),
        ).pack(side="left", padx=5)
        ttk.Button(
            actions,
            text="Train Recognition Model",
            command=self.train_model_async,
        ).pack(side="left", padx=5)
        ttk.Button(
            actions,
            text="Start Check-In Camera",
            command=lambda: self.start_recognition_async("IN"),
        ).pack(side="left", padx=5)
        ttk.Button(
            actions,
            text="Start Check-Out Camera",
            command=lambda: self.start_recognition_async("OUT"),
        ).pack(side="left", padx=5)
        ttk.Button(
            actions,
            text="Backup Database",
            command=self.backup_database,
        ).pack(side="left", padx=5)

        note = (
            "Recognition is a security aid, not a complete physical-access solution. "
            "For production, add liveness detection, badge/OTP verification, encrypted "
            "storage, access-controller integration, consent policies, and human review."
        )
        ttk.Label(
            self.dashboard_tab,
            text=note,
            wraplength=950,
            foreground="#6b3b00",
        ).pack(anchor="w", pady=10)

    def _build_registration(self):
        ttk.Label(
            self.register_tab,
            text="Register an Authorized Person",
            style="Heading.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        labels = ["Person Code *", "Full Name *", "Department", "Phone", "Notes"]
        self.reg_entries = {}
        for row, label in enumerate(labels, start=1):
            ttk.Label(self.register_tab, text=label).grid(
                row=row, column=0, sticky="nw", padx=(0, 12), pady=8
            )
            if label == "Notes":
                widget = tk.Text(self.register_tab, width=56, height=5)
            else:
                widget = ttk.Entry(self.register_tab, width=58)
            widget.grid(row=row, column=1, sticky="ew", pady=8)
            self.reg_entries[label] = widget

        self.register_tab.columnconfigure(1, weight=1)

        self.capture_progress = tk.StringVar(
            value=f"Camera will capture {CAPTURE_SAMPLES} face samples."
        )
        ttk.Label(
            self.register_tab,
            textvariable=self.capture_progress,
        ).grid(row=6, column=1, sticky="w", pady=(12, 5))

        buttons = ttk.Frame(self.register_tab)
        buttons.grid(row=7, column=1, sticky="w", pady=12)
        ttk.Button(
            buttons,
            text="Save Person and Capture Face",
            command=self.register_person_async,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Clear Form", command=self.clear_registration).pack(
            side="left"
        )

        help_text = (
            "Use a unique code such as EMP-001. During capture, keep one person in "
            "front of the camera, look left/right slightly, and maintain good lighting."
        )
        ttk.Label(
            self.register_tab,
            text=help_text,
            wraplength=850,
            foreground="#444444",
        ).grid(row=8, column=1, sticky="w", pady=8)

    def _build_people(self):
        controls = ttk.Frame(self.people_tab)
        controls.pack(fill="x", pady=(0, 10))
        self.people_search = tk.StringVar()
        ttk.Label(controls, text="Search").pack(side="left")
        ttk.Entry(
            controls,
            textvariable=self.people_search,
            width=35,
        ).pack(side="left", padx=8)
        ttk.Button(controls, text="Search", command=self.refresh_people).pack(side="left")
        ttk.Button(controls, text="Edit", command=self.edit_selected_person).pack(
            side="right", padx=4
        )
        ttk.Button(
            controls,
            text="Delete",
            command=self.delete_selected_person,
        ).pack(side="right", padx=4)

        columns = (
            "id",
            "code",
            "name",
            "department",
            "phone",
            "active",
            "samples",
            "created",
        )
        self.people_tree = ttk.Treeview(
            self.people_tab,
            columns=columns,
            show="headings",
        )
        headings = {
            "id": "ID",
            "code": "Code",
            "name": "Full Name",
            "department": "Department",
            "phone": "Phone",
            "active": "Active",
            "samples": "Samples",
            "created": "Created",
        }
        widths = {
            "id": 45,
            "code": 90,
            "name": 190,
            "department": 140,
            "phone": 120,
            "active": 60,
            "samples": 70,
            "created": 145,
        }
        for col in columns:
            self.people_tree.heading(col, text=headings[col])
            self.people_tree.column(col, width=widths[col], anchor="center")
        self.people_tree.column("name", anchor="w")
        self.people_tree.column("department", anchor="w")
        self.people_tree.pack(fill="both", expand=True)

    def _build_recognition(self):
        ttk.Label(
            self.recognition_tab,
            text="Live Access Recognition",
            style="Heading.TLabel",
        ).pack(anchor="w")

        box = ttk.LabelFrame(
            self.recognition_tab,
            text="Recognition Session",
            padding=20,
        )
        box.pack(fill="x", pady=18)

        ttk.Label(box, text="Access event mode").grid(row=0, column=0, sticky="w")
        self.recognition_mode = tk.StringVar(value="IN")
        ttk.Combobox(
            box,
            textvariable=self.recognition_mode,
            values=["IN", "OUT"],
            state="readonly",
            width=15,
        ).grid(row=0, column=1, padx=12, sticky="w")

        ttk.Button(
            box,
            text="Start Camera",
            command=lambda: self.start_recognition_async(self.recognition_mode.get()),
        ).grid(row=1, column=0, pady=20, sticky="w")
        ttk.Button(
            box,
            text="Train / Refresh Model",
            command=self.train_model_async,
        ).grid(row=1, column=1, pady=20, padx=12, sticky="w")

        instructions = (
            "The OpenCV camera window will open. Recognized people are shown in green; "
            "unknown people are shown in red and captured periodically. Press Q inside "
            "the camera window to stop. The percentage shown is an approximate display "
            "derived from LBPH distance, not a biometric probability."
        )
        ttk.Label(
            self.recognition_tab,
            text=instructions,
            wraplength=900,
        ).pack(anchor="w")

    def _build_attendance(self):
        controls = ttk.Frame(self.attendance_tab)
        controls.pack(fill="x", pady=(0, 10))

        ttk.Label(controls, text="From (YYYY-MM-DD)").pack(side="left")
        self.date_from = ttk.Entry(controls, width=13)
        self.date_from.pack(side="left", padx=(5, 10))
        ttk.Label(controls, text="To").pack(side="left")
        self.date_to = ttk.Entry(controls, width=13)
        self.date_to.pack(side="left", padx=(5, 10))
        ttk.Button(
            controls,
            text="Filter",
            command=self.refresh_attendance,
        ).pack(side="left")
        ttk.Button(
            controls,
            text="Export CSV",
            command=self.export_attendance,
        ).pack(side="right")

        columns = ("id", "code", "name", "department", "type", "confidence", "time")
        self.attendance_tree = ttk.Treeview(
            self.attendance_tab,
            columns=columns,
            show="headings",
        )
        headings = {
            "id": "ID",
            "code": "Code",
            "name": "Name",
            "department": "Department",
            "type": "Event",
            "confidence": "Approx. Match",
            "time": "Date and Time",
        }
        widths = {
            "id": 50,
            "code": 95,
            "name": 190,
            "department": 150,
            "type": 70,
            "confidence": 110,
            "time": 160,
        }
        for col in columns:
            self.attendance_tree.heading(col, text=headings[col])
            self.attendance_tree.column(col, width=widths[col], anchor="center")
        self.attendance_tree.column("name", anchor="w")
        self.attendance_tree.column("department", anchor="w")
        self.attendance_tree.pack(fill="both", expand=True)

    def _build_unknown(self):
        controls = ttk.Frame(self.unknown_tab)
        controls.pack(fill="x", pady=(0, 10))

        ttk.Button(
            controls,
            text="Mark Selected Reviewed",
            command=self.review_selected_unknown,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls,
            text="Delete Selected",
            command=self.delete_selected_unknown,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls,
            text="Delete All",
            command=self.delete_all_unknown,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls,
            text="Export CSV",
            command=self.export_unknown,
        ).pack(side="right")

        columns = ("id", "camera", "image", "reviewed", "time")
        self.unknown_tree = ttk.Treeview(
            self.unknown_tab,
            columns=columns,
            show="headings",
            selectmode="extended",
        )

        headings = {
            "id": "ID",
            "camera": "Camera",
            "image": "Captured Image",
            "reviewed": "Reviewed",
            "time": "Date and Time",
        }

        widths = {
            "id": 55,
            "camera": 100,
            "image": 520,
            "reviewed": 90,
            "time": 170,
        }

        for col in columns:
            self.unknown_tree.heading(col, text=headings[col])
            self.unknown_tree.column(col, width=widths[col], anchor="center")

        self.unknown_tree.column("image", anchor="w")
        self.unknown_tree.pack(fill="both", expand=True)
        self.unknown_tree.bind("<Double-1>", self.open_unknown_image)

    def _build_settings(self):
        ttk.Label(
            self.settings_tab,
            text="Administrator and System Settings",
            style="Heading.TLabel",
        ).pack(anchor="w")

        password_box = ttk.LabelFrame(
            self.settings_tab,
            text="Change Administrator Password",
            padding=18,
        )
        password_box.pack(fill="x", pady=18)

        self.current_password = ttk.Entry(password_box, show="*", width=35)
        self.new_password = ttk.Entry(password_box, show="*", width=35)
        self.confirm_password = ttk.Entry(password_box, show="*", width=35)

        ttk.Label(password_box, text="Current password").grid(row=0, column=0, sticky="w", pady=6)
        self.current_password.grid(row=0, column=1, padx=12, pady=6)
        ttk.Label(password_box, text="New password").grid(row=1, column=0, sticky="w", pady=6)
        self.new_password.grid(row=1, column=1, padx=12, pady=6)
        ttk.Label(password_box, text="Confirm new password").grid(row=2, column=0, sticky="w", pady=6)
        self.confirm_password.grid(row=2, column=1, padx=12, pady=6)

        ttk.Button(
            password_box,
            text="Change Password",
            command=self.change_password,
        ).grid(row=3, column=1, sticky="w", padx=12, pady=12)

        maintenance = ttk.LabelFrame(
            self.settings_tab,
            text="Maintenance",
            padding=18,
        )
        maintenance.pack(fill="x")
        ttk.Button(
            maintenance,
            text="Create Database Backup",
            command=self.backup_database,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            maintenance,
            text="Train Recognition Model",
            command=self.train_model_async,
        ).pack(side="left")

        email_help = (
            "Optional email alerts are configured with environment variables: "
            "FRS_SMTP_HOST, FRS_SMTP_PORT, FRS_SMTP_USER, FRS_SMTP_PASSWORD, "
            "FRS_ALERT_TO and FRS_SMTP_USE_TLS."
        )
        ttk.Label(
            self.settings_tab,
            text=email_help,
            wraplength=900,
            foreground="#444444",
        ).pack(anchor="w", pady=18)

    def get_face_engine(self) -> FaceEngine:
        if self.face_engine is None:
            self.face_engine = FaceEngine(self.db)
        return self.face_engine

    def set_status(self, message: str):
        self.root.after(0, lambda: self.status_var.set(message))

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_people()
        self.refresh_attendance()
        self.refresh_unknown()

    def refresh_dashboard(self):
        counts = self.db.dashboard_counts()
        for key, value in counts.items():
            self.card_vars[key].set(str(value))

    def refresh_people(self):
        for item in self.people_tree.get_children():
            self.people_tree.delete(item)
        for person in self.db.list_persons(self.people_search.get()):
            self.people_tree.insert(
                "",
                "end",
                values=(
                    person["id"],
                    person["person_code"],
                    person["full_name"],
                    person["department"],
                    person["phone"],
                    "Yes" if person["active"] else "No",
                    person["sample_count"],
                    person["created_at"],
                ),
            )

    def refresh_attendance(self):
        for item in self.attendance_tree.get_children():
            self.attendance_tree.delete(item)
        rows = self.db.list_attendance(
            self.date_from.get().strip(),
            self.date_to.get().strip(),
        )
        for row in rows:
            self.attendance_tree.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["person_code"],
                    row["full_name"],
                    row["department"],
                    row["event_type"],
                    f'{row["confidence"]:.1f}%',
                    row["event_time"],
                ),
            )

    def refresh_unknown(self):
        for item in self.unknown_tree.get_children():
            self.unknown_tree.delete(item)
        for row in self.db.list_unknown_events():
            self.unknown_tree.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["camera_name"],
                    row["image_path"],
                    "Yes" if row["reviewed"] else "No",
                    row["event_time"],
                ),
            )

    def clear_registration(self):
        for label, widget in self.reg_entries.items():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", "end")
            else:
                widget.delete(0, "end")
        self.capture_progress.set(
            f"Camera will capture {CAPTURE_SAMPLES} face samples."
        )

    def register_person_async(self):
        code = self.reg_entries["Person Code *"].get().strip()
        name = self.reg_entries["Full Name *"].get().strip()
        department = self.reg_entries["Department"].get().strip()
        phone = self.reg_entries["Phone"].get().strip()
        notes = self.reg_entries["Notes"].get("1.0", "end").strip()

        if not code or not name:
            messagebox.showwarning("Required fields", "Person code and full name are required.")
            return

        def task():
            person_id = None
            try:
                person_id = self.db.add_person(code, name, department, phone, notes)
                self.db.add_audit(
                    self.admin["username"],
                    "ADD_PERSON",
                    f"Created person {code} - {name}.",
                )
                engine = self.get_face_engine()

                def progress(current: int, total: int):
                    self.root.after(
                        0,
                        lambda: self.capture_progress.set(
                            f"Captured {current}/{total} samples."
                        ),
                    )

                captured = engine.capture_samples(
                    person_id, name, CAPTURE_SAMPLES, progress
                )
                if captured < 10:
                    raise FaceEngineError(
                        "Too few samples were captured. At least 10 are required."
                    )

                trained = engine.train_model()
                self.db.add_audit(
                    self.admin["username"],
                    "TRAIN_MODEL",
                    f"Model trained with {trained} samples.",
                )
                self.root.after(0, self.clear_registration)
                self.root.after(0, self.refresh_all)
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Registration completed",
                        f"{name} was registered with {captured} face samples.",
                    ),
                )
            except sqlite3.IntegrityError:
                if person_id:
                    self.db.delete_person(person_id)
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Duplicate code",
                        "The person code is already registered.",
                    ),
                )
            except Exception as exc:
                if person_id:
                    try:
                        self.db.delete_person(person_id)
                    except Exception:
                        pass
                self.root.after(
                    0,
                    lambda exc=exc: messagebox.showerror("Registration failed", str(exc)),
                )
            finally:
                self.set_status("Ready.")

        self.set_status("Registering person and capturing face samples...")
        threading.Thread(target=task, daemon=True).start()

    def train_model_async(self):
        def task():
            try:
                count = self.get_face_engine().train_model()
                self.db.add_audit(
                    self.admin["username"],
                    "TRAIN_MODEL",
                    f"Model trained with {count} samples.",
                )
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Training completed",
                        f"Recognition model trained with {count} samples.",
                    ),
                )
            except Exception as exc:
                self.root.after(
                    0,
                    lambda exc=exc: messagebox.showerror("Training failed", str(exc)),
                )
            finally:
                self.set_status("Ready.")

        self.set_status("Training recognition model...")
        threading.Thread(target=task, daemon=True).start()

    def start_recognition_async(self, mode: str):
        def task():
            try:
                summary = self.get_face_engine().run_recognition(
                    mode=mode,
                    status_callback=self.set_status,
                )
                self.root.after(0, self.refresh_all)
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Recognition stopped",
                        f'Attendance events saved: {summary["attendance"]}\n'
                        f'Unknown detections: {summary["unknown"]}',
                    ),
                )
            except Exception as exc:
                self.root.after(
                    0,
                    lambda exc=exc: messagebox.showerror("Recognition error", str(exc)),
                )
            finally:
                self.set_status("Ready.")

        self.set_status(f"Starting camera in {mode} mode...")
        threading.Thread(target=task, daemon=True).start()

    def _selected_person_id(self) -> Optional[int]:
        selected = self.people_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a person first.")
            return None
        values = self.people_tree.item(selected[0], "values")
        return int(values[0])

    def edit_selected_person(self):
        person_id = self._selected_person_id()
        if person_id is None:
            return
        person = self.db.get_person(person_id)
        if not person:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Person")
        dialog.geometry("520x500")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)

        entries = {}
        fields = [
            ("Person Code", person["person_code"]),
            ("Full Name", person["full_name"]),
            ("Department", person["department"] or ""),
            ("Phone", person["phone"] or ""),
        ]
        for row, (label, value) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=7)
            entry = ttk.Entry(frame, width=42)
            entry.insert(0, value)
            entry.grid(row=row, column=1, padx=10, pady=7)
            entries[label] = entry

        ttk.Label(frame, text="Notes").grid(row=4, column=0, sticky="nw", pady=7)
        notes = tk.Text(frame, width=42, height=7)
        notes.insert("1.0", person["notes"] or "")
        notes.grid(row=4, column=1, padx=10, pady=7)

        active_var = tk.IntVar(value=int(person["active"]))
        ttk.Checkbutton(
            frame,
            text="Active and authorized",
            variable=active_var,
        ).grid(row=5, column=1, sticky="w", padx=10, pady=7)

        def save():
            try:
                self.db.update_person(
                    person_id,
                    entries["Person Code"].get(),
                    entries["Full Name"].get(),
                    entries["Department"].get(),
                    entries["Phone"].get(),
                    notes.get("1.0", "end").strip(),
                    active_var.get(),
                )
                self.db.add_audit(
                    self.admin["username"],
                    "UPDATE_PERSON",
                    f"Updated person ID {person_id}.",
                )
                dialog.destroy()
                self.refresh_all()
                messagebox.showinfo("Updated", "Person information was updated.")
            except sqlite3.IntegrityError:
                messagebox.showerror("Duplicate code", "The person code already exists.")
            except Exception as exc:
                messagebox.showerror("Update failed", str(exc))

        ttk.Button(frame, text="Save Changes", command=save).grid(
            row=6, column=1, sticky="w", padx=10, pady=15
        )

    def delete_selected_person(self):
        person_id = self._selected_person_id()
        if person_id is None:
            return
        person = self.db.get_person(person_id)
        if not person:
            return
        if not messagebox.askyesno(
            "Delete person",
            f'Delete {person["full_name"]} and all related records?',
        ):
            return
        self.db.delete_person(person_id)
        self.db.add_audit(
            self.admin["username"],
            "DELETE_PERSON",
            f'Deleted person ID {person_id}: {person["full_name"]}.',
        )
        self.refresh_all()

    def export_attendance(self):
        path = filedialog.asksaveasfilename(
            title="Save attendance report",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="attendance_report.csv",
        )
        if not path:
            return
        output = self.report_service.export_attendance_csv(
            self.date_from.get().strip(),
            self.date_to.get().strip(),
            path,
        )
        messagebox.showinfo("Report exported", f"Saved to:\n{output}")

    def export_unknown(self):
        path = filedialog.asksaveasfilename(
            title="Save unknown events report",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="unknown_events.csv",
        )
        if not path:
            return
        output = self.report_service.export_unknown_csv(path)
        messagebox.showinfo("Report exported", f"Saved to:\n{output}")

    def review_selected_unknown(self):
        selected = self.unknown_tree.selection()
        if not selected:
            messagebox.showwarning(
                "No selection",
                "Select one or more unknown events first.",
            )
            return

        for item in selected:
            values = self.unknown_tree.item(item, "values")
            self.db.mark_unknown_reviewed(int(values[0]), 1)

        self.db.add_audit(
            self.admin["username"],
            "REVIEW_UNKNOWN",
            f"Reviewed {len(selected)} unknown event(s).",
        )
        self.refresh_unknown()
        self.refresh_dashboard()

    def delete_selected_unknown(self):
        selected_items = self.unknown_tree.selection()
        if not selected_items:
            messagebox.showwarning(
                "No selection",
                "Select one or more unknown events first.",
            )
            return

        confirm = messagebox.askyesno(
            "Delete selected events",
            "Delete the selected records and their captured images?",
        )
        if not confirm:
            return

        deleted_records = 0
        deleted_images = 0
        errors = []

        for item in selected_items:
            values = self.unknown_tree.item(item, "values")
            event_id = int(values[0])

            try:
                image_path = self.db.delete_unknown_event(event_id)

                if image_path:
                    image_file = Path(image_path)
                    if image_file.exists() and image_file.is_file():
                        image_file.unlink()
                        deleted_images += 1

                deleted_records += 1

            except Exception as exc:
                errors.append(f"Event ID {event_id}: {exc}")

        self.db.add_audit(
            self.admin["username"],
            "DELETE_UNKNOWN_EVENTS",
            (
                f"Deleted {deleted_records} record(s) "
                f"and {deleted_images} image(s)."
            ),
        )

        self.refresh_unknown()
        self.refresh_dashboard()

        if deleted_records:
            messagebox.showinfo(
                "Delete completed",
                (
                    f"Deleted records: {deleted_records}\n"
                    f"Deleted images: {deleted_images}"
                ),
            )

        if errors:
            messagebox.showerror(
                "Some records were not deleted",
                "\n".join(errors),
            )

    def delete_all_unknown(self):
        unknown_events = self.db.list_unknown_events(limit=100000)
        if not unknown_events:
            messagebox.showinfo(
                "No records",
                "There are no unknown events to delete.",
            )
            return

        confirm = messagebox.askyesno(
            "Delete all unknown events",
            (
                "This will permanently delete all unknown-person "
                "records and captured images.\n\nContinue?"
            ),
        )
        if not confirm:
            return

        try:
            image_paths = self.db.delete_all_unknown_events()
            deleted_images = 0

            for image_path in image_paths:
                try:
                    image_file = Path(image_path)
                    if image_file.exists() and image_file.is_file():
                        image_file.unlink()
                        deleted_images += 1
                except OSError:
                    pass

            self.db.add_audit(
                self.admin["username"],
                "DELETE_ALL_UNKNOWN_EVENTS",
                (
                    f"Deleted {len(unknown_events)} records "
                    f"and {deleted_images} captured images."
                ),
            )

            self.refresh_unknown()
            self.refresh_dashboard()

            messagebox.showinfo(
                "Delete completed",
                (
                    f"Deleted records: {len(unknown_events)}\n"
                    f"Deleted images: {deleted_images}"
                ),
            )

        except Exception as exc:
            messagebox.showerror("Delete failed", str(exc))

    def open_unknown_image(self, _event=None):
        selected = self.unknown_tree.selection()
        if not selected:
            return
        values = self.unknown_tree.item(selected[0], "values")
        path = Path(values[2])
        if not path.exists():
            messagebox.showerror("Missing image", "The captured image no longer exists.")
            return
        try:
            import os
            os.startfile(path)  # Windows
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", str(path)])

    def change_password(self):
        current = self.current_password.get()
        new = self.new_password.get()
        confirm = self.confirm_password.get()

        if new != confirm:
            messagebox.showerror("Password mismatch", "New passwords do not match.")
            return
        if len(new) < 8:
            messagebox.showerror(
                "Weak password",
                "Use at least 8 characters with mixed character types.",
            )
            return
        if not self.db.authenticate_admin(self.admin["username"], current):
            messagebox.showerror("Incorrect password", "Current password is incorrect.")
            return

        try:
            self.db.change_admin_password(self.admin["username"], new)
            self.current_password.delete(0, "end")
            self.new_password.delete(0, "end")
            self.confirm_password.delete(0, "end")
            self.admin["must_change_password"] = 0
            messagebox.showinfo("Password changed", "Administrator password was changed.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def backup_database(self):
        try:
            path = create_database_backup()
            self.db.add_audit(
                self.admin["username"],
                "DATABASE_BACKUP",
                f"Backup created at {path}.",
            )
            messagebox.showinfo("Backup completed", f"Backup saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Backup failed", str(exc))

    def on_close(self):
        try:
            self.db.add_audit(
                self.admin["username"],
                "LOGOUT",
                "Application closed.",
            )
        finally:
            self.root.destroy()