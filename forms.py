from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class EdirEvent(models.Model):
    """An event that triggers edir support (death, illness, etc.)."""

    class EventType(models.TextChoices):
        DEATH_MEMBER = 'death_member', _('Death of Member')
        DEATH_SPOUSE = 'death_spouse', _("Death of Member's Spouse")
        DEATH_CHILD = 'death_child', _("Death of Member's Child")
        DEATH_PARENT = 'death_parent', _("Death of Member's Parent")
        SERIOUS_ILLNESS = 'illness', _('Serious Illness')
        MARRIAGE = 'marriage', _('Marriage')
        OTHER = 'other', _('Other')

    class Status(models.TextChoices):
        REPORTED = 'reported', _('Reported')
        VERIFIED = 'verified', _('Verified')
        APPROVED = 'approved', _('Approved')
        PAYOUT_PENDING = 'payout_pending', _('Payout Pending')
        CLOSED = 'closed', _('Closed')
        REJECTED = 'rejected', _('Rejected')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edir = models.ForeignKey('members.EdirGroup', on_delete=models.CASCADE, related_name='events')
    member = models.ForeignKey(
        'members.Member', on_delete=models.CASCADE, related_name='events',
        verbose_name=_('Affected Member')
    )
    event_type = models.CharField(_('Event Type'), max_length=30, choices=EventType.choices)
    status = models.CharField(_('Status'), max_length=20, choices=Status.choices, default=Status.REPORTED)

    # Event details
    event_date = models.DateField(_('Event Date'))
    deceased_name = models.CharField(_('Deceased / Affected Person Name'), max_length=200, blank=True)
    description = models.TextField(_('Description'), blank=True)

    # Location
    funeral_location = models.CharField(_('Funeral / Event Location'), max_length=300, blank=True)
    funeral_date = models.DateField(_('Funeral / Ceremony Date'), null=True, blank=True)

    # Documents
    death_certificate = models.FileField(
        _('Death Certificate'), upload_to='events/documents/', blank=True, null=True
    )
    supporting_document = models.FileField(
        _('Supporting Document'), upload_to='events/documents/', blank=True, null=True
    )

    # Workflow
    reported_by = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reported_events', verbose_name=_('Reported By')
    )
    verified_by = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_events', verbose_name=_('Verified By')
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_events', verbose_name=_('Approved By')
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(_('Internal Notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Edir Event')
        verbose_name_plural = _('Edir Events')
        ordering = ['-event_date']

    def __str__(self):
        return f"{self.get_event_type_display()} – {self.member.full_name} ({self.event_date})"

    def get_payout_amount(self):
        """Determine payout based on event type and edir rules."""
        base = self.edir.death_payout
        multipliers = {
            self.EventType.DEATH_MEMBER: 1.0,
            self.EventType.DEATH_SPOUSE: 0.75,
            self.EventType.DEATH_CHILD: 0.5,
            self.EventType.DEATH_PARENT: 0.5,
            self.EventType.SERIOUS_ILLNESS: 0.25,
            self.EventType.MARRIAGE: 0.1,
            self.EventType.OTHER: 0.0,
        }
        return base * multipliers.get(self.event_type, 0)


class Payout(models.Model):
    """Financial payout for an event."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        DISBURSED = 'disbursed', _('Disbursed')
        CANCELLED = 'cancelled', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(EdirEvent, on_delete=models.CASCADE, related_name='payout')
    amount = models.DecimalField(_('Payout Amount (ETB)'), max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    recipient_name = models.CharField(_('Recipient Name'), max_length=200)
    recipient_phone = models.CharField(_('Recipient Phone'), max_length=20, blank=True)
    payment_method = models.CharField(_('Payment Method'), max_length=100, blank=True)
    payment_reference = models.CharField(_('Payment Reference'), max_length=100, blank=True)

    disbursed_by = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='disbursed_payouts'
    )
    disbursed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Payout')
        verbose_name_plural = _('Payouts')

    def __str__(self):
        return f"Payout {self.amount} ETB – {self.event}"


class MeetingMinute(models.Model):
    """Record of edir meetings."""
    edir = models.ForeignKey('members.EdirGroup', on_delete=models.CASCADE, related_name='meetings')
    date = models.DateField(_('Meeting Date'))
    location = models.CharField(_('Location'), max_length=200, blank=True)
    agenda = models.TextField(_('Agenda'), blank=True)
    minutes = models.TextField(_('Minutes / Notes'))
    attendees = models.ManyToManyField('members.Member', blank=True, verbose_name=_('Attendees'))
    document = models.FileField(_('Attached Document'), upload_to='meetings/', blank=True, null=True)
    recorded_by = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Meeting Minute')
        verbose_name_plural = _('Meeting Minutes')
        ordering = ['-date']

    def __str__(self):
        return f"Meeting – {self.date}"
