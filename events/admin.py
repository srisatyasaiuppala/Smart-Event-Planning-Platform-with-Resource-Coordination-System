from django.contrib import admin
from .models import Category, Event, Registration, Attendance

admin.site.register(Category)
admin.site.register(Event)
admin.site.register(Registration)
admin.site.register(Attendance)