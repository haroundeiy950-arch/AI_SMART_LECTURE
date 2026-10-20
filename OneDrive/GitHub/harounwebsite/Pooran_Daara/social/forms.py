from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    Comment,
    DirectMessage,
    Post,
    Profile,
    Report,
)
from .translations import tr


# =========================================================
# Language Mixin
# =========================================================
class LanguageFormMixin:
    def __init__(self, *args, language="ar", **kwargs):
        self.language = language
        super().__init__(*args, **kwargs)


# =========================================================
# Register Form
# =========================================================
class RegisterForm(LanguageFormMixin, UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
    )

    email = forms.EmailField(
        required=True,
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )

    def __init__(self, *args, language="ar", **kwargs):
        super().__init__(
            *args,
            language=language,
            **kwargs,
        )

        selected_language = (
            language
            if language in {"ar", "en", "fr"}
            else "ar"
        )

        labels = {
            "ar": [
                "اسم المستخدم",
                "الاسم الأول",
                "اسم العائلة",
                "البريد الإلكتروني",
                "كلمة المرور",
                "تأكيد كلمة المرور",
            ],
            "en": [
                "Username",
                "First name",
                "Last name",
                "Email",
                "Password",
                "Confirm password",
            ],
            "fr": [
                "Nom d’utilisateur",
                "Prénom",
                "Nom",
                "E-mail",
                "Mot de passe",
                "Confirmer le mot de passe",
            ],
        }[selected_language]

        for field, label in zip(
            self.fields.values(),
            labels,
        ):
            field.label = label

    def clean_email(self):
        email = (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )

        if User.objects.filter(
            email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "هذا البريد الإلكتروني مستخدم بالفعل."
            )

        return email


# =========================================================
# Post Form - Image and Video
# =========================================================
class PostForm(LanguageFormMixin, forms.ModelForm):
    class Meta:
        model = Post

        fields = (
            "content",
            "image",
            "video",
        )

        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "post-textarea",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "accept": (
                        "image/jpeg,"
                        "image/png,"
                        "image/webp,"
                        "image/gif"
                    ),
                    "class": "media-file-input",
                }
            ),
            "video": forms.ClearableFileInput(
                attrs={
                    "accept": (
                        "video/mp4,"
                        "video/webm,"
                        "video/quicktime,"
                        "video/ogg,"
                        "video/x-m4v"
                    ),
                    "class": "media-file-input",
                }
            ),
        }

    def __init__(
        self,
        *args,
        language="ar",
        **kwargs,
    ):
        super().__init__(
            *args,
            language=language,
            **kwargs,
        )

        selected_language = (
            language
            if language in {"ar", "en", "fr"}
            else "ar"
        )

        video_labels = {
            "ar": "إضافة فيديو",
            "en": "Add video",
            "fr": "Ajouter une vidéo",
        }

        self.fields["content"].label = tr(
            "input_text",
            selected_language,
        )

        self.fields["content"].widget.attrs[
            "placeholder"
        ] = tr(
            "post_placeholder",
            selected_language,
        )

        self.fields["image"].label = tr(
            "add_image",
            selected_language,
        )

        self.fields["video"].label = (
            video_labels[selected_language]
        )

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if image:
            maximum_image_size = 10 * 1024 * 1024

            if image.size > maximum_image_size:
                raise forms.ValidationError(
                    "حجم الصورة يجب ألا يتجاوز "
                    "10 ميجابايت."
                )

        return image

    def clean_video(self):
        video = self.cleaned_data.get("video")

        if video:
            maximum_video_size = 100 * 1024 * 1024

            if video.size > maximum_video_size:
                raise forms.ValidationError(
                    "حجم الفيديو يجب ألا يتجاوز "
                    "100 ميجابايت."
                )

        return video

    def clean(self):
        cleaned_data = super().clean()

        content = (
            cleaned_data.get("content") or ""
        ).strip()

        image = cleaned_data.get("image")
        video = cleaned_data.get("video")

        if not content and not image and not video:
            language = self.language

            validation_messages = {
                "ar": (
                    "اكتب نصًا أو أضف صورة أو فيديو."
                ),
                "en": (
                    "Add text, an image, or a video."
                ),
                "fr": (
                    "Ajoutez du texte, une image "
                    "ou une vidéo."
                ),
            }

            selected_language = (
                language
                if language in validation_messages
                else "ar"
            )

            raise forms.ValidationError(
                validation_messages[
                    selected_language
                ]
            )

        cleaned_data["content"] = content

        return cleaned_data


# =========================================================
# Comment Form
# =========================================================
class CommentForm(
    LanguageFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = Comment
        fields = ("body",)

        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 2,
                }
            )
        }

    def __init__(
        self,
        *args,
        language="ar",
        **kwargs,
    ):
        super().__init__(
            *args,
            language=language,
            **kwargs,
        )

        self.fields["body"].label = tr(
            "comments",
            language,
        )

        self.fields["body"].widget.attrs[
            "placeholder"
        ] = tr(
            "comment_placeholder",
            language,
        )


# =========================================================
# User Update Form
# =========================================================
class UserUpdateForm(
    LanguageFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = User

        fields = (
            "first_name",
            "last_name",
            "email",
        )


# =========================================================
# Profile Update Form
# =========================================================
class ProfileUpdateForm(
    LanguageFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = Profile

        fields = (
            "avatar",
            "bio",
            "location",
            "preferred_language",
        )

        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            )
        }


# =========================================================
# Direct Message Form
# =========================================================
class DirectMessageForm(
    LanguageFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = DirectMessage

        fields = ("body",)

        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 2,
                    "maxlength": 4000,
                }
            )
        }

    def __init__(
        self,
        *args,
        language="ar",
        **kwargs,
    ):
        super().__init__(
            *args,
            language=language,
            **kwargs,
        )

        self.fields["body"].label = ""

        self.fields["body"].widget.attrs[
            "placeholder"
        ] = tr(
            "type_message",
            language,
        )


# =========================================================
# Report Form
# =========================================================
class ReportForm(
    LanguageFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = Report

        fields = (
            "reason",
            "details",
        )

        widgets = {
            "details": forms.Textarea(
                attrs={
                    "rows": 4,
                }
            )
        }

    def __init__(
        self,
        *args,
        language="ar",
        **kwargs,
    ):
        super().__init__(
            *args,
            language=language,
            **kwargs,
        )

        self.fields["reason"].label = tr(
            "report_reason",
            language,
        )

        self.fields["details"].label = tr(
            "report_details",
            language,
        )

        self.fields["reason"].choices = [
            (
                "spam",
                tr("spam", language),
            ),
            (
                "harassment",
                tr("harassment", language),
            ),
            (
                "violence",
                tr("violence", language),
            ),
            (
                "privacy",
                tr("privacy", language),
            ),
            (
                "misinformation",
                tr("misinformation", language),
            ),
            (
                "other",
                tr("other", language),
            ),
        ]


# =========================================================
# AI Tool Form
# =========================================================
class AIToolForm(forms.Form):
    FEATURE_CHOICES = [
        (
            "assistant",
            "Assistant",
        ),
        (
            "translation",
            "Translation",
        ),
        (
            "analysis",
            "Content analysis",
        ),
    ]

    LANGUAGE_CHOICES = [
        (
            "ar",
            "العربية",
        ),
        (
            "en",
            "English",
        ),
        (
            "fr",
            "Français",
        ),
    ]

    feature = forms.ChoiceField(
        choices=FEATURE_CHOICES,
    )

    text = forms.CharField(
        max_length=6000,
        widget=forms.Textarea(
            attrs={
                "rows": 7,
            }
        ),
    )

    source_language = forms.ChoiceField(
        choices=LANGUAGE_CHOICES,
        required=False,
    )

    target_language = forms.ChoiceField(
        choices=LANGUAGE_CHOICES,
        required=False,
    )

    def __init__(
        self,
        *args,
        language="ar",
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields["feature"].choices = [
            (
                "assistant",
                tr("assistant", language),
            ),
            (
                "translation",
                tr("translation", language),
            ),
            (
                "analysis",
                tr(
                    "content_analysis",
                    language,
                ),
            ),
        ]

        self.fields["feature"].label = tr(
            "ai_tools",
            language,
        )

        self.fields["text"].label = tr(
            "input_text",
            language,
        )

        self.fields[
            "source_language"
        ].label = tr(
            "source_language",
            language,
        )

        self.fields[
            "target_language"
        ].label = tr(
            "target_language",
            language,
        )