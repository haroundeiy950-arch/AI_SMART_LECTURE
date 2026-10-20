from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .config import BASE_DIR, settings
from .database import SessionLocal, User
from .security import current_user, ensure_csrf_token


templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


def db_session() -> Session:
    return SessionLocal()


def require_user(request: Request, db: Session) -> User:
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return user


def require_admin(request: Request, db: Session) -> User:
    user = require_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def template_context(request: Request, db: Session, **extra: Any) -> dict[str, Any]:
    return {
        "request": request,
        "user": current_user(request, db),
        "app_name": settings.app_name,
        "csrf_token": ensure_csrf_token(request),
        "ai_enabled": settings.ai_enabled,
        **extra,
    }


def render_page(
    request: Request,
    db: Session,
    template_name: str,
    **extra: Any,
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=template_context(request, db, **extra),
    )
