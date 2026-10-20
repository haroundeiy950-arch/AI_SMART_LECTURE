import hashlib
import secrets
from typing import Tuple


class SecuritySystem:
    def generate_salt(self) -> str:
        return secrets.token_hex(16)

    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        if salt is None:
            salt = self.generate_salt()

        data = (password + salt).encode("utf-8")
        password_hash = hashlib.sha256(data).hexdigest()

        return password_hash, salt

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        new_hash, _ = self.hash_password(password, salt)
        return new_hash == password_hash

    def simple_login(self, username: str, password: str) -> bool:
        # Demo login only.
        # Username: admin
        # Password: 1234
        return username == "admin" and password == "1234"

    def mask_sensitive_text(self, text: str) -> str:
        if not text:
            return ""

        words = text.split()
        protected = []

        for word in words:
            if "@" in word:
                protected.append("***email***")
            elif word.isdigit() and len(word) >= 6:
                protected.append("***number***")
            else:
                protected.append(word)

        return " ".join(protected)

    def privacy_warning(self):
        return (
            "Privacy Notice: Camera and microphone should only be used "
            "with permission from people around you."
        )
