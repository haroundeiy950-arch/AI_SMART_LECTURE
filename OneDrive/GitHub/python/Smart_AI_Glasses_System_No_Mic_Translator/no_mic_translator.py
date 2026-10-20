import os
import time
import tempfile
from pathlib import Path
from typing import Dict

from translator import TranslatorSystem
from settings import SOUNDS_DIR, create_project_folders


class NoMicTranslator:
    """
    No Microphone Translator
from googletrans import Translator
translator = Translator()
result = translator.translate('Hello', dest='es')
print(result.text)  # Should print 'Hola'
    هذا الملف للحالات التي لا يوجد فيها مايكروفون.

    يعمل بطريقتين:
    1. تكتب النص يدويًا، والنظام يترجم وينطق بالصوت.
    2. تضع ملف صوت WAV داخل مجلد sounds، والنظام يحوله إلى نص ثم يترجم وينطق.

    ملاحظة:
    - الكتابة لا تحتاج مايكروفون.
    - النطق يعمل من سماعة اللابتوب أو سماعة البلوتوث.
    - قراءة ملف صوت تحتاج ملف WAV واضح.
    """

    LANGUAGES: Dict[str, Dict[str, str]] = {
        "1": {
            "name_ar": "العربية",
            "name_en": "Arabic",
            "speech_code": "ar-SA",
            "translate_code": "ar",
            "tts_code": "ar"
        },
        "2": {
            "name_ar": "الإنجليزية",
            "name_en": "English",
            "speech_code": "en-US",
            "translate_code": "en",
            "tts_code": "en"
        },
        "3": {
            "name_ar": "الفرنسية",
            "name_en": "French",
            "speech_code": "fr-FR",
            "translate_code": "fr",
            "tts_code": "fr"
        },
        "4": {
            "name_ar": "الإسبانية",
            "name_en": "Spanish",
            "speech_code": "es-ES",
            "translate_code": "es",
            "tts_code": "es"
        }
    }

    def __init__(self):
        create_project_folders()
        self.translator = TranslatorSystem()

    def show_languages(self):
        print("\nAvailable Languages / اللغات المتاحة")
        print("-" * 45)

        for key, info in self.LANGUAGES.items():
            print(f"{key}. {info['name_ar']} - {info['name_en']}")

        print("-" * 45)

    def choose_language(self, title: str) -> Dict[str, str]:
        while True:
            self.show_languages()
            choice = input(title).strip()

            if choice in self.LANGUAGES:
                return self.LANGUAGES[choice]

            print("Invalid choice. اختر رقم صحيح.")

    def translate_text(self, text: str, source_language: Dict[str, str], target_language: Dict[str, str]) -> str:
        if not text.strip():
            return ""

        return self.translator.translate_text(
            text=text,
            source_language=source_language["translate_code"],
            target_language=target_language["translate_code"]
        )

    def speak_with_gtts(self, text: str, language_code: str) -> bool:
        if not text.strip():
            return False

        try:
            from gtts import gTTS
            import pygame

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                audio_path = temp_file.name

            tts = gTTS(text=text, lang=language_code, slow=False)
            tts.save(audio_path)

            pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            pygame.mixer.music.stop()
            pygame.mixer.quit()

            try:
                os.remove(audio_path)
            except OSError:
                pass

            return True

        except Exception as error:
            print(f"gTTS error: {error}")
            return False

    def speak_with_pyttsx3(self, text: str) -> bool:
        if not text.strip():
            return False

        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()

            return True

        except Exception as error:
            print(f"pyttsx3 error: {error}")
            return False

    def speak(self, text: str, target_language: Dict[str, str]):
        print("\nSpeaking from laptop speaker or Bluetooth speaker...")
        success = self.speak_with_gtts(text, target_language["tts_code"])

        if not success:
            print("Trying offline speaker fallback...")
            self.speak_with_pyttsx3(text)

    def type_translate_mode(self):
        print("\nText to Voice Translation")
        print("هذه الطريقة لا تحتاج مايكروفون.")
        print("اكتب النص، والنظام يترجم وينطق من سماعة الجهاز.")

        source_language = self.choose_language("Choose source language / اختر لغة النص: ")
        target_language = self.choose_language("Choose target language / اختر لغة الترجمة: ")

        print("\nExample:")
        print("اكتب: صباح الخير")
        print("النظام يترجم وينطق: Bonjour / Good morning")

        while True:
            text = input("\nWrite text, or Q to quit: ").strip()

            if text.lower() == "q":
                break

            translated = self.translate_text(text, source_language, target_language)

            print("\nOriginal:")
            print(text)

            print("\nTranslation:")
            print(translated)

            self.speak(translated, target_language)

    def audio_file_to_text(self, audio_path: Path, source_language: Dict[str, str]) -> str:
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()

            with sr.AudioFile(str(audio_path)) as source:
                audio = recognizer.record(source)

            text = recognizer.recognize_google(
                audio,
                language=source_language["speech_code"]
            )

            return text.strip()

        except Exception as error:
            return f"Audio file recognition error: {error}"

    def audio_file_translate_mode(self):
        print("\nAudio File to Voice Translation")
        print("هذه الطريقة لا تحتاج مايكروفون في الكمبيوتر.")
        print("سجل الصوت بالتلفون، ثم انقل الملف إلى مجلد sounds.")
        print("أفضل صيغة: WAV")

        source_language = self.choose_language("Choose audio language / اختر لغة الصوت: ")
        target_language = self.choose_language("Choose target language / اختر لغة الترجمة: ")

        print(f"\nPut audio file inside this folder:")
        print(SOUNDS_DIR)

        filename = input("\nAudio filename, example input.wav: ").strip()

        audio_path = SOUNDS_DIR / filename

        if not audio_path.exists():
            print(f"File not found: {audio_path}")
            return

        original_text = self.audio_file_to_text(audio_path, source_language)

        print("\nRecognized Text:")
        print(original_text)

        if original_text.startswith("Audio file recognition error"):
            return

        translated = self.translate_text(original_text, source_language, target_language)

        print("\nTranslation:")
        print(translated)

        self.speak(translated, target_language)

    def run(self):
        while True:
            print("\nNo Microphone Translator")
            print("=" * 50)
            print("1. Type text -> Translate -> Speak")
            print("2. Audio file WAV -> Translate -> Speak")
            print("0. Exit")

            choice = input("Choose option: ").strip()

            if choice == "1":
                self.type_translate_mode()

            elif choice == "2":
                self.audio_file_translate_mode()

            elif choice == "0":
                print("No microphone translator closed.")
                break

            else:
                print("Invalid option.")


if __name__ == "__main__":
    app = NoMicTranslator()
    app.run()
