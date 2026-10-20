from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.urls import reverse
from django.utils import timezone


# =========================================================
# User Profile
# =========================================================
class Profile(models.Model):
    LANGUAGE_CHOICES = [
        ("ar", "العربية"),
        ("en", "English"),
        ("fr", "Français"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                ]
            )
        ],
    )

    bio = models.CharField(
        max_length=220,
        blank=True,
    )

    location = models.CharField(
        max_length=100,
        blank=True,
    )

    preferred_language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="ar",
    )

    is_verified = models.BooleanField(
        default=False,
    )

    is_suspended = models.BooleanField(
        default=False,
        db_index=True,
    )

    suspension_reason = models.CharField(
        max_length=300,
        blank=True,
    )

    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"Profile {self.user.username}"


# =========================================================
# Posts
# =========================================================
class Post(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("review", "Pending review"),
        ("hidden", "Hidden"),
        ("removed", "Removed"),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )

    content = models.TextField(
        max_length=3000,
        blank=True,
        verbose_name="محتوى المنشور",
    )

    image = models.ImageField(
        upload_to="posts/images/%Y/%m/%d/",
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                    "gif",
                ]
            )
        ],
        verbose_name="صورة",
    )

    video = models.FileField(
        upload_to="posts/videos/%Y/%m/%d/",
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "mp4",
                    "webm",
                    "mov",
                    "m4v",
                    "ogg",
                    "ogv",
                ]
            )
        ],
        verbose_name="فيديو",
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
    )

    moderation_reason = models.CharField(
        max_length=400,
        blank=True,
    )

    ai_risk_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    ai_label = models.CharField(
        max_length=80,
        blank=True,
    )

    ai_summary = models.CharField(
        max_length=400,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post {self.author.username}: {self.content[:40]}"

    def get_absolute_url(self):
        return reverse(
            "post_detail",
            args=[self.pk],
        )

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.filter(
            status="active"
        ).count()


# =========================================================
# Comments
# =========================================================
class Comment(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("hidden", "Hidden"),
        ("removed", "Removed"),
    ]

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    body = models.TextField(
        max_length=800,
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
    )

    ai_risk_score = models.PositiveSmallIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment {self.author.username}"


# =========================================================
# Likes
# =========================================================
class Like(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="likes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"],
                name="unique_post_like",
            )
        ]

    def __str__(self):
        return (
            f"{self.user.username} "
            f"liked post {self.post_id}"
        )


# =========================================================
# Blocks
# =========================================================
class Block(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_created",
    )

    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_received",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="unique_user_block",
            )
        ]

    def clean(self):
        if self.blocker_id == self.blocked_id:
            raise ValidationError(
                "A user cannot block themselves."
            )

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"


# =========================================================
# Conversations
# =========================================================
class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ConversationMember",
        related_name="conversations",
    )

    title = models.CharField(
        max_length=160,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Conversation {self.pk}"

    def other_participant(self, user):
        return self.participants.exclude(
            pk=user.pk
        ).first()


class ConversationMember(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="members",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_memberships",
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    last_read_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="unique_conversation_member",
            )
        ]

    def __str__(self):
        return f"{self.user} in {self.conversation_id}"


# =========================================================
# Direct Messages
# =========================================================
class DirectMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direct_messages",
    )

    body = models.TextField(
        max_length=4000,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    ai_risk_score = models.PositiveSmallIntegerField(
        default=0,
    )

    ai_label = models.CharField(
        max_length=80,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message {self.pk} by {self.sender}"


# =========================================================
# Notifications
# =========================================================
class Notification(models.Model):
    KIND_CHOICES = [
        ("like", "Like"),
        ("comment", "Comment"),
        ("message", "Message"),
        ("moderation", "Moderation"),
        ("system", "System"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="actions",
    )

    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default="system",
        db_index=True,
    )

    text = models.CharField(
        max_length=300,
    )

    link = models.CharField(
        max_length=300,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Notification for "
            f"{self.recipient}: {self.text[:40]}"
        )


# =========================================================
# Reports
# =========================================================
class Report(models.Model):
    REASON_CHOICES = [
        ("spam", "Spam or fraud"),
        ("harassment", "Harassment or abuse"),
        ("violence", "Threat or violence"),
        ("privacy", "Privacy violation"),
        ("misinformation", "Misinformation"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]

    TARGET_CHOICES = [
        ("post", "Post"),
        ("user", "User"),
        ("message", "Message"),
        ("comment", "Comment"),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_created",
    )

    target_type = models.CharField(
        max_length=12,
        choices=TARGET_CHOICES,
    )

    post = models.ForeignKey(
        Post,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reports_received",
    )

    message = models.ForeignKey(
        DirectMessage,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    comment = models.ForeignKey(
        Comment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    reason = models.CharField(
        max_length=24,
        choices=REASON_CHOICES,
    )

    details = models.TextField(
        max_length=1000,
        blank=True,
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="open",
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports_reviewed",
    )

    review_note = models.CharField(
        max_length=500,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Report {self.pk}: "
            f"{self.target_type}/{self.reason}"
        )

    @property
    def target_object(self):
        objects = {
            "post": self.post,
            "user": self.target_user,
            "message": self.message,
            "comment": self.comment,
        }

        return objects.get(self.target_type)


# =========================================================
# Moderation Actions
# =========================================================
class ModerationAction(models.Model):
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="moderation_actions",
    )

    action = models.CharField(
        max_length=60,
    )

    target_type = models.CharField(
        max_length=30,
    )

    target_id = models.PositiveIntegerField()

    reason = models.CharField(
        max_length=500,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.action} on "
            f"{self.target_type} {self.target_id}"
        )


# =========================================================
# AI Interactions
# =========================================================
class AIInteraction(models.Model):
    FEATURE_CHOICES = [
        ("assistant", "Assistant"),
        ("translation", "Translation"),
        ("analysis", "Analysis"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_interactions",
    )

    feature = models.CharField(
        max_length=20,
        choices=FEATURE_CHOICES,
    )

    input_text = models.TextField(
        max_length=6000,
    )

    output_text = models.TextField()

    source_language = models.CharField(
        max_length=20,
        blank=True,
    )

    target_language = models.CharField(
        max_length=20,
        blank=True,
    )

    provider = models.CharField(
        max_length=30,
        default="local",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.feature} interaction "
            f"by {self.user}"
        )