from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from .config import settings

ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 5_000_000

PRODUCT_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("phones", "تلفونات"),
    ("laptops", "لابتوبات"),
    ("clothes", "ملابس"),
    ("electronics", "إلكترونيات"),
    ("tools", "أدوات"),
    ("accessories", "إكسسوارات"),
    ("other", "أخرى"),
)

PRODUCT_CONDITIONS: tuple[tuple[str, str], ...] = (
    ("new", "جديد"),
    ("used", "مستعمل"),
    ("refurbished", "مجدّد"),
)

SUPPORTED_CURRENCIES: tuple[str, ...] = ("USD", "RWF", "SDG", "EUR")


def parse_price_to_cents(value: str) -> int:
    cleaned = value.strip().replace(",", "")
    try:
        amount = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as error:
        raise HTTPException(status_code=400, detail="السعر غير صحيح") from error
    if amount < 0:
        raise HTTPException(status_code=400, detail="السعر لا يمكن أن يكون سالبًا")
    if amount > Decimal("999999999.99"):
        raise HTTPException(status_code=400, detail="السعر أكبر من الحد المسموح")
    return int(amount * 100)


def format_price(price_cents: int) -> str:
    return f"{Decimal(price_cents) / Decimal(100):,.2f}"


def validate_product_fields(
    *,
    title: str,
    category: str,
    currency: str,
    condition: str,
    quantity: int,
) -> tuple[str, str, str, str, int]:
    clean_title = title.strip()[:180]
    if len(clean_title) < 2:
        raise HTTPException(status_code=400, detail="اكتب اسم المنتج")

    category_keys = {key for key, _ in PRODUCT_CATEGORIES}
    if category not in category_keys:
        raise HTTPException(status_code=400, detail="فئة المنتج غير صحيحة")

    clean_currency = currency.upper().strip()
    if clean_currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail="العملة غير مدعومة")

    condition_keys = {key for key, _ in PRODUCT_CONDITIONS}
    if condition not in condition_keys:
        raise HTTPException(status_code=400, detail="حالة المنتج غير صحيحة")

    if quantity < 0 or quantity > 1_000_000:
        raise HTTPException(status_code=400, detail="الكمية غير صحيحة")

    return clean_title, category, clean_currency, condition, quantity


async def save_product_image(upload: UploadFile | None) -> str:
    if upload is None or not upload.filename:
        return ""

    content_type = (upload.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(
            status_code=400,
            detail="الصورة يجب أن تكون JPG أو PNG أو WEBP",
        )

    data = await upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="حجم الصورة أكبر من 5MB")
    if not data:
        raise HTTPException(status_code=400, detail="ملف الصورة فارغ")

    settings.products_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    path = settings.products_dir / filename
    path.write_bytes(data)
    return filename


def delete_product_image(filename: str) -> None:
    if not filename:
        return
    safe_name = Path(filename).name
    path = settings.products_dir / safe_name
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
