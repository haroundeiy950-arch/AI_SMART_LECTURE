from __future__ import annotations

import base64
import binascii
import io
import json
import secrets
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .ai_service import (
    analyze_image,
    assistant_reply,
    generate_speech,
    summarize_meeting,
    transcribe_audio,
)
from .config import BASE_DIR, settings
from .database import (
    Conversation,
    LoginAttempt,
    Meeting,
    Passkey,
    Person,
    Product,
    SessionLocal,
    User,
    init_db,
    utcnow,
)
from .face_service import recognize_faces, save_face_sample, train_face_model, vision_status
from .translator_service import get_supported_languages, translate_text
from .security import (
    current_user,
    ensure_csrf_token,
    get_client_ip,
    hash_password,
    is_login_locked,
    record_login_attempt,
    validate_csrf,
    verify_password,
)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="smart_glasses_session",
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=settings.secure_cookies,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
app.mount("/product-media", StaticFiles(directory=settings.products_dir), name="product_media")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


def db_session() -> Session:
    return SessionLocal()


def require_user(request: Request, db: Session) -> User:
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return user


def template_context(request: Request, db: Session, **extra: Any) -> dict[str, Any]:
    user = current_user(request, db)
    return {
        "request": request,
        "user": user,
        "app_name": settings.app_name,
        "csrf_token": ensure_csrf_token(request),
        "ai_enabled": settings.ai_enabled,
        **extra,
    }


def decode_data_url(data_url: str, max_bytes: int = 8_000_000) -> tuple[bytes, str]:
    if not data_url.startswith("data:image/") or "," not in data_url:
        raise ValueError("Invalid image data")
    header, encoded = data_url.split(",", 1)
    mime = header.split(";", 1)[0].replace("data:", "")
    content = base64.b64decode(encoded, validate=True)
    if len(content) > max_bytes:
        raise ValueError("Image is too large")
    extension = {"image/png": ".png", "image/webp": ".webp"}.get(mime, ".jpg")
    return content, extension


def safe_code(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch.isalnum() or ch in "-_" )
    if not cleaned:
        raise ValueError("Invalid code")
    return cleaned[:60]


@app.on_event("startup")
def startup() -> None:
    init_db()
    with db_session() as db:
        admin = db.scalar(select(User).where(User.username == settings.admin_username.lower()))
        if not admin:
            db.add(
                User(
                    username=settings.admin_username.lower(),
                    display_name=settings.admin_display_name,
                    password_hash=hash_password(settings.admin_password),
                    user_handle=secrets.token_bytes(32),
                    role="admin",
                )
            )
            db.commit()


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        return RedirectResponse("/login", status_code=303)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    with db_session() as db:
        return RedirectResponse("/dashboard" if current_user(request, db) else "/login", 303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    with db_session() as db:
        if current_user(request, db):
            return RedirectResponse("/dashboard", 303)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=template_context(request, db, title="Secure Login"),
        )


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    normalized = username.lower().strip()
    ip = get_client_ip(request)
    with db_session() as db:
        locked, remaining = is_login_locked(db, normalized, ip)
        if locked:
            return RedirectResponse("/login?error=locked", 303)
        user = db.scalar(select(User).where(User.username == normalized))
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            record_login_attempt(
                db,
                username=normalized,
                ip_address=ip,
                success=False,
                method="password",
                reason=f"Invalid credentials; {max(0, remaining - 1)} attempts remaining",
            )
            return RedirectResponse("/login?error=invalid", 303)
        record_login_attempt(
            db, username=normalized, ip_address=ip, success=True, method="password"
        )
        request.session.clear()
        request.session["user_id"] = user.id
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        return RedirectResponse("/dashboard", 303)


@app.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse("/login", 303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        stats = {
            "people": db.scalar(select(func.count(Person.id))) or 0,
            "meetings": db.scalar(select(func.count(Meeting.id))) or 0,
            "conversations": db.scalar(select(func.count(Conversation.id))) or 0,
            "products": db.scalar(select(func.count(Product.id))) or 0,
            "failed_logins": db.scalar(
                select(func.count(LoginAttempt.id)).where(LoginAttempt.success.is_(False))
            )
            or 0,
        }
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=template_context(request, db, title="Dashboard", stats=stats, current=user),
        )


@app.get("/voice", response_class=HTMLResponse)
def voice_page(request: Request):
    with db_session() as db:
        require_user(request, db)
        history = db.scalars(
            select(Conversation).order_by(desc(Conversation.created_at)).limit(10)
        ).all()
        return templates.TemplateResponse(
            request=request,
            name="voice.html",
            context=template_context(request, db, title="AI Voice Assistant", history=history),
        )


@app.get("/camera", response_class=HTMLResponse)
def camera_page(request: Request):
    with db_session() as db:
        require_user(request, db)
        return templates.TemplateResponse(
            request=request,
            name="camera.html",
            context=template_context(request, db, title="Live Camera"),
        )


@app.get("/people", response_class=HTMLResponse)
def people_page(request: Request):
    with db_session() as db:
        require_user(request, db)
        people = db.scalars(select(Person).order_by(Person.full_name)).all()
        return templates.TemplateResponse(
            request=request,
            name="people.html",
            context=template_context(request, db, title="Registered People", people=people),
        )


@app.get("/translation", response_class=HTMLResponse)
def translation_page(request: Request):
    with db_session() as db:
        require_user(request, db)
        languages = get_supported_languages()
        return templates.TemplateResponse(
            request=request,
            name="translation.html",
            context=template_context(
                request, db, title="Live Translation", languages=languages
            ),
        )


@app.get("/meetings", response_class=HTMLResponse)
def meetings_page(request: Request):
    with db_session() as db:
        require_user(request, db)
        meetings = db.scalars(select(Meeting).order_by(desc(Meeting.created_at))).all()
        return templates.TemplateResponse(
            request=request,
            name="meetings.html",
            context=template_context(request, db, title="Meeting Assistant", meetings=meetings),
        )


@app.get("/modules", response_class=HTMLResponse)
def modules_page(request: Request):
    with db_session() as db:
        require_user(request, db)
        return templates.TemplateResponse(
            request=request,
            name="modules.html",
            context=template_context(request, db, title="System Modules"),
        )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        passkeys = db.scalars(select(Passkey).where(Passkey.user_id == user.id)).all()
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context=template_context(request, db, title="Security Settings", passkeys=passkeys),
        )


@app.get("/api/me")
def api_me(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        return {"username": user.username, "display_name": user.display_name, "role": user.role}


@app.post("/api/assistant/chat")
async def api_chat(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
        body = await request.json()
        message = str(body.get("message", ""))[:6000]
        language = str(body.get("language", "ar"))[:20]
        reply = await assistant_reply(message, language)
        db.add(
            Conversation(
                user_id=user.id,
                user_text=message,
                assistant_text=reply,
                language=language,
            )
        )
        db.commit()
        return {"reply": reply, "ai_enabled": settings.ai_enabled}


@app.post("/api/voice/speak")
async def api_speak(request: Request):
    with db_session() as db:
        require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
    body = await request.json()
    text = str(body.get("text", ""))[:4096]
    voice = str(body.get("voice", "coral"))[:40]
    audio = await generate_speech(text, voice)
    if audio is None:
        raise HTTPException(503, "Online AI voice is not configured; use browser voice fallback.")
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/voice/transcribe")
async def api_transcribe(request: Request, audio: UploadFile = File(...)):
    with db_session() as db:
        require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
    content = await audio.read()
    if len(content) > 20_000_000:
        raise HTTPException(413, "Audio file is too large")
    try:
        text = await transcribe_audio(audio.filename or "recording.webm", content, audio.content_type or "audio/webm")
        return {"text": text}
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


@app.post("/api/camera/analyze")
async def api_camera_analyze(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
    body = await request.json()
    data_url = str(body.get("image", ""))
    try:
        image, extension = decode_data_url(data_url)
    except (ValueError, binascii.Error) as error:
        raise HTTPException(400, "Invalid camera image") from error
    filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + f"_{user.id}{extension}"
    path = settings.captures_dir / filename
    path.write_bytes(image)
    result = await analyze_image(data_url)
    try:
        local_faces = recognize_faces(image)
        if local_faces.get("faces"):
            codes = [item.get("code") for item in local_faces["faces"] if item.get("known")]
            with db_session() as face_db:
                people = face_db.scalars(select(Person).where(Person.code.in_(codes))).all() if codes else []
            names = {person.code: person.full_name for person in people}
            for face in local_faces["faces"]:
                if face.get("code") in names:
                    face["name"] = names[face["code"]]
        result["local_face_recognition"] = local_faces
    except RuntimeError as error:
        result["local_face_recognition"] = {"available": False, "reason": str(error), "faces": []}
    result["saved_as"] = filename
    return result


@app.post("/api/people")
async def api_create_person(request: Request):
    with db_session() as db:
        require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
        body = await request.json()
        try:
            code = safe_code(str(body.get("code", "")))
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        name = str(body.get("full_name", "")).strip()[:160]
        if not name:
            raise HTTPException(400, "Full name is required")
        if db.scalar(select(Person).where(Person.code == code)):
            raise HTTPException(409, "Person code already exists")
        photo_path = ""
        data_url = str(body.get("photo", ""))
        if data_url:
            try:
                image, extension = decode_data_url(data_url)
                directory = settings.known_faces_dir / code
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / f"profile{extension}"
                path.write_bytes(image)
                photo_path = str(path.relative_to(BASE_DIR))
                try:
                    save_face_sample(code, image)
                except (ValueError, RuntimeError):
                    pass
            except (ValueError, binascii.Error) as error:
                raise HTTPException(400, "Invalid person photo") from error
        person = Person(
            code=code,
            full_name=name,
            department=str(body.get("department", ""))[:120],
            notes=str(body.get("notes", ""))[:2000],
            photo_path=photo_path,
        )
        db.add(person)
        db.commit()
        return {"ok": True, "id": person.id}


@app.delete("/api/people/{person_id}")
def api_delete_person(person_id: int, request: Request):
    with db_session() as db:
        user = require_user(request, db)
        if user.role != "admin":
            raise HTTPException(403, "Admin role required")
        validate_csrf(request, request.headers.get("x-csrf-token"))
        person = db.get(Person, person_id)
        if not person:
            raise HTTPException(404, "Person not found")
        if person.photo_path:
            folder = (BASE_DIR / person.photo_path).parent
            if folder.exists() and settings.known_faces_dir in folder.parents:
                shutil.rmtree(folder, ignore_errors=True)
        db.delete(person)
        db.commit()
        return {"ok": True}


@app.get("/api/faces/status")
def api_face_status(request: Request):
    with db_session() as db:
        require_user(request, db)
    return vision_status()


@app.post("/api/people/{person_id}/samples")
async def api_face_sample(person_id: int, request: Request):
    with db_session() as db:
        require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
        person = db.get(Person, person_id)
        if not person:
            raise HTTPException(404, "Person not found")
        body = await request.json()
        try:
            image, _ = decode_data_url(str(body.get("image", "")))
            path = save_face_sample(person.code, image)
        except (ValueError, RuntimeError, binascii.Error) as error:
            raise HTTPException(400 if isinstance(error, ValueError) else 503, str(error)) from error
        return {"ok": True, "sample": path}


@app.post("/api/faces/train")
def api_train_faces(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        if user.role != "admin":
            raise HTTPException(403, "Admin role required")
        validate_csrf(request, request.headers.get("x-csrf-token"))
    try:
        return train_face_model()
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


@app.post("/api/translate")
async def api_translate(request: Request):
    with db_session() as db:
        require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))

    body = await request.json()
    text = str(body.get("text", ""))[:50_000]
    source = str(body.get("source", "auto"))[:40]
    target = str(body.get("target", "en"))[:40]

    if not text.strip():
        raise HTTPException(400, "Text is required")

    try:
        result = await translate_text(
            text=text,
            source_language=source,
            target_language=target,
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error

    return {"translation": result, "source": source, "target": target}


@app.post("/api/meetings")
async def api_create_meeting(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
        body = await request.json()
        title = str(body.get("title", "Untitled meeting"))[:200]
        transcript = str(body.get("transcript", ""))[:50_000]
        summary, tasks = await summarize_meeting(transcript)
        meeting = Meeting(
            title=title,
            transcript=transcript,
            summary=summary,
            tasks=tasks,
            created_by=user.id,
        )
        db.add(meeting)
        db.commit()
        return {"id": meeting.id, "summary": summary, "tasks": tasks}


@app.post("/api/change-password")
async def api_change_password(request: Request):
    body = await request.json()
    with db_session() as db:
        user = require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
        current_password = str(body.get("current_password", ""))
        new_password = str(body.get("new_password", ""))
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(400, "Current password is incorrect")
        if new_password == current_password:
            raise HTTPException(400, "New password must be different")
        try:
            user.password_hash = hash_password(new_password)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        db.commit()
        return {"ok": True}


@app.post("/api/passkeys/register/options")
def passkey_register_options(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
        existing = db.scalars(select(Passkey).where(Passkey.user_id == user.id)).all()
        options = generate_registration_options(
            rp_id=settings.rp_id,
            rp_name=settings.rp_name,
            user_id=user.user_handle,
            user_name=user.username,
            user_display_name=user.display_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=item.credential_id) for item in existing
            ],
        )
        request.session["webauthn_register_challenge"] = bytes_to_base64url(options.challenge)
        return Response(options_to_json(options), media_type="application/json")


@app.post("/api/passkeys/register/verify")
async def passkey_register_verify(request: Request):
    body = await request.json()
    with db_session() as db:
        user = require_user(request, db)
        validate_csrf(request, request.headers.get("x-csrf-token"))
        challenge = request.session.pop("webauthn_register_challenge", None)
        if not challenge:
            raise HTTPException(400, "Passkey challenge expired")
        try:
            verified = verify_registration_response(
                credential=body,
                expected_challenge=base64url_to_bytes(challenge),
                expected_rp_id=settings.rp_id,
                expected_origin=settings.origin,
                require_user_verification=True,
            )
        except Exception as error:
            raise HTTPException(400, f"Passkey registration failed: {error}") from error
        db.add(
            Passkey(
                user_id=user.id,
                credential_id=verified.credential_id,
                public_key=verified.credential_public_key,
                sign_count=verified.sign_count,
                device_type=str(verified.credential_device_type.value),
                backed_up=verified.credential_backed_up,
                label=str(body.get("label", "Windows Hello"))[:100],
            )
        )
        db.commit()
        return {"ok": True}


@app.post("/api/passkeys/login/options")
async def passkey_login_options(request: Request):
    validate_csrf(request, request.headers.get("x-csrf-token"))
    body = await request.json()
    username = str(body.get("username", "")).lower().strip()
    with db_session() as db:
        user = db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
        if not user:
            raise HTTPException(404, "User not found")
        credentials = db.scalars(select(Passkey).where(Passkey.user_id == user.id)).all()
        if not credentials:
            raise HTTPException(404, "No Windows Hello/passkey is registered for this user")
        options = generate_authentication_options(
            rp_id=settings.rp_id,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=item.credential_id) for item in credentials
            ],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        request.session["webauthn_login_challenge"] = bytes_to_base64url(options.challenge)
        request.session["webauthn_login_user_id"] = user.id
        return Response(options_to_json(options), media_type="application/json")


@app.post("/api/passkeys/login/verify")
async def passkey_login_verify(request: Request):
    validate_csrf(request, request.headers.get("x-csrf-token"))
    body = await request.json()
    challenge = request.session.pop("webauthn_login_challenge", None)
    user_id = request.session.pop("webauthn_login_user_id", None)
    if not challenge or not user_id:
        raise HTTPException(400, "Passkey challenge expired")
    credential_id = base64url_to_bytes(str(body.get("id", "")))
    with db_session() as db:
        user = db.get(User, int(user_id))
        key = db.scalar(
            select(Passkey).where(
                Passkey.user_id == int(user_id), Passkey.credential_id == credential_id
            )
        )
        if not user or not key:
            raise HTTPException(404, "Passkey not found")
        try:
            verified = verify_authentication_response(
                credential=body,
                expected_challenge=base64url_to_bytes(challenge),
                expected_rp_id=settings.rp_id,
                expected_origin=settings.origin,
                credential_public_key=key.public_key,
                credential_current_sign_count=key.sign_count,
                require_user_verification=True,
            )
        except Exception as error:
            record_login_attempt(
                db,
                username=user.username,
                ip_address=get_client_ip(request),
                success=False,
                method="passkey",
                reason=str(error),
            )
            raise HTTPException(401, f"Windows Hello verification failed: {error}") from error
        key.sign_count = verified.new_sign_count
        key.last_used_at = utcnow()
        db.commit()
        record_login_attempt(
            db,
            username=user.username,
            ip_address=get_client_ip(request),
            success=True,
            method="passkey",
        )
        request.session.clear()
        request.session["user_id"] = user.id
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        return {"ok": True, "redirect": "/dashboard"}


@app.get("/api/backup")
def api_backup(request: Request):
    with db_session() as db:
        user = require_user(request, db)
        if user.role != "admin":
            raise HTTPException(403, "Admin role required")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = settings.backups_dir / f"smart_ai_glasses_backup_{timestamp}.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in settings.data_dir.rglob("*"):
            if path.is_file() and path != output and settings.backups_dir not in path.parents:
                archive.write(path, path.relative_to(BASE_DIR))
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            # Do not include secrets; only include a reminder file.
            archive.writestr("ENV_NOT_INCLUDED.txt", "The .env file is intentionally excluded for security.\n")
    return FileResponse(output, filename=output.name, media_type="application/zip")


# Separate backend and marketplace routes.
from .routes.backend_routes import router as backend_router
from .routes.product_routes import router as product_router

app.include_router(backend_router)
app.include_router(product_router)
