from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class Notification(models.Model):
    class Type(models.TextChoices):
        CONTRIBUTION_DUE = 'contribution_due', _('Contribution Due')
        CONTRIBUTION_OVERDUE = 'contribution_overdue', _('Contribution Overdue')
        EVENT_REPORTED = 'event_reported', _('Event Reported')
        PAYOUT_APPROVED = 'payout_approved', _('Payout Approved')
        MEETING_REMINDER = 'meeting_reminder', _('Meeting Reminder')
        GENERAL = 'general', _('General Announcement')

    class Channel(models.TextChoices):
        EMAIL = 'email', _('Email')
        SMS = 'sms', _('SMS')
        IN_APP = 'in_app', _('In-App')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        'members.Member', on_delete=models.CASCADE, related_name='notifications',
        null=True, blank=True  # null = broadcast to all
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional links
    related_event = models.ForeignKey(
        'events.EdirEvent', on_delete=models.SET_NULL, null=True, blank=True
    )
    related_contribution_period = models.ForeignKey(
        'contributions.ContributionPeriod', on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} → {self.member or 'All'}"

    def mark_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Announcement(models.Model):
    """Broadcast announcement to all edir members."""
    edir = models.ForeignKey('members.EdirGroup', on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(_('Title'), max_length=200)
    body = models.TextField(_('Body'))
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('members.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Announcement')
        verbose_name_plural = _('Announcements')
        ordering = ['-created_at']

    def __str__(self):
        return self.title
