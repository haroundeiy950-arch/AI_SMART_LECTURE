from django.urls import path

from . import views


urlpatterns = [
    # الصفحة الرئيسية والتسجيل
    path(
        "",
        views.landing,
        name="landing",
    ),
    path(
        "feed/",
        views.home,
        name="home",
    ),
    path(
        "register/",
        views.register,
        name="register",
    ),

    # تغيير اللغة
    path(
        "language/set/",
        views.set_language,
        name="set_language",
    ),

    # المنشورات
    path(
        "post/create/",
        views.create_post,
        name="create_post",
    ),
    path(
        "post/<int:pk>/",
        views.post_detail,
        name="post_detail",
    ),
    path(
        "post/<int:pk>/edit/",
        views.edit_post,
        name="edit_post",
    ),
    path(
        "post/<int:pk>/delete/",
        views.delete_post,
        name="delete_post",
    ),
    path(
        "post/<int:pk>/like/",
        views.toggle_like,
        name="toggle_like",
    ),
    path(
        "post/<int:pk>/comment/",
        views.add_comment,
        name="add_comment",
    ),

    # التعليقات
    path(
        "comment/<int:pk>/delete/",
        views.delete_comment,
        name="delete_comment",
    ),

    # الملف الشخصي
    path(
        "profile/edit/",
        views.edit_profile,
        name="edit_profile",
    ),
    path(
        "profile/<str:username>/",
        views.profile_view,
        name="profile",
    ),
    path(
        "profile/<str:username>/block/",
        views.toggle_block,
        name="toggle_block",
    ),

    # البحث
    path(
        "search/",
        views.search,
        name="search",
    ),

    # المحادثات
    path(
        "messages/",
        views.conversation_list,
        name="conversation_list",
    ),
    path(
        "messages/start/<str:username>/",
        views.start_conversation,
        name="start_conversation",
    ),
    path(
        "messages/<int:pk>/",
        views.conversation_detail,
        name="conversation_detail",
    ),
    path(
        "messages/<int:pk>/send/",
        views.send_message,
        name="send_message",
    ),

    # الإشعارات
    path(
        "notifications/",
        views.notifications_view,
        name="notifications",
    ),
    path(
        "notifications/read-all/",
        views.notifications_read_all,
        name="notifications_read_all",
    ),
    path(
        "notifications/<int:pk>/read/",
        views.notification_read,
        name="notification_read",
    ),

    # البلاغات
    path(
        "report/<str:target_type>/<int:pk>/",
        views.report_target,
        name="report_target",
    ),

    # أدوات الذكاء الاصطناعي
    path(
        "ai/",
        views.ai_tools,
        name="ai_tools",
    ),

    # لوحة الإشراف
    path(
        "control/",
        views.moderation_dashboard,
        name="moderation_dashboard",
    ),
    path(
        "control/report/<int:pk>/",
        views.moderation_report_action,
        name="moderation_report_action",
    ),
    path(
        "control/post/<int:pk>/",
        views.moderation_post_action,
        name="moderation_post_action",
    ),
    path(
        "control/user-action/",
        views.moderation_user_quick_action,
        name="moderation_user_quick_action",
    ),
    path(
        "control/user/<str:username>/",
        views.moderation_user_action,
        name="moderation_user_action",
    ),
]