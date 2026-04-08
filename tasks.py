from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, EdirGroup, Member, Beneficiary
from .models_extra import MemberApplication, Message, Document, MassMessage


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']


class BeneficiaryInline(admin.TabularInline):
    model = Beneficiary
    extra = 1
    fields = ['name', 'relationship', 'phone', 'share_percentage']


@admin.register(EdirGroup)
class EdirGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'monthly_contribution', 'death_payout', 'is_active']
    list_editable = ['is_active']
    fieldsets = [
        (None, {'fields': ['name', 'description', 'logo']}),
        ('Location', {'fields': ['location', 'founded_date']}),
        ('Financial Rules', {'fields': ['monthly_contribution', 'death_payout']}),
        ('Status', {'fields': ['is_active']}),
    ]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['member_number', 'full_name', 'city', 'phone', 'status', 'join_date', 'edir']
    list_filter = ['status', 'gender', 'edir', 'city']
    search_fields = ['first_name', 'last_name', 'member_number', 'phone', 'email']
    readonly_fields = ['member_number', 'created_at', 'updated_at']
    inlines = [BeneficiaryInline]
    fieldsets = [
        ('Identity', {'fields': ['member_number', 'first_name', 'last_name', 'gender', 'date_of_birth', 'photo']}),
        ('Contact', {'fields': ['phone', 'email', 'address', 'city', 'state', 'zip_code', 'kebele', 'woreda']}),
        ('Membership', {'fields': ['edir', 'user', 'status', 'join_date', 'exit_date']}),
        ('Emergency Contact', {'fields': ['emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation']}),
        ('Notes', {'fields': ['notes']}),
        ('Timestamps', {'fields': ['created_at', 'updated_at'], 'classes': ['collapse']}),
    ]

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'


@admin.register(MemberApplication)
class MemberApplicationAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'city', 'state', 'status', 'created_at', 'reviewed_by']
    list_filter = ['status', 'city', 'state']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at', 'reviewed_at']
    fieldsets = [
        ('Applicant', {'fields': ['id', 'first_name', 'last_name', 'gender', 'date_of_birth', 'phone', 'email']}),
        ('Address', {'fields': ['address', 'city', 'state', 'zip_code']}),
        ('Representative', {'fields': ['rep_name', 'rep_phone', 'rep_relation']}),
        ('Status', {'fields': ['status', 'edir', 'reviewed_by', 'reviewed_at', 'approval_notes', 'denial_reason']}),
        ('Verification', {'fields': ['residential_verified', 'county_verified']}),
        ('Conversion', {'fields': ['converted_member']}),
        ('Timestamps', {'fields': ['created_at', 'updated_at'], 'classes': ['collapse']}),
    ]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sender', 'recipient', 'message_type', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'archived']
    search_fields = ['subject', 'body']
    readonly_fields = ['created_at', 'read_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'edir', 'year', 'is_public', 'uploaded_by', 'created_at']
    list_filter = ['category', 'is_public', 'year', 'edir']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']


@admin.register(MassMessage)
class MassMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'channel', 'status', 'recipients_count', 'sent_count', 'sent_by', 'created_at']
    list_filter = ['channel', 'status']
    search_fields = ['subject', 'body']
    readonly_fields = ['sent_at', 'created_at', 'recipients_count', 'sent_count', 'failed_count']
