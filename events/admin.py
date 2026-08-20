from django.contrib import admin
from django.utils.html import format_html
from .models import Attendance, Category, Event, Registration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
  list_display = (
      "name",
      "category",
      "event_date",
      "venue",
      "status",
      "qr_code_preview",
  )
  readonly_fields = ("qr_code_display",)
  fields = (
      "category",
      "name",
      "description",
      "event_date",
      "end_date",
      "event_time",
      "venue",
      "status",
      "qr_code_display",
  )

  def qr_code_preview(self, obj):
    if obj.qr_code:
      return format_html(
          '<img src="{}" style="width: 45px; height: 45px; border-radius:'
          ' 4px;" />',
          obj.qr_code.url,
      )
    return "No QR"

  qr_code_preview.short_description = "QR Preview"

  def qr_code_display(self, obj):
    if obj.qr_code:
      return format_html(
          '<a href="{}" target="_blank">'
          '<img src="{}" style="width: 180px; height: 180px; border: 1px solid'
          ' #ddd; padding: 6px; border-radius: 6px;" />'
          "</a>"
          '<p style="color: #666; margin-top: 6px;">Click image to'
          " open/download full size.</p>",
          obj.qr_code.url,
          obj.qr_code.url,
      )
    return "QR Code will be generated automatically upon saving."

  qr_code_display.short_description = "Generated QR Code"


admin.site.register(Category)
admin.site.register(Registration)
admin.site.register(Attendance)