from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class ContributionPeriod(models.Model):
    """A monthly billing period."""
    edir = models.ForeignKey('members.EdirGroup', on_delete=models.CASCADE, related_name='periods')
    year = models.PositiveIntegerField(_('Year'))
    month = models.PositiveIntegerField(_('Month'))  # 1-12
    amount = models.DecimalField(_('Amount (ETB)'), max_digits=10, decimal_places=2)
    due_date = models.DateField(_('Due Date'))
    is_closed = models.BooleanField(_('Closed'), default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Contribution Period')
        verbose_name_plural = _('Contribution Periods')
        unique_together = [('edir', 'year', 'month')]
        ordering = ['-year', '-month']

    def __str__(self):
        import calendar
        return f"{calendar.month_name[self.month]} {self.year}"

    @property
    def label(self):
        import calendar
        return f"{calendar.month_name[self.month]} {self.year}"

    def get_collection_rate(self):
        total = self.contributions.filter(
            member__status='active'
        ).count()
        paid = self.contributions.filter(status=Contribution.Status.PAID).count()
        return (paid / total * 100) if total else 0


class Contribution(models.Model):
    """A single member's contribution record for a period."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PAID = 'paid', _('Paid')
        WAIVED = 'waived', _('Waived')
        DEFAULTED = 'defaulted', _('Defaulted')

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', _('Cash')
        BANK = 'bank', _('Bank Transfer')
        MOBILE = 'mobile', _('Mobile Money (CBE Birr / TeleBirr)')
        CHEQUE = 'cheque', _('Cheque')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.ForeignKey(ContributionPeriod, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(_('Amount (ETB)'), max_digits=10, decimal_places=2)
    status = models.CharField(_('Status'), max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(
        _('Payment Method'), max_length=20, choices=PaymentMethod.choices, blank=True
    )
    paid_date = models.DateField(_('Paid Date'), null=True, blank=True)
    receipt_number = models.CharField(_('Receipt #'), max_length=50, blank=True)
    collected_by = models.ForeignKey(
        'members.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='collected_contributions', verbose_name=_('Collected By')
    )
    waiver_reason = models.TextField(_('Waiver Reason'), blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Contribution')
        verbose_name_plural = _('Contributions')
        unique_together = [('period', 'member')]
        ordering = ['-period__year', '-period__month', 'member__member_number']

    def __str__(self):
        return f"{self.member.full_name} – {self.period} – {self.get_status_display()}"

    def mark_paid(self, method, collected_by=None, receipt=None):
        self.status = self.Status.PAID
        self.paid_date = timezone.now().date()
        self.payment_method = method
        if collected_by:
            self.collected_by = collected_by
        if receipt:
            self.receipt_number = receipt
        self.save()


class SpecialLevy(models.Model):
    """Extra one-off levy (e.g., funeral costs beyond standard payout)."""
    edir = models.ForeignKey('members.EdirGroup', on_delete=models.CASCADE, related_name='levies')
    title = models.CharField(_('Title'), max_length=200)
    reason = models.TextField(_('Reason'))
    amount_per_member = models.DecimalField(_('Amount per Member (ETB)'), max_digits=10, decimal_places=2)
    due_date = models.DateField(_('Due Date'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    event = models.ForeignKey(
        'events.EdirEvent', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='levies', verbose_name=_('Related Event')
    )

    class Meta:
        verbose_name = _('Special Levy')
        verbose_name_plural = _('Special Levies')

    def __str__(self):
        return self.title


class LevyPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PAID = 'paid', _('Paid')
        WAIVED = 'waived', _('Waived')

    levy = models.ForeignKey(SpecialLevy, on_delete=models.CASCADE, related_name='payments')
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='levy_payments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paid_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = [('levy', 'member')]

    def __str__(self):
        return f"{self.member.full_name} – {self.levy.title}"
