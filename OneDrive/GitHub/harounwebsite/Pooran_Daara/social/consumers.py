from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.urls import reverse
from django.utils import timezone

from .ai_services import analyze_content
from .models import Conversation, ConversationMember, DirectMessage
from .services import create_notification, users_blocked


class NotificationConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            self.close(code=4401)
            return
        self.group_name = f"notifications_{user.pk}"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, code):
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def notification_message(self, event):
        self.send_json({"type": "notification", **event["notification"]})


class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.user = self.scope.get("user")
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        if not self.user or not self.user.is_authenticated:
            self.close(code=4401)
            return
        if not ConversationMember.objects.filter(conversation_id=self.conversation_id, user=self.user).exists():
            self.close(code=4403)
            return
        self.group_name = f"conversation_{self.conversation_id}"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, code):
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def receive_json(self, content, **kwargs):
        body = str(content.get("message", "")).strip()
        if not body or len(body) > 4000:
            self.send_json({"type": "error", "message": "Invalid message."})
            return
        conversation = Conversation.objects.filter(pk=self.conversation_id, members__user=self.user).first()
        if conversation is None:
            self.close(code=4403)
            return
        other = conversation.other_participant(self.user)
        if other is None or users_blocked(self.user, other):
            self.send_json({"type": "error", "message": "Messaging is blocked."})
            return
        analysis = analyze_content(body)
        if analysis["risk_score"] >= 90:
            self.send_json({"type": "error", "message": "This message was blocked by the safety check."})
            return
        message = DirectMessage.objects.create(
            conversation=conversation,
            sender=self.user,
            body=body,
            ai_risk_score=analysis["risk_score"],
            ai_label=analysis["label"],
        )
        conversation.save(update_fields=["updated_at"])
        sender_name = self.user.get_full_name() or self.user.username
        payload = {
            "id": message.pk,
            "body": message.body,
            "sender_id": self.user.pk,
            "sender_username": self.user.username,
            "sender_name": sender_name,
            "created_at": timezone.localtime(message.created_at).strftime("%Y-%m-%d %H:%M"),
        }
        async_to_sync(self.channel_layer.group_send)(
            self.group_name, {"type": "chat.message", "message": payload}
        )
        other_lang = other.profile.preferred_language
        text = {
            "ar": f"رسالة جديدة من {sender_name}.",
            "en": f"New message from {sender_name}.",
            "fr": f"Nouveau message de {sender_name}.",
        }.get(other_lang, f"New message from {sender_name}.")
        create_notification(
            recipient=other,
            actor=self.user,
            kind="message",
            text=text,
            link=reverse("conversation_detail", args=[conversation.pk]),
        )

    def chat_message(self, event):
        self.send_json({"type": "message", **event["message"]})
