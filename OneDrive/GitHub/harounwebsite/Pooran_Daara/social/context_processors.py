from .models import Notification
from .translations import SUPPORTED_LANGUAGES, get_language, ui_for


def site_context(request):
    language = get_language(request)
    unread_notifications = 0
    unread_messages = 0
    if getattr(request, "user", None) and request.user.is_authenticated:
        unread = Notification.objects.filter(recipient=request.user, is_read=False)
        unread_notifications = unread.count()
        unread_messages = unread.filter(kind="message").count()
    return {
        "ui": ui_for(language),
        "site_language": language,
        "site_dir": SUPPORTED_LANGUAGES[language]["dir"],
        "language_options": SUPPORTED_LANGUAGES,
        "unread_notifications": unread_notifications,
        "unread_messages": unread_messages,
    }
