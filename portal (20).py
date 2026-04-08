from apps.members.models import EdirGroup


def edir_context(request):
    """Inject edir-wide context into every template."""
    edir = EdirGroup.objects.filter(is_active=True).first()
    unread_notif = 0
    unread_msgs = 0
    pending_apps = 0

    if request.user.is_authenticated:
        try:
            from apps.notifications.models import Notification
            from django.db.models import Q
            unread_notif = Notification.objects.filter(
                Q(member__user=request.user) | Q(member__isnull=True),
                is_read=False
            ).count()
        except Exception:
            pass

        try:
            from apps.members.models_extra import Message, MemberApplication
            unread_msgs = Message.objects.filter(
                recipient=request.user, is_read=False
            ).count()
            if request.user.is_staff:
                pending_apps = MemberApplication.objects.filter(status='pending').count()
        except Exception:
            pass

    return {
        'edir': edir,
        'unread_notifications': unread_notif,
        'unread_messages': unread_msgs,
        'pending_apps_count': pending_apps,
    }
