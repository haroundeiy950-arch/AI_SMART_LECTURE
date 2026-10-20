import cv2
from typing import Optional


class OCRSystem:
    def __init__(self):
        self.available = False
        self.pytesseract = None
        self.load_engine()

    def load_engine(self):
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.available = True
            print("OCR engine loaded.")
        except Exception as error:
            self.available = False
            print("pytesseract is not available.")
            print("Install with: pip install pytesseract")
            print("Also install Tesseract OCR app on Windows.")
            print(f"Details: {error}")

    def image_to_text(self, image, lang: str = "eng") -> str:
        if not self.available or self.pytesseract is None:
            return "OCR is not available."

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            text = self.pytesseract.image_to_string(gray, lang=lang)
            text = text.strip()

            if not text:
                return "No text detected."

            return text

        except Exception as error:
            return f"OCR error: {error}"

    def image_file_to_text(self, image_path: str, lang: str = "eng") -> str:
        image = cv2.imread(image_path)

        if image is None:
            return "Cannot read image file."

        return self.image_to_text(image, lang=lang)
