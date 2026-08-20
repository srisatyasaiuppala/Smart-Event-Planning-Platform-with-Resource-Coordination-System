from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import CustomPasswordChangeForm

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard_explicit"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("reset-password/", views.reset_password, name="reset_password"),
    path(
        "change-password/",
        auth_views.PasswordChangeView.as_view(
            form_class=CustomPasswordChangeForm,
            template_name="change_password.html",
            success_url="/change-password/done/",
        ),
        name="change_password",
    ),
    path(
        "change-password/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="change_password_done.html"
        ),
        name="password_change_done",
    ),
    path("category/create/", views.create_category, name="create_category"),
    path("category/list/", views.category_list, name="category_list"),
    path("category/edit/<int:pk>/", views.edit_category, name="edit_category"),
    path(
        "category/delete/<int:pk>/",
        views.delete_category,
        name="delete_category",
    ),
    path("events/create/", views.create_event, name="create_event"),
    path("events/list/", views.event_list, name="event_list"),
    path("events/<int:pk>/", views.event_detail, name="event_detail"),
    path("events/edit/<int:pk>/", views.edit_event, name="edit_event"),
    path("events/delete/<int:pk>/", views.delete_event, name="delete_event"),
    path("members/register/", views.register_member, name="register_member"),
    path("members/list/", views.member_list, name="member_list"),
    path("members/edit/<int:pk>/", views.edit_member, name="edit_member"),
    path("members/delete/<int:pk>/", views.delete_member, name="delete_member"),
    path("attendance/mark/", views.mark_attendance, name="mark_attendance"),
    path("attendance/list/", views.attendance_list, name="attendance_list"),
    path(
        "attendance/edit/<int:pk>/",
        views.edit_attendance,
        name="edit_attendance",
    ),
    path(
        "attendance/delete/<int:pk>/",
        views.delete_attendance,
        name="delete_attendance",
    ),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile_view, name="edit_profile"),
    path(
        "profile/upload-pic/",
        views.upload_profile_pic,
        name="upload_profile_pic",
    ),
    path(
        "profile/remove-pic/",
        views.remove_profile_pic,
        name="remove_profile_pic",
    ),
    path("settings/", views.settings_view, name="settings"),
    path(
        "notifications/read/<int:notification_id>/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/all/",
        views.all_notifications,
        name="all_notifications",
    ),
    path("chat/", views.chat_room, name="chat_room"),
    path("chat/send/", views.send_message, name="send_message"),
    path("user/dashboard/", views.user_dashboard, name="user_dashboard"),
    path("user/events/", views.user_event_list, name="user_event_list"),
    path(
        "user/registered-events/",
        views.my_registered_events,
        name="my_registered_events",
    ),
    path(
        "user/event/<int:event_id>/",
        views.user_event_detail,
        name="user_event_detail",
    ),
    path("user/calendar/", views.user_calendar, name="user_calendar"),
    path("registration-qr/", views.qr_code_page, name="qr_code_page"),
    path(
        "admin-registration-qr/",
        views.admin_global_registration_qr,
        name="admin_global_registration_qr",
    ),
    path(
        "register/",
        views.public_event_registration,
        name="public_event_registration",
    ),
]