from .models import Notification

def notifications_processor(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            # Admin gets all unread system notifications
            unread_notifications = Notification.objects.filter(is_read=False)
        else:
            # Regular User gets only their own unread notifications
            unread_notifications = Notification.objects.filter(user=request.user, is_read=False)

        return {
            'notifications_count': unread_notifications.count(),
            'notifications_list': unread_notifications.order_by('-created_at')[:5]
        }
    return {
        'notifications_count': 0,
        'notifications_list': []
    }