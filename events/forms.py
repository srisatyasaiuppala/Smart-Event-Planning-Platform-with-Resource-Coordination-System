from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Category,Event,Registration
from .models import Attendance
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from datetime import date

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "password1",
            "password2",
        )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'category_code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name','required': 'required'}),
            'category_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CAT-01','required': 'required'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            query = Category.objects.filter(name__iexact=name)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                raise forms.ValidationError("A category with this name already exists!")
        return name

from datetime import date
from django import forms
from django.utils import timezone
from .models import Event


class EventForm(forms.ModelForm):

  class Meta:
    model = Event
    fields = [
        'category',
        'name',
        'description',
        'event_date',
        'end_date',
        'event_time',
        'venue',
        'status',
    ]

    widgets = {
        'category': forms.Select(attrs={'class': 'form-control'}),
        'name': forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Enter event title'}
        ),
        'description': forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter event description...',
            }
        ),
        'event_date': forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.localdate().isoformat(),
            }
        ),
        'end_date': forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.localdate().isoformat(),
            }
        ),
        'event_time': forms.TimeInput(
            attrs={'class': 'form-control', 'type': 'time'}
        ),
        'venue': forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter venue or location',
            }
        ),
        'status': forms.Select(attrs={'class': 'form-control'}),
    }

  def clean_name(self):
    name = self.cleaned_data.get('name', '').strip()

    # Case-insensitive duplicate check
    existing_events = Event.objects.filter(name__iexact=name)

    # Allow keeping the same name when editing an existing event
    if self.instance and self.instance.pk:
      existing_events = existing_events.exclude(pk=self.instance.pk)

    if existing_events.exists():
      raise forms.ValidationError(
          f"An event named '{name}' already exists (names must be unique"
          ' regardless of uppercase/lowercase).'
      )

    return name

  def clean(self):
    cleaned_data = super().clean()
    event_date = cleaned_data.get('event_date')
    end_date = cleaned_data.get('end_date')

    # Date range validation
    if event_date and end_date and end_date < event_date:
      self.add_error(
          'end_date', 'The end date cannot be earlier than the start date.'
      )

    return cleaned_data

  def clean_event_date(self):
    event_date = self.cleaned_data.get('event_date')
    if not self.instance.pk and event_date and event_date < date.today():
      raise forms.ValidationError('Date must be today or a future date.')
    return event_date

  def clean(self):
    cleaned_data = super().clean()
    event_date = cleaned_data.get('event_date')
    end_date = cleaned_data.get('end_date')

    if event_date and end_date:
      if end_date < event_date:
        self.add_error(
            'end_date', 'End date must be the same as or after start date.'
        )

    return cleaned_data

class RegistrationForm(forms.ModelForm):
  first_name = forms.CharField(
      max_length=100,
      required=True,
      widget=forms.TextInput(
          attrs={'class': 'form-control', 'placeholder': 'Enter first name'}
      ),
  )
  last_name = forms.CharField(
      max_length=100,
      required=True,
      widget=forms.TextInput(
          attrs={'class': 'form-control', 'placeholder': 'Enter last name'}
      ),
  )

  class Meta:
    model = Registration
    fields = [
        'event',
        'email',
        'phone',
        'college',
    ]
    widgets = {
        'event': forms.Select(attrs={'class': 'form-control'}),
        'email': forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address',
            }
        ),
        'phone': forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}
        ),
        'college': forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter college/institution name',
            }
        ),
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # Populate first_name and last_name when editing an existing registration
    if self.instance and self.instance.pk and self.instance.full_name:
      name_parts = self.instance.full_name.strip().split(' ', 1)
      self.fields['first_name'].initial = name_parts[0]
      if len(name_parts) > 1:
        self.fields['last_name'].initial = name_parts[1]

    # Explicitly enforce field rendering order
    self.order_fields(
        ['event', 'first_name', 'last_name', 'email', 'phone', 'college']
    )

  def clean(self):
    cleaned_data = super().clean()
    event = cleaned_data.get('event')
    email = cleaned_data.get('email')
    phone = cleaned_data.get('phone')

    # Duplicate email check for this specific event
    if event and email:
      email_query = Registration.objects.filter(
          event=event, email__iexact=email
      )
      if self.instance and self.instance.pk:
        email_query = email_query.exclude(pk=self.instance.pk)

      if email_query.exists():
        self.add_error(
            'email',
            'A member with this email is already registered for this event!',
        )

    # Duplicate phone check for this specific event
    if event and phone:
      phone_query = Registration.objects.filter(
          event=event, phone=phone.strip()
      )
      if self.instance and self.instance.pk:
        phone_query = phone_query.exclude(pk=self.instance.pk)

      if phone_query.exists():
        self.add_error(
            'phone',
            'A member with this phone number is already registered for this'
            ' event!',
        )

    return cleaned_data

  def save(self, commit=True):
    instance = super().save(commit=False)
    first_name = self.cleaned_data.get('first_name', '').strip()
    last_name = self.cleaned_data.get('last_name', '').strip()
    instance.full_name = f'{first_name} {last_name}'.strip()

    if commit:
      instance.save()
    return instance

class AttendanceForm(forms.ModelForm):

    class Meta:

        model = Attendance

        fields = [
            "registration",
            "status",
        ]

        widgets = {

            "registration": forms.Select(attrs={
                "class":"form-control"
            }),

            "status": forms.Select(attrs={
                "class":"form-control"
            }),

        }
class CustomPasswordChangeForm(PasswordChangeForm):
    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password')
        new_password1 = cleaned_data.get('new_password1')

        if old_password and new_password1 and old_password == new_password1:
            raise ValidationError(
                "Your new password cannot be the same as your old password."
            )
        return cleaned_data