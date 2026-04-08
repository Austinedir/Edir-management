from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
import uuid


class User(AbstractUser):
    """Extended user model for edir members."""
    email = models.EmailField(_('email address'), unique=True)

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')


class EdirGroup(models.Model):
    """An edir organization (supports multi-edir setups)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Edir Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    founded_date = models.DateField(_('Founded Date'), null=True, blank=True)
    location = models.CharField(_('Location'), max_length=300, blank=True)
    monthly_contribution = models.DecimalField(
        _('Monthly Contribution (ETB)'), max_digits=10, decimal_places=2, default=100
    )
    death_payout = models.DecimalField(
        _('Death Event Payout (ETB)'), max_digits=12, decimal_places=2, default=5000
    )
    logo = models.ImageField(_('Logo'), upload_to='edir/logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Edir Group')
        verbose_name_plural = _('Edir Groups')

    def __str__(self):
        return self.name


class Member(models.Model):
    """An edir member."""

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        SUSPENDED = 'suspended', _('Suspended')
        DECEASED = 'deceased', _('Deceased')
        WITHDRAWN = 'withdrawn', _('Withdrawn')

    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='member_profile', verbose_name=_('User Account')
    )
    edir = models.ForeignKey(
        EdirGroup, on_delete=models.CASCADE, related_name='members', verbose_name=_('Edir')
    )

    # Identity
    member_number = models.CharField(_('Member Number'), max_length=20, unique=True, blank=True)
    first_name = models.CharField(_('First Name'), max_length=100)
    last_name = models.CharField(_('Last Name'), max_length=100)
    gender = models.CharField(_('Gender'), max_length=1, choices=Gender.choices)
    date_of_birth = models.DateField(_('Date of Birth'), null=True, blank=True)
    photo = models.ImageField(_('Photo'), upload_to='members/photos/', blank=True, null=True)

    # Contact
    phone = PhoneNumberField(_('Phone Number'), blank=True)
    email = models.EmailField(_('Email'), blank=True)
    address = models.TextField(_('Address'), blank=True)
    kebele = models.CharField(_('Kebele'), max_length=100, blank=True)
    woreda = models.CharField(_('Woreda'), max_length=100, blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True, default='Austin')
    state = models.CharField(_('State'), max_length=10, blank=True, default='TX')
    zip_code = models.CharField(_('Zip Code'), max_length=20, blank=True)

    # Membership
    status = models.CharField(
        _('Status'), max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    join_date = models.DateField(_('Join Date'))
    exit_date = models.DateField(_('Exit Date'), null=True, blank=True)

    # Emergency contact
    emergency_contact_name = models.CharField(_('Emergency Contact Name'), max_length=200, blank=True)
    emergency_contact_phone = PhoneNumberField(_('Emergency Contact Phone'), blank=True)
    emergency_contact_relation = models.CharField(_('Relationship'), max_length=100, blank=True)

    # Internal
    notes = models.TextField(_('Internal Notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Member')
        verbose_name_plural = _('Members')
        ordering = ['member_number']

    def __str__(self):
        return f"{self.member_number} – {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.member_number:
            last = Member.objects.filter(edir=self.edir).order_by('-created_at').first()
            if last and last.member_number:
                try:
                    num = int(last.member_number.split('-')[-1]) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            self.member_number = f"EDR-{num:04d}"
        super().save(*args, **kwargs)

    def get_arrears(self):
        """How many months behind on contributions."""
        from apps.contributions.models import Contribution
        from django.utils import timezone
        import datetime
        paid = Contribution.objects.filter(
            member=self, status=Contribution.Status.PAID
        ).count()
        months_active = max(
            (timezone.now().date() - self.join_date).days // 30, 0
        )
        return max(months_active - paid, 0)


class Beneficiary(models.Model):
    """Member's registered beneficiaries for payouts."""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='beneficiaries')
    name = models.CharField(_('Full Name'), max_length=200)
    relationship = models.CharField(_('Relationship'), max_length=100)
    phone = PhoneNumberField(_('Phone'), blank=True)
    share_percentage = models.DecimalField(
        _('Share %'), max_digits=5, decimal_places=2, default=100
    )

    class Meta:
        verbose_name = _('Beneficiary')
        verbose_name_plural = _('Beneficiaries')

    def __str__(self):
        return f"{self.name} ({self.relationship}) – {self.member.full_name}"


# ── Additional models (FR requirements) ─────────────────────────
from apps.members.models_extra import MemberApplication, Message, Document, MassMessage
