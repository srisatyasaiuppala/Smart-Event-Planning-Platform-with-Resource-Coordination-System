from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Category(models.Model):
    name = models.CharField(max_length=100)
    category_code = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.category_code})" 


class Event(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="events"
    )

    name = models.CharField(max_length=200, unique=True)

    description = models.TextField()

    event_date = models.DateField()

    end_date = models.DateField(null=True, blank=True)

    event_time = models.TimeField()

    venue = models.CharField(max_length=200)

    status = models.CharField(
        max_length=20,
        choices=[
            ("Upcoming", "Upcoming"),
            ("Completed", "Completed"),
        ],
        default="Upcoming",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Registration(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations"
    )

    full_name = models.CharField(max_length=100)

    email = models.EmailField()

    phone = models.CharField(max_length=15)

    college = models.CharField(max_length=200)

    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["event", "email"]

    def __str__(self):
        return self.full_name


class Attendance(models.Model):
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE
    )

    attendance_date = models.DateField(auto_now_add=True)

    status = models.CharField(
        max_length=10,
        choices=[
            ("Present", "Present"),
            ("Absent", "Absent"),
        ],
        default="Present",
    )

    class Meta:
        unique_together = ["registration", "attendance_date"]

    def __str__(self):
        return f"{self.registration.full_name} - {self.status}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    icon = models.CharField(max_length=50, default="fas fa-bell")
    link = models.CharField(max_length=255, default="/dashboard/")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


@receiver(post_save, sender=Event)
def event_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            title="New Event Created",
            message=f"Event '{instance.name}' was created.",
            icon="fas fa-calendar-plus text-success",
            link="/events/list/"
        )
    else:
        Notification.objects.create(
            title="Event Updated",
            message=f"Event '{instance.name}' details were updated.",
            icon="fas fa-calendar-alt text-warning",
            link="/events/list/"
        )


@receiver(post_save, sender=Category)
def category_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            title="New Category Added",
            message=f"Category '{instance.name}' was added.",
            icon="fas fa-folder-plus text-info",
            link="/category/list/"
        )
    else:
        Notification.objects.create(
            title="Category Updated",
            message=f"Category '{instance.name}' was updated.",
            icon="fas fa-folder text-warning",
            link="/category/list/"
        )


@receiver(post_save, sender=Registration)
def member_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            title="New Member Registered",
            message=f"Member '{instance.full_name}' was registered.",
            icon="fas fa-user-plus text-primary",
            link="/members/list/"
        )
    else:
        Notification.objects.create(
            title="Member Updated",
            message=f"Member '{instance.full_name}' profile was updated.",
            icon="fas fa-user-edit text-warning",
            link="/members/list/"
        )


@receiver(post_save, sender=Attendance)
def attendance_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            title="Attendance Marked",
            message=f"Attendance marked for {instance.registration.full_name}.",
            icon="fas fa-check-circle text-success",
            link="/attendance/list/"
        )
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
    
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.username}: {self.content[:20]}"