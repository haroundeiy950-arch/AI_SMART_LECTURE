from database import Database
from config import DATABASE_PATH

USERNAME = "admin"
NEW_PASSWORD = ""

db = Database()

print("Database path:")
print(DATABASE_PATH.resolve())

db.change_admin_password(
    USERNAME,
    NEW_PASSWORD
)

test_login = db.authenticate_admin(
    USERNAME,
    NEW_PASSWORD
)

if test_login:
    print("=" * 40)
    print("PASSWORD RESET SUCCESSFULLY")
    print("Username: admin")
    print("Password:")
    print("=" * 40)
else:
    print("ERROR: Password reset failed.")