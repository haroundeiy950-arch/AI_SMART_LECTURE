from settings import DEFAULT_SOURCE_LANGUAGE, DEFAULT_TARGET_LANGUAGE

from deep_translator import GoogleTranslator


class TranslatorSystem:
    def translate_text(self, text, source_language="auto", target_language="en"):
        try:
            translated = GoogleTranslator(
                source=source_language,
                target=target_language
            ).translate(text)

            return translated

        except Exception as error:
            return f"Translation error: {error}"
class TranslatorSystem:
    def __init__(self):
        self.translator = None
        self.available = False
        self.load_translator()

    def load_translator(self):
        try:
            from googletrans import Translator
            self.translator = Translator()
            self.available = True
            print("Translator loaded.")
        except Exception as error:
            self.available = False
            print("Translator not available.")
            print("Install with: pip install googletrans==4.0.0-rc1")
            print(f"Details: {error}")

    def translate_text(
        self,
        text: str,
        source_language: str = DEFAULT_SOURCE_LANGUAGE,
        target_language: str = DEFAULT_TARGET_LANGUAGE
    ) -> str:
        if not text:
            return ""

        if not self.available or self.translator is None:
            return f"[Translation unavailable] {text}"

        try:
            result = self.translator.translate(
                text,
                src=source_language,
                dest=target_language
            )
            return result.text

        except Exception as error:
            return f"Translation error: {error}"

    def translate_arabic_to_english(self, text: str) -> str:
        return self.translate_text(text, "ar", "en")

    def translate_english_to_arabic(self, text: str) -> str:
        return self.translate_text(text, "en", "ar")

    def translate_english_to_french(self, text: str) -> str:
        return self.translate_text(text, "en", "fr")
