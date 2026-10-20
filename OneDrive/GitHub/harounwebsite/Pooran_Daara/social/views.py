from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .ai_services import (
    analyze_content,
    assistant_reply,
    translate_text,
)
from .forms import (
    AIToolForm,
    CommentForm,
    DirectMessageForm,
    PostForm,
    ProfileUpdateForm,
    RegisterForm,
    ReportForm,
    UserUpdateForm,
)
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
    Report,
)
from .services import create_notification, users_blocked
from .translations import (
    SUPPORTED_LANGUAGES,
    get_language,
    tr,
)


# =========================================================
# Language
# =========================================================
def language(request):
    return get_language(request)


# =========================================================
# Staff permission decorator
# =========================================================
def staff_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied(
                tr(
                    "admin_only",
                    language(request),
                )
            )

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapper


# =========================================================
# Blocked users helpers
# =========================================================
def _blocked_ids(user):
    if not user.is_authenticated:
        return set()

    outgoing = Block.objects.filter(
        blocker=user
    ).values_list(
        "blocked_id",
        flat=True,
    )

    incoming = Block.objects.filter(
        blocked=user
    ).values_list(
        "blocker_id",
        flat=True,
    )

    return set(outgoing).union(incoming)


def _visible_posts_for(user):
    posts = Post.objects.filter(
        status="active",
        author__profile__is_suspended=False,
    )

    if user.is_authenticated:
        posts = posts.exclude(
            author_id__in=_blocked_ids(user)
        )

    return posts


# =========================================================
# Landing page
# =========================================================
def landing(request):
    if request.user.is_authenticated:
        return redirect("home")

    recent_posts = (
        Post.objects.filter(
            status="active",
            author__profile__is_suspended=False,
        )
        .select_related(
            "author",
            "author__profile",
        )[:6]
    )

    return render(
        request,
        "social/landing.html",
        {
            "recent_posts": recent_posts,
        },
    )


# =========================================================
# Registration
# =========================================================
def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    lang = language(request)

    if request.method == "POST":
        form = RegisterForm(
            request.POST,
            language=lang,
        )

        if form.is_valid():
            user = form.save()

            user.profile.preferred_language = lang
            user.profile.save(
                update_fields=[
                    "preferred_language",
                ]
            )

            login(
                request,
                user,
            )

            messages.success(
                request,
                f"{tr('welcome', lang)}. "
                f"{tr('created_ok', lang)}",
            )

            return redirect("home")

    else:
        form = RegisterForm(
            language=lang,
        )

    return render(
        request,
        "registration/register.html",
        {
            "form": form,
        },
    )


# =========================================================
# Home feed
# =========================================================
@login_required
def home(request):
    lang = language(request)

    posts_query = (
        _visible_posts_for(request.user)
        .select_related(
            "author",
            "author__profile",
        )
        .prefetch_related(
            "likes",
            "comments__author",
        )
    )

    paginator = Paginator(
        posts_query,
        10,
    )

    posts = paginator.get_page(
        request.GET.get("page")
    )

    liked_ids = set(
        Like.objects.filter(
            user=request.user,
            post__in=posts.object_list,
        ).values_list(
            "post_id",
            flat=True,
        )
    )

    post_form = PostForm(
        language=lang,
    )

    return render(
        request,
        "social/home.html",
        {
            "posts": posts,
            "post_form": post_form,
            "liked_ids": liked_ids,
        },
    )


# =========================================================
# Create post with image and video
# =========================================================
@login_required
@require_POST
def create_post(request):
    lang = language(request)

    form = PostForm(
        request.POST,
        request.FILES,
        language=lang,
    )

    if form.is_valid():
        post = form.save(
            commit=False
        )

        post.author = request.user

        analysis = analyze_content(
            post.content
        )

        post.ai_risk_score = analysis[
            "risk_score"
        ]

        post.ai_label = analysis[
            "label"
        ]

        post.ai_summary = analysis[
            "summary"
        ]

        if post.ai_risk_score >= 85:
            post.status = "review"

            post.moderation_reason = (
                "Automatically held for "
                "moderator review."
            )

        post.save()

        if post.status == "review":
            messages.warning(
                request,
                tr(
                    "post_review",
                    lang,
                ),
            )

        else:
            messages.success(
                request,
                tr(
                    "post_created",
                    lang,
                ),
            )

    else:
        error_messages = {
            "ar": (
                "تعذر إنشاء المنشور. "
                "أضف نصًا أو صورة أو فيديو صالحًا."
            ),
            "en": (
                "Could not create the post. "
                "Add valid text, an image, or a video."
            ),
            "fr": (
                "Impossible de créer la publication. "
                "Ajoutez un texte, une image "
                "ou une vidéo valide."
            ),
        }

        messages.error(
            request,
            error_messages.get(
                lang,
                error_messages["ar"],
            ),
        )

        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(
                    request,
                    str(error),
                )

    return redirect("home")


# =========================================================
# Post details
# =========================================================
def post_detail(request, pk):
    post = get_object_or_404(
        Post.objects.select_related(
            "author",
            "author__profile",
        ).prefetch_related(
            "comments__author__profile",
        ),
        pk=pk,
    )

    can_review = (
        request.user.is_authenticated
        and (
            request.user == post.author
            or request.user.is_staff
        )
    )

    if post.status != "active" and not can_review:
        raise Http404

    if (
        request.user.is_authenticated
        and users_blocked(
            request.user,
            post.author,
        )
    ):
        raise Http404

    liked = (
        request.user.is_authenticated
        and post.likes.filter(
            user=request.user
        ).exists()
    )

    if can_review:
        visible_comments = post.comments.all()
    else:
        visible_comments = post.comments.filter(
            status="active"
        )

    return render(
        request,
        "social/post_detail.html",
        {
            "post": post,
            "visible_comments": visible_comments,
            "comment_form": CommentForm(
                language=language(request)
            ),
            "liked": liked,
        },
    )


# =========================================================
# Edit post
# =========================================================
@login_required
def edit_post(request, pk):
    lang = language(request)

    post = get_object_or_404(
        Post,
        pk=pk,
        author=request.user,
    )

    if request.method == "POST":
        form = PostForm(
            request.POST,
            request.FILES,
            instance=post,
            language=lang,
        )

        if form.is_valid():
            post = form.save(
                commit=False
            )

            analysis = analyze_content(
                post.content
            )

            post.ai_risk_score = analysis[
                "risk_score"
            ]

            post.ai_label = analysis[
                "label"
            ]

            post.ai_summary = analysis[
                "summary"
            ]

            if post.ai_risk_score >= 85:
                post.status = "review"

                post.moderation_reason = (
                    "Automatically held for "
                    "moderator review."
                )

            elif (
                post.status == "review"
                and post.moderation_reason.startswith(
                    "Automatically"
                )
            ):
                post.status = "active"
                post.moderation_reason = ""

            post.save()

            messages.success(
                request,
                tr(
                    "post_updated",
                    lang,
                ),
            )

            return redirect(
                "post_detail",
                pk=post.pk,
            )

    else:
        form = PostForm(
            instance=post,
            language=lang,
        )

    return render(
        request,
        "social/form_page.html",
        {
            "form": form,
            "title": tr(
                "edit",
                lang,
            ),
            "button": tr(
                "save",
                lang,
            ),
        },
    )


# =========================================================
# Delete post
# =========================================================
@login_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(
        Post,
        pk=pk,
        author=request.user,
    )

    post.delete()

    messages.success(
        request,
        tr(
            "post_deleted",
            language(request),
        ),
    )

    return redirect("home")


# =========================================================
# Likes
# =========================================================
@login_required
@require_POST
def toggle_like(request, pk):
    post = get_object_or_404(
        Post,
        pk=pk,
        status="active",
    )

    if users_blocked(
        request.user,
        post.author,
    ):
        raise Http404

    like, created = Like.objects.get_or_create(
        post=post,
        user=request.user,
    )

    if not created:
        like.delete()

    elif post.author != request.user:
        owner_language = (
            post.author
            .profile
            .preferred_language
        )

        actor_name = (
            request.user.get_full_name()
            or request.user.username
        )

        notification_text = {
            "ar": (
                f"أعجب {actor_name} بمنشورك."
            ),
            "en": (
                f"{actor_name} liked your post."
            ),
            "fr": (
                f"{actor_name} a aimé "
                f"votre publication."
            ),
        }.get(
            owner_language,
            f"{actor_name} liked your post.",
        )

        create_notification(
            recipient=post.author,
            actor=request.user,
            kind="like",
            text=notification_text,
            link=post.get_absolute_url(),
        )

    if (
        request.headers.get(
            "x-requested-with"
        )
        == "XMLHttpRequest"
    ):
        return JsonResponse(
            {
                "liked": created,
                "count": post.likes.count(),
            }
        )

    return redirect(
        request.POST.get("next")
        or post.get_absolute_url()
    )


# =========================================================
# Add comment
# =========================================================
@login_required
@require_POST
def add_comment(request, pk):
    lang = language(request)

    post = get_object_or_404(
        Post,
        pk=pk,
        status="active",
    )

    if users_blocked(
        request.user,
        post.author,
    ):
        raise Http404

    form = CommentForm(
        request.POST,
        language=lang,
    )

    if form.is_valid():
        comment = form.save(
            commit=False
        )

        comment.post = post
        comment.author = request.user

        analysis = analyze_content(
            comment.body
        )

        comment.ai_risk_score = analysis[
            "risk_score"
        ]

        if comment.ai_risk_score >= 85:
            comment.status = "hidden"

        comment.save()

        if comment.status == "active":
            messages.success(
                request,
                tr(
                    "comment_added",
                    lang,
                ),
            )

            if post.author != request.user:
                owner_language = (
                    post.author
                    .profile
                    .preferred_language
                )

                actor_name = (
                    request.user.get_full_name()
                    or request.user.username
                )

                notification_text = {
                    "ar": (
                        f"علّق {actor_name} "
                        f"على منشورك."
                    ),
                    "en": (
                        f"{actor_name} commented "
                        f"on your post."
                    ),
                    "fr": (
                        f"{actor_name} a commenté "
                        f"votre publication."
                    ),
                }.get(
                    owner_language,
                    (
                        f"{actor_name} commented "
                        f"on your post."
                    ),
                )

                create_notification(
                    recipient=post.author,
                    actor=request.user,
                    kind="comment",
                    text=notification_text,
                    link=post.get_absolute_url(),
                )

        else:
            messages.warning(
                request,
                tr(
                    "post_review",
                    lang,
                ),
            )

    else:
        messages.error(
            request,
            "Invalid comment.",
        )

    return redirect(
        "post_detail",
        pk=pk,
    )


# =========================================================
# Delete comment
# =========================================================
@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(
        Comment,
        pk=pk,
    )

    allowed = (
        comment.author == request.user
        or comment.post.author == request.user
        or request.user.is_staff
    )

    if not allowed:
        raise Http404

    post_id = comment.post_id

    comment.delete()

    return redirect(
        "post_detail",
        pk=post_id,
    )


# =========================================================
# Profile
# =========================================================
def profile_view(request, username):
    profile_user = get_object_or_404(
        User.objects.select_related(
            "profile"
        ),
        username=username,
    )

    if (
        profile_user.profile.is_suspended
        and not (
            request.user.is_authenticated
            and request.user.is_staff
        )
    ):
        raise Http404

    is_blocked = (
        request.user.is_authenticated
        and users_blocked(
            request.user,
            profile_user,
        )
    )

    if (
        is_blocked
        and request.user != profile_user
    ):
        posts_query = Post.objects.none()

    else:
        posts_query = (
            profile_user.posts.filter(
                status="active"
            )
            .prefetch_related(
                "likes",
                "comments",
            )
        )

    posts = Paginator(
        posts_query,
        10,
    ).get_page(
        request.GET.get("page")
    )

    blocked_by_me = (
        request.user.is_authenticated
        and Block.objects.filter(
            blocker=request.user,
            blocked=profile_user,
        ).exists()
    )

    return render(
        request,
        "social/profile.html",
        {
            "profile_user": profile_user,
            "posts": posts,
            "is_blocked": is_blocked,
            "blocked_by_me": blocked_by_me,
        },
    )


# =========================================================
# Edit profile
# =========================================================
@login_required
def edit_profile(request):
    lang = language(request)

    if request.method == "POST":
        user_form = UserUpdateForm(
            request.POST,
            instance=request.user,
            language=lang,
        )

        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user.profile,
            language=lang,
        )

        if (
            user_form.is_valid()
            and profile_form.is_valid()
        ):
            user_form.save()

            profile = profile_form.save()

            request.session[
                "site_language"
            ] = profile.preferred_language

            messages.success(
                request,
                tr(
                    "profile_updated",
                    profile.preferred_language,
                ),
            )

            return redirect(
                "profile",
                username=request.user.username,
            )

    else:
        user_form = UserUpdateForm(
            instance=request.user,
            language=lang,
        )

        profile_form = ProfileUpdateForm(
            instance=request.user.profile,
            language=lang,
        )

    return render(
        request,
        "social/edit_profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
        },
    )


# =========================================================
# Search
# =========================================================
def search(request):
    query = request.GET.get(
        "q",
        "",
    ).strip()

    users = User.objects.none()
    posts = Post.objects.none()

    if request.user.is_authenticated:
        excluded_ids = _blocked_ids(
            request.user
        )
    else:
        excluded_ids = set()

    if query:
        users = (
            User.objects.select_related(
                "profile"
            )
            .filter(
                profile__is_suspended=False
            )
            .exclude(
                pk__in=excluded_ids
            )
            .filter(
                Q(
                    username__icontains=query
                )
                | Q(
                    first_name__icontains=query
                )
                | Q(
                    last_name__icontains=query
                )
            )[:20]
        )

        posts = (
            Post.objects.filter(
                status="active",
                author__profile__is_suspended=False,
            )
            .exclude(
                author_id__in=excluded_ids
            )
            .select_related(
                "author",
                "author__profile",
            )
            .filter(
                content__icontains=query
            )
            .annotate(
                total_likes=Count("likes")
            )[:30]
        )

    return render(
        request,
        "social/search.html",
        {
            "query": query,
            "users": users,
            "posts": posts,
        },
    )


# =========================================================
# Set language
# =========================================================
@require_POST
def set_language(request):
    selected = request.POST.get(
        "language",
        "ar",
    )

    if selected not in SUPPORTED_LANGUAGES:
        selected = "ar"

    request.session[
        "site_language"
    ] = selected

    if request.user.is_authenticated:
        request.user.profile.preferred_language = (
            selected
        )

        request.user.profile.save(
            update_fields=[
                "preferred_language",
            ]
        )

    next_url = (
        request.POST.get("next")
        or reverse("home")
    )

    allowed = url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={
            request.get_host()
        },
        require_https=request.is_secure(),
    )

    if not allowed:
        if request.user.is_authenticated:
            next_url = reverse("home")
        else:
            next_url = reverse("landing")

    return redirect(next_url)


# =========================================================
# Block and unblock
# =========================================================
@login_required
@require_POST
def toggle_block(request, username):
    target = get_object_or_404(
        User,
        username=username,
    )

    if target == request.user:
        raise Http404

    block, created = (
        Block.objects.get_or_create(
            blocker=request.user,
            blocked=target,
        )
    )

    if not created:
        block.delete()

        messages.success(
            request,
            tr(
                "unblocked",
                language(request),
            ),
        )

    else:
        messages.success(
            request,
            tr(
                "blocked",
                language(request),
            ),
        )

    return redirect(
        "profile",
        username=target.username,
    )


# =========================================================
# Private conversation helper
# =========================================================
def _private_conversation(user, other):
    return (
        Conversation.objects.filter(
            members__user=user
        )
        .filter(
            members__user=other
        )
        .annotate(
            member_count=Count(
                "members",
                distinct=True,
            )
        )
        .filter(
            member_count=2
        )
        .first()
    )


# =========================================================
# Start conversation
# =========================================================
@login_required
@require_POST
def start_conversation(request, username):
    other = get_object_or_404(
        User,
        username=username,
        profile__is_suspended=False,
    )

    if (
        other == request.user
        or users_blocked(
            request.user,
            other,
        )
    ):
        messages.error(
            request,
            tr(
                "message_blocked",
                language(request),
            ),
        )

        return redirect(
            "profile",
            username=other.username,
        )

    with transaction.atomic():
        conversation = _private_conversation(
            request.user,
            other,
        )

        if conversation is None:
            conversation = (
                Conversation.objects.create()
            )

            ConversationMember.objects.bulk_create(
                [
                    ConversationMember(
                        conversation=conversation,
                        user=request.user,
                    ),
                    ConversationMember(
                        conversation=conversation,
                        user=other,
                    ),
                ]
            )

    return redirect(
        "conversation_detail",
        pk=conversation.pk,
    )


# =========================================================
# Conversation list
# =========================================================
@login_required
def conversation_list(request):
    memberships = (
        ConversationMember.objects.filter(
            user=request.user
        )
        .select_related(
            "conversation"
        )
        .prefetch_related(
            "conversation__participants__profile",
            "conversation__messages",
        )
        .order_by(
            "-conversation__updated_at"
        )
    )

    rows = []

    for membership in memberships:
        conversation = membership.conversation

        other = conversation.other_participant(
            request.user
        )

        latest = (
            conversation.messages.filter(
                is_deleted=False
            )
            .select_related("sender")
            .last()
        )

        unread = (
            conversation.messages.filter(
                created_at__gt=membership.last_read_at,
                is_deleted=False,
            )
            .exclude(
                sender=request.user
            )
            .count()
        )

        rows.append(
            {
                "conversation": conversation,
                "other": other,
                "latest": latest,
                "unread": unread,
            }
        )

    return render(
        request,
        "social/chat_list.html",
        {
            "conversation_rows": rows,
        },
    )


# =========================================================
# Conversation details
# =========================================================
@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related(
            "participants__profile",
            "messages__sender__profile",
        ),
        pk=pk,
    )

    membership = get_object_or_404(
        ConversationMember,
        conversation=conversation,
        user=request.user,
    )

    other = conversation.other_participant(
        request.user
    )

    is_blocked = (
        other is not None
        and users_blocked(
            request.user,
            other,
        )
    )

    membership.last_read_at = timezone.now()

    membership.save(
        update_fields=[
            "last_read_at",
        ]
    )

    Notification.objects.filter(
        recipient=request.user,
        kind="message",
        is_read=False,
        link__contains=(
            f"/messages/{conversation.pk}/"
        ),
    ).update(
        is_read=True
    )

    message_items = (
        conversation.messages.filter(
            is_deleted=False
        )
        .select_related(
            "sender",
            "sender__profile",
        )
    )

    return render(
        request,
        "social/chat_detail.html",
        {
            "conversation": conversation,
            "other": other,
            "message_items": message_items,
            "message_form": DirectMessageForm(
                language=language(request)
            ),
            "is_blocked": is_blocked,
        },
    )


# =========================================================
# Send message
# =========================================================
@login_required
@require_POST
def send_message(request, pk):
    conversation = get_object_or_404(
        Conversation,
        pk=pk,
        members__user=request.user,
    )

    other = conversation.other_participant(
        request.user
    )

    if (
        other is None
        or users_blocked(
            request.user,
            other,
        )
    ):
        messages.error(
            request,
            tr(
                "message_blocked",
                language(request),
            ),
        )

        return redirect(
            "conversation_detail",
            pk=pk,
        )

    form = DirectMessageForm(
        request.POST,
        language=language(request),
    )

    if form.is_valid():
        analysis = analyze_content(
            form.cleaned_data["body"]
        )

        if analysis["risk_score"] >= 90:
            messages.error(
                request,
                tr(
                    "dangerous",
                    language(request),
                ),
            )

            return redirect(
                "conversation_detail",
                pk=pk,
            )

        message = form.save(
            commit=False
        )

        message.conversation = conversation
        message.sender = request.user

        message.ai_risk_score = analysis[
            "risk_score"
        ]

        message.ai_label = analysis[
            "label"
        ]

        message.save()

        conversation.save(
            update_fields=[
                "updated_at",
            ]
        )

        other_language = (
            other.profile.preferred_language
        )

        actor_name = (
            request.user.get_full_name()
            or request.user.username
        )

        notification_text = {
            "ar": (
                f"رسالة جديدة من {actor_name}."
            ),
            "en": (
                f"New message from {actor_name}."
            ),
            "fr": (
                f"Nouveau message de {actor_name}."
            ),
        }.get(
            other_language,
            f"New message from {actor_name}.",
        )

        create_notification(
            recipient=other,
            actor=request.user,
            kind="message",
            text=notification_text,
            link=reverse(
                "conversation_detail",
                args=[conversation.pk],
            ),
        )

    return redirect(
        "conversation_detail",
        pk=pk,
    )


# =========================================================
# Notifications
# =========================================================
@login_required
def notifications_view(request):
    notifications = Paginator(
        request.user.notifications.select_related(
            "actor"
        ),
        25,
    ).get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "social/notifications.html",
        {
            "notification_items": notifications,
        },
    )


@login_required
@require_POST
def notification_read(request, pk):
    item = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )

    item.is_read = True

    item.save(
        update_fields=[
            "is_read",
        ]
    )

    destination = (
        item.link
        or reverse("notifications")
    )

    allowed = url_has_allowed_host_and_scheme(
        destination,
        allowed_hosts={
            request.get_host()
        },
        require_https=request.is_secure(),
    )

    if not allowed:
        destination = reverse(
            "notifications"
        )

    return redirect(destination)


@login_required
@require_POST
def notifications_read_all(request):
    request.user.notifications.filter(
        is_read=False
    ).update(
        is_read=True
    )

    return redirect("notifications")


# =========================================================
# Reports
# =========================================================
@login_required
def report_target(
    request,
    target_type,
    pk,
):
    lang = language(request)

    target_map = {
        "post": (
            Post,
            "post",
        ),
        "user": (
            User,
            "target_user",
        ),
        "message": (
            DirectMessage,
            "message",
        ),
        "comment": (
            Comment,
            "comment",
        ),
    }

    if target_type not in target_map:
        raise Http404

    model, field_name = target_map[
        target_type
    ]

    target = get_object_or_404(
        model,
        pk=pk,
    )

    if (
        target_type == "message"
        and not target.conversation.members.filter(
            user=request.user
        ).exists()
    ):
        raise Http404

    if request.method == "POST":
        form = ReportForm(
            request.POST,
            language=lang,
        )

        if form.is_valid():
            report = form.save(
                commit=False
            )

            report.reporter = request.user
            report.target_type = target_type

            setattr(
                report,
                field_name,
                target,
            )

            report.save()

            messages.success(
                request,
                tr(
                    "report_sent",
                    lang,
                ),
            )

            return redirect("home")

    else:
        form = ReportForm(
            language=lang,
        )

    return render(
        request,
        "social/report_form.html",
        {
            "form": form,
            "target": target,
            "target_type": target_type,
        },
    )


# =========================================================
# AI tools
# =========================================================
@login_required
def ai_tools(request):
    lang = language(request)

    result = None
    analysis_data = None
    provider = None

    if request.method == "POST":
        form = AIToolForm(
            request.POST,
            language=lang,
        )

        if form.is_valid():
            feature = form.cleaned_data[
                "feature"
            ]

            text = form.cleaned_data[
                "text"
            ]

            source = (
                form.cleaned_data.get(
                    "source_language"
                )
                or lang
            )

            target = (
                form.cleaned_data.get(
                    "target_language"
                )
                or lang
            )

            if feature == "translation":
                ai_result = translate_text(
                    text,
                    source,
                    target,
                )

                result = ai_result.text
                provider = ai_result.provider

            elif feature == "analysis":
                analysis_data = analyze_content(
                    text
                )

                result = analysis_data[
                    "summary"
                ]

                provider = analysis_data[
                    "provider"
                ]

            else:
                ai_result = assistant_reply(
                    text,
                    lang,
                )

                result = ai_result.text
                provider = ai_result.provider

            AIInteraction.objects.create(
                user=request.user,
                feature=feature,
                input_text=text,
                output_text=result or "",
                source_language=source,
                target_language=target,
                provider=provider or "local",
            )

    else:
        form = AIToolForm(
            language=lang,
            initial={
                "source_language": lang,
                "target_language": (
                    "en"
                    if lang == "ar"
                    else "ar"
                ),
            },
        )

    history = (
        request.user
        .ai_interactions
        .all()[:8]
    )

    return render(
        request,
        "social/ai_tools.html",
        {
            "form": form,
            "result": result,
            "analysis_data": analysis_data,
            "provider": provider,
            "history": history,
        },
    )


# =========================================================
# Moderation dashboard
# =========================================================
@staff_required
def moderation_dashboard(request):
    context = {
        "total_users": (
            User.objects.count()
        ),
        "active_posts": (
            Post.objects.filter(
                status="active"
            ).count()
        ),
        "open_reports_count": (
            Report.objects.filter(
                status="open"
            ).count()
        ),
        "flagged_count": (
            Post.objects.filter(
                status="review"
            ).count()
            + Comment.objects.filter(
                status="hidden"
            ).count()
        ),
        "reports": (
            Report.objects.filter(
                status="open"
            )
            .select_related(
                "reporter",
                "target_user",
                "post__author",
                "message__sender",
                "comment__author",
            )[:30]
        ),
        "flagged_posts": (
            Post.objects.filter(
                status="review"
            )
            .select_related(
                "author"
            )[:20]
        ),
        "suspended_users": (
            User.objects.filter(
                profile__is_suspended=True
            )
            .select_related(
                "profile"
            )[:20]
        ),
        "recent_actions": (
            ModerationAction.objects
            .select_related(
                "moderator"
            )[:20]
        ),
    }

    return render(
        request,
        "social/moderation_dashboard.html",
        context,
    )


# =========================================================
# Report moderation action
# =========================================================
@staff_required
@require_POST
def moderation_report_action(
    request,
    pk,
):
    report = get_object_or_404(
        Report,
        pk=pk,
    )

    action = request.POST.get(
        "action"
    )

    note = request.POST.get(
        "note",
        "",
    )[:500]

    if action not in {
        "resolved",
        "dismissed",
    }:
        raise Http404

    report.status = action
    report.reviewed_by = request.user
    report.review_note = note
    report.reviewed_at = timezone.now()

    report.save(
        update_fields=[
            "status",
            "reviewed_by",
            "review_note",
            "reviewed_at",
        ]
    )

    ModerationAction.objects.create(
        moderator=request.user,
        action=f"report_{action}",
        target_type="report",
        target_id=report.pk,
        reason=note,
    )

    return redirect(
        "moderation_dashboard"
    )


# =========================================================
# Post moderation action
# =========================================================
@staff_required
@require_POST
def moderation_post_action(
    request,
    pk,
):
    post = get_object_or_404(
        Post,
        pk=pk,
    )

    action = request.POST.get(
        "action"
    )

    reason = request.POST.get(
        "reason",
        "",
    )[:400]

    mapping = {
        "hide": "hidden",
        "restore": "active",
        "remove": "removed",
    }

    if action not in mapping:
        raise Http404

    post.status = mapping[action]
    post.moderation_reason = reason

    post.save(
        update_fields=[
            "status",
            "moderation_reason",
        ]
    )

    ModerationAction.objects.create(
        moderator=request.user,
        action=action,
        target_type="post",
        target_id=post.pk,
        reason=reason,
    )

    owner_language = (
        post.author
        .profile
        .preferred_language
    )

    notification_text = {
        "ar": (
            "قامت الإدارة بتحديث حالة "
            f"منشورك إلى: "
            f"{post.get_status_display()}."
        ),
        "en": (
            "Moderation changed your "
            f"post status to: "
            f"{post.get_status_display()}."
        ),
        "fr": (
            "La modération a changé "
            "le statut de votre publication : "
            f"{post.get_status_display()}."
        ),
    }.get(
        owner_language,
        (
            "Moderation changed your "
            f"post status to: "
            f"{post.get_status_display()}."
        ),
    )

    create_notification(
        recipient=post.author,
        actor=request.user,
        kind="moderation",
        text=notification_text,
        link=post.get_absolute_url(),
    )

    return redirect(
        "moderation_dashboard"
    )


# =========================================================
# Quick user moderation action
# =========================================================
@staff_required
@require_POST
def moderation_user_quick_action(request):
    username = request.POST.get(
        "username",
        "",
    ).strip()

    target = get_object_or_404(
        User,
        username=username,
    )

    if (
        target.is_superuser
        and target != request.user
    ):
        raise PermissionDenied

    action = request.POST.get(
        "action"
    )

    reason = request.POST.get(
        "reason",
        "",
    )[:300]

    if action == "suspend":
        target.profile.is_suspended = True
        target.profile.suspension_reason = reason
        target.profile.suspended_at = (
            timezone.now()
        )

    elif action == "activate":
        target.profile.is_suspended = False
        target.profile.suspension_reason = ""
        target.profile.suspended_at = None

    else:
        raise Http404

    target.profile.save(
        update_fields=[
            "is_suspended",
            "suspension_reason",
            "suspended_at",
        ]
    )

    ModerationAction.objects.create(
        moderator=request.user,
        action=action,
        target_type="user",
        target_id=target.pk,
        reason=reason,
    )

    return redirect(
        "moderation_dashboard"
    )


# =========================================================
# User moderation action
# =========================================================
@staff_required
@require_POST
def moderation_user_action(
    request,
    username,
):
    target = get_object_or_404(
        User,
        username=username,
    )

    if (
        target.is_superuser
        and target != request.user
    ):
        raise PermissionDenied

    action = request.POST.get(
        "action"
    )

    reason = request.POST.get(
        "reason",
        "",
    )[:300]

    if action == "suspend":
        target.profile.is_suspended = True
        target.profile.suspension_reason = reason
        target.profile.suspended_at = (
            timezone.now()
        )

    elif action == "activate":
        target.profile.is_suspended = False
        target.profile.suspension_reason = ""
        target.profile.suspended_at = None

    else:
        raise Http404

    target.profile.save(
        update_fields=[
            "is_suspended",
            "suspension_reason",
            "suspended_at",
        ]
    )

    ModerationAction.objects.create(
        moderator=request.user,
        action=action,
        target_type="user",
        target_id=target.pk,
        reason=reason,
    )

    return redirect(
        "moderation_dashboard"
    )