import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from config import DATABASE_PATH
from security import hash_password, verify_password


class Database:
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            must_change_password INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            department TEXT,
            phone TEXT,
            notes TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS face_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            event_type TEXT NOT NULL CHECK(event_type IN ('IN','OUT')),
            confidence REAL,
            captured_image TEXT,
            event_time TEXT NOT NULL,
            FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS unknown_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            camera_name TEXT NOT NULL DEFAULT 'Camera 1',
            event_time TEXT NOT NULL,
            reviewed INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_attendance_time ON attendance(event_time);
        CREATE INDEX IF NOT EXISTS idx_attendance_person ON attendance(person_id);
        CREATE INDEX IF NOT EXISTS idx_unknown_time ON unknown_events(event_time);
        """
        with self.connect() as conn:
            conn.executescript(schema)
            existing = conn.execute(
                "SELECT id FROM admins WHERE username = ?", ("admin",)
            ).fetchone()
            if not existing:
                salt, digest = hash_password("Admin@123")
                conn.execute(
                    """
                    INSERT INTO admins
                    (username, password_salt, password_hash, full_name,
                    must_change_password, created_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (
                        "admin",
                        salt,
                        digest,
                        "System Administrator",
                        self.now(),
                    ),
                )

    @staticmethod
    def now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---------- Admin ----------
    def authenticate_admin(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM admins WHERE username = ?", (username.strip(),)
            ).fetchone()
            if not row:
                return None
            if not verify_password(password, row["password_salt"], row["password_hash"]):
                return None
            return dict(row)

    def change_admin_password(self, username: str, new_password: str) -> None:
        salt, digest = hash_password(new_password)
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE admins
                SET password_salt = ?, password_hash = ?, must_change_password = 0
                WHERE username = ?
                """,
                (salt, digest, username),
            )
        self.add_audit(username, "CHANGE_PASSWORD", "Administrator password changed.")

    # ---------- Persons ----------
    def add_person(
        self,
        person_code: str,
        full_name: str,
        department: str = "",
        phone: str = "",
        notes: str = "",
    ) -> int:
        now = self.now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO persons
                (person_code, full_name, department, phone, notes, active,
                created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    person_code.strip(),
                    full_name.strip(),
                    department.strip(),
                    phone.strip(),
                    notes.strip(),
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def update_person(
        self,
        person_id: int,
        person_code: str,
        full_name: str,
        department: str,
        phone: str,
        notes: str,
        active: int,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE persons
                SET person_code = ?, full_name = ?, department = ?, phone = ?,
                    notes = ?, active = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    person_code.strip(),
                    full_name.strip(),
                    department.strip(),
                    phone.strip(),
                    notes.strip(),
                    int(active),
                    self.now(),
                    person_id,
                ),
            )

    def delete_person(self, person_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM persons WHERE id = ?", (person_id,))

    def get_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM persons WHERE id = ?", (person_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_persons(self, search: str = "") -> List[Dict[str, Any]]:
        query = """
            SELECT p.*,
                (SELECT COUNT(*) FROM face_samples f WHERE f.person_id = p.id)
                AS sample_count
            FROM persons p
        """
        params: tuple = ()
        if search.strip():
            like = f"%{search.strip()}%"
            query += """
                WHERE p.person_code LIKE ? OR p.full_name LIKE ?
                OR p.department LIKE ? OR p.phone LIKE ?
            """
            params = (like, like, like, like)
        query += " ORDER BY p.full_name"
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def add_face_sample(self, person_id: int, image_path: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO face_samples (person_id, image_path, created_at)
                VALUES (?, ?, ?)
                """,
                (person_id, image_path, self.now()),
            )

    def list_face_samples(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT f.id, f.person_id, f.image_path, p.active
                FROM face_samples f
                JOIN persons p ON p.id = f.person_id
                WHERE p.active = 1
                ORDER BY f.person_id, f.id
                """
            ).fetchall()
            return [dict(r) for r in rows]

    # ---------- Attendance ----------
    def add_attendance(
        self,
        person_id: int,
        event_type: str,
        confidence: float,
        captured_image: str = "",
    ) -> int:
        event_type = event_type.upper()
        if event_type not in {"IN", "OUT"}:
            raise ValueError("event_type must be IN or OUT")
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO attendance
                (person_id, event_type, confidence, captured_image, event_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    person_id,
                    event_type,
                    float(confidence),
                    captured_image,
                    self.now(),
                ),
            )
            return int(cur.lastrowid)

    def list_attendance(
        self,
        date_from: str = "",
        date_to: str = "",
        search: str = "",
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT a.id, a.person_id, p.person_code, p.full_name, p.department,
                a.event_type, a.confidence, a.captured_image, a.event_time
            FROM attendance a
            JOIN persons p ON p.id = a.person_id
            WHERE 1 = 1
        """
        params: List[Any] = []
        if date_from:
            query += " AND date(a.event_time) >= date(?)"
            params.append(date_from)
        if date_to:
            query += " AND date(a.event_time) <= date(?)"
            params.append(date_to)
        if search.strip():
            like = f"%{search.strip()}%"
            query += " AND (p.person_code LIKE ? OR p.full_name LIKE ?)"
            params.extend([like, like])
        query += " ORDER BY a.event_time DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def last_attendance_for_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM attendance
                WHERE person_id = ?
                ORDER BY event_time DESC
                LIMIT 1
                """,
                (person_id,),
            ).fetchone()
            return dict(row) if row else None

    # ---------- Unknown events ----------
    def add_unknown_event(self, image_path: str, camera_name: str = "Camera 1") -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO unknown_events
                (image_path, camera_name, event_time, reviewed)
                VALUES (?, ?, ?, 0)
                """,
                (image_path, camera_name, self.now()),
            )
            return int(cur.lastrowid)

    def list_unknown_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM unknown_events
                ORDER BY event_time DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_unknown_reviewed(self, event_id: int, reviewed: int = 1) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE unknown_events SET reviewed = ? WHERE id = ?",
                (int(reviewed), event_id),
            )


    def delete_unknown_event(self, event_id: int) -> Optional[str]:
        """Delete one unknown event and return its image path."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT image_path FROM unknown_events WHERE id = ?",
                (event_id,),
            ).fetchone()

            if not row:
                return None

            image_path = row["image_path"]
            conn.execute(
                "DELETE FROM unknown_events WHERE id = ?",
                (event_id,),
            )
            return image_path

    def delete_all_unknown_events(self) -> List[str]:
        """Delete all unknown events and return their image paths."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT image_path FROM unknown_events"
            ).fetchall()

            image_paths = [
                row["image_path"]
                for row in rows
                if row["image_path"]
            ]

            conn.execute("DELETE FROM unknown_events")
            return image_paths

    # ---------- Dashboard ----------
    def dashboard_counts(self) -> Dict[str, int]:
        today = datetime.now().strftime("%Y-%m-%d")
        with self.connect() as conn:
            people = conn.execute(
                "SELECT COUNT(*) FROM persons WHERE active = 1"
            ).fetchone()[0]
            events = conn.execute(
                "SELECT COUNT(*) FROM attendance WHERE date(event_time) = date(?)",
                (today,),
            ).fetchone()[0]
            unknown = conn.execute(
                """
                SELECT COUNT(*) FROM unknown_events
                WHERE date(event_time) = date(?) AND reviewed = 0
                """,
                (today,),
            ).fetchone()[0]
            samples = conn.execute(
                "SELECT COUNT(*) FROM face_samples"
            ).fetchone()[0]
        return {
            "active_people": int(people),
            "today_events": int(events),
            "unreviewed_unknown": int(unknown),
            "face_samples": int(samples),
        }

    # ---------- Audit ----------
    def add_audit(self, admin_username: str, action: str, details: str = "") -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs
                (admin_username, action, details, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (admin_username, action, details, self.now()),
            )

    def list_audit_logs(self, limit: int = 300) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM audit_logs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]