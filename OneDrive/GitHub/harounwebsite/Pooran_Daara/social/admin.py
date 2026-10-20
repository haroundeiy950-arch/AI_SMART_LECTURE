from django.contrib import admin

from .models import (
    AIInteraction,
    Block,
    Comment,
    Conversation,
    ConversationMember,
    DirectMessage,
    Like,
    ModerationAction,
    Notification,
    Post,
    Profile,
    Report,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "preferred_language", "is_verified", "is_suspended", "created_at")
    list_filter = ("preferred_language", "is_verified", "is_suspended")
    search_fields = ("user__username", "user__first_name", "user__last_name", "location")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "short_content", "status", "ai_risk_score", "created_at")
    list_filter = ("status", "ai_label", "created_at")
    search_fields = ("content", "author__username")
    actions = ("make_active", "make_hidden", "make_removed")

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:70]

    @admin.action(description="Mark selected posts active")
    def make_active(self, request, queryset):
        queryset.update(status="active")

    @admin.action(description="Hide selected posts")
    def make_hidden(self, request, queryset):
        queryset.update(status="hidden")

    @admin.action(description="Remove selected posts")
    def make_removed(self, request, queryset):
        queryset.update(status="removed")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "post", "status", "ai_risk_score", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("body", "author__username")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "target_type", "reason", "status", "created_at")
    list_filter = ("target_type", "reason", "status")
    search_fields = ("details", "reporter__username", "target_user__username")


admin.site.register(Like)
admin.site.register(Block)
admin.site.register(Conversation)
admin.site.register(ConversationMember)
admin.site.register(DirectMessage)
admin.site.register(Notification)
admin.site.register(ModerationAction)
admin.site.register(AIInteraction)

admin.site.site_header = "Pooran Daara Administration"
admin.site.site_title = "Pooran Daara Admin"
