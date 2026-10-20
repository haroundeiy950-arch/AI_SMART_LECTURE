from datetime import datetime
from typing import List

from database import DatabaseManager


class MeetingAssistant:
    def __init__(self):
        self.db = DatabaseManager()
        self.current_title = None
        self.participants = []
        self.transcript_lines = []

    def start_meeting(self, title: str, participants: List[str]):
        self.current_title = title
        self.participants = participants
        self.transcript_lines = []

        print(f"Meeting started: {title}")
        print("Participants:", ", ".join(participants))

    def add_note(self, note: str):
        if not note:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {note}"
        self.transcript_lines.append(line)
        print(line)

    def simple_summary(self, text: str, max_points: int = 5) -> str:
        if not text.strip():
            return "No meeting notes to summarize."

        sentences = text.replace("\n", " ").split(".")
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return text[:300]

        selected = sentences[:max_points]

        summary_lines = []

        for index, sentence in enumerate(selected, start=1):
            summary_lines.append(f"{index}. {sentence}")

        return "\n".join(summary_lines)

    def end_meeting(self):
        if not self.current_title:
            print("No meeting is running.")
            return

        transcript = "\n".join(self.transcript_lines)
        summary = self.simple_summary(transcript)

        self.db.add_meeting(
            title=self.current_title,
            participants=self.participants,
            transcript=transcript,
            summary=summary
        )

        print("Meeting saved.")
        print("Summary:")
        print(summary)

        self.current_title = None
        self.participants = []
        self.transcript_lines = []

    def list_meetings(self):
        meetings = self.db.list_meetings()

        if not meetings:
            print("No meetings found.")
            return

        for meeting in meetings:
            print("-" * 50)
            print(f"ID: {meeting['id']}")
            print(f"Title: {meeting['title']}")
            print(f"Date: {meeting['created_at']}")
            print("Summary:")
            print(meeting["summary"])
