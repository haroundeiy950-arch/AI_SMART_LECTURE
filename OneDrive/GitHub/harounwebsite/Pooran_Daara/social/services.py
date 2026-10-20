from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from django.urls import reverse

from .models import Block, Notification


def users_blocked(user_a, user_b):
    if not user_a or not user_b:
        return False
    return Block.objects.filter(
        Q(blocker=user_a, blocked=user_b) | Q(blocker=user_b, blocked=user_a)
    ).exists()


def create_notification(*, recipient, text, kind="system", actor=None, link=""):
    if actor and recipient.pk == actor.pk:
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        kind=kind,
        text=text[:300],
        link=link[:300],
    )
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            f"notifications_{recipient.pk}",
            {
                "type": "notification.message",
                "notification": {
                    "id": notification.pk,
                    "kind": notification.kind,
                    "text": notification.text,
                    "link": notification.link or reverse("notifications"),
                    "created_at": notification.created_at.isoformat(),
                },
            },
        )
    return notification
