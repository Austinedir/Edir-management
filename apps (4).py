from django.contrib import admin
from .models import EdirEvent, Payout, MeetingMinute


@admin.register(EdirEvent)
class EdirEventAdmin(admin.ModelAdmin):
    list_display = ['member', 'event_type', 'event_date', 'status', 'edir']
    list_filter = ['event_type', 'status', 'edir']
    search_fields = ['member__first_name', 'member__last_name', 'deceased_name']
    readonly_fields = ['reported_by', 'verified_by', 'verified_at', 'approved_by', 'approved_at']


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['event', 'amount', 'status', 'recipient_name', 'disbursed_at']
    list_filter = ['status']
    readonly_fields = ['disbursed_by', 'disbursed_at']


@admin.register(MeetingMinute)
class MeetingMinuteAdmin(admin.ModelAdmin):
    list_display = ['date', 'location', 'edir', 'recorded_by']
    list_filter = ['edir']
    filter_horizontal = ['attendees']
