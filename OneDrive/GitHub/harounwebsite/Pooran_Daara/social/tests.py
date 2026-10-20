from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    AIInteraction,
    Block,
    Conversation,
    DirectMessage,
    Like,
    ModerationAction,
    Notification,
    Post,
    Report,
)


@override_settings(AI_PROVIDER="local", PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SocialFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", first_name="Test", email="tester@example.com", password="StrongPass123!"
        )
        self.other = User.objects.create_user(
            username="other", first_name="Other", email="other@example.com", password="StrongPass123!"
        )
        self.staff = User.objects.create_user(
            username="moderator", password="StrongPass123!", is_staff=True
        )

    def login(self, user=None):
        user = user or self.user
        self.client.force_login(user)

    def test_profile_created_automatically(self):
        self.assertEqual(self.user.profile.user, self.user)
        self.assertEqual(self.user.profile.preferred_language, "ar")

    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_user_can_create_safe_post(self):
        self.login()
        response = self.client.post(reverse("create_post"), {"content": "منشور تجريبي محترم"})
        self.assertRedirects(response, reverse("home"))
        post = Post.objects.get(author=self.user)
        self.assertEqual(post.status, "active")
        self.assertEqual(post.ai_risk_score, 0)

    def test_high_risk_post_is_held_for_review(self):
        self.login()
        self.client.post(reverse("create_post"), {"content": "سوف أقتلك"})
        post = Post.objects.get(author=self.user)
        self.assertEqual(post.status, "review")
        self.assertGreaterEqual(post.ai_risk_score, 85)

    def test_user_can_like_unlike_and_owner_gets_notification(self):
        post = Post.objects.create(author=self.other, content="Like test")
        self.login()
        self.client.post(reverse("toggle_like", args=[post.pk]))
        self.assertTrue(Like.objects.filter(post=post, user=self.user).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.other, actor=self.user, kind="like").exists())
        self.client.post(reverse("toggle_like", args=[post.pk]))
        self.assertFalse(Like.objects.filter(post=post, user=self.user).exists())

    def test_other_user_cannot_delete_post(self):
        post = Post.objects.create(author=self.user, content="Protected")
        self.login(self.other)
        response = self.client.post(reverse("delete_post", args=[post.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_start_conversation_and_send_message(self):
        self.login()
        response = self.client.post(reverse("start_conversation", args=[self.other.username]))
        conversation = Conversation.objects.get()
        self.assertRedirects(response, reverse("conversation_detail", args=[conversation.pk]))
        self.assertEqual(conversation.participants.count(), 2)
        response = self.client.post(reverse("send_message", args=[conversation.pk]), {"body": "Hello there"})
        self.assertRedirects(response, reverse("conversation_detail", args=[conversation.pk]))
        self.assertTrue(DirectMessage.objects.filter(conversation=conversation, sender=self.user, body="Hello there").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.other, kind="message").exists())

    def test_block_prevents_new_conversation(self):
        Block.objects.create(blocker=self.other, blocked=self.user)
        self.login()
        response = self.client.post(reverse("start_conversation", args=[self.other.username]))
        self.assertRedirects(response, reverse("profile", args=[self.other.username]))
        self.assertEqual(Conversation.objects.count(), 0)

    def test_report_post(self):
        post = Post.objects.create(author=self.other, content="Report target")
        self.login()
        response = self.client.post(
            reverse("report_target", args=["post", post.pk]),
            {"reason": "spam", "details": "Repeated suspicious links"},
        )
        self.assertRedirects(response, reverse("home"))
        report = Report.objects.get()
        self.assertEqual(report.post, post)
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.status, "open")

    def test_hidden_posts_not_in_search(self):
        Post.objects.create(author=self.other, content="unique-visible-term", status="hidden")
        response = self.client.get(reverse("search"), {"q": "unique-visible-term"})
        self.assertEqual(response.context["posts"].count(), 0)

    def test_language_switch_updates_profile_and_session(self):
        self.login()
        response = self.client.post(reverse("set_language"), {"language": "fr", "next": reverse("home")})
        self.assertRedirects(response, reverse("home"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.preferred_language, "fr")
        self.assertEqual(self.client.session["site_language"], "fr")

    def test_language_switch_rejects_external_redirect(self):
        self.login()
        response = self.client.post(reverse("set_language"), {"language": "en", "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("home"))

    def test_local_ai_translation_is_saved(self):
        self.login()
        response = self.client.post(
            reverse("ai_tools"),
            {"feature": "translation", "text": "مرحبا", "source_language": "ar", "target_language": "en"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello")
        item = AIInteraction.objects.get()
        self.assertEqual(item.provider, "local")
        self.assertEqual(item.output_text, "Hello")

    def test_non_staff_cannot_open_moderation_dashboard(self):
        self.login()
        response = self.client.get(reverse("moderation_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_suspend_and_reactivate_user(self):
        self.login(self.staff)
        response = self.client.post(
            reverse("moderation_user_quick_action"),
            {"username": self.other.username, "action": "suspend", "reason": "Policy review"},
        )
        self.assertRedirects(response, reverse("moderation_dashboard"))
        self.other.profile.refresh_from_db()
        self.assertTrue(self.other.profile.is_suspended)
        self.assertTrue(ModerationAction.objects.filter(target_id=self.other.pk, action="suspend").exists())
        self.client.post(
            reverse("moderation_user_quick_action"),
            {"username": self.other.username, "action": "activate", "reason": "Resolved"},
        )
        self.other.profile.refresh_from_db()
        self.assertFalse(self.other.profile.is_suspended)

    def test_suspended_user_is_blocked_by_middleware(self):
        self.user.profile.is_suspended = True
        self.user.profile.suspension_reason = "Temporary review"
        self.user.profile.save()
        self.login()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Temporary review", status_code=403)

    def test_asgi_application_imports(self):
        from pooran_daara.asgi import application
        self.assertIsNotNone(application)
