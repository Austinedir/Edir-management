"""
Additional models to fulfil the Functional Requirements Document:
- MemberApplication  (FR 1.2 – New/prospective members register online)
- Message            (FR 1.1.6 – send/receive/document messages)
- Document           (FR 1.1.7 – view archived documents)
- MassMessage        (FR 3 – mass email / text)
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class MemberApplication(models.Model):
    """
    FR 1.2.1 – New users register online.
    FR 2.4.1/2.4.2 – Admin reviews and approves/denies.
    """
    class Status(models.TextChoices):
        PENDING   = 'pending',   _('Pending Review')
        APPROVED  = 'approved',  _('Approved')
        DENIED    = 'denied',    _('Denied')
        WAITLIST  = 'waitlist',  _('Waitlist')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edir = models.ForeignKey('members.EdirGroup', on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Applicant info
    first_name   = models.CharField(_('First Name'), max_length=100)
    last_name    = models.CharField(_('Last Name'), max_length=100)
    gender       = models.CharField(_('Gender'), max_length=1, choices=[('M','Male'),('F','Female')])
    date_of_birth = models.DateField(_('Date of Birth'), null=True, blank=True)
    phone        = models.CharField(_('Phone'), max_length=20)
    email        = models.EmailField(_('Email'))
    address      = models.TextField(_('Address'))
    city         = models.CharField(max_length=100)
    state        = models.CharField(max_length=2, default='TX')
    zip_code     = models.CharField(max_length=10)

    # Emergency/designee
    rep_name     = models.CharField(_('Designated Representative'), max_length=200, blank=True)
    rep_phone    = models.CharField(_('Rep Phone'), max_length=20, blank=True)
    rep_relation = models.CharField(_('Rep Relationship'), max_length=100, blank=True)

    # Family members (JSON list of dicts)
    family_members_json = models.TextField(_('Family Members (JSON)'), blank=True, default='[]')

    # Registration payment
    registration_fee_paid = models.BooleanField(default=False)
    payment_reference     = models.CharField(max_length=100, blank=True)
    payment_method        = models.CharField(max_length=30, blank=True)

    # County/state verification (FR 2.4.8, 2.4.9)
    residential_verified = models.BooleanField(default=False)
    county_verified      = models.BooleanField(default=False)

    # Workflow
    reviewed_by  = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_applications'
    )
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    denial_reason = models.TextField(blank=True)
    approval_notes = models.TextField(blank=True)

    # Converted member (set when approved)
    converted_member = models.OneToOneField(
        'members.Member', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='application'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Membership Application')
        verbose_name_plural = _('Membership Applications')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} – {self.get_status_display()}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Message(models.Model):
    """
    FR 1.1.6 – Members can send, receive, and document messages.
    FR 4.3 – Archive of notices sent to members.
    """
    class MessageType(models.TextChoices):
        INBOX     = 'inbox',    _('Inbox')
        OUTBOX    = 'outbox',   _('Outbox')
        SYSTEM    = 'system',   _('System Notice')
        BROADCAST = 'broadcast', _('Broadcast')

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender      = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_messages'
    )
    recipient   = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='received_messages'
    )
    # If recipient is None → broadcast to all
    edir        = models.ForeignKey(
        'members.EdirGroup', on_delete=models.CASCADE, related_name='messages',
        null=True, blank=True
    )
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.INBOX)
    subject     = models.CharField(max_length=255)
    body        = models.TextField()
    is_read     = models.BooleanField(default=False)
    read_at     = models.DateTimeField(null=True, blank=True)
    archived    = models.BooleanField(default=False)
    # Related objects (optional)
    related_event_id    = models.UUIDField(null=True, blank=True)  # soft ref to EdirEvent
    related_application = models.ForeignKey(MemberApplication, null=True, blank=True, on_delete=models.SET_NULL)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} → {self.recipient or 'All'}"

    def mark_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Document(models.Model):
    """
    FR 1.1.7 – Members can view archived documents.
    FR 2.1.1 – Admin uploads bank statements.
    """
    class Category(models.TextChoices):
        FINANCIAL   = 'financial',   _('Financial Statement')
        BANK_STMT   = 'bank_stmt',   _('Bank Statement')
        MINUTES     = 'minutes',     _('Meeting Minutes')
        POLICY      = 'policy',      _('Policy / Rules')
        RECEIPT     = 'receipt',     _('Receipt')
        OTHER       = 'other',       _('Other')

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edir        = models.ForeignKey('members.EdirGroup', on_delete=models.CASCADE, related_name='documents')
    title       = models.CharField(_('Title'), max_length=255)
    category    = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    description = models.TextField(blank=True)
    file        = models.FileField(upload_to='documents/%Y/%m/', blank=True, null=True)
    is_public   = models.BooleanField(_('Visible to Members'), default=True)
    uploaded_by = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    year        = models.PositiveIntegerField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"


class MassMessage(models.Model):
    """
    FR 3.1 – Admin sends mass emails.
    FR 3.2 – Admin sends mass texts.
    FR 4.1/4.2 – Extract contact info and send from website.
    FR 4.3 – Archive of notices sent.
    """
    class Channel(models.TextChoices):
        EMAIL = 'email', _('Email')
        SMS   = 'sms',   _('SMS / Text')
        BOTH  = 'both',  _('Email + SMS')

    class Status(models.TextChoices):
        DRAFT     = 'draft',     _('Draft')
        SCHEDULED = 'scheduled', _('Scheduled')
        SENDING   = 'sending',   _('Sending')
        SENT      = 'sent',      _('Sent')
        FAILED    = 'failed',    _('Failed')

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edir      = models.ForeignKey('members.EdirGroup', on_delete=models.CASCADE, related_name='mass_messages')
    channel   = models.CharField(max_length=10, choices=Channel.choices, default=Channel.EMAIL)
    subject   = models.CharField(max_length=255)
    body      = models.TextField()
    status    = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)

    # Targeting
    target_active_only = models.BooleanField(default=True)
    target_city        = models.CharField(max_length=100, blank=True, help_text='Filter by city (blank = all)')

    # Tracking
    recipients_count   = models.PositiveIntegerField(default=0)
    sent_count         = models.PositiveIntegerField(default=0)
    failed_count       = models.PositiveIntegerField(default=0)

    sent_by   = models.ForeignKey('members.User', on_delete=models.SET_NULL, null=True)
    sent_at   = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Mass Message')
        verbose_name_plural = _('Mass Messages')
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_channel_display()}] {self.subject} – {self.get_status_display()}"
