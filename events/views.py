from datetime import date
from io import BytesIO
import json
import random
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
import qrcode
from .bot import generate_bot_response, get_or_create_bot_user

from .forms import (
    AttendanceForm,
    CategoryForm,
    EventForm,
    RegistrationForm,
    SignUpForm,
)
from .models import (
    Attendance,
    Category,
    Event,
    Message,
    Notification,
    Profile,
    Registration,
)


def signup(request):
  if request.method == "POST":
    form = SignUpForm(request.POST)
    if form.is_valid():
      user = form.save()
      if request.user.is_authenticated and (
          request.user.is_staff or request.user.is_superuser
      ):
        messages.success(
            request, f"User '{user.username}' created successfully!"
        )
        return redirect("member_list")
      login(request, user)
      return redirect("user_event_list")
  else:
    form = SignUpForm()

  return render(request, "registration/signup.html", {"form": form})


def user_login(request):
  if request.method == "POST":
    form = AuthenticationForm(request, data=request.POST)
    selected_role = request.POST.get("role", "user")

    if form.is_valid():
      username = form.cleaned_data["username"]
      password = form.cleaned_data["password"]
      user = authenticate(username=username, password=password)

      if user is not None:
        is_admin = user.is_staff or user.is_superuser

        if selected_role == "user" and is_admin:
          messages.error(
              request,
              "Access Denied: Admin accounts must select the 'Admin' option to"
              " log in.",
          )
          return render(request, "registration/login.html", {"form": form})

        if selected_role == "admin" and not is_admin:
          messages.error(
              request,
              "Access Denied: Regular user accounts cannot log in as Admin.",
          )
          return render(request, "registration/login.html", {"form": form})

        login(request, user)
        return redirect("dashboard" if is_admin else "user_dashboard")
    else:
      messages.error(request, "Invalid username or password.")
  else:
    form = AuthenticationForm()

  return render(request, "registration/login.html", {"form": form})


def user_logout(request):
  logout(request)
  return redirect("login")


def forgot_password(request):
  if request.method == "POST":
    identifier = request.POST.get("identifier", "").strip()
    user = User.objects.filter(
        Q(email__iexact=identifier) | Q(username__iexact=identifier)
    ).first()

    if user:
      otp = str(random.randint(100000, 999999))
      request.session["reset_user_id"] = user.id
      request.session["reset_otp"] = otp
      request.session.set_expiry(600)

      if user.email:
        send_mail(
            subject="Password Reset OTP - Event Management",
            message=(
                f"Hello {user.first_name or user.username},\n\nYour OTP to"
                f" reset your password is: {otp}\n\nThis OTP is valid for 10"
                " minutes."
            ),
            from_email=getattr(
                settings, "DEFAULT_FROM_EMAIL", "noreply@eventmanagement.com"
            ),
            recipient_list=[user.email],
            fail_silently=True,
        )

      print(
          f"\n===========================\nOTP FOR {user.username}:"
          f" {otp}\n===========================\n"
      )
      messages.success(
          request, "OTP has been sent to your registered email/phone!"
      )
      return redirect("verify_otp")
    else:
      messages.error(
          request, "No account found with provided Email or Username."
      )

  return render(request, "registration/forgot_password.html")


def verify_otp(request):
  if "reset_otp" not in request.session:
    messages.error(request, "Session expired. Please request OTP again.")
    return redirect("forgot_password")

  if request.method == "POST":
    entered_otp = request.POST.get("otp", "").strip()
    session_otp = request.session.get("reset_otp")

    if entered_otp == session_otp:
      request.session["otp_verified"] = True
      messages.success(request, "OTP verified! Please set a new password.")
      return redirect("reset_password")
    else:
      messages.error(request, "Invalid OTP. Please try again.")

  return render(request, "registration/verify_otp.html")


def reset_password(request):
  if not request.session.get("otp_verified"):
    messages.error(request, "Unauthorized access. Please verify OTP first.")
    return redirect("forgot_password")

  if request.method == "POST":
    password = request.POST.get("password")
    confirm_password = request.POST.get("confirm_password")

    if password != confirm_password:
      messages.error(request, "Passwords do not match!")
    else:
      user_id = request.session.get("reset_user_id")
      user = get_object_or_404(User, id=user_id)
      user.set_password(password)
      user.save()

      for key in ["reset_user_id", "reset_otp", "otp_verified"]:
        if key in request.session:
          del request.session[key]

      messages.success(request, "Password reset successful! Please login.")
      return redirect("login")

  return render(request, "registration/reset_password.html")


@login_required
def dashboard(request):
  if not (request.user.is_staff or request.user.is_superuser):
    return redirect("user_dashboard")

  search = request.GET.get("search", "").strip()
  today = date.today()

  total_categories = Category.objects.count()
  total_events = Event.objects.count()
  total_members = Registration.objects.count()
  total_attendance = Attendance.objects.count()

  upcoming_events = Event.objects.filter(
      event_date__gte=today, status="Upcoming"
  ).count()
  completed_events = Event.objects.filter(
      Q(event_date__lt=today) | Q(status="Completed")
  ).count()

  events = (
      Event.objects.select_related("category")
      .all()
      .order_by("-created_at", "-id")
  )
  categories = Category.objects.all().order_by("-created_at", "-id")
  members = (
      Registration.objects.select_related("event")
      .all()
      .order_by("-registered_at", "-id")
  )
  attendance = (
      Attendance.objects.select_related("registration", "registration__event")
      .all()
      .order_by("-attendance_date", "-id")
  )

  if search:
    events = events.filter(
        Q(name__icontains=search)
        | Q(category__name__icontains=search)
        | Q(venue__icontains=search)
        | Q(description__icontains=search)
    )
    categories = categories.filter(
        Q(name__icontains=search) | Q(category_code__icontains=search)
    )
    members = members.filter(
        Q(full_name__icontains=search)
        | Q(email__icontains=search)
        | Q(phone__icontains=search)
        | Q(college__icontains=search)
        | Q(event__name__icontains=search)
    )
    attendance = attendance.filter(
        Q(registration__full_name__icontains=search)
        | Q(registration__event__name__icontains=search)
        | Q(status__icontains=search)
    )

  context = {
      "total_categories": total_categories,
      "total_events": total_events,
      "total_members": total_members,
      "total_attendance": total_attendance,
      "upcoming_events": upcoming_events,
      "completed_events": completed_events,
      "events": events,
      "categories": categories,
      "members": members,
      "attendance": attendance,
      "today": today,
      "search": search,
  }
  return render(request, "dashboard/dashboard.html", context)


@login_required
def create_category(request):
  if request.method == "POST":
    form = CategoryForm(request.POST)
    if form.is_valid():
      form.save()
      return redirect("category_list")
  else:
    form = CategoryForm()
  return render(request, "category/create_category.html", {"form": form})


@login_required
def category_list(request):
  categories = Category.objects.all().order_by("-created_at", "-id")
  return render(
      request, "category/category_list.html", {"categories": categories}
  )


@login_required
def edit_category(request, pk):
  category = get_object_or_404(Category, id=pk)
  if request.method == "POST":
    form = CategoryForm(request.POST, instance=category)
    if form.is_valid():
      form.save()
      return redirect("category_list")
  else:
    form = CategoryForm(instance=category)
  return render(request, "category/edit_category.html", {"form": form})


@login_required
def delete_category(request, pk):
  category = get_object_or_404(Category, id=pk)
  category.delete()
  return redirect("category_list")


@login_required
def create_event(request):
  if not (request.user.is_staff or request.user.is_superuser):
    return redirect("user_event_list")

  if request.method == "POST":
    form = EventForm(request.POST)
    if form.is_valid():
      event = form.save()
      messages.success(
          request, f"Event '{event.name}' has been created successfully!"
      )
      return redirect("event_list")
    else:
      messages.error(
          request, "Failed to create event. Please check the errors below."
      )
  else:
    form = EventForm()
  return render(request, "events/create_event.html", {"form": form})


@login_required
def event_list(request):
  search_query = request.GET.get("search", "")
  events = (
      Event.objects.all().select_related("category").order_by("-event_date")
  )

  if search_query:
    events = events.filter(name__icontains=search_query)

  context = {
      "events": events,
      "today": date.today(),
      "search_query": search_query,
  }
  return render(request, "events/event_list.html", context)


@login_required
def event_detail(request, pk):
  event = get_object_or_404(Event, id=pk)
  return render(request, "events/event_detail.html", {"event": event})


@login_required
def edit_event(request, pk):
  event = get_object_or_404(Event, id=pk)
  if request.method == "POST":
    form = EventForm(request.POST, instance=event)
    if form.is_valid():
      form.save()
      return redirect("event_list")
  else:
    form = EventForm(instance=event)
  return render(request, "events/edit_event.html", {"form": form})


@login_required
def delete_event(request, pk):
  event = get_object_or_404(Event, id=pk)
  event.delete()
  return redirect("event_list")


@login_required
def register_member(request):
  if request.method == "POST":
    form = RegistrationForm(request.POST)
    if form.is_valid():
      registration = form.save(commit=False)

      if (
          registration.event.event_date
          and registration.event.event_date < date.today()
      ):
        messages.error(
            request, "Registration closed: This event has already ended."
        )
        return render(request, "members/register_member.html", {"form": form})

      if not registration.email and request.user.email:
        registration.email = request.user.email

      if not registration.full_name:
        registration.full_name = (
            request.user.get_full_name() or request.user.username
        )

      registration.save()

      create_notification(
          user=request.user,
          title="Registration Confirmed",
          message=(
              f"You have successfully registered for {registration.event.name}!"
          ),
          icon="fas fa-calendar-check text-success",
      )

      messages.success(request, "Registration successful!")
      return (
          redirect("member_list")
          if (request.user.is_staff or request.user.is_superuser)
          else redirect("my_registered_events")
      )
  else:
    initial_data = {}
    if request.user.email:
      initial_data["email"] = request.user.email
    if request.user.username:
      initial_data["full_name"] = (
          request.user.get_full_name() or request.user.username
      )

    form = RegistrationForm(initial=initial_data)
    if "event" in form.fields and not (
        request.user.is_staff or request.user.is_superuser
    ):
      form.fields["event"].queryset = Event.objects.filter(
          event_date__gte=date.today()
      ).order_by("event_date")

  return render(request, "members/register_member.html", {"form": form})


@login_required
def member_list(request):
  members = (
      Registration.objects.select_related("event")
      .all()
      .order_by("-registered_at", "-id")
  )
  return render(request, "members/member_list.html", {"members": members})


@login_required
def edit_member(request, pk):
  member = get_object_or_404(Registration, id=pk)
  if request.method == "POST":
    form = RegistrationForm(request.POST, instance=member)
    if form.is_valid():
      form.save()
      return redirect("member_list")
  else:
    form = RegistrationForm(instance=member)
  return render(
      request,
      "members/register_member.html",
      {"form": form, "edit_mode": True},
  )


@login_required
def delete_member(request, pk):
  member = get_object_or_404(Registration, id=pk)
  member.delete()
  return redirect("member_list")


@login_required
def mark_attendance(request):
  if request.method == "POST":
    form = AttendanceForm(request.POST)
    if form.is_valid():
      form.save()
      return redirect("attendance_list")
  else:
    form = AttendanceForm()
  return render(request, "attendance/mark_attendance.html", {"form": form})


@login_required
def attendance_list(request):
  attendance = (
      Attendance.objects.select_related("registration", "registration__event")
      .all()
      .order_by("-attendance_date", "-id")
  )
  return render(
      request, "attendance/attendance_list.html", {"attendance": attendance}
  )


@login_required
def edit_attendance(request, pk):
  attendance = get_object_or_404(Attendance, id=pk)
  if request.method == "POST":
    form = AttendanceForm(request.POST, instance=attendance)
    if form.is_valid():
      form.save()
      return redirect("attendance_list")
  else:
    form = AttendanceForm(instance=attendance)
  return render(request, "attendance/edit_attendance.html", {"form": form})


@login_required
def delete_attendance(request, pk):
  attendance = get_object_or_404(Attendance, id=pk)
  attendance.delete()
  return redirect("attendance_list")


@login_required
def user_dashboard(request):
  user = request.user
  today = date.today()

  total_events_count = Event.objects.count()

  conditions = Q()
  if user.email:
    conditions |= Q(email__iexact=user.email)
  if user.username:
    conditions |= Q(full_name__iexact=user.username)
  user_full_name = user.get_full_name().strip()
  if user_full_name:
    conditions |= Q(full_name__iexact=user_full_name)

  user_registrations = (
      Registration.objects.filter(conditions)
      .distinct()
      .select_related("event")
  )
  registrations_count = user_registrations.count()

  upcoming_count = Event.objects.filter(
      event_date__gte=today, status="Upcoming"
  ).count()
  completed_count = Event.objects.filter(
      Q(event_date__lt=today) | Q(status="Completed")
  ).count()

  context = {
      "total_events_count": total_events_count,
      "registrations_count": registrations_count,
      "upcoming_count": upcoming_count,
      "completed_count": completed_count,
      "recent_registrations": (
          user_registrations.order_by("-registered_at")[:5]
      ),
  }
  return render(request, "user/user_dashboard.html", context)


@login_required
def user_event_list(request):
  if request.user.is_staff or request.user.is_superuser:
    return redirect("dashboard")

  search = request.GET.get("search", "").strip()
  events = Event.objects.select_related("category").filter(status="Upcoming")

  if search:
    events = events.filter(
        Q(name__icontains=search)
        | Q(category__name__icontains=search)
        | Q(venue__icontains=search)
    )

  events = events.order_by("-event_date")
  return render(
      request, "user/user_events.html", {"events": events, "search": search}
  )


@login_required
def my_registered_events(request):
  user = request.user
  conditions = Q()
  if user.email:
    conditions |= Q(email__iexact=user.email)
  if user.username:
    conditions |= Q(full_name__iexact=user.username)
  user_full_name = user.get_full_name().strip()
  if user_full_name:
    conditions |= Q(full_name__iexact=user_full_name)

  registrations = (
      Registration.objects.filter(conditions)
      .distinct()
      .select_related("event")
      .order_by("-registered_at")
  )

  return render(
      request,
      "user/my_registered_events.html",
      {"registrations": registrations, "today": date.today()},
  )


@login_required
def user_event_detail(request, event_id):
  event = get_object_or_404(Event, id=event_id)
  is_ended = event.event_date < date.today() if event.event_date else False
  return render(
      request,
      "user/user_event_detail.html",
      {"event": event, "is_ended": is_ended},
  )


@login_required
def user_calendar(request):
  today = date.today()
  user = request.user

  user_conditions = Q()
  if user.email:
    user_conditions |= Q(email__iexact=user.email)
  if user.username:
    user_conditions |= Q(full_name__iexact=user.username)
  full_name = user.get_full_name().strip()
  if full_name:
    user_conditions |= Q(full_name__iexact=full_name)

  registered_event_ids = set(
      Registration.objects.filter(user_conditions).values_list(
          "event_id", flat=True
      )
  )

  events = Event.objects.select_related("category").all()
  calendar_events = []

  for ev in events:
    is_registered = ev.id in registered_event_ids
    is_past = ev.event_date < today

    if is_registered:
      bg_color = "#28a745"
      border_color = "#1e7e34"
      prefix = "⭐ [Registered] "
    elif is_past:
      bg_color = "#6c757d"
      border_color = "#545b62"
      prefix = "[Completed] "
    else:
      bg_color = "#007bff"
      border_color = "#0056b3"
      prefix = ""

    calendar_events.append({
        "title": f"{prefix}{ev.name}",
        "start": ev.event_date.isoformat(),
        "end": ev.end_date.isoformat() if ev.end_date else None,
        "backgroundColor": bg_color,
        "borderColor": border_color,
        "extendedProps": {
            "category": ev.category.name if ev.category else "General",
            "venue": ev.venue,
            "time": (
                ev.event_time.strftime("%I:%M %p") if ev.event_time else "TBD"
            ),
            "status": "Completed" if is_past else "Upcoming",
            "is_registered": is_registered,
            "description": ev.description or "No description provided.",
        },
    })

  return render(
      request,
      "user/user_calendar.html",
      {"calendar_events_json": json.dumps(calendar_events)},
  )


@login_required
def profile_view(request):
  return render(request, "profile.html")


@login_required
def edit_profile_view(request):
  if request.method == "POST":
    user = request.user
    user.first_name = request.POST.get("first_name", "")
    user.last_name = request.POST.get("last_name", "")
    user.email = request.POST.get("email", "")
    user.save()
    messages.success(request, "Profile updated successfully!")
    return redirect("profile")
  return render(request, "edit_profile.html")


@login_required
def upload_profile_pic(request):
  if request.method == "POST" and request.FILES.get("profile_image"):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.image = request.FILES["profile_image"]
    profile.save()
    messages.success(request, "Profile picture updated!")
  return redirect("profile")


@login_required
def remove_profile_pic(request):
  if hasattr(request.user, "profile") and request.user.profile.image:
    request.user.profile.image.delete()
    request.user.profile.save()
    messages.success(request, "Profile picture removed!")
  return redirect("profile")


@login_required
def settings_view(request):
  return render(request, "settings.html")


def create_notification(
    user, title, message, icon="fas fa-user-plus text-success"
):
  Notification.objects.create(
      user=user, title=title, message=message, icon=icon
  )


def mark_notification_read(request, notification_id):
  notification = get_object_or_404(Notification, id=notification_id)
  notification.is_read = True
  notification.save()
  return redirect(notification.link)


@login_required
def all_notifications(request):
  if request.user.is_staff or request.user.is_superuser:
    notifications = Notification.objects.all().order_by("-created_at")
  else:
    notifications = Notification.objects.filter(user=request.user).order_by(
        "-created_at"
    )
  return render(
      request,
      "events/all_notifications.html",
      {"notifications": notifications},
  )


@login_required
def send_message(request):
  if request.method == "POST":
    content = request.POST.get("content", "").strip()
    if content:
      Message.objects.create(sender=request.user, content=content)
      messages.success(request, "Message sent successfully!")
  return redirect(request.META.get("HTTP_REFERER", "dashboard"))


@login_required
def chat_room(request):
  bot_user = get_or_create_bot_user()

  if request.method == "POST":
    content = request.POST.get("content", "").strip()
    if content:
      Message.objects.create(
          sender=request.user, receiver=bot_user, content=content
      )
      bot_reply = generate_bot_response(request.user, content)
      Message.objects.create(
          sender=bot_user, receiver=request.user, content=bot_reply
      )
      return redirect("chat_room")

  chat_messages = Message.objects.filter(
      (Q(sender=request.user) & Q(receiver=bot_user))
      | (Q(sender=bot_user) & Q(receiver=request.user))
  ).order_by("timestamp")

  Message.objects.filter(
      sender=bot_user, receiver=request.user, is_read=False
  ).update(is_read=True)

  return render(
      request, "chat/chat_room.html", {"chat_messages": chat_messages}
  )


def qr_code_page(request):
  return render(request, "events/qr_page.html")


def admin_global_registration_qr(request):

  registration_url = 'http://127.0.0.1:8000/register/'

  qr = qrcode.QRCode(
      version=1,
      error_correction=qrcode.constants.ERROR_CORRECT_M,
      box_size=8,
      border=2,
  )
  qr.add_data(registration_url)
  qr.make(fit=True)

  img = qr.make_image(fill_color='black', back_color='white')
  buffer = BytesIO()
  img.save(buffer, format='PNG')
  buffer.seek(0)
  return HttpResponse(buffer.getvalue(), content_type='image/png')


def public_event_registration(request):
  if request.method == "POST":
    form = RegistrationForm(request.POST)
    if form.is_valid():
      form.save()
      messages.success(
          request,
          "Your registration has been submitted successfully! Welcome.",
      )
      return redirect("public_event_registration")
  else:
    form = RegistrationForm()

  return render(request, "events/public_registration.html", {"form": form})