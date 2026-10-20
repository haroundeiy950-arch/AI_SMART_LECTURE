from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from social.models import Conversation, ConversationMember, DirectMessage, Notification, Post


class Command(BaseCommand):
    help = "Create demo users, posts, messages, and notifications"

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@example.com", "first_name": "Platform", "last_name": "Admin"},
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("Admin@12345")
        admin.save()
        admin.profile.preferred_language = "ar"
        admin.profile.is_verified = True
        admin.profile.save()

        demo_users = [
            ("amina", "Amina", "Mohammed", "amina@example.com", "ar"),
            ("haroun", "Haroun", "Mohammed", "haroun@example.com", "en"),
            ("youssef", "Youssef", "Ali", "youssef@example.com", "fr"),
        ]
        created_users = []
        for username, first, last, email, lang in demo_users:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "email": email},
            )
            user.set_password("Demo@12345")
            user.save()
            user.profile.preferred_language = lang
            user.profile.bio = "Pooran Daara demo member"
            user.profile.save()
            created_users.append(user)

        samples = [
            "مرحباً بكم في Pooran Daara، مساحة للتواصل ومشاركة المعرفة باحترام.",
            "Continuous learning helps us build a stronger future.",
            "Partagez une idée utile aujourd’hui et inspirez quelqu’un.",
        ]
        for user, text in zip(created_users, samples):
            Post.objects.get_or_create(author=user, content=text, defaults={"status": "active"})

        amina, haroun, _ = created_users
        conversation = (
            Conversation.objects.filter(members__user=amina)
            .filter(members__user=haroun)
            .first()
        )
        if conversation is None:
            conversation = Conversation.objects.create()
            ConversationMember.objects.create(conversation=conversation, user=amina)
            ConversationMember.objects.create(conversation=conversation, user=haroun)
        DirectMessage.objects.get_or_create(
            conversation=conversation,
            sender=amina,
            body="مرحباً هارون، هذه محادثة تجريبية فورية.",
        )
        Notification.objects.get_or_create(
            recipient=haroun,
            actor=amina,
            kind="message",
            text="New demo message from Amina.",
            link=f"/messages/{conversation.pk}/",
        )

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))
        self.stdout.write("Admin: admin / Admin@12345")
        self.stdout.write("Demo users: amina, haroun, youssef / Demo@12345")
