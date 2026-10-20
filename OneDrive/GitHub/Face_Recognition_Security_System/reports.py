import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from config import REPORTS_DIR
from database import Database


class ReportService:
    def __init__(self, db: Database):
        self.db = db
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def export_attendance_csv(
        self,
        date_from: str = "",
        date_to: str = "",
        output_path: str = "",
    ) -> Path:
        rows = self.db.list_attendance(date_from, date_to, limit=100000)
        if output_path:
            path = Path(output_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = REPORTS_DIR / f"attendance_{timestamp}.csv"

        path.parent.mkdir(parents=True, exist_ok=True)
        headers = [
            "event_id",
            "person_code",
            "full_name",
            "department",
            "event_type",
            "confidence_percent",
            "event_time",
        ]
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "event_id": row["id"],
                        "person_code": row["person_code"],
                        "full_name": row["full_name"],
                        "department": row["department"],
                        "event_type": row["event_type"],
                        "confidence_percent": f'{row["confidence"]:.2f}',
                        "event_time": row["event_time"],
                    }
                )
        return path

    def export_unknown_csv(self, output_path: str = "") -> Path:
        rows = self.db.list_unknown_events(limit=100000)
        if output_path:
            path = Path(output_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = REPORTS_DIR / f"unknown_events_{timestamp}.csv"

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["event_id", "camera_name", "image_path", "reviewed", "event_time"])
            for row in rows:
                writer.writerow(
                    [
                        row["id"],
                        row["camera_name"],
                        row["image_path"],
                        row["reviewed"],
                        row["event_time"],
                    ]
                )
        return path
