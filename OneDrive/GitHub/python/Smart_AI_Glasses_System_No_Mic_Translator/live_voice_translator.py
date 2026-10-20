from deep_translator import GoogleTranslator
from gtts import gTTS
from playsound3 import playsound
from pathlib import Path
import tempfile
import uuid

try:
    import speech_recognition as sr
except ImportError:
    sr = None


def speak(text, lang="en"):
    audio_path = Path(tempfile.gettempdir()) / f"translation_{uuid.uuid4().hex}.mp3"

    tts = gTTS(text=text, lang=lang)
    tts.save(str(audio_path))

    playsound(str(audio_path))

    try:
        audio_path.unlink()
    except:
        pass


def translate_text(text):
    translated = GoogleTranslator(source="ar", target="en").translate(text)
    print("\nالنص الأصلي:", text)
    print("English:", translated)
    speak(translated, "en")


def listen_voice():
    if sr is None:
        print("SpeechRecognition غير مثبت.")
        print("اكتب: python -m pip install SpeechRecognition[audio]")
        return None

    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            print("\nتكلم الآن بالعربي...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=10)

        print("جاري فهم الصوت...")
        text = recognizer.recognize_google(audio, language="ar-SA")
        return text

    except sr.WaitTimeoutError:
        print("لم أسمع صوت.")
        return None

    except sr.UnknownValueError:
        print("لم أفهم الكلام.")
        return None

    except Exception as e:
        print("مشكلة في المايكروفون:", e)
        return None


print(" Arabic to English  Translator")
print("جملة أو صوت")
print("--------------------------")

while True:
    print("\n1. أكتب جملة")
    print("2. أتكلم بالصوت")
    print("3. خروج")

    choice = input("اختر: ").strip()

    if choice == "1":
        sentence = input("\nاكتب الجملة بالعربي: ").strip()

        if sentence:
            translate_text(sentence)
        else:
            print("اكتب جملة أولاً.")

    elif choice == "2":
        sentence = listen_voice()

        if sentence:
            translate_text(sentence)

    elif choice == "3":
        print("تم إيقاف البرنامج.")
        break

    else:
        print("اختيار خطأ.")