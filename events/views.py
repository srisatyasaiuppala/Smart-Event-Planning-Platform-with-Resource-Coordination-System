from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
import random
from django.core.mail import send_mail
from django.conf import settings
from datetime import date



from .models import (
    Category,
    Event,
    Registration,
    Attendance,
    Notification,
    Profile,
    Message,
)
from .forms import (
    SignUpForm,
    CategoryForm,
    EventForm,
    RegistrationForm,
    AttendanceForm,
)


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
                messages.success(request, f"User '{user.username}' created successfully!")
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

                # STRICT CHECK 1: If Admin tries logging in with 'User' radio selected
                if selected_role == "user" and is_admin:
                    messages.error(
                        request,
                        "Access Denied: Admin accounts must select the 'Admin' option to log in."
                    )
                    return render(request, "registration/login.html", {"form": form})

                # STRICT CHECK 2: If Regular User tries logging in with 'Admin' radio selected
                if selected_role == "admin" and not is_admin:
                    messages.error(
                        request,
                        "Access Denied: Regular user accounts cannot log in as Admin."
                    )
                    return render(request, "registration/login.html", {"form": form})

                # Successful validation - Proceed to log in and redirect
                login(request, user)

                if is_admin:
                    return redirect("dashboard")
                else:
                    return redirect("user_dashboard")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, "registration/login.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("login")


@login_required
def user_event_list(request):
    # If an Admin attempts to access the user page, send them to the Dashboard
    if request.user.is_staff or request.user.is_superuser:
        return redirect("dashboard")

    search = request.GET.get("search", "").strip()
    events = Event.objects.select_related("category").filter(status="Upcoming")

    if search:
        events = events.filter(
            Q(name__icontains=search) |
            Q(category__name__icontains=search) |
            Q(venue__icontains=search)
        )

    events = events.order_by("-event_date")
    return render(request, "user/user_events.html", {"events": events, "search": search})

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

    registrations = Registration.objects.filter(conditions).distinct().select_related('event').order_by('-registered_at')

    return render(request, 'user/my_registered_events.html', {
        'registrations': registrations,
        'today': date.today()
    })

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

  # Dynamic count based on date and status
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
      Attendance.objects.select_related(
          "registration", "registration__event"
      )
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

    # Replaced description with category_code
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
    return render(request, "category/category_list.html", {"categories": categories})


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
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("event_list")
    else:
        form = EventForm()

    return render(request, "events/create_event.html", {"form": form})


@login_required
def event_list(request):
    search_query = request.GET.get('search', '')
    events = Event.objects.all().select_related('category').order_by('-event_date')

    if search_query:
        events = events.filter(name__icontains=search_query)

    context = {
        'events': events,
        'today': date.today(),
        'search_query': search_query,
    }
    return render(request, 'events/event_list.html', context)

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

            if registration.event.event_date and registration.event.event_date < date.today():
                messages.error(request, "Registration closed: This event has already ended.")
                return render(request, "members/register_member.html", {"form": form})
            
            if not registration.email and request.user.email:
                registration.email = request.user.email
                
            if not registration.full_name:
                registration.full_name = request.user.get_full_name() or request.user.username

            registration.save()

            create_notification(
                user=request.user,
                title="Registration Confirmed",
                message=f"You have successfully registered for {registration.event.name}!",
                icon="fas fa-calendar-check text-success",
            )

            messages.success(request, "Registration successful!")

            if request.user.is_staff or request.user.is_superuser:
                return redirect("member_list")
            else:
                return redirect("my_registered_events")
    else:
        initial_data = {}
        if request.user.email:
            initial_data['email'] = request.user.email
        if request.user.username:
            initial_data['full_name'] = request.user.get_full_name() or request.user.username
            
        form = RegistrationForm(initial=initial_data)
        if 'event' in form.fields and not (request.user.is_staff or request.user.is_superuser):
            form.fields['event'].queryset = Event.objects.filter(event_date__gte=date.today()).order_by('event_date')

    return render(request, "members/register_member.html", {"form": form})

@login_required
def member_list(request):
    members = Registration.objects.select_related("event").all().order_by("-registered_at", "-id")
    return render(request, "members/member_list.html", {"members": members})


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
    attendance = Attendance.objects.select_related(
        "registration",
        "registration__event"
    ).all().order_by("-attendance_date", "-id")

    return render(
        request,
        "attendance/attendance_list.html",
        {"attendance": attendance},
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
def edit_member(request, pk):
    member = get_object_or_404(Registration, id=pk)

    if request.method == "POST":
        form = RegistrationForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            return redirect("member_list")
    else:
        form = RegistrationForm(instance=member)

    return render(request, "members/register_member.html", {"form": form, "edit_mode": True})


@login_required
def delete_member(request, pk):
    member = get_object_or_404(Registration, id=pk)
    member.delete()
    return redirect("member_list")


@login_required
def profile_view(request):
    return render(request, 'profile.html')


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    return render(request, 'edit_profile.html')


@login_required
def upload_profile_pic(request):
    if request.method == 'POST' and request.FILES.get('profile_image'):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.image = request.FILES['profile_image']
        profile.save()
        messages.success(request, 'Profile picture updated!')
    return redirect('profile')


@login_required
def remove_profile_pic(request):
    if hasattr(request.user, 'profile') and request.user.profile.image:
        request.user.profile.image.delete()
        request.user.profile.save()
        messages.success(request, 'Profile picture removed!')
    return redirect('profile')


@login_required
def settings_view(request):
    return render(request, 'settings.html')


def create_notification(user, title, message, icon="fas fa-user-plus text-success"):
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        icon=icon
    )


def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    notification.is_read = True
    notification.save()
    return redirect(notification.link)


@login_required
def all_notifications(request):
    if request.user.is_staff or request.user.is_superuser:
        # Admin gets all system notifications
        notifications = Notification.objects.all().order_by('-created_at')
    else:
        # Regular user gets only notifications assigned to their account
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'events/all_notifications.html', {'notifications': notifications})


@login_required
def send_message(request):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                sender=request.user,
                content=content
            )
            messages.success(request, 'Message sent successfully!')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
def chat_room(request):
    chat_messages = Message.objects.all().order_by('timestamp')
    Message.objects.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return render(request, 'chat/chat_room.html', {'chat_messages': chat_messages})

def forgot_password(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        
        # Search user by email or username
        user = User.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier)).first()
        
        if user:
            # Generate 6-digit OTP
            otp = str(random.randint(100000, 999999))
            
            # Store OTP and User ID in session (expires in 10 mins)
            request.session['reset_user_id'] = user.id
            request.session['reset_otp'] = otp
            request.session.set_expiry(600)

            # Send OTP via Email
            if user.email:
                send_mail(
                    subject="Password Reset OTP - Event Management",
                    message=f"Hello {user.first_name or user.username},\n\nYour OTP to reset your password is: {otp}\n\nThis OTP is valid for 10 minutes.",
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventmanagement.com'),
                    recipient_list=[user.email],
                    fail_silently=True,
                )

            # Note: For SMS in local dev, OTP is printed in terminal
            print(f"\n===========================\nOTP FOR {user.username}: {otp}\n===========================\n")

            messages.success(request, f"OTP has been sent to your registered email/phone!")
            return redirect('verify_otp')
        else:
            messages.error(request, "No account found with provided Email or Username.")

    return render(request, "registration/forgot_password.html")


def verify_otp(request):
    if 'reset_otp' not in request.session:
        messages.error(request, "Session expired. Please request OTP again.")
        return redirect('forgot_password')

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        session_otp = request.session.get("reset_otp")

        if entered_otp == session_otp:
            request.session['otp_verified'] = True
            messages.success(request, "OTP verified! Please set a new password.")
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "registration/verify_otp.html")


def reset_password(request):
    if not request.session.get('otp_verified'):
        messages.error(request, "Unauthorized access. Please verify OTP first.")
        return redirect('forgot_password')

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
        else:
            user_id = request.session.get('reset_user_id')
            user = get_object_or_404(User, id=user_id)
            user.set_password(password)
            user.save()

            # Clear reset session keys
            for key in ['reset_user_id', 'reset_otp', 'otp_verified']:
                if key in request.session:
                    del request.session[key]

            messages.success(request, "Password reset successful! Please login.")
            return redirect('login')

    return render(request, "registration/reset_password.html")

@login_required
def user_dashboard(request):
  user = request.user
  today = date.today()

  # 1. Total events created in the system
  total_events_count = Event.objects.count()

  # 2. Registrations for the logged-in user
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
      .select_related('event')
  )
  registrations_count = user_registrations.count()

  # 3. Upcoming events
  upcoming_count = Event.objects.filter(
      event_date__gte=today, status='Upcoming'
  ).count()

  # 4. Completed events
  completed_count = Event.objects.filter(
      Q(event_date__lt=today) | Q(status='Completed')
  ).count()

  context = {
      'total_events_count': total_events_count,
      'registrations_count': registrations_count,
      'upcoming_count': upcoming_count,
      'completed_count': completed_count,
      'recent_registrations': user_registrations.order_by('-registered_at')[:5],
  }
  return render(request, 'user/user_dashboard.html', context)


@login_required
def user_event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    is_ended = event.event_date < date.today() if event.event_date else False
    return render(request, "user/user_event_detail.html", {"event": event, "is_ended": is_ended})