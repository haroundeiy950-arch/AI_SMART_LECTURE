import sys
import tkinter as tk
from tkinter import messagebox

from config import APP_TITLE
from database import Database
from ui import LoginWindow, SecurityApp


def main() -> None:
    try:
        db = Database()

        login_root = tk.Tk()
        login = LoginWindow(login_root, db)
        login_root.mainloop()

        if not login.result:
            return

        app_root = tk.Tk()
        SecurityApp(app_root, db, login.result)
        app_root.mainloop()
    except Exception as exc:
        try:
            messagebox.showerror(APP_TITLE, str(exc))
        except Exception:
            print(f"Fatal error: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
