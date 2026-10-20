from translator import TranslatorSystem
from speech import SpeechSystem
from meeting_assistant import MeetingAssistant
from security import SecuritySystem


class SmartAssistant:
    def __init__(self):
        self.translator = TranslatorSystem()
        self.speech = SpeechSystem()
        self.meeting = MeetingAssistant()
        self.security = SecuritySystem()

    def help_text(self) -> str:
        return """
Available commands:
- help
- translate en ar your text
- translate ar en your text
- voice-translate
- speak your text
- privacy
- note your meeting note
- exit
"""

    def handle_command(self, command: str) -> bool:
        command = command.strip()

        if not command:
            return True

        if command.lower() == "help":
            print(self.help_text())
            return True

        if command.lower() == "privacy":
            print(self.security.privacy_warning())
            return True

        if command.lower() == "voice-translate":
            from live_voice_translator import LiveVoiceTranslator
            LiveVoiceTranslator().run()
            return True

        if command.lower().startswith("speak "):
            text = command[6:].strip()
            self.speech.text_to_speech(text)
            return True

        if command.lower().startswith("note "):
            note = command[5:].strip()
            self.meeting.add_note(note)
            return True

        if command.lower().startswith("translate "):
            parts = command.split(maxsplit=3)

            if len(parts) < 4:
                print("Use: translate en ar your text")
                return True

            _, source, target, text = parts
            result = self.translator.translate_text(text, source, target)
            print("Translation:", result)
            return True

        if command.lower() == "exit":
            return False

        print("Unknown command. Type help.")
        return True

    def run_terminal(self):
        print("Smart Assistant started. Type help.")
        running = True

        while running:
            command = input("Assistant> ")
            running = self.handle_command(command)


if __name__ == "__main__":
    assistant = SmartAssistant()
    assistant.run_terminal()
