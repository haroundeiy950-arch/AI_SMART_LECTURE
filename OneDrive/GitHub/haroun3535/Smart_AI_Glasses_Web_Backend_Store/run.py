from __future__ import annotations

import threading
import webbrowser

import uvicorn

from app.config import settings


if __name__ == "__main__":
    url = settings.origin
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
