# ترقية النسخة السابقة

بعد استبدال ملفات المشروع أو فك النسخة الجديدة في مجلد جديد، نفّذ:

```powershell
.\venv311\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

لا تنفّذ `makemigrations` إلا عند تعديل النماذج بنفسك؛ ملف الترحيل الجديد موجود داخل المشروع.

إذا كانت لديك قاعدة `db.sqlite3` قديمة، خذ نسخة احتياطية منها قبل الترقية:

```powershell
Copy-Item .\db.sqlite3 .\db_backup_before_upgrade.sqlite3
```
