from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .database import LoginAttempt, User

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def validate_csrf(request: Request, token: str | None) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not token or not secrets.compare_digest(expected, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def record_login_attempt(
    db: Session,
    *,
    username: str,
    ip_address: str,
    success: bool,
    method: str,
    reason: str = "",
) -> None:
    db.add(
        LoginAttempt(
            username=username.lower().strip(),
            ip_address=ip_address,
            success=success,
            method=method,
            reason=reason[:255],
        )
    )
    db.commit()


def is_login_locked(db: Session, username: str, ip_address: str) -> tuple[bool, int]:
    since = datetime.now(timezone.utc) - timedelta(minutes=5)
    attempts = db.scalars(
        select(LoginAttempt)
        .where(
            LoginAttempt.username == username.lower().strip(),
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.success.is_(False),
            LoginAttempt.created_at >= since,
        )
        .order_by(desc(LoginAttempt.created_at))
    ).all()
    remaining = max(0, 5 - len(attempts))
    return len(attempts) >= 5, remaining


def current_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        request.session.clear()
        return None
    return user
