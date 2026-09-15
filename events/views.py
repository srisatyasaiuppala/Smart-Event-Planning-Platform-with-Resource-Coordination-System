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
from django.http import HttpResponse,HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
import qrcode
from .bot import generate_bot_response, get_or_create_bot_user
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from google import genai
from google.genai import types
from .models import Attendance, Category, Event, Message, Registration
from django.utils import timezone
from django.urls import reverse

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
    form = EventForm(request.POST, request.FILES or None)

    # Pre-check case-insensitive name uniqueness before saving
    raw_name = request.POST.get("name", "").strip()
    if raw_name and Event.objects.filter(name__iexact=raw_name).exists():
      messages.error(
          request,
          f"An event named '{raw_name}' already exists (case-insensitive duplicate).",
      )
      return render(request, "events/create_event.html", {"form": form})

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
  today = timezone.localdate()

  # Queryset for events that are today or in the future
  upcoming_events_qs = Event.objects.filter(event_date__gte=today).order_by(
      'event_date', 'event_time'
  )

  if request.method == 'POST':
    # 1. Grab first_name and last_name, combine into full_name
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    full_name = f'{first_name} {last_name}'.strip()

    # Copy POST data so we can inject full_name into form validation
    data = request.POST.copy()
    if full_name:
      data['full_name'] = full_name

    form = RegistrationForm(data)

    # Restrict dropdown choices during validation to active upcoming events
    if 'event' in form.fields:
      form.fields['event'].queryset = upcoming_events_qs

    if form.is_valid():
      registration = form.save(commit=False)

      # 2. Assign combined name or fallback
      if full_name:
        registration.full_name = full_name
      elif not registration.full_name:
        registration.full_name = (
            request.user.get_full_name() or request.user.username
        )

      # 3. Fallbacks for User Info
      if not registration.email and request.user.email:
        registration.email = request.user.email.strip().lower()
      elif registration.email:
        registration.email = registration.email.strip().lower()

      # 4. Block registration for past/ended events
      if (
          registration.event.event_date
          and registration.event.event_date < today
      ):
        messages.error(
            request,
            f"Registration closed: '{registration.event.name}' has already"
            ' ended.',
        )
        return render(
            request,
            'members/register_member.html',
            {'form': form, 'edit_mode': False},
        )

      # 5. Duplicate Prevention: Check if email or phone already exists for this event
      duplicate_query = Q(email__iexact=registration.email)
      if hasattr(registration, 'phone') and registration.phone:
        duplicate_query |= Q(phone=registration.phone.strip())

      is_duplicate = (
          Registration.objects.filter(event=registration.event)
          .filter(duplicate_query)
          .exists()
      )

      if is_duplicate:
        messages.warning(
            request,
            f'Duplicate Registration: Attendee ({registration.email}) is'
            f" already registered for '{registration.event.name}'.",
        )
        return render(
            request,
            'members/register_member.html',
            {'form': form, 'edit_mode': False},
        )

      # 6. Save registration and generate ticket
      registration.save()

      # 7. Create confirmation notification
      create_notification(
          user=request.user,
          title='Registration Confirmed',
          message=(
              f'You have successfully registered for {registration.event.name}!'
          ),
          icon='fas fa-calendar-check text-success',
      )

      messages.success(
          request,
          f"Registration confirmed for '{registration.event.name}'! Your"
          ' attendance ticket has been generated.',
      )

      if request.user.is_staff or request.user.is_superuser:
        return redirect('member_list')
      return redirect('my_ticket', reg_id=registration.id)

    else:
      messages.error(request, 'Please correct the errors below.')
      return render(
          request,
          'members/register_member.html',
          {'form': form, 'edit_mode': False},
      )

  else:
    # GET Request: Pre-fill defaults
    initial_data = {}
    if request.user.email:
      initial_data['email'] = request.user.email

    # Pre-fill First and Last Name if present on the User account
    initial_data['first_name'] = request.user.first_name or ''
    initial_data['last_name'] = request.user.last_name or ''

    # Support QR scan parameter (e.g. /register/?event=3)
    preselected_event_id = request.GET.get('event')
    if preselected_event_id:
      initial_data['event'] = preselected_event_id

    form = RegistrationForm(initial=initial_data)

    # Filter dropdown to only upcoming events
    if 'event' in form.fields:
      form.fields['event'].queryset = upcoming_events_qs

  return render(
      request,
      'members/register_member.html',
      {'form': form, 'edit_mode': False},
  )


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
  today = timezone.localdate()

  total_events_count = Event.objects.count()

  # Match registrations belonging to this user
  conditions = Q()
  if user.email:
    conditions |= Q(email__iexact=user.email)
  if user.username:
    conditions |= Q(full_name__iexact=user.username)
  user_full_name = user.get_full_name().strip()
  if user_full_name:
    conditions |= Q(full_name__iexact=user_full_name)

  # Fetch all registrations for this user
  user_registrations = (
      Registration.objects.filter(conditions)
      .distinct()
      .select_related('event')
  )
  registrations_count = user_registrations.count()

  # Active upcoming tickets (events occurring today or in the future)
  upcoming_tickets = (
      user_registrations.filter(event__event_date__gte=today)
      .exclude(event__status='Completed')
      .order_by('event__event_date', 'event__event_time')
  )

  # Platform event counts
  upcoming_count = Event.objects.filter(
      event_date__gte=today, status='Upcoming'
  ).count()
  completed_count = Event.objects.filter(
      Q(event_date__lt=today) | Q(status='Completed')
  ).count()

  context = {
      'total_events_count': total_events_count,
      'registrations_count': registrations_count,
      'upcoming_count': upcoming_count,
      'completed_count': completed_count,
      'user_registrations': user_registrations.order_by('-registered_at'),
      'upcoming_tickets': upcoming_tickets,
      'recent_registrations': user_registrations.order_by('-registered_at')[:5],
  }
  return render(request, 'user/user_dashboard.html', context)

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


def get_project_bot_reply(user, text):
  msg = text.lower().strip()
  today = timezone.localdate()

  # 1. Greetings
  if any(w in msg for w in ['hi', 'hello', 'hey', 'start', 'help']):
    return (
        f'Hello {user.first_name or user.username}! 👋 I am your Event'
        ' Platform Assistant.\n\nYou can ask me about:\n• "Upcoming events" or'
        ' "Event list"\n• "My registrations" (Events you joined)\n• "How to'
        ' register" (Step-by-step guide)\n• "Registrations list" (Total'
        ' registered participants)\n• "Event categories"\n• "Theme /'
        ' Customization"\n• "Mark attendance" (Admin)\n• "Create event" (Admin)'
    )

  # 2. User's Personal Registrations
  elif any(
      w in msg
      for w in [
          'my registration',
          'my registered',
          'my events',
          'my event',
          'am i registered',
          'events i joined',
      ]
  ):
    my_regs = Registration.objects.filter(
        Q(email__iexact=user.email)
        | Q(full_name__iexact=user.get_full_name())
        | Q(full_name__iexact=user.username)
    )

    if not my_regs.exists():
      return (
          f'No event registrations found for {user.username} (Email:'
          f' {user.email or "not set"}).\nClick "Register for Event" in the'
          ' sidebar to sign up for upcoming events!'
      )

    reply = f'🎟️ Events registered by {user.first_name or user.username}:\n'
    for r in my_regs:
      ev_date = (
          r.event.event_date.strftime('%b %d, %Y')
          if r.event.event_date
          else 'TBA'
      )
      reply += f'• {r.event.name} | Date: {ev_date} | Venue: {r.event.venue}\n'
    return reply.strip()

  # 3. All Registrations / Member Count Directory
  elif any(
      w in msg
      for w in [
          'all registrations',
          'registrations list',
          'registration list',
          'registrations',
          'total members',
          'how many registered',
          'participants',
          'member list',
      ]
  ):
    total = Registration.objects.count()
    if user.is_staff or user.is_superuser:
      recent = Registration.objects.select_related('event').order_by(
          '-registered_at'
      )[:5]
      reply = f'👥 Platform Registrations ({total} total entries):\n'
      for r in recent:
        reply += f'• {r.full_name} ➔ {r.event.name} ({r.college})\n'
      reply += '\nView the complete list under "Members" -> "Member List".'
      return reply.strip()
    else:
      return (
          f'👥 Platform Statistics: There are currently {total} total registered'
          ' participant entries across all events.'
      )

  # 4. How to Register Guide
  elif any(
      w in msg
      for w in [
          'how to register',
          'how to join',
          'how do i register',
          'registration process',
          'register member',
          'steps to register',
      ]
  ):
    return (
        '📝 To register for an event:\n1. Click "Register for Event" in the'
        ' left sidebar.\n2. Or scan the QR code from the "Registration QR"'
        ' page.\n3. Fill in your Name, Email, Phone, College, and select your'
        ' Event.\n4. Click Submit to save your registration.'
    )

  # 5. Upcoming Events (Future dates only)
  elif any(
      w in msg
      for w in [
          'upcoming',
          'next event',
          'future event',
          'what is next',
          'coming soon',
      ]
  ):
    upcoming_events = Event.objects.filter(event_date__gte=today).order_by(
        'event_date', 'event_time'
    )
    if not upcoming_events.exists():
      return '📅 No upcoming events scheduled at the moment. Check back soon!'

    reply = f'⏳ Upcoming Events (From {today.strftime("%b %d, %Y")}):\n'
    for ev in upcoming_events:
      date_str = (
          ev.event_date.strftime('%b %d, %Y') if ev.event_date else 'TBA'
      )
      time_str = ev.event_time.strftime('%I:%M %p') if ev.event_time else ''
      reply += (
          f'• {ev.name} | Date: {date_str} | Time: {time_str} | Venue:'
          f' {ev.venue}\n'
      )
    return reply.strip()

  # 6. All Events / Event Directory
  elif any(
      w in msg
      for w in [
          'event list',
          'list events',
          'all events',
          'events list',
          'schedule',
          'events',
      ]
  ):
    all_events = Event.objects.all().order_by('-event_date')[:10]
    if not all_events.exists():
      return 'There are currently no events registered in the platform.'

    reply = '📋 All Events Directory:\n'
    for ev in all_events:
      date_str = (
          ev.event_date.strftime('%b %d, %Y') if ev.event_date else 'TBA'
      )
      status_tag = (
          '🟢 Upcoming'
          if (ev.event_date and ev.event_date >= today)
          else '⚪ Completed'
      )
      reply += (
          f'• {ev.name} ({status_tag}) | Date: {date_str} | Venue: {ev.venue}\n'
      )
    return reply.strip()

  # 7. Categories
  elif any(w in msg for w in ['category', 'categories', 'types']):
    cats = Category.objects.all()
    if cats.exists():
      cat_list = [f'{c.name} ({c.category_code})' for c in cats]
      return '📂 Available Event Categories:\n• ' + '\n• '.join(cat_list)
    return 'No event categories have been created yet.'

  # 8. Admin Create Event
  elif any(w in msg for w in ['create event', 'add event', 'new event']):
    if user.is_staff or user.is_superuser:
      return (
          '🛠️ Admin Event Creation:\n1. Click "Events" in the left sidebar.\n2.'
          ' Select "Create Event".\n3. Fill in Name, Category, Date, Time, and'
          ' Venue.\n4. Save (A QR code will generate automatically).'
      )
    return 'Event creation is restricted to Admin accounts.'

  # 9. Attendance
  elif any(w in msg for w in ['attendance', 'mark attendance', 'present']):
    if user.is_staff or user.is_superuser:
      return (
          '📋 Attendance Flow:\n1. Navigate to "Attendance" -> "Mark'
          ' Attendance".\n2. Select the event and mark attendees Present or'
          ' Absent.\n3. View records anytime under "Attendance List".'
      )
    return (
        'Attendance is marked by event administrators during event check-ins.'
    )

  # 10. Theme / Customization
  elif any(
      w in msg
      for w in [
          'customize',
          'theme',
          'color',
          'dark mode',
          'light mode',
          'appearance',
          'change look',
      ]
  ):
    if user.is_staff or user.is_superuser:
      return (
          '🎨 Customization Guide (Admin):\n1. Click the Sliders icon'
          ' (Customize) in the top navbar.\n2. Choose your preferred Navbar and'
          ' Sidebar colors.\n3. Adjust font sizing or toggle between Dark and'
          ' Light mode.\n4. Settings apply immediately to your dashboard.'
      )
    return (
        '🎨 Interface Customization:\nDashboard themes and color schemes are'
        ' managed by platform administrators via the top navigation controls.'
    )

  # 11. Fallback / Out of Scope
  else:
    return (
        "I specialize only in this Event Management System (events,"
        " registrations, categories, and attendance).\n\n💡 For general"
        " questions, search queries, or weather, please use the blue AI"
        " Assistant popup at the bottom-right corner!"
    )
  
@login_required(login_url='login')
def chat_room(request):
  # Get or create the EventBot system user
  bot_user, _ = User.objects.get_or_create(
      username='EventBot', defaults={'first_name': 'Event', 'last_name': 'Bot'}
  )

  if request.method == 'POST':
    content = request.POST.get('content', '').strip()
    if content:
      # 1. Save user's message
      Message.objects.create(
          sender=request.user, receiver=bot_user, content=content
      )

      # 2. Get local project reply
      bot_reply = get_project_bot_reply(request.user, content)

      # 3. Save bot's reply
      Message.objects.create(
          sender=bot_user, receiver=request.user, content=bot_reply
      )

    return redirect('chat_room')

  # Fetch all messages between user and bot
  chat_messages = (
      Message.objects.filter(
          sender__in=[request.user, bot_user],
          receiver__in=[request.user, bot_user],
      )
      .select_related('sender')
      .order_by('timestamp')
  )

  return render(
      request, 'chat/chat_room.html', {'chat_messages': chat_messages}
  )

@login_required(login_url='login')
def qr_code_page(request):
  today = timezone.localdate()

  upcoming_events = Event.objects.filter(event_date__gte=today).order_by(
      'event_date', 'event_time'
  )

  return render(
      request,
      'events/qr_page.html',
      {'events': upcoming_events, 'today': today},
  )


def admin_global_registration_qr(request, event_id=None):
  today = timezone.localdate()


  if event_id:
    event = get_object_or_404(Event, id=event_id)
    if event.event_date and event.event_date < today:
      return HttpResponseBadRequest(
          'Registration QR cannot be generated for completed events.'
      )
    relative_url = f"{reverse('register_member')}?event={event.id}"
  else:
  
    relative_url = reverse('register_member')


  registration_url = request.build_absolute_uri(relative_url)

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
  today = timezone.localdate()

  # Only permit upcoming or today's active events
  upcoming_events_qs = Event.objects.filter(event_date__gte=today).order_by(
      'event_date', 'event_time'
  )

  if request.method == 'POST':
    form = RegistrationForm(request.POST)

    # Restrict form validation choices strictly to future/today events
    if 'event' in form.fields:
      form.fields['event'].queryset = upcoming_events_qs

    if form.is_valid():
      registration = form.save(commit=False)
      event = registration.event
      email = registration.email.strip().lower() if registration.email else ''
      phone = registration.phone.strip() if hasattr(registration, 'phone') and registration.phone else ''

      # 1. Block registration if the event date has already passed
      if event.event_date and event.event_date < today:
        messages.error(
            request,
            f"Registration closed: '{event.name}' has already taken place on {event.event_date.strftime('%b %d, %Y')}."
        )
        return render(request, 'events/public_registration.html', {'form': form})

      # 2. Duplicate Prevention: Verify attendee has not already registered with this email or phone
      duplicate_filter = Q(email__iexact=email)
      if phone:
        duplicate_filter |= Q(phone=phone)

      if Registration.objects.filter(event=event).filter(duplicate_filter).exists():
        messages.warning(
            request,
            f"Duplicate Registration: You have already registered for '{event.name}' with this email or phone number."
        )
        return render(request, 'events/public_registration.html', {'form': form})

      # 3. Save instance (auto-generates ticket_id and attendance QR)
      registration.email = email
      registration.save()

      messages.success(
          request,
          f"Registration confirmed for '{event.name}'! Your attendance ticket has been generated."
      )
      return redirect('my_ticket', reg_id=registration.id)

  else:
    # Handle pre-selected event from URL parameter (e.g., from an event-specific QR code)
    initial_data = {}
    event_id = request.GET.get('event')
    if event_id:
      initial_data['event'] = event_id

    form = RegistrationForm(initial=initial_data)

    # Filter dropdown options so past events are never selectable
    if 'event' in form.fields:
      form.fields['event'].queryset = upcoming_events_qs

  return render(request, 'events/public_registration.html', {'form': form})

@csrf_exempt
def global_ai_chatbot_reply(request):
  if request.method == "POST":
    try:
      data = json.loads(request.body)
      prompt = data.get("message", "").strip()

      if not prompt:
        return JsonResponse(
            {"reply": "Please enter a valid question."}, status=400
        )
      
      client = genai.Client(api_key="REMOVED_GEMINI_API_KEY")

      config = types.GenerateContentConfig(
          tools=[types.Tool(google_search=types.GoogleSearch())],
          system_instruction=(
              "You are an intelligent, helpful AI assistant. Answer user"
              " questions accurately, concisely, and use plain clean text or"
              " short bullet points. Do not mention API limitations."
          ),
      )

      response = client.models.generate_content(
          model="gemini-2.5-flash", contents=prompt, config=config
      )

      reply = response.text if response.text else "No response received."
      return JsonResponse({"reply": reply})

    except Exception as e:
      return JsonResponse(
          {"reply": f"Error answering question: {str(e)}"}, status=500
      )

  return JsonResponse({"error": "Invalid request"}, status=400)

# 1. View & Download Personal Ticket
def my_ticket_view(request, reg_id):
  registration = get_object_or_404(Registration, id=reg_id)
  return render(request, 'events/ticket.html', {'reg': registration})


# 2. Admin Live Camera QR Scanner
@staff_member_required(login_url='login')
def scan_attendance_view(request):
  return render(request, 'events/scan_attendance.html')


# 3. Verify Scanned QR and Record Attendance
@staff_member_required(login_url='login')
def verify_ticket_attendance(request, ticket_id):
  registration = get_object_or_404(Registration, ticket_id=ticket_id)
  today = timezone.localdate()

  # Check if attendance is already recorded today
  attendance, created = Attendance.objects.get_or_create(
      registration=registration,
      attendance_date=today,
      defaults={'status': 'Present'},
  )

  if created:
    status = 'success'
    msg = f"Attendance Marked: {registration.full_name} is marked Present for '{registration.event.name}'."
  else:
    status = 'already_marked'
    msg = f"Notice: {registration.full_name} was already checked in today."

  if request.headers.get('x-requested-with') == 'XMLHttpRequest':
    return JsonResponse({
        'status': status,
        'message': msg,
        'name': registration.full_name,
        'event': registration.event.name,
        'college': registration.college,
    })

  messages.info(request, msg)
  return redirect('scan_attendance')