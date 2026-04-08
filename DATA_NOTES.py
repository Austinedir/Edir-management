from django.contrib import admin
from .models import ContributionPeriod, Contribution, SpecialLevy, LevyPayment


class ContributionInline(admin.TabularInline):
    model = Contribution
    extra = 0
    fields = ['member', 'amount', 'status', 'payment_method', 'paid_date', 'receipt_number']
    readonly_fields = ['member']


@admin.register(ContributionPeriod)
class ContributionPeriodAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'edir', 'amount', 'due_date', 'is_closed']
    list_filter = ['edir', 'year', 'is_closed']
    inlines = [ContributionInline]


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ['member', 'period', 'amount', 'status', 'payment_method', 'paid_date']
    list_filter = ['status', 'payment_method', 'period__year', 'period__month']
    search_fields = ['member__first_name', 'member__last_name', 'member__member_number', 'receipt_number']
    list_editable = ['status']


@admin.register(SpecialLevy)
class SpecialLevyAdmin(admin.ModelAdmin):
    list_display = ['title', 'edir', 'amount_per_member', 'due_date', 'is_active']
    list_filter = ['edir', 'is_active']
