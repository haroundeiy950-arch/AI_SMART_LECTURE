from app.security import hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("StrongPassword@123")
    assert verify_password("StrongPassword@123", hashed)
    assert not verify_password("wrong-password", hashed)
