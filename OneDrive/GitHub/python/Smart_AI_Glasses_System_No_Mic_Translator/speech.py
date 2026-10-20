class SpeechSystem:
    def __init__(self):
        self.tts_engine = None

        try:
            import pyttsx3
            self.pyttsx3 = pyttsx3
            self.tts_engine = pyttsx3.init()
        except Exception as error:
            self.pyttsx3 = None
            print("pyttsx3 not available.")
            print("Install with: python -m pip install pyttsx3 pywin32")
            print("Details:", error)

        try:
            import speech_recognition as sr
            self.sr = sr
        except Exception as error:
            self.sr = None
            print("SpeechRecognition not available.")
            print("Install with: python -m pip install SpeechRecognition")
            print("For microphone support install PyAudio if needed.")
            print("Details:", error)

    def text_to_speech(self, text):
        if not text:
            print("No text entered.")
            return

        if self.tts_engine is None:
            print("Text to speech is not available.")
            print("Run: python -m pip install pyttsx3 pywin32")
            return

        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def speech_to_text(self):
        if self.sr is None:
            print("Speech recognition is not available.")
            print("Run: python -m pip install SpeechRecognition")
            return ""

        try:
            recognizer = self.sr.Recognizer()

            with self.sr.Microphone() as source:
                print("Speak now...")
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source)

            text = recognizer.recognize_google(audio)
            return text

        except Exception as error:
            print("Speech to text error:")
            print(error)
            return ""

    def load_speech(self):
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone_class = sr.Microphone
            self.speech_available = True
            print("Speech recognition loaded.")
        except Exception as error:
            self.speech_available = False
            print("SpeechRecognition not available.")
            print("Install with: pip install SpeechRecognition")
            print("For microphone support install PyAudio if needed.")
            print(f"Details: {error}")

    def load_tts(self):
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_available = True
            print("Text-to-speech loaded.")
        except Exception as error:
            self.tts_available = False
            print("pyttsx3 not available.")
            print("Install with: pip install pyttsx3")
            print(f"Details: {error}")

    def speech_to_text(self, language: str = "en-US", timeout: int = 5) -> str:
        if not self.speech_available:
            return "Speech recognition is not available."

        try:
            with self.microphone_class() as source:
                print("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=timeout)

            print("Recognizing...")
            text = self.recognizer.recognize_google(audio, language=language)
            return text

        except Exception as error:
            return f"Speech error: {error}"

    def text_to_speech(self, text: str):
        if not self.tts_available or self.tts_engine is None:
            print("TTS is not available.")
            return

        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as error:
            print(f"TTS error: {error}")

    def read_notification(self, text: str):
        print(f"Notification: {text}")
        self.text_to_speech(text)
