# Backend + Product Store

## الصفحات الجديدة

- `http://localhost:8000/backend` لوحة Backend للمدير.
- `http://localhost:8000/backend/products` إضافة وتعديل وحذف وإخفاء المنتجات.
- `http://localhost:8000/products` عرض المنتجات في شكل بطاقات.

## مثال إضافة تلفون

- اسم المنتج: Samsung Galaxy S24
- الفئة: تلفونات
- السعر: 799.99
- العملة: USD
- الكمية: 3
- الحالة: جديد
- الموقع: Rwanda - Kigali
- WhatsApp: 2507XXXXXXXX
- الصورة: JPG/PNG/WEBP حتى 5MB

## تقسيم الكود

- `app/routes/backend_routes.py`: صفحة Backend والإحصاءات.
- `app/routes/product_routes.py`: صفحات ومسارات المنتجات.
- `app/product_service.py`: التحقق من السعر والصور والفئات.
- `app/route_helpers.py`: جلسة قاعدة البيانات ورسم صفحات Jinja.
- `app/database.py`: جدول Product.
- `app/templates/backend.html`: تصميم Backend.
- `app/templates/product_manager.html`: نموذج رفع المنتج والقائمة.
- `app/templates/products.html`: سوق المنتجات.
- `app/templates/product_edit.html`: تعديل المنتج.
