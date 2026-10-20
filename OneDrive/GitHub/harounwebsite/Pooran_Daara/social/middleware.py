from django.shortcuts import render
from django.utils import translation

from .translations import SUPPORTED_LANGUAGES


class SiteLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.session.get("site_language")
        if not language and getattr(request, "user", None) and request.user.is_authenticated:
            try:
                language = request.user.profile.preferred_language
            except Exception:
                language = None
        if language not in SUPPORTED_LANGUAGES:
            language = "ar"
        request.site_language = language
        request.LANGUAGE_CODE = language
        translation.activate(language)
        response = self.get_response(request)
        response.set_cookie("pooran_language", language, max_age=31536000, samesite="Lax")
        return response


class SuspendedAccountMiddleware:
    EXEMPT_PREFIXES = ("/logout/", "/static/", "/media/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and not user.is_staff
            and not request.path.startswith(self.EXEMPT_PREFIXES)
        ):
            try:
                if user.profile.is_suspended:
                    return render(request, "social/suspended.html", status=403)
            except Exception:
                pass
        return self.get_response(request)
