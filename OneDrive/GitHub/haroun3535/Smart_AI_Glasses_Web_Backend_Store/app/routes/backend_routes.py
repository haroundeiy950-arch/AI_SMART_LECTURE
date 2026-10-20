from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import desc, func, select

from ..database import LoginAttempt, Meeting, Person, Product, User
from ..route_helpers import db_session, render_page, require_admin

router = APIRouter(tags=["backend"])


@router.get("/backend", response_class=HTMLResponse)
def backend_page(request: Request):
    with db_session() as db:
        admin = require_admin(request, db)
        stats = {
            "users": db.scalar(select(func.count(User.id))) or 0,
            "products": db.scalar(select(func.count(Product.id))) or 0,
            "active_products": db.scalar(
                select(func.count(Product.id)).where(Product.is_active.is_(True))
            )
            or 0,
            "people": db.scalar(select(func.count(Person.id))) or 0,
            "meetings": db.scalar(select(func.count(Meeting.id))) or 0,
            "failed_logins": db.scalar(
                select(func.count(LoginAttempt.id)).where(LoginAttempt.success.is_(False))
            )
            or 0,
        }
        recent_products = db.scalars(
            select(Product).order_by(desc(Product.created_at)).limit(6)
        ).all()
        recent_attempts = db.scalars(
            select(LoginAttempt).order_by(desc(LoginAttempt.created_at)).limit(8)
        ).all()
        return render_page(
            request,
            db,
            "backend.html",
            title="Backend Control Center",
            admin=admin,
            stats=stats,
            recent_products=recent_products,
            recent_attempts=recent_attempts,
        )
