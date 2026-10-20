from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import desc, or_, select

from ..database import Product
from ..product_service import (
    PRODUCT_CATEGORIES,
    PRODUCT_CONDITIONS,
    SUPPORTED_CURRENCIES,
    delete_product_image,
    format_price,
    parse_price_to_cents,
    save_product_image,
    validate_product_fields,
)
from ..route_helpers import db_session, render_page, require_admin, require_user
from ..security import validate_csrf

router = APIRouter(tags=["products"])


def _catalog_context() -> dict[str, object]:
    return {
        "categories": PRODUCT_CATEGORIES,
        "conditions": PRODUCT_CONDITIONS,
        "currencies": SUPPORTED_CURRENCIES,
        "format_price": format_price,
    }


@router.get("/products", response_class=HTMLResponse)
def products_page(request: Request, q: str = "", category: str = ""):
    with db_session() as db:
        require_user(request, db)
        query = select(Product).where(Product.is_active.is_(True))
        clean_q = q.strip()[:100]
        if clean_q:
            pattern = f"%{clean_q}%"
            query = query.where(
                or_(
                    Product.title.ilike(pattern),
                    Product.description.ilike(pattern),
                    Product.location.ilike(pattern),
                )
            )
        if category and category in {key for key, _ in PRODUCT_CATEGORIES}:
            query = query.where(Product.category == category)
        products = db.scalars(
            query.order_by(desc(Product.is_featured), desc(Product.created_at))
        ).all()
        return render_page(
            request,
            db,
            "products.html",
            title="سوق المنتجات",
            products=products,
            q=clean_q,
            selected_category=category,
            **_catalog_context(),
        )


@router.get("/backend/products", response_class=HTMLResponse)
def product_manager_page(request: Request):
    with db_session() as db:
        require_admin(request, db)
        products = db.scalars(select(Product).order_by(desc(Product.created_at))).all()
        return render_page(
            request,
            db,
            "product_manager.html",
            title="إدارة المنتجات",
            products=products,
            **_catalog_context(),
        )


@router.post("/backend/products")
async def create_product(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    price: str = Form(...),
    currency: str = Form("USD"),
    quantity: int = Form(1),
    condition: str = Form("new"),
    description: str = Form(""),
    location: str = Form(""),
    whatsapp: str = Form(""),
    is_active: str | None = Form(None),
    is_featured: str | None = Form(None),
    csrf_token: str = Form(...),
    image: UploadFile | None = File(None),
):
    validate_csrf(request, csrf_token)
    with db_session() as db:
        admin = require_admin(request, db)
        clean_title, category, currency, condition, quantity = validate_product_fields(
            title=title,
            category=category,
            currency=currency,
            condition=condition,
            quantity=quantity,
        )
        price_cents = parse_price_to_cents(price)
        image_filename = await save_product_image(image)
        product = Product(
            title=clean_title,
            category=category,
            price_cents=price_cents,
            currency=currency,
            quantity=quantity,
            condition=condition,
            description=description.strip()[:5000],
            location=location.strip()[:160],
            whatsapp=whatsapp.strip()[:80],
            image_filename=image_filename,
            is_active=is_active == "on",
            is_featured=is_featured == "on",
            created_by=admin.id,
        )
        db.add(product)
        db.commit()
    return RedirectResponse("/backend/products?created=1", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/backend/products/{product_id}/edit", response_class=HTMLResponse)
def edit_product_page(product_id: int, request: Request):
    with db_session() as db:
        require_admin(request, db)
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return render_page(
            request,
            db,
            "product_edit.html",
            title="تعديل المنتج",
            product=product,
            **_catalog_context(),
        )


@router.post("/backend/products/{product_id}/edit")
async def update_product(
    product_id: int,
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    price: str = Form(...),
    currency: str = Form("USD"),
    quantity: int = Form(1),
    condition: str = Form("new"),
    description: str = Form(""),
    location: str = Form(""),
    whatsapp: str = Form(""),
    is_active: str | None = Form(None),
    is_featured: str | None = Form(None),
    csrf_token: str = Form(...),
    image: UploadFile | None = File(None),
):
    validate_csrf(request, csrf_token)
    with db_session() as db:
        require_admin(request, db)
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        clean_title, category, currency, condition, quantity = validate_product_fields(
            title=title,
            category=category,
            currency=currency,
            condition=condition,
            quantity=quantity,
        )
        new_image = await save_product_image(image)
        if new_image:
            delete_product_image(product.image_filename)
            product.image_filename = new_image
        product.title = clean_title
        product.category = category
        product.price_cents = parse_price_to_cents(price)
        product.currency = currency
        product.quantity = quantity
        product.condition = condition
        product.description = description.strip()[:5000]
        product.location = location.strip()[:160]
        product.whatsapp = whatsapp.strip()[:80]
        product.is_active = is_active == "on"
        product.is_featured = is_featured == "on"
        db.commit()
    return RedirectResponse("/backend/products?updated=1", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/backend/products/{product_id}/toggle")
def toggle_product(product_id: int, request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    with db_session() as db:
        require_admin(request, db)
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        product.is_active = not product.is_active
        db.commit()
    return RedirectResponse("/backend/products", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/backend/products/{product_id}/delete")
def delete_product(product_id: int, request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    with db_session() as db:
        require_admin(request, db)
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        delete_product_image(product.image_filename)
        db.delete(product)
        db.commit()
    return RedirectResponse("/backend/products?deleted=1", status_code=status.HTTP_303_SEE_OTHER)
